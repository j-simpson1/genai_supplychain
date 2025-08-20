from dotenv import load_dotenv
load_dotenv()

import os
import traceback
import json, os, inspect

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage


from FastAPI.core.state import AgentState
from FastAPI.core.database_tools import parts_summary, top_5_parts_by_price, top_5_part_distribution_by_country, bottom_quartile_average_price, total_component_price, top_5_suppliers_by_articles, calculator
from FastAPI.core.utils import _json_dump_safe
from FastAPI.core.prompts import db_call_model_prompt, db_summary_prompt

import json
from langchain_core.messages import SystemMessage, ToolMessage

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports_and_graphs")

model = ChatOpenAI(
    model="o4-mini"
)

tools = [
    parts_summary,
    top_5_parts_by_price,
    top_5_part_distribution_by_country,
    bottom_quartile_average_price,
    total_component_price,
    top_5_suppliers_by_articles
]

db_model = ChatOpenAI(
    model="o4-mini"
).bind_tools(tools)

tools_by_name = {tool.name: tool for tool in tools}

def tool_node(state: AgentState):
    outputs = []

    # no-op if nothing to do
    msgs = state.get("db_content") or []
    if not msgs:
        return {"db_content": outputs}
    last = msgs[-1]
    tool_calls = getattr(last, "tool_calls", None) or []
    if not tool_calls:
        return {"db_content": outputs}

    # paths from state
    state_articles = state.get("articles_path")
    state_parts = state.get("parts_path")

    for call in tool_calls:
        tool_name = (call or {}).get("name")
        tool_id = (call or {}).get("id") or ""
        tool_obj = tools_by_name.get(tool_name)

        # 1) Unknown tool guard
        if tool_obj is None:
            outputs.append(ToolMessage(
                content=json.dumps({"error": "unknown_tool", "tool": tool_name}),
                name=tool_name or "unknown",
                tool_call_id=tool_id,
            ))
            continue

        # Start from model args but 2) prevent path override
        model_args = dict((call or {}).get("args") or {})
        model_args.pop("articles_path", None)
        model_args.pop("parts_path", None)

        # Quietly filter to the tool's accepted params
        fn = getattr(tool_obj, "func", None) or getattr(tool_obj, "coroutine", None)
        accepted = set(inspect.signature(fn).parameters.keys()) if fn else set()

        args = {k: v for k, v in model_args.items() if k in accepted}
        if "articles_path" in accepted and isinstance(state_articles, str):
            args["articles_path"] = state_articles
        if "parts_path" in accepted and isinstance(state_parts, str):
            args["parts_path"] = state_parts

        # 3) File existence check
        for p in ("articles_path", "parts_path"):
            if p in args and not os.path.isfile(args[p]):
                outputs.append(ToolMessage(
                    content=json.dumps({"error": "path_not_found", p+"_exists": False}),
                    name=tool_name,
                    tool_call_id=tool_id,
                ))
                break
        else:
            # 4) JSON‑safe output and catch any tool exception
            try:
                raw = tool_obj.invoke(args)
                content_str = _json_dump_safe(raw)
                outputs.append(ToolMessage(
                    content=content_str,
                    name=tool_name,
                    tool_call_id=tool_id,
                ))
            except Exception as e:
                outputs.append(ToolMessage(
                    content=json.dumps({"error": "tool_execution_failed", "tool": tool_name, "message": str(e)}),
                    name=tool_name,
                    tool_call_id=tool_id,
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

db_analyst_tools = [calculator]
db_analyst_model = ChatOpenAI(model="o4-mini").bind_tools(db_analyst_tools)

def db_analyst_node(state: AgentState):
    db_content_text = "\n\n".join(str(msg.content) for msg in state.get("db_content", []))

    # Encourage calculator use without touching your global prompt template
    tool_hint = (
        "You may call the `calculator` tool for any arithmetic "
        "(e.g., totals, percentages, weighted averages, medians). "
        "Return a concise executive summary at the end."
    )

    prompt = db_summary_prompt.format(db_content=db_content_text) + "\n\n" + tool_hint

    messages = [SystemMessage(content=prompt)]
    response = db_analyst_model.invoke(messages)

    # resolve calculator tool calls (usually 0–2 iterations)
    tool_msgs = []
    while getattr(response, "tool_calls", None):
        for call in (response.tool_calls or []):
            if call.get("name") == "calculator":
                args = (call.get("args") or {})
                # Normalize arg name; accept expression as either 'expression' or 'expr'
                expression = args.get("expression") or args.get("expr") or ""
                tool_output = calculator.invoke({"expression": expression})
                tool_msgs.append(ToolMessage(
                    content=_json_dump_safe(tool_output),
                    name="calculator",
                    tool_call_id=call.get("id", "")
                ))
            else:
                # Unknown tool safeguard
                tool_msgs.append(ToolMessage(
                    content=_json_dump_safe({"error": "unknown_tool", "tool": call.get("name")}),
                    name=call.get("name") or "unknown",
                    tool_call_id=call.get("id", "")
                ))

        messages.extend([response] + tool_msgs)
        response = db_analyst_model.invoke(messages)
        tool_msgs = []

    return {"db_summary": response.content}

def db_should_continue(state: AgentState):
    last_message = state["db_content"][-1]
    return "continue" if last_message.tool_calls else "end"

subgraph = StateGraph(AgentState)

subgraph.add_node("db_agent", call_model)
subgraph.add_node("db_tools", tool_node)
subgraph.add_node("db_analyst", db_analyst_node)

subgraph.add_edge(START, "db_agent")
subgraph.add_edge("db_tools", "db_agent")
subgraph.add_edge("db_analyst", END)

subgraph.add_conditional_edges(
    "db_agent",
    db_should_continue,
    {
        "continue": "db_tools",
        "end": "db_analyst"
    }
)

database_agent = subgraph.compile()

output_graph_path = os.path.join(REPORTS_DIR, "database_agent_langgraph.png")
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

