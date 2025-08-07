from dotenv import load_dotenv
load_dotenv()

import matplotlib
matplotlib.use("Agg")

import os
import json
import uuid
import traceback
import tempfile
import pandas as pd
import re
import asyncio

from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Annotated, Sequence, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AnyMessage
from langgraph.graph.message import add_messages
from langsmith import evaluate, Client
from langchain_core.messages import BaseMessage
from langgraph.prebuilt import ToolNode

from tavily import TavilyClient

from FastAPI.core.pdf_creator import save_to_pdf
from FastAPI.core.word_creator import save_to_word
from FastAPI.core.database_agent_3 import parts_summary, top_5_parts_by_price, top_5_part_distribution_by_country, parts_average_price, total_component_price
from FastAPI.core.evals import report_quality_evaluator
from FastAPI.core.utils import get_last_tool_result
from FastAPI.open_deep_research.deep_researcher import deep_researcher
from FastAPI.core.CoT_prompting import chain_of_thought_examples
from FastAPI.core.prompts import plan_prompt, research_plan_prompt
from FastAPI.core.state import AgentState

from FastAPI.automotive_simulation.simulation import analyze_tariff_impact
from FastAPI.core.utils import summarize_simulation_content, convert_numpy, serialize_state
from langchain.agents import tool

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
CHARTS_DIR = os.path.join(PROJECT_ROOT, "FastAPI", "core", "charts")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "FastAPI", "reports_and_graphs")
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

client = Client()

# setup inmemory sqlite checkpointers
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

async def get_checkpointer():
    return AsyncSqliteSaver.from_conn_string(":memory:")

# We'll initialize this in the run_agent function
memory = None

from langchain_openai import ChatOpenAI

# creating model
# temperature not supported by o4-mini
model = ChatOpenAI(model="gpt-4o", temperature=0.3)

# control how we are critiqing the draft of the essay
REFLECTION_PROMPT = """You are a manager reviewing the analysts report. \
Generate critique and recommendations for the analysts submission. \
Provide detailed recommendations, including requests for length, depth, style, etc."""

DATABASE_PLAN_INSTRUCTIONS = """ You are a supply chain data analyst with access to several \
database tools. Your role is to extract relevant automotive part insights that will inform a \
detailed written report. Do not hallucinate numbers. Only use tool outputs. Pick tools one at a time, \
picking the most appropriate tool.
"""

# given a plan will generate a bunch of queries and pass to tavily
RESEARCH_PLAN_PROMPT = """You are a researcher charged with providing information that can \
be used when writing the following essay. Generate a list of search queries that will gather \
any relevant information. Only generate 4 queries max."""
# RESEARCH_PLAN_PROMPT = """You are a research analyst charged with providing information that can \
# be used when writing the following supply chain report. Generate a detailed deep search query (50 words max) which \
# can be used as input into a deep search agent. Your query can contain multiple areas of research and the deep search \
# agent will be able to break these areas down and handle them individually. Can your ask for the response to be a \
# maximum of 800 words."""

# after we've made the critique will pass the list of queries to pass to tavily
RESEARCH_CRITIQUE_PROMPT = """You are a researcher charged with providing information that can \
be used when making any requested revisions (as outlined below). \
Generate a list of search queries that will gather any relevant information. Only generate 4 queries max."""
# RESEARCH_CRITIQUE_PROMPT = """You are a research analyst charged with providing information that can \
# be used when making any requested revisions (as outlined below). Generate a detailed deep search query \
# (50 words max) which can be used as input into a deep search agent. Your query can contain multiple areas of \
# research and the deep search agent will be able to break these areas down and handle them individually. Can your ask \
# for the response to be a maximum of 800 words."""

# for generating a list of queries to pass to tavily will use function calling so we get a list of strings
# from tavily

class ResearchQueries(BaseModel):
    queries: List[str]

class DBQueries(BaseModel):
    queries: List[str]

class SimulationResultsInput(BaseModel):
    simulation_result: dict

class simulation_inputs(BaseModel):
    target_country: str = Field(..., description="Country to simulate tariff shock for")
    tariff_rates: List[int] = Field(description="tariff rates to use in the tariff shock simulation.")

# importing taviliy as using it in a slightly unconventional way
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

