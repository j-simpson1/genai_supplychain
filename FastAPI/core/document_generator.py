from dotenv import load_dotenv
load_dotenv()

import matplotlib
matplotlib.use("Agg")

import os
import json
import tempfile
import pandas as pd
import re
import asyncio

from langgraph.graph import StateGraph, END
from typing import List
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import Client

from tavily import TavilyClient

from FastAPI.document_builders.pdf_creator import save_to_pdf
from FastAPI.document_builders.word_creator import save_to_word
from FastAPI.core.CoT_prompting import chain_of_thought_examples
from FastAPI.core.prompts import plan_prompt, research_plan_prompt, reflection_prompt, writers_prompt, chart_planning_prompt
from FastAPI.core.code_editor_agent import code_editor_agent
from FastAPI.core.database_agent import database_agent
from FastAPI.core.simulation_agent import simulation_agent
from FastAPI.core.state import AgentState

from FastAPI.automotive_simulation.simulation import analyze_tariff_impact
from FastAPI.core.utils import convert_numpy, serialize_state
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
model = ChatOpenAI(model="o4-mini")

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

# importing taviliy as using it in a slightly unconventional way
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

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

def chart_planning_node(state: AgentState):
    """
    Decides what charts to generate based on DB summary & content.
    Returns `chart_plan` for the next node to consume.
    """
    db_summary = state.get("db_summary", "")
    db_content = "\n\n".join(str(msg.content) for msg in state.get("db_content", []))

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

def generation_node(state: AgentState):
    db = state.get("db_summary", "")
    web = "\n\n".join(state.get("web_content", []))
    chart_metadata = state.get("chart_metadata", [])
    simulation_messages = state.get("clean_simulation", [])

    charts = "\n\n".join(
        [f"\n[[FIGURE:{item['id']}]]" for item in chart_metadata])

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
        SystemMessage(content=reflection_prompt),
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
        print(save_to_pdf(content=state["draft"], filename="../reports_and_graphs/report.pdf", chart_metadata=state.get("chart_metadata", [])))
        print(save_to_word(content=state["draft"], filename="../reports_and_graphs/report.docx", chart_metadata=state.get("chart_metadata", [])))
        result = END
    else:
        result = "reflect"
    return result

def simulation_should_continue(state: AgentState):
    messages = state.get("raw_simulation", [])
    if not messages:
        return "end"
    last = messages[-1]
    tool_calls = getattr(last, "tool_calls", None)
    return "continue" if tool_calls else "end"

# initialise the graph with the agent state
builder = StateGraph(AgentState)

# add all nodes
builder.add_node("planner", plan_node)
builder.add_node("db_agent", database_agent)
builder.add_node("chart_planning_node", chart_planning_node)
builder.add_node("generate_charts", code_editor_agent)
builder.add_node("simulation", simulation_agent)
builder.add_node("generate", generation_node)
builder.add_node("reflect", reflection_node)
builder.add_node("research_plan", research_plan_node)
builder.add_node("research_critique", research_critique_node)

# set entry point
builder.set_entry_point("planner")


# add in basic edges
builder.add_edge("planner", "db_agent")
builder.add_edge("db_agent", "chart_planning_node")
builder.add_edge("chart_planning_node", "generate_charts")
builder.add_edge("generate_charts", "research_plan")
builder.add_edge("research_plan", "simulation")
builder.add_edge("simulation", "generate")
builder.add_edge("reflect", "research_critique")
builder.add_edge("research_critique", "generate")


# add conditional edge
builder.add_conditional_edges(
    "generate",
    should_continue,
    {END: END, "reflect": "reflect"}
)

async def run_agent(messages, parts_path, articles_path):
    # Initialize the async checkpointer
    async with AsyncSqliteSaver.from_conn_string(":memory:") as checkpointer:
        # compile graph and add in checkpointer
        graph = builder.compile(checkpointer=checkpointer)

        # save the graph
        output_graph_path = "../reports_and_graphs/langgraph.png"
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
        },
            config={
                "recursion_limit": 100,
                "configurable": {"thread_id": "1"}
            },
        ):
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
    parts_path = os.path.join(BASE_DIR, "Toyota_RAV4_brake_corrupted_data/RAV4_brake_parts_data.csv")
    articles_path = os.path.join(BASE_DIR, "Toyota_RAV4_brake_corrupted_data/RAV4_brake_articles_data.csv")

    print(prompt)
    asyncio.run(run_agent(prompt, parts_path, articles_path))

    print("Done! Check results in LangSmith dashboard.")
