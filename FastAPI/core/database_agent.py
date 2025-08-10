from dotenv import load_dotenv
load_dotenv()

import os
import traceback

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

from FastAPI.core.state import AgentState
from FastAPI.core.database_tools import parts_summary, top_5_parts_by_price, top_5_part_distribution_by_country, average_parts_price, total_component_price, top_5_suppliers_by_articles
from FastAPI.core.utils import convert_numpy
from FastAPI.core.prompts import db_call_model_prompt, db_summary_prompt

import json
from langchain_core.messages import SystemMessage, ToolMessage


model = ChatOpenAI(
    model="o4-mini"
)

tools = [
    parts_summary,
    top_5_parts_by_price,
    top_5_part_distribution_by_country,
    average_parts_price,
    total_component_price,
    top_5_suppliers_by_articles
]

db_model = ChatOpenAI(
    model="o4-mini"
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
            result = convert_numpy(tools_by_name[tool_name].invoke(args))

        outputs.append(ToolMessage(
            content=json.dumps(result),
            name=tool_name,
            tool_call_id=tool_call["id"]
        ))
    return {"db_content": outputs}

# --- Model Node ---
def call_model(state: AgentState, config=None):

    prompt = db_call_model_prompt.format(
        plan=state.get('plan', 'No plan provided'),
        tools="\n".join(f"- {t.name}: {t.description}" for t in tools),
        # tool_names=", ".join(t.name for t in tools),
    )

    response = db_model.invoke([SystemMessage(content=prompt)] + state["db_content"], config)
    return {"db_content": [response]}

def summarize_db_node(state: AgentState):
    db_content_text = "\n\n".join(str(msg.content) for msg in state.get("db_content", []))

    prompt = db_summary_prompt.format(db_content=db_content_text)

    response = model.invoke([SystemMessage(content=prompt)])

    return {
        "db_summary": response.content
    }

def db_should_continue(state: AgentState):
    last_message = state["db_content"][-1]
    return "continue" if last_message.tool_calls else "end"

subgraph = StateGraph(AgentState)

subgraph.add_node("db_agent", call_model)
subgraph.add_node("db_tools", tool_node)
subgraph.add_node("summarize_db", summarize_db_node)

subgraph.add_edge(START, "db_agent")
subgraph.add_edge("db_tools", "db_agent")
subgraph.add_edge("summarize_db", END)

subgraph.add_conditional_edges(
    "db_agent",
    db_should_continue,
    {
        "continue": "db_tools",
        "end": "summarize_db"
    }
)

database_agent = subgraph.compile()

output_graph_path = "../reports_and_graphs/database_agent_langgraph.png"
with open(output_graph_path, "wb") as f:
    f.write(database_agent.get_graph().draw_mermaid_png())

if __name__ == "__main__":
    import asyncio

    async def run_test():

        # Define mock file paths (point these to real CSV/JSON files if available)
        articles_path = os.path.join(os.getcwd(), "Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
        parts_path = os.path.join(os.getcwd(), "Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")

        # Create initial state
        initial_state: AgentState = {
            "plan": "Get a summary of the top 5 parts by price and their country distribution.",
            "articles_path": articles_path,
            "parts_path": parts_path,
            "db_content": []  # no prior conversation history
        }

        print("\n--- Running DB Agent Test ---\n")
        try:
            async for step in database_agent.astream(initial_state):
                print("Step Output:", step)
            print("\n--- DB Agent Test Completed ---\n")
        except Exception as e:
            print("Error during test run:")
            traceback.print_exc()

    asyncio.run(run_test())

