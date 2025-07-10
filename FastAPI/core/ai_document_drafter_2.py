# import environment variables
from dotenv import load_dotenv
_ = load_dotenv()

# standard imports
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List
import operator
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage, ChatMessage


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
    content: List[str]
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
WRITER_PROMPT = """You are a research analyst tasked with writing an 800 word report\
Generate the best report possible for the user's request and the initial outline. \
If the user provides critique, respond with a revised version of your previous attempts. \
Utilize all the information below as needed: 



------

{content}"""

# control how we are critiqing the draft of the essay
REFLECTION_PROMPT = """You are a manager reviewing the analysts report. \
Generate critique and recommendations for the analysts submission. \
Provide detailed recommendations, including requests for length, depth, style, etc."""

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

class Queries(BaseModel):
    queries: List[str]

# importing taviliy as using it in a slightly unconventional way
from tavily import TavilyClient
import os
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# take in the state and create list of messages, one of them is going to be the planning prompt
# then create a human message which is what we want system to do
def plan_node(state: AgentState):
    messages = [
        SystemMessage(content=PLAN_PROMPT),
        HumanMessage(content=state['task'])
    ]
    # pass these messages to the model
    response = model.invoke(messages)
    # get the content of the messages and pass to the plan key
    return {"plan": response.content}

# takes in the plan and does some research
def research_plan_node(state: AgentState):
    # response with what we will invoke this with is the
    # response will be pydantic model which has the list of queries
    queries = model.with_structured_output(Queries).invoke([
        # researching planning prompt and planning prompt
        SystemMessage(content=RESEARCH_PLAN_PROMPT),
        HumanMessage(content=state['task'])
    ])
    # original content
    content = state['content'] or []
    # loop over the queries and search for them in Tavily
    for q in queries.queries:
        response = tavily.search(query=q, max_results=2)
        for r in response['results']:
            # get the list of results and append them to the content
            content.append(r['content'])
    # return the content key which is equal to the original content plus the accumulated content
    return {"content": content}

def generation_node(state: AgentState):
    # prepare the content - list of strings and join them into one big one
    content = "\n\n".join(state['content'] or [])
    # create user message which combines the task and the plan
    user_message = HumanMessage(
        # task and plan
        content=f"{state['task']}\n\nHere is my plan:\n\n{state['plan']}")
    messages = [
        # format in documents which has been fetched
        SystemMessage(
            content=WRITER_PROMPT.format(content=content)
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

def reflection_node(state: AgentState):
    messages = [
        # take the reflection node and the draft
        SystemMessage(content=REFLECTION_PROMPT),
        HumanMessage(content=state['draft'])
    ]
    response = model.invoke(messages)
    # going to generate the critique
    return {"critique": response.content}

def research_critique_node(state: AgentState):
    queries = model.with_structured_output(Queries).invoke([
        SystemMessage(content=RESEARCH_CRITIQUE_PROMPT),
        HumanMessage(content=state['critique'])
    ])
    # get the original content and append with new queries
    content = state['content'] or []
    for q in queries.queries:
        response = tavily.search(query=q, max_results=2)
        for r in response['results']:
            content.append(r['content'])
    return {"content": content}

# look at the revision number - if greater than the max revisions will then end.
def should_continue(state):
    if state["revision_number"] > state["max_revisions"]:
        return END
    return "reflect"

# initialise the graph with the agent state
builder = StateGraph(AgentState)

# add all nodes
builder.add_node("planner", plan_node)
builder.add_node("generate", generation_node)
builder.add_node("reflect", reflection_node)
builder.add_node("research_plan", research_plan_node)
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
builder.add_edge("planner", "research_plan")
builder.add_edge("research_plan", "generate")

builder.add_edge("reflect", "research_critique")
builder.add_edge("research_critique", "generate")

# compile graph and add in checkpointer
graph = builder.compile(checkpointer=memory)

# from IPython.display import Image
#
# Image(graph.get_graph().draw_png())

# adding in graph.stream so can see all the steps
thread = {"configurable": {"thread_id": "1"}}
for s in graph.stream({
    'task': "Write me a report on the Toyota RAV4",
    "max_revisions": 2,
    "revision_number": 1,
    "content": [],
}, thread):
    print(s)


