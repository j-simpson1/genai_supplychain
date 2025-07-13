# import environment variables
from dotenv import load_dotenv
_ = load_dotenv()

# standard imports
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List
import operator
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage, ChatMessage

import phoenix as px
from phoenix.otel import register
from openinference.instrumentation.openai import OpenAIInstrumentor
from openinference.semconv.trace import SpanAttributes
from opentelemetry.trace import Status, StatusCode
from openinference.instrumentation import TracerProvider

from FastAPI.core.pdf_creator import save_to_pdf
from FastAPI.core.database_agent_2 import parts_summary, top_5_parts_by_price, top_5_part_distrubution_by_country

import os
import json
from openai import AzureOpenAI

load_dotenv()
pheonix_key = os.getenv("PHOENIX_API_KEY")
pheonix_collector_endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")

# configure the Phoenix tracer
tracer_provider = register(
  project_name="my-llm-app", # Default is 'default'
  auto_instrument=True, # See 'Trace all calls made to a library' below
)
tracer = tracer_provider.get_tracer(__name__)

# setup inmemory sqlite checkpointers
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

conn = sqlite3.connect(":memory:", check_same_thread=False)
memory = SqliteSaver(conn)

# keeping
class AgentState(TypedDict):
    # human input
    task: str
    # plan the planning agent will generate
    plan: str
    # draft of the report
    draft: str
    # critique agent will populate this key
    critique: str
    # documents tavily has come back with
    web_content: List[str]
    # information from the database
    db_content: List[str]
    # keep track of how many times we've gone through the loop
    revision_number: int
    max_revisions: int

from langchain_openai import ChatOpenAI
# creating model
# temperature of 0 will make it very deterministic
model = ChatOpenAI(model="gpt-4o", temperature=0)

# prompt for llm that is going to write out the plan for the essay
PLAN_PROMPT = """You are an expert research analyst tasked with writing a high level outline of an automotive supply \
chain report. Write such an outline for the user provided topic using the sections below. Give an \
outline of the essay along with any relevant notes or instructions for the sections. 

    1. Executive Summary
    2. Introduction
    3. Current Overview
    5. Conclusion and Recommendations
    6. References
    7. Appendices

"""

# writing the essay given the information that was researched
WRITER_PROMPT = """You are a research analyst tasked with writing a report of at least 800 words with a maximum of \
1000 word report. \
Generate the best report possible for the user's request and the initial outline. \
If the user provides critique, respond with a revised version of your previous attempts. \
Provide the output in a JSON format using the structure below. \

{{
      "title": "<Report Title>",
      "sections": [
        {{
          "heading": "<Section Heading>",
          "content": "<Plain text or markdown content>",
          "subsections": [
            {{
              "heading": "<Subsection Heading>",
              "content": "<Plain text or markdown content>"
            }}
          ]
        }}
      ]
    }}

Utilize all the information below as needed: 



------

{content}"""

# control how we are critiqing the draft of the essay
REFLECTION_PROMPT = """You are a manager reviewing the analysts report. \
Generate critique and recommendations for the analysts submission. \
Provide detailed recommendations, including requests for length, depth, style, etc."""

DATABASE_PLAN_INSTRUCTIONS = """ You are a supply chain data analyst with access to several \
database tools. Your role is to extract relevant automotive part insights that will inform a \
detailed written report. Do not hallucinate numbers. Only use tool outputs.
"""

# given a plan will generate a bunch of queries and pass to tavily
RESEARCH_PLAN_PROMPT = """You are a researcher charged with providing information that can \
be used when writing the following essay. Generate a list of search queries that will gather \
any relevant information. Only generate 3 queries max."""

# after we've made the critique will pass the list of queries to pass to tavily
RESEARCH_CRITIQUE_PROMPT = """You are a researcher charged with providing information that can \
be used when making any requested revisions (as outlined below). \
Generate a list of search queries that will gather any relevant information. Only generate 3 queries max."""

# for generating a list of queries to pass to tavily will use function calling so we get a list of strings
# from tavily
from pydantic import BaseModel