@tool(args_schema=simulation_inputs)
def automotive_tariff_simulation(target_country: str, tariff_rates: List[float]) -> dict:
    """
    Run an automotive simulation on the component/vehicle showing the impact of tariff shocks of a certain country
    on the component/vehicle.

    Accepts either decimals (e.g., 0.1 for 10%) or integers (e.g., 10 for 10%) and normalizes all to decimals.
    """
    # Normalize rates: if any rate > 1, treat it as a percentage (e.g., 10 becomes 0.10)
    normalized_rates = [
        r / 100 if r > 1 else r
        for r in tariff_rates
    ]

    response = analyze_tariff_impact(target_country, normalized_rates)
    return convert_numpy(response)

simulation_analysis_model = ChatOpenAI(model="gpt-4o")

# take in the state and create list of messages, one of them is going to be the planning prompt
# then create a human message which is what we want system to do
def plan_node(state: AgentState):
    messages = [
        SystemMessage(content=plan_prompt),
        HumanMessage(content=state['task'])
    ]
    # pass these messages to the model
    response = model.invoke(messages)
    # get the content of the messages and pass to the plan key
    return {"plan": response.content}


tools = [
    parts_summary,
    top_5_parts_by_price,
    top_5_part_distribution_by_country,
    parts_average_price,
    total_component_price
]

db_model = ChatOpenAI(
    model="gpt-4o",
    temperature=0
).bind_tools(tools)

tools_by_name = {tool.name: tool for tool in tools}

# --- Tool Node ---
def tool_node(state: AgentState):
    outputs = []
    last_message = state["db_content"][-1]
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        args = dict(tool_call["args"])
        # Inject paths
        args["articles_path"] = state["articles_path"]
        args["parts_path"] = state["parts_path"]

        if tool_name not in tools_by_name:
            result = "Unknown tool, please retry."
        else:
            result = tools_by_name[tool_name].invoke(args)

        outputs.append(ToolMessage(
            content=json.dumps(result),
            name=tool_name,
            tool_call_id=tool_call["id"]
        ))
    return {"db_content": state["db_content"] + outputs}

# --- Model Node ---
def call_model(state: AgentState, config=None):
    system_prompt = SystemMessage(content=f"""
    You are a database assistant helping with the drafting of an automotive supply chain report. Use the available tools 
    to retrieve the relevant data for the report.
    The file paths required by the tools are available from state:
    - articles_path - path to the articles CSV file
    - parts_path - path to the parts CSV file
    
    Just return a summary of the raw data from the tools.
    
    See the following report plan to guide you what data to extract:
    {state.get('plan', 'No plan provided')}
    """)
    response = db_model.invoke([system_prompt] + state["db_content"], config)
    return {"db_content": state["db_content"] + [response]}

def summarize_db_node(state: AgentState):
    db_content_text = "\n\n".join(str(msg.content) for msg in state.get("db_content", []))
    response = model.invoke([
        SystemMessage(content="Analyse the data from the database agent and provide additional insight."
                              "All the data is in GBP (£). "
                              "Be succinct, don't speculate, only use the information provided and make the "
                              "analysis quantative:"),
        HumanMessage(content=db_content_text)
    ])

    return {
        "db_summary": response.content
    }

# takes in the plan and does some research
async def research_plan_node(state: AgentState):

    # using Tavily by creating a finite list of queries
    # response with what we will invoke this with is the
    # response will be pydantic model which has the list of queries
    queries = model.with_structured_output(ResearchQueries).invoke([
        # researching planning prompt and planning prompt
        SystemMessage(content=research_plan_prompt),
        HumanMessage(content=state['task'])
    ])
    # original content
    content = state['web_content'] or []
    # loop over the queries and search for them in Tavily
    for q in queries.queries:
        response = tavily.search(query=q, max_results=2)
        for r in response['results']:
            # get the list of results and append them to the content
            content.append(f"Source: {r['url']}\n{r['content']}")
    # return the content key which is equal to the original content plus the accumulated content


    # # using open-deep-research
    # query = await model.ainvoke([
    #     SystemMessage(content=RESEARCH_PLAN_PROMPT),
    #     HumanMessage(content=state['task'])
    # ])
    # # original content
    # content = state['web_content'] or []
    #
    # response = await deep_researcher.ainvoke({
    #     "messages": [HumanMessage(content=query.content)],
    # })
    #
    # output = response['messages'][-1].content
    # print(output)
    #
    # content.append(output)

    return {"web_content": content}

