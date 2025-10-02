from dotenv import load_dotenv
load_dotenv()

import os
import re
import uuid
import traceback
from typing import Dict, Any

import matplotlib
matplotlib.use("Agg")

from langchain_core.messages import SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI

from FastAPI.core.state import AgentState
from FastAPI.core.prompts import generate_chart_prompt
from FastAPI.core.utils import verify_generated_chart


# Constants
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "output", "reports")
CHARTS_DIR = os.path.join(PROJECT_ROOT, "output", "charts")
MAX_CHART_RETRIES = 2

# Ensure charts directory exists
os.makedirs(CHARTS_DIR, exist_ok=True)

# Initialize language model
model = ChatOpenAI(model="gpt-5")

# Utilities
_CODE_BLOCK_RE = re.compile(r"```(?:python)?\n(.*?)```", re.DOTALL)


def _extract_code(text: str) -> str:
    """Extract Python code from markdown code blocks.

    Args:
        text: Text potentially containing code blocks

    Returns:
        Extracted code string, stripped of whitespace
    """
    match = _CODE_BLOCK_RE.search(text)
    return (match.group(1) if match else text).strip()

# Graph Nodes
def generate_chart_code_node(state: AgentState) -> Dict[str, Any]:
    """Generate chart code based on the current chart plan and database content.

    Args:
        state: Current agent state containing chart plan and database content

    Returns:
        Updated state with generated chart code
    """
    print("\n=== GENERATE CHART CODE NODE STARTED ===")
    chart_index = state.get("current_chart_index", 0)
    chart_plan = state.get("chart_plan", [])
    print(f"Chart index: {chart_index}/{len(chart_plan)}")

    if chart_index >= len(chart_plan):
        print("No more charts to generate")
        return {"chart_code": "", "chart_generation_success": True}

    chart = chart_plan[chart_index]
    chart_description = chart.get("chart_description", "No description")
    print(f"Generating chart: {chart.get('chart_id', 'unknown')}")
    print(f"Description: {chart_description[:100]}...")

    tool_data = "\n\n".join(
        msg.content for msg in state.get("db_content", [])
        if isinstance(msg, ToolMessage)
    )
    print(f"Tool data length: {len(tool_data)} characters")

    retry_count = state.get("chart_retry_count", 0)
    last_error = state.get("chart_generation_error", "")

    error_hint = ""
    if last_error:
        print(f"Retry {retry_count} - Previous error: {last_error[:200]}...")
        error_hint = (
            f"\n\nPrevious attempt failed (retry {retry_count}). Error:\n{last_error}\n\n"
            "Regenerate the code without the error, preserving the original intent."
        )

    prompt = generate_chart_prompt.format(
        chart_description=chart_description,
        tool_data=tool_data
    ) + error_hint
    print(f"Prompt length: {len(prompt)} characters")

    print("Invoking model (this may take a while with o4-mini reasoning)...")
    import time
    start_time = time.time()
    response = model.invoke([SystemMessage(content=prompt)])
    elapsed = time.time() - start_time
    print(f"✓ Model response received in {elapsed:.1f}s")

    chart_code = _extract_code(response.content)
    print(f"Generated code length: {len(chart_code)} characters")

    return {
        "chart_code": chart_code,
        "chart_generation_error": "",
        "chart_generation_success": None,
    }

def execute_chart_code_node(state: AgentState) -> Dict[str, Any]:
    """Execute the generated chart code and validate the output.

    Args:
        state: Current agent state containing chart code

    Returns:
        Updated state with execution results and chart metadata
    """
    print("\n=== EXECUTE CHART CODE NODE STARTED ===")
    try:
        code = state["chart_code"]
        chart_index = state.get("current_chart_index", 0)
        chart_plan = state.get("chart_plan", [])

        chart_id = (
            chart_plan[chart_index]["chart_id"]
            if chart_index < len(chart_plan)
            else f"chart_{chart_index}"
        )
        print(f"Executing chart: {chart_id}")

        chart_path = os.path.join(CHARTS_DIR, f"{chart_id}_{uuid.uuid4().hex}.png")
        exec_globals = {"__file__": chart_path, "chart_path": chart_path}

        print("Executing generated code...")
        exec(code, exec_globals)
        print(f"✓ Code executed successfully")

        # Clean up matplotlib resources
        try:
            import matplotlib.pyplot as plt
            plt.close("all")
        except ImportError:
            pass

        # Validate the generated chart
        print("Validating generated chart...")
        is_valid, reason = verify_generated_chart(chart_path)
        if not is_valid:
            raise RuntimeError(f"Chart artifact invalid: {reason}")
        print(f"✓ Chart validated: {chart_path}")

        chart_metadata = list(state.get("chart_metadata", []))
        chart_metadata.append({"id": chart_id, "path": chart_path})

        return {
            "chart_metadata": chart_metadata,
            "chart_generation_success": True,
            "current_chart_index": chart_index + 1,
            "chart_retry_count": 0,
            "chart_generation_error": "",
        }

    except Exception as e:
        error_msg = traceback.format_exc()
        print(f"✗ Chart execution failed: {str(e)}")
        print(f"Error details: {error_msg[:500]}...")
        return {
            "chart_generation_success": False,
            "chart_generation_error": error_msg,
            "chart_code": state.get("chart_code", ""),
        }

