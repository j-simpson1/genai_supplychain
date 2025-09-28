from dotenv import load_dotenv
load_dotenv()

import json
import math
import os
from typing import List, Union

import matplotlib
matplotlib.use("Agg")
from langchain.agents import tool
from langchain_core.messages import ToolMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field

from FastAPI.core.state import AgentState
from FastAPI.core.prompts import simulation_prompt
from FastAPI.core.prompts import simulation_clean_prompt
from FastAPI.core.utils import convert_numpy
from FastAPI.automotive_simulation.simulation import analyze_tariff_impact

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "output", "reports")

class SimulationResultsInput(BaseModel):
    simulation_result: dict

class SimulationInputs(BaseModel):
    target_country: str = Field(..., description="Country to simulate tariff shock for")
    tariff_rates: List[Union[int, float]] = Field(
        ..., description="Tariff rates; decimals (0.1) or integers (10)."
    )

def _normalize_rates(rates: List[Union[int, float]]) -> List[float]:
    cleaned = []
    for r in rates:
        if isinstance(r, bool):  # avoid True/False becoming 1/0
            continue
        val = float(r)
        if val > 1:
            val /= 100.0
        if math.isfinite(val) and 0 <= val <= 1:
            cleaned.append(val)
    return sorted(set(cleaned))

