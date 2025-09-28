from dotenv import load_dotenv
load_dotenv()

import os
import traceback
import json
import inspect
from typing import Dict, Any, Optional
from langchain_core.runnables import RunnableConfig

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage, SystemMessage

from FastAPI.core.state import AgentState
from FastAPI.core.database_tools import (
    parts_summary,
    top_5_parts_by_price,
    top_5_part_distribution_by_country,
    bottom_quartile_average_price,
    total_component_price,
    top_5_suppliers_by_articles,
    calculator
)
from FastAPI.core.utils import _json_dump_safe
from FastAPI.core.prompts import db_call_model_prompt, db_summary_prompt

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports_and_graphs")
MODEL_NAME = "o4-mini"
GRAPH_OUTPUT_FILENAME = "database_agent_langgraph.png"

model = ChatOpenAI(model=MODEL_NAME)

tools = [
    parts_summary,
    top_5_parts_by_price,
    top_5_part_distribution_by_country,
    bottom_quartile_average_price,
    total_component_price,
    top_5_suppliers_by_articles
]

db_model = ChatOpenAI(model=MODEL_NAME).bind_tools(tools)

tools_by_name = {tool.name: tool for tool in tools}

def tool_node(state: AgentState) -> Dict[str, Any]:
    """Execute database tools based on tool calls in the state.

    Processes tool calls from the last message in db_content, validates file paths,
    and executes the appropriate database tools with proper error handling.

    Args:
        state: The current agent state containing db_content and file paths

    Returns:
        Dictionary with db_content key containing tool execution results
    """
    outputs = []

    msgs = state.get("db_content", [])
    if not msgs:
        return {"db_content": outputs}

    last_message = msgs[-1]
    tool_calls = getattr(last_message, "tool_calls", []) or []
    if not tool_calls:
        return {"db_content": outputs}

    articles_path = state.get("articles_path")
    parts_path = state.get("parts_path")

    for call in tool_calls:
        tool_name = (call or {}).get("name")
        tool_id = (call or {}).get("id") or ""
        tool_obj = tools_by_name.get(tool_name)

        if tool_obj is None:
            outputs.append(ToolMessage(
                content=json.dumps({"error": "unknown_tool", "tool": tool_name}),
                name=tool_name or "unknown",
                tool_call_id=tool_id,
            ))
            continue

        model_args = dict((call or {}).get("args", {}))
        model_args.pop("articles_path", None)
        model_args.pop("parts_path", None)

        tool_function = getattr(tool_obj, "func", None) or getattr(tool_obj, "coroutine", None)
        accepted_params = set(inspect.signature(tool_function).parameters.keys()) if tool_function else set()

        args = {k: v for k, v in model_args.items() if k in accepted_params}
        if "articles_path" in accepted_params and isinstance(articles_path, str):
            args["articles_path"] = articles_path
        if "parts_path" in accepted_params and isinstance(parts_path, str):
            args["parts_path"] = parts_path

        path_missing = False
        for path_key in ("articles_path", "parts_path"):
            if path_key in args and not os.path.isfile(args[path_key]):
                outputs.append(ToolMessage(
                    content=json.dumps({"error": "path_not_found", f"{path_key}_exists": False}),
                    name=tool_name,
                    tool_call_id=tool_id,
                ))
                path_missing = True
                break

        if not path_missing:
            try:
                result = tool_obj.invoke(args)
                content_str = _json_dump_safe(result)
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
def call_model(state: AgentState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """Call the database model to generate tool calls based on the current plan.

    Args:
        state: The current agent state containing plan and db_content
        config: Optional configuration for the model call

    Returns:
        Dictionary with db_content key containing the model response
    """

    prompt = db_call_model_prompt.format(
        plan=state.get('plan', 'No plan provided'),
        tools="\n".join(f"- {t.name}: {t.description}" for t in tools),
        # tool_names=", ".join(t.name for t in tools),
    )

    response = db_model.invoke([SystemMessage(content=prompt)] + state["db_content"], config)
    return {"db_content": [response]}

db_analyst_tools = [calculator]
db_analyst_model = ChatOpenAI(model=MODEL_NAME).bind_tools(db_analyst_tools)

def db_analyst_node(state: AgentState) -> Dict[str, str]:
    """Analyze database tool results and generate an executive summary.

    Processes the db_content messages, optionally uses calculator for arithmetic,
    and produces a concise summary of the database analysis results.

    Args:
        state: The current agent state containing db_content messages

    Returns:
        Dictionary with db_summary key containing the analysis summary
    """
    db_content_text = "\n\n".join(str(msg.content) for msg in state.get("db_content", []))

    # Encourage calculator use without touching the global prompt template
    tool_hint = (
        "You may call the `calculator` tool for any arithmetic "
        "(e.g., totals, percentages, weighted averages, medians). "
        "Return a concise executive summary at the end."
    )

    prompt = db_summary_prompt.format(db_content=db_content_text) + "\n\n" + tool_hint

    messages = [SystemMessage(content=prompt)]
    response = db_analyst_model.invoke(messages)

    tool_messages = []
    while getattr(response, "tool_calls", None):
        for call in response.tool_calls or []:
            call_name = call.get("name")
            call_id = call.get("id", "")

            if call_name == "calculator":
                call_args = call.get("args", {})
                expression = call_args.get("expression") or call_args.get("expr", "")
                tool_output = calculator.invoke({"expression": expression})
                tool_messages.append(ToolMessage(
                    content=_json_dump_safe(tool_output),
                    name="calculator",
                    tool_call_id=call_id
                ))
            else:
                tool_messages.append(ToolMessage(
                    content=_json_dump_safe({"error": "unknown_tool", "tool": call_name}),
                    name=call_name or "unknown",
                    tool_call_id=call_id
                ))

        messages.extend([response] + tool_messages)
        response = db_analyst_model.invoke(messages)
        tool_messages = []

    return {"db_summary": response.content}

def db_should_continue(state: AgentState) -> str:
    """Determine whether to continue with tool execution or move to analysis.

    Args:
        state: The current agent state

    Returns:
        'continue' if there are tool calls to execute, 'end' otherwise
    """
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

# output_graph_path = os.path.join(REPORTS_DIR, GRAPH_OUTPUT_FILENAME)
# with open(output_graph_path, "wb") as f:
#     f.write(database_agent.get_graph().draw_mermaid_png())

if __name__ == "__main__":
    import asyncio

    async def run_test() -> None:
        """Run a test of the database agent with sample data."""

        base_dir = os.path.dirname(os.path.abspath(__file__))
        parts_path = os.path.join(base_dir, "Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")
        articles_path = os.path.join(base_dir, "Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")

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
        except Exception:
            print("Error during test run:")
            traceback.print_exc()

    asyncio.run(run_test())