model_with_tools = model.bind_tools([automotive_tariff_simulation])

def chart_planning_node(state: AgentState):
    """
    Decides what charts to generate based on DB summary & content.
    Returns `chart_plan` for the next node to consume.
    """
    db_summary = state.get("db_summary", "")
    db_content = "\n\n".join(str(msg.content) for msg in state.get("db_content", []))

    chart_planning_prompt = client.pull_prompt("chart_planning_prompt", include_model=False)

    formatted_chart_planning_prompt = chart_planning_prompt.format(
        db_summary=db_summary,
        db_content=db_content
    )

    response = model.invoke([SystemMessage(content=formatted_chart_planning_prompt)])

    raw = response.content.strip()

    # Remove ```json or ``` from start/end if present
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"```$", "", raw).strip()

    try:
        chart_plan = json.loads(raw)
        if isinstance(chart_plan, dict):
            chart_plan = [chart_plan]  # wrap single dict as list
    except json.JSONDecodeError:
        chart_plan = [{"chart_id": "chart1", "chart_description": raw}]

    return {"chart_plan": chart_plan}

def generate_chart_code_node(state: AgentState):

    # Determine which chart we are working on
    chart_index = state.get("current_chart_index", 0)
    chart_plan = state.get("chart_plan", [])

    if chart_index >= len(chart_plan):
        # No charts left to process
        return {"chart_code": "", "chart_generation_success": True}

    chart = chart_plan[chart_index]
    chart_description = chart.get("chart_description", "No description")

    tool_data = "\n\n".join(
        msg.content for msg in state['db_content'] if isinstance(msg, ToolMessage)
    )

    GENERATE_CHART_PROMPT = client.pull_prompt("generate_chart_prompt", include_model=False)
    FORMATTED_GENERATE_CHART_PROMPT = GENERATE_CHART_PROMPT.format(
        chart_description=chart_description,
        tool_data=tool_data
    )

    response = model.invoke([SystemMessage(content=FORMATTED_GENERATE_CHART_PROMPT)])
    match = re.search(r"```(?:python)?\n(.*?)```", response.content, re.DOTALL)
    chart_code = match.group(1).strip() if match else response.content.strip()

    return {"chart_code": chart_code}

def execute_chart_code_node(state: AgentState):
    try:
        code = state["chart_code"]

        # Get chart info
        chart_index = state.get("current_chart_index", 0)
        chart_plan = state.get("chart_plan", [])
        chart_id = chart_plan[chart_index]["chart_id"] if chart_index < len(chart_plan) else f"chart_{chart_index}"

        chart_path = os.path.join(CHARTS_DIR, f"{chart_id}_{uuid.uuid4().hex}.png")
        exec_globals = {"__file__": chart_path, "chart_path": chart_path}
        exec(code, exec_globals)

        # Append to chart_metadata
        chart_metadata = state.get("chart_metadata", [])
        chart_metadata.append({"id": chart_id, "path": chart_path})

        return {
            "chart_metadata": chart_metadata,
            "chart_generation_success": True,
            "current_chart_index": chart_index + 1,
            "chart_retry_count": 0
        }
    except Exception as e:
        return {
            "chart_generation_success": False,
            "chart_generation_error": traceback.format_exc(),
            "chart_code": state["chart_code"]
        }


def reflect_chart_node(state: AgentState):
    # If previous execution failed → fix code
    if not state.get("chart_generation_success", False):
        error = state.get("chart_generation_error", "")
        previous_code = state.get("chart_code", "")

        prompt = f"""The previous chart code failed with this error:
{error}

Here is the failed code:
{previous_code}

Please revise the code so it avoids the error and still meets the requirements.
"""
        response = model.invoke([SystemMessage(content=prompt)])
        return {
            "chart_code": response.content,
            "chart_retry_count": state.get("chart_retry_count", 0) + 1,
            "chart_generation_success": False,
            "chart_generation_error": ""
        }

    # If successful (but still more charts), just continue
    return {}