def _assert_finite_numbers(obj, path="root"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            _assert_finite_numbers(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _assert_finite_numbers(v, f"{path}[{i}]")
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if not math.isfinite(obj):
            raise ValueError(f"Non-finite number at {path}: {obj}")

@tool(
    args_schema=SimulationInputs,
    description="Run an automotive tariff shock simulation after normalising and validating inputs."
)
def automotive_tariff_simulation(target_country: str, tariff_rates: List[Union[int, float]]) -> dict:
    """
    Run an automotive tariff shock simulation for the given country at the specified rates.
    Note: This function is a wrapper that gets called by the tool system.
    The actual tariff_path will be passed through the simulation_tool_node.

    Args:
        target_country: The country to simulate tariff shock for
        tariff_rates: List of tariff rates (decimals 0.1 or integers 10)

    Returns:
        dict: Simulation result from analyze_tariff_impact

    Raises:
        ValueError: If target_country is blank or no valid tariff rates
        TypeError: If output is not JSON-serializable
    """
    if not target_country.strip():
        raise ValueError("target_country cannot be blank.")

    rates = _normalize_rates(tariff_rates)
    if not rates:
        raise ValueError("No valid tariff rates after normalization.")

    # This will be handled by simulation_tool_node with proper file paths
    # This function is mainly for schema validation
    return {
        "target_country": target_country.strip(),
        "tariff_rates": rates,
        "note": "This will be processed by simulation_tool_node with file paths"
    }

simulation_tools = [automotive_tariff_simulation]

simulation_model = ChatOpenAI(model="o4-mini").bind_tools(simulation_tools)
model = ChatOpenAI(model="o4-mini")


def simulation_tool_node(state: AgentState):
    """
    Tool node that handles automotive_tariff_simulation calls.
    Uses articles_path, parts_path, and tariff_path from AgentState.
    """
    outputs = []
    messages = state.get("raw_simulation", [])

    if not messages:
        return {}

    last_message = messages[-1]
    chart_metadata = list(state.get("chart_metadata", []))

    if not (hasattr(last_message, "tool_calls") and last_message.tool_calls):
        return {"raw_simulation": messages}

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        args = tool_call["args"]
        tool_call_id = tool_call["id"]

        if tool_name == "automotive_tariff_simulation":
            try:
                articles_path = state.get("articles_path")
                parts_path = state.get("parts_path")
                tariff_path = state.get("tariff_path")

                result = analyze_tariff_impact(
                    suppliers_csv_path=articles_path,
                    parts_csv_path=parts_path,
                    target_country=args["target_country"].strip(),
                    tariff_rates=_normalize_rates(args["tariff_rates"]),
                    tariff_csv_path=tariff_path
                )

                if "output_files" in result and "chart_paths" in result["output_files"]:
                    chart_paths = result["output_files"]["chart_paths"]
                    existing_paths = [meta["path"] for meta in chart_metadata]

                    for chart_id, chart_path in chart_paths.items():
                        if chart_path not in existing_paths:
                            chart_id_clean = os.path.splitext(os.path.basename(chart_path))[0]
                            chart_metadata.append({
                                "id": chart_id_clean,
                                "path": chart_path
                            })

            except Exception as e:
                result = {"error": str(e)}

            outputs.append(ToolMessage(
                content=json.dumps(result),
                name=tool_name,
                tool_call_id=tool_call_id
            ))
        else:
            outputs.append(ToolMessage(
                content="Unknown tool",
                name=tool_name,
                tool_call_id=tool_call_id
            ))

    return {
        "raw_simulation": messages + outputs,
        "chart_metadata": chart_metadata
    }

def simulation_model_call(state: AgentState):
    """
    Call the simulation model with the current task and tools.
    """
    prompt = simulation_prompt.format(
        task=state["task"],
        tools=simulation_tools,
        tool_names=[t.name for t in simulation_tools]
    )
    response = simulation_model.invoke([prompt] + state["raw_simulation"])

    return {"raw_simulation": state["raw_simulation"] + [response]}

def simulation_clean(state: AgentState):
    """
    Clean and format the simulation output.
    """
    simulation_output = "\n\n".join(str(m.content) for m in state["raw_simulation"])
    response = model.invoke([
        SystemMessage(content=simulation_clean_prompt),
        HumanMessage(content=simulation_output)
    ])

    return {"clean_simulation": response}


def simulation_should_continue(state: AgentState):
    """
    Determine if the simulation should continue based on tool calls.
    """
    messages = state.get("raw_simulation", [])
    if not messages:
        return "end"

    last_message = messages[-1]
    tool_calls = getattr(last_message, "tool_calls", None)
    return "continue" if tool_calls else "end"


def create_simulation_agent():
    """
    Create and compile the simulation agent graph.
    """
    subgraph = StateGraph(AgentState)

    subgraph.add_node("simulation_agent", simulation_model_call)
    subgraph.add_node("simulation_tools", simulation_tool_node)
    subgraph.add_node("simulation_clean", simulation_clean)

    subgraph.add_edge(START, "simulation_agent")
    subgraph.add_edge("simulation_tools", "simulation_agent")
    subgraph.add_edge("simulation_clean", END)

    subgraph.add_conditional_edges(
        "simulation_agent",
        simulation_should_continue,
        {
            "continue": "simulation_tools",
            "end": "simulation_clean",
        },
    )

    return subgraph.compile()

simulation_agent = create_simulation_agent()

# output_graph_path = os.path.join(REPORTS_DIR, "simulation_agent_langgraph.png")
# with open(output_graph_path, "wb") as f:
#     f.write(simulation_agent.get_graph().draw_mermaid_png())

def create_test_state() -> AgentState:
    """
    Create a test state for the simulation agent.
    """
    articles_path = os.path.join(os.getcwd(), "FastAPI/core/Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
    parts_path = os.path.join(os.getcwd(), "FastAPI/core/Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")
    tariff_path = os.path.join(os.getcwd(), "FastAPI/core/Toyota_RAV4_brake_dummy_data/RAV4_brake_tariff_data.csv")

    return {
        "task": "Run a tariff shock simulation for Japan with 20%, 40%, and 70% rates.",
        "plan": "",
        "draft": "",
        "critique": "",
        "web_content": [],
        "db_content": [],
        "db_summary": "",
        "trajectory": [],
        "raw_simulation": [],
        "clean_simulation": "",
        "revision_number": 0,
        "max_revisions": 1,
        "chart_plan": [],
        "chart_metadata": [],
        "current_chart_index": 0,
        "chart_code": "",
        "chart_generation_success": False,
        "chart_generation_error": "",
        "chart_retry_count": 0,
        "max_chart_retries": 1,
        "articles_path": articles_path,
        "parts_path": parts_path,
        "tariff_path": tariff_path,
        "messages": [],
        "remaining_steps": 10,
    }

async def run_simulation_test():
    """
    Run a test of the simulation agent.
    """
    import asyncio
    import traceback

    initial_state = create_test_state()

    print("\n--- Running Simulation Agent Test ---\n")
    try:
        async for step in simulation_agent.astream(initial_state):
            print("Step Output:", step)
        print("\n--- Simulation Agent Test Completed ---\n")
    except Exception as e:
        print("Error during test run:")
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_simulation_test())