class ResearchQueries(BaseModel):
    queries: List[str]

class DBQueries(BaseModel):
    queries: List[str]

# importing taviliy as using it in a slightly unconventional way
from tavily import TavilyClient
import os
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# take in the state and create list of messages, one of them is going to be the planning prompt
# then create a human message which is what we want system to do
@tracer.chain
def plan_node(state: AgentState):
    messages = [
        SystemMessage(content=PLAN_PROMPT),
        HumanMessage(content=state['task'])
    ]
    # pass these messages to the model
    response = model.invoke(messages)
    # get the content of the messages and pass to the plan key
    return {"plan": response.content}

@tracer.chain
def database_plan_node(state: AgentState):

    client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-05-01-preview"
    )

    tools = [
        {
            "type": "function",
            "function": {
                "name": "parts_summary",
                "description": "Summarizes product groups by price, count, and origin.",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "top_5_parts_by_price",
                "description": "Top 5 product groups by average price.",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "top_5_part_distrubution_by_country",
                "description": "Top 5 countries by part distribution.",
                "parameters": {"type": "object", "properties": {}, "required": []}
            }
        }
    ]

    available_functions = {
        "parts_summary": parts_summary,
        "top_5_parts_by_price": top_5_parts_by_price,
        "top_5_part_distrubution_by_country": top_5_part_distrubution_by_country
    }

    assistant = client.beta.assistants.create(
        name="DB Assistant",
        instructions=DATABASE_PLAN_INSTRUCTIONS,
        tools=tools,
        model="gpt-4o"
    )

    thread = client.beta.threads.create()

    # Responses API: create_and_poll
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant.id,
        instructions=state["task"],
        tool_choice="auto"
    )

    # If the assistant called tools, handle it
    if run.status == "requires_action":
        tool_outputs = []
        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
            fn = available_functions.get(tool_call.function.name)
            args = json.loads(tool_call.function.arguments)
            output = fn(**args) if args else fn()
            tool_outputs.append({
                "tool_call_id": tool_call.id,
                "output": json.dumps(output)
            })

        # Submit outputs and get final result
        run = client.beta.threads.runs.submit_tool_outputs_and_poll(
            thread_id=thread.id,
            run_id=run.id,
            tool_outputs=tool_outputs
        )

    # Fetch the final response from the thread
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    final_message = messages.data[0].content[0].text.value

    return {"db_content": state.get("db_content", []) + [final_message]}

# takes in the plan and does some research
@tracer.chain
def research_plan_node(state: AgentState):
    # response with what we will invoke this with is the
    # response will be pydantic model which has the list of queries
    queries = model.with_structured_output(ResearchQueries).invoke([
        # researching planning prompt and planning prompt
        SystemMessage(content=RESEARCH_PLAN_PROMPT),
        HumanMessage(content=state['task'])
    ])
    # original content
    content = state['web_content'] or []
    # loop over the queries and search for them in Tavily
    for q in queries.queries:
        with tracer.start_as_current_span(
                "TavilySearch",
                openinference_span_kind="tool",
                attributes={"query": q}
        ) as span:
            span.set_input(value=q)
            response = tavily.search(query=q, max_results=2)
            span.set_output(value=response)
            for r in response['results']:
                # get the list of results and append them to the content
                content.append(r['content'])
    # return the content key which is equal to the original content plus the accumulated content
    return {"web_content": content}

@tracer.chain
def generation_node(state: AgentState):
    # prepare the content - list of strings and join them into one big one
    db = "\n\n".join(state.get("db_content", []))
    web = "\n\n".join(state.get("web_content", []))
    combined = f"# Database Insights:\n\n{db}\n\n---\n\n# Web Research:\n\n{web}"
    # create user message which combines the task and the plan
    user_message = HumanMessage(
        # task and plan
        content=f"{state['task']}\n\nHere is my plan:\n\n{state['plan']}")
    messages = [
        # format in documents which has been fetched
        SystemMessage(
            content=WRITER_PROMPT.format(content=combined)
        ),
        # task and the plan
        user_message
        ]
    response = model.invoke(messages)
    return {
        # update the draft with response and add 1 to the current revision number in the state
        "draft": response.content,
        "revision_number": state.get("revision_number", 1) + 1
    }