simulation_tools = [automotive_tariff_simulation]


def simulation_tool_node(state: AgentState):
    """
    Enhanced tool node that handles both automotive_tariff_simulation and simulation_results_analyst
    """
    outputs = []
    messages = state.get("raw_simulation", [])
    if not messages:
        return {"raw_simulation": []}

    last_message = messages[-1]
    chart_metadata = list(state.get("chart_metadata", []))

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            args = tool_call["args"]
            tool_call_id = tool_call["id"]

            if tool_name == "automotive_tariff_simulation":
                # Execute the tariff simulation tool
                result = automotive_tariff_simulation.invoke(args)

                # Extract chart metadata from simulation results
                if "output_files" in result and "chart_paths" in result["output_files"]:
                    chart_paths = result["output_files"]["chart_paths"]
                    for chart_id, chart_path in chart_paths.items():
                        chart_id_clean = os.path.splitext(os.path.basename(chart_path))[0]
                        existing_paths = [meta["path"] for meta in chart_metadata]
                        if chart_path not in existing_paths:
                            chart_metadata.append({
                                "id": chart_id_clean,
                                "path": chart_path
                            })

                # Create the tool message with full result
                outputs.append(ToolMessage(
                    content=json.dumps(result),
                    name=tool_name,
                    tool_call_id=tool_call_id
                ))
            else:
                # Handle unknown tools
                outputs.append(ToolMessage(
                    content="Unknown tool",
                    name=tool_name,
                    tool_call_id=tool_call_id
                ))

    return {
        "raw_simulation": messages + outputs,
        "chart_metadata": chart_metadata
    }

# Your model with tools bound
simulation_model = ChatOpenAI(model="gpt-4o").bind_tools(simulation_tools)

def simulation_model_call(state: AgentState):
    system_prompt = SystemMessage(content=(
        "You are a professional supply chain analyst. "
        "When asked for a tariff shock simulation, you must call the automotive_tariff_simulation tool "
        "with the appropriate parameters before answering. Make sure to call automotive_tariff_simulation before the "
        "simulation_results_analyst tool."
    ))
    task_message = HumanMessage(content=state['task'])

    response = simulation_model.invoke([system_prompt, task_message] + state["raw_simulation"])
    return {"raw_simulation": [response]}

def simulation_clean(state: AgentState):

    system_prompt = SystemMessage(content=(
        """
        All above messages are from a supply chain simulation tool. Please clean up these findings.
        DO NOT summarize the information. Return the raw information, just in a cleaner format. 
        Make sure all relevant information is preserved - you can rewrite findings verbatim.
        """
    ))

    response = model.invoke([
        system_prompt,
        HumanMessage(content="\n\n".join(str(m.content) for m in state['raw_simulation']))
    ])

    return {"clean_simulation": response}

def generation_node(state: AgentState):
    db = state.get("db_summary", "")
    web = "\n\n".join(state.get("web_content", []))
    chart_metadata = state.get("chart_metadata", [])
    simulation_messages = state.get("clean_simulation", [])

    charts = "\n\n".join(
        [f"Include these charts in the report: \n[[FIGURE:{item['id']}]]" for item in chart_metadata])

    writers_prompt = client.pull_prompt("writer_prompt", include_model=False)
    formatted_writers_prompt = writers_prompt.format(
        CoT_examples=chain_of_thought_examples,
        task=state['task'],
        plan=state['plan'],
        db=db,
        web=web,
        charts=charts,
        simulation=simulation_messages
    )

    initial_response = model.invoke(formatted_writers_prompt)

    return {
        "draft": initial_response.content,
        "revision_number": state.get("revision_number", 1) + 1
    }

def reflection_node(state: AgentState):
    messages = [
        # take the reflection node and the draft
        SystemMessage(content=REFLECTION_PROMPT),
        HumanMessage(content=state['draft'])
    ]
    response = model.invoke(messages)
    # going to generate the critique
    return {"critique": response.content}