def reflect_chart_node(state: AgentState) -> Dict[str, Any]:
    """Handle chart generation failures and retry logic.

    Args:
        state: Current agent state

    Returns:
        Updated state with retry or skip logic
    """
    if state.get("chart_generation_success", False):
        return {}

    retry_count = state.get("chart_retry_count", 0)
    max_retries = state.get("max_chart_retries", MAX_CHART_RETRIES)

    if retry_count < max_retries:
        return {
            "chart_generation_success": None,
            "chart_retry_count": retry_count + 1,
        }

    # Maximum retries reached, skip this chart
    return {
        "chart_generation_success": True,
        "chart_generation_error": "",
        "chart_retry_count": 0,
        "current_chart_index": state.get("current_chart_index", 0) + 1,
    }


def execute_chart_next_node(state: AgentState) -> str:
    """Determine the next node based on chart generation status.

    Args:
        state: Current agent state

    Returns:
        Name of the next node to execute
    """
    if state.get("chart_generation_success", False):
        current_index = state.get("current_chart_index", 0)
        chart_plan = state.get("chart_plan", [])
        has_more_charts = current_index < len(chart_plan)
        return "generate_chart_code" if has_more_charts else "end"
    else:
        return "reflect_chart"

# Graph Construction
def create_code_editor_agent():
    """Create and compile the code editor agent graph.

    Returns:
        Compiled LangGraph agent for chart code generation
    """
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("generate_chart_code", generate_chart_code_node)
    graph.add_node("execute_chart_code", execute_chart_code_node)
    graph.add_node("reflect_chart", reflect_chart_node)

    # Add edges
    graph.add_edge(START, "generate_chart_code")
    graph.add_edge("generate_chart_code", "execute_chart_code")
    graph.add_edge("reflect_chart", "generate_chart_code")

    # Add conditional edges
    graph.add_conditional_edges(
        "execute_chart_code",
        execute_chart_next_node,
        {
            "reflect_chart": "reflect_chart",
            "end": END,
            "generate_chart_code": "generate_chart_code",
        }
    )

    return graph.compile()


# Create the agent
code_editor_agent = create_code_editor_agent()

# # Generate graph visualization
# output_graph_path = os.path.join(REPORTS_DIR, "code_editor_langgraph.png")
# with open(output_graph_path, "wb") as f:
#     f.write(code_editor_agent.get_graph().draw_mermaid_png())

# Demo
if __name__ == "__main__":
    import asyncio
    from langchain_core.messages import ToolMessage

    async def run_demo():
        """Run a demonstration of the code editor agent."""
        # Create sample tool message simulating database output
        sample_data = ToolMessage(
            content="{'months': ['Jan','Feb','Mar','Apr'], 'sales': [100, 200, 150, 300]}",
            name="sales_tool",
            tool_call_id="tool_1",
        )

        # Create initial state for demonstration
        initial_state = {
            "chart_plan": [
                {
                    "chart_id": "sales_trend",
                    "chart_description": "Plot monthly sales trends. Save to chart_path.",
                }
            ],
            "db_content": [sample_data],
        }

        print("Running code editor agent demo...")
        final_state = None

        async for chunk in code_editor_agent.astream(initial_state):
            print(f"Step Output: {chunk}")
            if "__end__" in chunk:
                final_state = chunk["__end__"]

        if final_state:
            print("\n=== Demo Results ===")
            print(f"Success: {final_state.get('chart_generation_success')}")
            print(f"Chart metadata: {final_state.get('chart_metadata')}")

    asyncio.run(run_demo())