@tracer.chain
def reflection_node(state: AgentState):
    messages = [
        # take the reflection node and the draft
        SystemMessage(content=REFLECTION_PROMPT),
        HumanMessage(content=state['draft'])
    ]
    response = model.invoke(messages)
    # going to generate the critique
    return {"critique": response.content}

@tracer.chain
def research_critique_node(state: AgentState):
    queries = model.with_structured_output(ResearchQueries).invoke([
        SystemMessage(content=RESEARCH_CRITIQUE_PROMPT),
        HumanMessage(content=state['critique'])
    ])
    # get the original content and append with new queries
    content = state['web_content'] or []
    for q in queries.queries:
        with tracer.start_as_current_span(
                "TavilySearch",
                openinference_span_kind="tool",
                attributes={"query": q}
        ) as span:
            span.set_input(value=q)
            response = tavily.search(query=q, max_results=2)
            span.set_output(value=response)
            for r in response['results']:
                content.append(r['content'])
    return {"web_content": content}

# look at the revision number - if greater than the max revisions will then end.
def should_continue(state):
    with tracer.start_as_current_span(
            "ShouldContinueCheck",
            openinference_span_kind="chain"
    ) as span:
        span.set_input(value=state)
        if state["revision_number"] > state["max_revisions"]:
            save_to_pdf(content=state["draft"], filename="report.pdf")
            result = END
        else:
            result = "reflect"
        span.set_output(value=result)
        return result

# initialise the graph with the agent state
builder = StateGraph(AgentState)

# add all nodes
builder.add_node("planner", plan_node)
builder.add_node("generate", generation_node)
builder.add_node("reflect", reflection_node)
builder.add_node("research_plan", research_plan_node)
builder.add_node("db_plan", database_plan_node)
builder.add_node("research_critique", research_critique_node)

# set entry point
builder.set_entry_point("planner")

# add conditional edge
builder.add_conditional_edges(
    "generate",
    should_continue,
    {END: END, "reflect": "reflect"}
)

# add in basic edges
builder.add_edge("planner", "db_plan")
builder.add_edge("db_plan", "research_plan")
builder.add_edge("research_plan", "generate")

builder.add_edge("reflect", "research_critique")
builder.add_edge("research_critique", "generate")

# compile graph and add in checkpointer
graph = builder.compile(checkpointer=memory)

# from IPython.display import Image
#
# Image(graph.get_graph().draw_png())

# save the graph
output_graph_path = "graph.png"
with open(output_graph_path, "wb") as f:
    f.write(graph.get_graph().draw_mermaid_png())


def run_agent(messages):
    with (tracer.start_as_current_span(
            "LangGraphExecution",
            openinference_span_kind="chain")
    as span):
        span.set_input(value=messages)

        # adding in graph.stream so can see all the steps
        thread = {"configurable": {"thread_id": "1"}}
        for s in graph.stream({
            'task': messages,
            "max_revisions": 2,
            "revision_number": 1,
            "db_content": [],
            "web_content": [],
        }, thread):
            print(s)
        span.set_status(StatusCode.OK)


# start from the outermost layer and work your way down so you capture the right info
# only just calling this run_agent span and calls to add tracing
def start_main_span(messages):
    print("Starting main span with messages:", messages)

    # span_kind maps to colors etc...
    # anything in the with cause block will be treated as part of that span
    with tracer.start_as_current_span(
            "AgentRun", openinference_span_kind="agent"
    ) as span:
        # setting the input
        span.set_input(value=messages)
        ret = run_agent(messages)
        print("Main span completed with return value:", ret)
        # setting the output
        span.set_output(value=ret)
        # set status call - called correctly
        span.set_status(StatusCode.OK)
        return ret

start_main_span("Write me a report on the supply chain of the Toyota RAV4 braking system")