async def research_critique_node(state: AgentState):

    # creating a list of tavily queries
    queries = model.with_structured_output(ResearchQueries).invoke([
        SystemMessage(content=RESEARCH_CRITIQUE_PROMPT),
        HumanMessage(content=state['critique'])
    ])
    # get the original content and append with new queries
    content = state['web_content'] or []
    for q in queries.queries:
        response = tavily.search(query=q, max_results=2)
        for r in response['results']:
            content.append(r['content'])

    # # using open-deep-research
    # query = await model.ainvoke([
    #     SystemMessage(content=RESEARCH_CRITIQUE_PROMPT),
    #     HumanMessage(content=state['critique'])
    # ])
    # # get the original content and append with new queries
    # content = state['web_content'] or []
    #
    # response = await deep_researcher.ainvoke({
    #     "messages": [HumanMessage(content=query.content)],
    # })
    #
    # output = response['messages'][-1].content
    # content.append(output)

    return {"web_content": content}

# look at the revision number - if greater than the max revisions will then end.
def should_continue(state):
    if state["revision_number"] > state["max_revisions"]:
        print(save_to_pdf(content=state["draft"], filename="report.pdf", chart_metadata=state.get("chart_metadata", [])))
        print(save_to_word(content=state["draft"], filename="report.docx", chart_metadata=state.get("chart_metadata", [])))
        result = END
    else:
        result = "reflect"
    return result

def simulation_should_continue(state: AgentState):
    messages = state["raw_simulation"]
    last_message = messages[-1]
    if not last_message.tool_calls:
        return "end"
    else:
        return "continue"

def execute_chart_next_node(state: AgentState) -> str:
    if state.get("chart_generation_success", False):
        # Was successful – check if more charts left
        if state.get("current_chart_index", 0) >= len(state.get("chart_plan", [])):
            return "research_plan"
        else:
            return "reflect_chart"
    else:
        # Failed, need to reflect
        return "reflect_chart"

def db_should_continue(state: AgentState):
    last_message = state["db_content"][-1]
    return "continue" if last_message.tool_calls else "end"

# initialise the graph with the agent state
builder = StateGraph(AgentState)

# add all nodes
builder.add_node("planner", plan_node)
builder.add_node("db_agent", call_model)
builder.add_node("db_tools", tool_node)
builder.add_node("summarize_db", summarize_db_node)
builder.add_node("chart_planning_node", chart_planning_node)
builder.add_node("generate_chart_code", generate_chart_code_node)
builder.add_node("execute_chart_code", execute_chart_code_node)
builder.add_node("reflect_chart", reflect_chart_node)
builder.add_node("simulation_agent", simulation_model_call)
builder.add_node("simulation_tools", simulation_tool_node)
builder.add_node("simulation_clean", simulation_clean)
builder.add_node("generate", generation_node)
builder.add_node("reflect", reflection_node)
builder.add_node("research_plan", research_plan_node)
builder.add_node("research_critique", research_critique_node)

# set entry point
builder.set_entry_point("planner")


# add in basic edges
builder.add_edge("planner", "db_agent")
builder.add_edge("db_tools", "db_agent")
builder.add_edge("summarize_db", "chart_planning_node")
builder.add_edge("chart_planning_node", "generate_chart_code")
builder.add_edge("generate_chart_code", "execute_chart_code")
builder.add_edge("reflect_chart", "generate_chart_code")
builder.add_edge("research_plan", "simulation_agent")
builder.add_edge("simulation_tools", "simulation_agent")
builder.add_edge("simulation_clean", "generate")
builder.add_edge("reflect", "research_critique")
builder.add_edge("research_critique", "generate")

builder.add_conditional_edges(
    "db_agent",
    db_should_continue,
    {
        "continue": "db_tools",
        "end": "summarize_db"
    }
)

builder.add_conditional_edges(
    "execute_chart_code",
    execute_chart_next_node,
    {
        "reflect_chart": "reflect_chart",
        "research_plan": "research_plan"
    }
)

# add conditional edge
builder.add_conditional_edges(
    "generate",
    should_continue,
    {END: END, "reflect": "reflect"}
)

builder.add_conditional_edges(
    "simulation_agent",
    simulation_should_continue,
    {
        "continue": "simulation_tools",
        "end": "simulation_clean",
    },
)

