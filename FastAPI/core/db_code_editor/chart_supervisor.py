# chart_supervisor.py  (LLM-driven supervisor with status emitters)
import os
from typing import TypedDict, Dict, List, Optional, Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent, InjectedState
from langgraph.types import Command
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage, ToolMessage

# --- Import your existing workers and base state -------------------------------
from FastAPI.core.db_code_editor.database_agent import database_agent
from FastAPI.core.db_code_editor.code_editor import code_editor_agent
from FastAPI.core.db_code_editor.state import SharedState as BaseSharedState

# If MAX_RETRIES is exported by code_editor module, import it; else set here.
try:
    from FastAPI.core.db_code_editor.code_editor import MAX_RETRIES  # type: ignore
except Exception:
    MAX_RETRIES = 3

# Extend your state to add a message lane for the supervisor (safe: total=False)
class SharedState(BaseSharedState, total=False):  # type: ignore[misc]
    messages: Annotated[List[AnyMessage], add_messages]


# If you don't already have this function imported elsewhere, keep it here
def build_chart_spec_node(state: SharedState):
    if not state.get("chart_spec"):
        state["chart_spec"] = {
            "chart_id": "spend_share_by_part",
            "chart_description": (
                "Pie chart of spend share by product group using DB tool outputs "
                "(bottom-quartile average price × quantity)."
            ),
            "chart_figure_caption": "Spend share by product group."
        }
    return state


# --- Handoff tools: supervisor -> workers -------------------------------------
# IMPORTANT: no kwargs on @tool; set __name__ and __doc__ for name/description.
def create_task_description_handoff_tool(*, agent_name: str, description: str):
    def _handoff(
        task_description: Annotated[
            str,
            "Describe exactly what the next agent should do, with all needed context."
        ],
        state: Annotated[SharedState, InjectedState],
    ) -> Command:
        # Give the worker a focused user message; keep the rest of the state (paths, plan, etc.)
        worker_input = {
            **state,
            "messages": [{"role": "user", "content": task_description}],
        }
        # Route to the target worker within the parent graph
        return Command(goto=agent_name, update=worker_input, graph=Command.PARENT)

    _handoff.__name__ = f"transfer_to_{agent_name}"
    _handoff.__doc__ = description
    return tool()(_handoff)


assign_to_db = create_task_description_handoff_tool(
    agent_name="run_db",
    description="Assign a database/data-extraction task (use DB tools with provided CSV paths).",
)
assign_to_chart_spec = create_task_description_handoff_tool(
    agent_name="build_chart_spec",
    description="Ask the chart-spec builder to create or refine the chart_spec.",
)
assign_to_code = create_task_description_handoff_tool(
    agent_name="run_code",
    description="Assign a chart-generation task (write & execute matplotlib code).",
)


# --- Supervisor agent (LLM decides the next hop) -------------------------------
supervisor_llm = ChatOpenAI(model="o4-mini")

supervisor_agent = create_react_agent(
    model=supervisor_llm,
    tools=[assign_to_db, assign_to_chart_spec, assign_to_code],
    prompt=(
        "You are a supervisor for a report-building system.\n\n"
        "Workers you can transfer to (ONE at a time):\n"
        "- run_db: retrieve/aggregate data via DB tools using provided CSV paths.\n"
        "- build_chart_spec: create or refine a chart_spec for the report.\n"
        "- run_code: generate & execute matplotlib code to produce the chart.\n\n"
        "Guidance:\n"
        "- Prefer minimal hops. Typical flow: run_db → build_chart_spec (if missing) → run_code.\n"
        "- If data is missing, transfer to run_db; if chart_spec is missing or weak, transfer to build_chart_spec; "
        "  if code failed or needs updating, transfer to run_code with clear instructions.\n"
        "- Do NOT do the task yourself. Always transfer via a tool.\n"
        "- When you transfer, provide a concise, complete task description.\n\n"
        "Signals:\n"
        "- After each worker, you'll receive a short status message in this chat indicating progress.\n"
        "- Use those messages to decide the next transfer. Stop once the chart is successfully generated."
    ),
    name="supervisor",
)


# --- Status emitters so supervisor can observe progress ------------------------
def _append_msg(state: SharedState, *, name: str, content: str):
    msgs = list(state.get("messages", []))
    msgs.append({"role": "assistant", "name": name, "content": content})
    return {"messages": msgs}

