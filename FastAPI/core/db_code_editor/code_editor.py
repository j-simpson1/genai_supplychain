import matplotlib
matplotlib.use("Agg")

from dotenv import load_dotenv
load_dotenv()

import os
import uuid
import traceback
import re

from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langsmith import Client

from FastAPI.core.db_code_editor.state import SharedState

# --- Setup --------------------------------------------------------------------

client = Client()
model = ChatOpenAI(model="o4-mini")

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
CHARTS_DIR = os.path.join(PROJECT_ROOT, "FastAPI", "core", "charts")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "FastAPI", "reports_and_graphs")
os.makedirs(CHARTS_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

MAX_RETRIES = 3  # total failed attempts allowed before END

# --- Nodes --------------------------------------------------------------------

def generate_chart_code_node(state: SharedState):
    """Generate (or regenerate) full chart code from spec, tool data, and last error context."""
    chart_spec = state.get("chart_spec") or {}
    chart_description = chart_spec.get("chart_description", "No description")
    if "chart_retry_count" not in state:
        state["chart_retry_count"] = 0
    retry_count = state["chart_retry_count"]

    # Collect any tool outputs to guide generation
    tool_data = "\n\n".join(
        msg.content for msg in state.get("db_content", []) if isinstance(msg, ToolMessage)
    )

    # Base prompt (assumes you have a LangSmith Prompt named 'generate_chart_prompt')
    base_prompt = client.pull_prompt("generate_chart_prompt", include_model=False).format(
        chart_description=chart_description,
        tool_data=tool_data
    )

    # Add regeneration constraints + error context if we've failed before
    last_error = state.get("chart_generation_error", "")
    last_code  = state.get("chart_code", "")

    if last_error:
        base_prompt += f"""

    Regenerate the FULL script from scratch using the spec above and the available tool data.
    
    Hard constraints:
    - Use matplotlib only (no seaborn).
    - Save the figure to the provided variable `chart_path` via `plt.savefig(chart_path)`.
    - Do not call `plt.show()`.
    - Ensure figures are closed (e.g., `plt.close('all')`).
    
    Previous attempt #{retry_count} failed with this traceback:
    {last_error}
    
    Last code (for reference only; do not patch blindly, write clean code):
    {last_code}
    """

    response = model.invoke([SystemMessage(content=base_prompt)])
    match = re.search(r"```(?:python)?\n(.*?)```", response.content, re.DOTALL)
    chart_code = match.group(1).strip() if match else (response.content or "").strip()

    if not chart_code:
        chart_code = "import matplotlib.pyplot as plt\nplt.figure()\nplt.savefig(chart_path)\nplt.close('all')\n"

    # NOTE: Do NOT reset retry counter here.
    return {
        "chart_code": chart_code,
        "chart_generation_success": None
    }


def execute_chart_code_node(state: SharedState):
    """Execute the generated code. On failure, capture the traceback; on success, return metadata."""
    try:
        code = state["chart_code"]
        chart_spec = state.get("chart_spec") or {}
        chart_id = chart_spec.get("chart_id", f"chart_{uuid.uuid4().hex}")
        chart_description = chart_spec.get("chart_description")
        chart_figure_caption = chart_spec.get("chart_figure_caption")
        attempt = state.get("chart_retry_count", 0)

        # Deterministic filename per attempt for traceability
        chart_path = os.path.join(CHARTS_DIR, f"{chart_id}_attempt_{attempt}.png")

        # Minimal, explicit globals (we let the snippet import its own libs)
        exec_globals = {"__file__": chart_path, "chart_path": chart_path}
        exec(code, exec_globals)

        return {
            "chart_metadata": {"id": chart_id, "path": chart_path, "chart_description": chart_description, "chart_figure_caption": chart_figure_caption},
            "chart_generation_success": True,
            "chart_generation_error": ""
        }
    except Exception:
        return {
            "chart_generation_success": False,
            "chart_generation_error": traceback.format_exc(),
            "chart_code": state.get("chart_code", "")
        }


def reflect_chart_node(state: SharedState):
    """Failure bookkeeping. Do NOT modify code here; we regenerate in the next generate step."""
    if state.get("chart_generation_success") is True:
        return {}

    retry_count = state.get("chart_retry_count", 0)
    if retry_count >= MAX_RETRIES:
        # Signal terminal failure; router will END the graph
        return {"chart_generation_success": False}

    return {
        "chart_retry_count": retry_count + 1,
        "chart_generation_success": None
    }


def execute_chart_next_node(state: SharedState) -> str:
    """Route after execution."""
    # Success → done
    if state.get("chart_generation_success") is True:
        return "done"

    # If we've reached retry limit (reflect node increments), stop.
    if state.get("chart_retry_count", 0) >= MAX_RETRIES:
        return "done"

    # Otherwise go to reflect (which bumps counter), then back to generate
    return "reflect_chart"

# --- Graph --------------------------------------------------------------------

chart_builder = StateGraph(SharedState)
chart_builder.add_node("generate_chart_code", generate_chart_code_node)
chart_builder.add_node("execute_chart_code", execute_chart_code_node)
chart_builder.add_node("reflect_chart", reflect_chart_node)

chart_builder.set_entry_point("generate_chart_code")
chart_builder.add_edge("generate_chart_code", "execute_chart_code")

chart_builder.add_conditional_edges(
    "execute_chart_code",
    execute_chart_next_node,
    {
        "reflect_chart": "reflect_chart",
        "done": END
    }
)

# **Reflect → Generate** (regen path)
chart_builder.add_edge("reflect_chart", "generate_chart_code")

code_editor_agent = chart_builder.compile(name="code_editor_agent")

# Optionally save the graph image
output_graph_path = "code_editor_langgraph.png"
with open(output_graph_path, "wb") as f:
    f.write(code_editor_agent.get_graph().draw_mermaid_png())

# --- Example run --------------------------------------------------------------

if __name__ == "__main__":
    import asyncio

    # Example tool output passed as ToolMessage
    tm = ToolMessage(
        content="{'sales_data': [100, 200, 150, 300]}",
        name="sales_tool",
        tool_call_id="tool_1"
    )

    initial_state: SharedState = {
        "chart_spec": {"chart_id": "sales_trend", "chart_description": "Plot monthly sales trends.", "chart_figure_caption": "Figure 1: Monthly sales trends for the current year."},
        "db_content": [tm],
    }

    async def run():
        async for s in code_editor_agent.astream(initial_state):
            print(s)

    asyncio.run(run())
     