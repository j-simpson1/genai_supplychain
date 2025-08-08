import matplotlib
matplotlib.use("Agg")

from dotenv import load_dotenv
load_dotenv()

import os
import re
import uuid
import traceback
from typing import Dict, Any

from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

from FastAPI.core.state import AgentState
from FastAPI.core.prompts import generate_chart_prompt

# ---------- Paths / Model ----------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
CHARTS_DIR = os.path.join(PROJECT_ROOT, "FastAPI", "core", "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

model = ChatOpenAI(model="o4-mini")

# ---------- Helpers ----------
_CODE_BLOCK_RE = re.compile(r"```(?:python)?\n(.*?)```", re.DOTALL)

def _extract_code(text: str) -> str:
    m = _CODE_BLOCK_RE.search(text)
    return (m.group(1) if m else text).strip()

# ---------- Nodes ----------
def generate_chart_code_node(state: AgentState) -> Dict[str, Any]:
    chart_index = state.get("current_chart_index", 0)
    chart_plan = state.get("chart_plan", [])
    if chart_index >= len(chart_plan):
        return {"chart_code": "", "chart_generation_success": True}

    chart = chart_plan[chart_index]
    chart_description = chart.get("chart_description", "No description")

    tool_data = "\n\n".join(
        msg.content for msg in state.get("db_content", []) if isinstance(msg, ToolMessage)
    )

    # Defaults if missing
    retry_count = state.get("chart_retry_count", 0)
    last_error = state.get("chart_generation_error", "")
    prev_success = state.get("chart_generation_success", None)
    previous_code = state.get("chart_code", "") if prev_success is False else ""

    error_hint = (
        f"\n\nPrevious attempt failed (retry {retry_count}). Error:\n{last_error}\n\n"
        "Regenerate the code without the error, preserving the original intent."
        if last_error else ""
    )

    prompt = generate_chart_prompt.format(
        chart_description=chart_description,
        tool_data=tool_data
    ) + error_hint

    response = model.invoke([SystemMessage(content=prompt)])
    chart_code = _extract_code(response.content)

    return {
        "chart_code": chart_code,
        "chart_generation_error": "",     # consume error
        "chart_generation_success": None, # will be set by execute
    }

def execute_chart_code_node(state: AgentState) -> Dict[str, Any]:
    try:
        code = state["chart_code"]

        chart_index = state.get("current_chart_index", 0)
        chart_plan = state.get("chart_plan", [])
        chart_id = chart_plan[chart_index]["chart_id"] if chart_index < len(chart_plan) else f"chart_{chart_index}"

        chart_path = os.path.join(CHARTS_DIR, f"{chart_id}_{uuid.uuid4().hex}.png")

        exec_globals = {"__file__": chart_path, "chart_path": chart_path}
        exec(code, exec_globals)

        chart_metadata = list(state.get("chart_metadata", []))
        chart_metadata.append({"id": chart_id, "path": chart_path})

        return {
            "chart_metadata": chart_metadata,
            "chart_generation_success": True,
            "current_chart_index": chart_index + 1,
            "chart_retry_count": 0,
            "chart_generation_error": "",
        }
    except Exception:
        return {
            "chart_generation_success": False,
            "chart_generation_error": traceback.format_exc(),
            "chart_code": state.get("chart_code", ""),
        }

def reflect_chart_node(state: AgentState) -> Dict[str, Any]:
    if state.get("chart_generation_success", False):
        return {}

    retry = state.get("chart_retry_count", 0)
    max_retries = state.get("max_chart_retries", 2)

    if retry < max_retries:
        return {
            "chart_generation_success": None,  # let Generate run again
            "chart_retry_count": retry + 1,
            # keep chart_generation_error as-is for Generate to include
        }

    # Give up on this chart, advance
    return {
        "chart_generation_success": True,   # treated as handled
        "chart_generation_error": "",
        "chart_retry_count": 0,
        "current_chart_index": state.get("current_chart_index", 0) + 1,
    }

def execute_chart_next_node(state: AgentState) -> str:
    if state.get("chart_generation_success", False):
        more = state.get("current_chart_index", 0) < len(state.get("chart_plan", []))
        return "generate_chart_code" if more else "research_plan"
    else:
        return "reflect_chart"

# ---------- Graph ----------
subgraph = StateGraph(AgentState)

subgraph.add_node("generate_chart_code", generate_chart_code_node)
subgraph.add_node("execute_chart_code", execute_chart_code_node)
subgraph.add_node("reflect_chart", reflect_chart_node)

subgraph.add_edge(START, "generate_chart_code")
subgraph.add_edge("generate_chart_code", "execute_chart_code")
subgraph.add_edge("reflect_chart", "generate_chart_code")

subgraph.add_conditional_edges(
    "execute_chart_code",
    execute_chart_next_node,
    {
        "reflect_chart": "reflect_chart",
        "research_plan": END,
        "generate_chart_code": "generate_chart_code",
    }
)

code_editor_agent = subgraph.compile()

# ---------- Demo ----------
if __name__ == "__main__":
    import asyncio
    from langchain_core.messages import ToolMessage

    # Minimal ToolMessage to simulate db tool output
    tm = ToolMessage(
        content="{'months': ['Jan','Feb','Mar','Apr'], 'sales': [100, 200, 150, 300]}",
        name="sales_tool",
        tool_call_id="tool_1",
    )

    # Use your AgentState (or SharedState if that’s what you’ve typed)
    initial_state: AgentState = {
        "chart_plan": [
            {
                "chart_id": "sales_trend",
                "chart_description": "Plot monthly sales trends. Save to chart_path.",
            }
        ],
        "db_content": [tm],
        # everything else is optional; nodes handle defaults
    }

    async def run():
        final_state = None
        async for chunk in code_editor_agent.astream(initial_state):
            # Each `chunk` looks like {"<node_name>": {delta...}} or {"__end__": {final_state...}}
            print(chunk)
            if "__end__" in chunk:
                final_state = chunk["__end__"]

        # Optional: do something with the final state
        if final_state:
            print("\n=== Final ===")
            print("success:", final_state.get("chart_generation_success"))
            print("metadata:", final_state.get("chart_metadata"))

    asyncio.run(run())