def emit_db_status(state: SharedState):
    tool_msgs = [m for m in state.get("db_content", []) if isinstance(m, ToolMessage)]
    if not tool_msgs:
        return _append_msg(state, name="run_db", content="DB agent ran; no tool outputs yet.")
    last = tool_msgs[-1]
    content = f"DB complete. Tool outputs={len(tool_msgs)}. Last tool='{getattr(last, 'name', 'unknown')}'."
    return _append_msg(state, name="run_db", content=content)

def emit_chart_spec_status(state: SharedState):
    spec = state.get("chart_spec") or {}
    content = (
        f"Chart spec ready. id={spec.get('chart_id')!s}; "
        f"desc={spec.get('chart_description')!s}; "
        f"caption={spec.get('chart_figure_caption')!s}"
    )
    return _append_msg(state, name="build_chart_spec", content=content)

def emit_code_status(state: SharedState):
    success = state.get("chart_generation_success")
    if success is True:
        path = (state.get("chart_metadata") or {}).get("path")
        content = f"Chart generated ✅. path={path}"
    elif success is False:
        err_tail = (state.get("chart_generation_error") or "").splitlines()[-1][:220]
        content = f"Chart generation failed ❌. retries={state.get('chart_retry_count', 0)}. last_error_tail={err_tail}"
    else:
        content = "Chart generation status unknown."
    return _append_msg(state, name="run_code", content=content)


# --- Post-worker router: finish or go back to supervisor ----------------------
def next_after_worker(state: SharedState) -> str:
    if state.get("chart_generation_success") is True:
        return "end"
    if state.get("chart_generation_success") is False and state.get("chart_retry_count", 0) >= MAX_RETRIES:
        return "end"
    return "supervisor"


# --- Build the multi-agent graph ---------------------------------------------
graph = (
    StateGraph(SharedState)
    # Workers
    .add_node("run_db", database_agent)
    .add_node("build_chart_spec", build_chart_spec_node)
    .add_node("run_code", code_editor_agent)
    # Status emitters
    .add_node("emit_db_status", emit_db_status)
    .add_node("emit_chart_spec_status", emit_chart_spec_status)
    .add_node("emit_code_status", emit_code_status)
    # Supervisor
    .add_node("supervisor", supervisor_agent)

    # Flow
    .add_edge(START, "supervisor")

    # Worker → emit status → supervisor (or end after code)
    .add_edge("run_db", "emit_db_status")
    .add_edge("emit_db_status", "supervisor")

    .add_edge("build_chart_spec", "emit_chart_spec_status")
    .add_edge("emit_chart_spec_status", "supervisor")

    .add_edge("run_code", "emit_code_status")
    .add_conditional_edges("emit_code_status", next_after_worker, {
        "supervisor": "supervisor",
        "end": END
    })
    .compile()
)


# --- Demo runner --------------------------------------------------------------
if __name__ == "__main__":
    import asyncio

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    parts_path = os.path.join(BASE_DIR, "../Toyota_RAV4_brake_dummy_data", "RAV4_brake_parts_data.csv")
    articles_path = os.path.join(BASE_DIR, "../Toyota_RAV4_brake_dummy_data", "RAV4_brake_articles_data.csv")

    initial_state: SharedState = {
        "messages": [
            {
                "role": "user",
                "content": (
                    "Build a pie chart for Toyota RAV4 brake parts showing the cost breakdown of the component at the part level. "
                    "Use DB tools to compute total_component_price and parts_summary first if needed."
                ),
            }
        ],
        "db_content": [],
        "articles_path": articles_path,
        "parts_path": parts_path,
        "plan": "Call total_component_price and parts_summary, then chart spend share by part.",
        # Optional: omit chart_spec to let builder create it.
    }

    def _print_chunk(update):
        # Minimal trace: show latest chat message (what the supervisor sees)
        for node, payload in update.items():
            if "messages" in payload:
                msgs = payload["messages"]
                if msgs:
                    last = msgs[-1]
                    role = getattr(last, "type", getattr(last, "role", ""))
                    name = getattr(last, "name", "")
                    print(f"\n[{node}] {role} {('('+name+')' if name else '')}")
                    try:
                        print(getattr(last, "content", last))
                    except Exception:
                        print(last)
            # Also show DB tool message count for sanity
            if "db_content" in payload:
                try:
                    tool_count = sum(isinstance(m, ToolMessage) for m in payload["db_content"])
                    if tool_count:
                        print(f"[{node}] db_content tool messages: {tool_count}")
                except Exception:
                    pass

    async def run():
        async for chunk in graph.astream(initial_state):
            _print_chunk(chunk)

    asyncio.run(run())