async def run_agent(messages, parts_path, articles_path):
    # Initialize the async checkpointer
    async with AsyncSqliteSaver.from_conn_string(":memory:") as checkpointer:
        # compile graph and add in checkpointer
        graph = builder.compile(checkpointer=checkpointer)

        # save the graph
        output_graph_path = "langgraph.png"
        with open(output_graph_path, "wb") as f:
            f.write(graph.get_graph().draw_mermaid_png())

        final_state = {}

        # adding in graph.astream so can see all the steps
        thread = {"configurable": {"thread_id": "1"}}
        async for s in graph.astream({
            'task': messages,
            'max_revisions': 2,
            'revision_number': 1,
            'db_content': [],
            'web_content': [],
            'raw_simulation': [],
            'clean_simulation': '',
            'chart_metadata': [],
            'plan': '',
            'draft': '',
            'critique': '',
            'chart_code': '',
            'chart_generation_success': False,
            'chart_generation_error': '',
            'chart_retry_count': 0,
            'max_chart_retries': 2,
            'chart_plan': [],
            'current_chart_index': 0,
            'articles_path': articles_path,
            'parts_path': parts_path,
            'messages': [],
            'remaining_steps': 5
        }, thread):
            print(s)

            final_state = s

        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        SAVE_PATH = os.path.join(BASE_DIR, "streamlit_data/ai_supplychain_state.json")

        with open(SAVE_PATH, "w") as f:
            json.dump(serialize_state(final_state), f, indent=2)

        return serialize_state(final_state)


def auto_supplychain_prompt_template(manufacturer, model, component, tariff_shock_country, rates, vat_rate, manufacturing_country):
    rates_str = ", ".join(f"{r}%" for r in rates)
    return (
        f"Write me a report on the supply chain of the {manufacturer} {model} {component}. "
        f"Include a tariff shock simulation for {tariff_shock_country} with rates of {rates_str}.\n"
        f"Assume the following:\n"
        f" - VAT Rate: {vat_rate}%\n"
        f" - Manufacturing country: {manufacturing_country}"
    )

prompt = auto_supplychain_prompt_template(
    manufacturer="Toyota",
    model="RAV4",
    component="braking system",
    tariff_shock_country="Japan",
    rates=[20, 50, 80],
    vat_rate=20,
    manufacturing_country="United Kingdom"
)

async def target(inputs: dict) -> dict:
    prompt = auto_supplychain_prompt_template(
        manufacturer=inputs["setup"]["manufacturer"],
        model=inputs["setup"]["model"],
        component=inputs["setup"]["component"],
        tariff_shock_country=inputs["setup"]["country"],
        rates=inputs["setup"]["rates"]
    )

    parts_order = [
        "productGroupId",
        "partDescription",
        "quantity",
        "taxable"
    ]

    parts = inputs["parts"]
    parts_df = pd.DataFrame(parts)
    parts_df = parts_df[parts_order]

    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as parts_tmp_file:
        parts_df.to_csv(parts_tmp_file.name, index=False)
        print(f"Temporary CSV file created: {parts_tmp_file.name}")

    articles_order = [
        "productGroupId",
        "articleNo",
        "articleProductName",
        "price",
        "countryOfOrigin",
        "supplierId",
        "supplierName"
    ]

    articles = inputs["articles"]
    articles_df = pd.DataFrame(articles)
    articles_df = articles_df[articles_order]

    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as articles_tmp_file:
        articles_df.to_csv(articles_tmp_file.name, index=False)
        print(f"Temporary CSV file created: {articles_tmp_file.name}")

    final_state = await run_agent(prompt, parts_tmp_file.name, articles_tmp_file.name)
    draft = final_state.get("generate", {}).get("draft", "")

    return {"draft": draft}


if __name__ == "__main__":

    # dataset_name = "Toyota RAV4 Brake System"
    #
    # results = evaluate(
    #     target,
    #     data=dataset_name,
    #     evaluators=[report_quality_evaluator],
    #     experiment_prefix = "Toyota RAV4 Brake System experiment"
    # )

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    parts_path = os.path.join(BASE_DIR, "Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")
    articles_path = os.path.join(BASE_DIR, "Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")

    print(prompt)
    asyncio.run(run_agent(prompt, parts_path, articles_path))

    print("Done! Check results in LangSmith dashboard.")
