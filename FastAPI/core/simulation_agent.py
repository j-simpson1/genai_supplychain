import matplotlib
matplotlib.use("Agg")

from dotenv import load_dotenv
load_dotenv()

import os
import math
import json
from typing import List, Union
from pydantic import BaseModel, Field

from langchain_core.messages import ToolMessage
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain.agents import tool

from FastAPI.core.state import AgentState
from FastAPI.core.prompts import simulation_prompt
from FastAPI.core.prompts import simulation_clean_prompt
from FastAPI.core.utils import convert_numpy
from FastAPI.automotive_simulation.simulation import analyze_tariff_impact

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports_and_graphs")

class SimulationResultsInput(BaseModel):
    simulation_result: dict

class simulation_inputs(BaseModel):
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
    args_schema=simulation_inputs,
    description="Run an automotive tariff shock simulation after normalising and validating inputs."
)
def automotive_tariff_simulation(target_country: str, tariff_rates: List[Union[int, float]]) -> dict:
    """
    Run an automotive tariff shock simulation for the given country at the specified rates.
    - Normalises tariff rates: integers like 20 -> 0.2; keeps decimals in [0,1].
    - Validates: non-blank target_country; at least one valid rate.
    - Post-checks: result is a non-empty dict; all numbers finite; JSON-serialisable via convert_numpy.
    Returns the simulation result dict from analyze_tariff_impact(...).
    """
    # --- Input checks ---
    if not target_country.strip():
        raise ValueError("target_country cannot be blank.")
    rates = _normalize_rates(tariff_rates)
    if not rates:
        raise ValueError("No valid tariff rates after normalization.")

    # --- Run simulation ---
    result = analyze_tariff_impact(target_country=target_country.strip(), tariff_rates=rates)

    # --- Output checks ---
    if not isinstance(result, dict) or not result:
        raise ValueError("Simulation returned empty or non-dict result.")
    _assert_finite_numbers(result)
    try:
        json.dumps(result, default=convert_numpy)
    except Exception as e:
        raise TypeError(f"Output not JSON-serialisable: {e}")

    return result


simulation_tools = [automotive_tariff_simulation]

# create models
simulation_model = ChatOpenAI(model="o4-mini").bind_tools(simulation_tools)
model = ChatOpenAI(model="o4-mini")


def simulation_tool_node(state: AgentState):
    """
    Enhanced tool node that handles both automotive_tariff_simulation and simulation_results_analyst.
    Uses articles_path and parts_path from AgentState.
    """
    outputs = []
    messages = state.get("raw_simulation", [])
    if not messages:
        return {}

    last_message = messages[-1]
    chart_metadata = list(state.get("chart_metadata", []))

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            args = tool_call["args"]
            tool_call_id = tool_call["id"]

            if tool_name == "automotive_tariff_simulation":
                try:
                    articles_path = state.get("articles_path")
                    parts_path = state.get("parts_path")

                    result = analyze_tariff_impact(
                        suppliers_csv_path=articles_path,
                        parts_csv_path=parts_path,
                        target_country=args["target_country"].strip(),
                        tariff_rates=_normalize_rates(args["tariff_rates"])
                    )

                except Exception as e:
                    result = {"error": str(e)}

                # Extract chart metadata if charts were generated
                if "output_files" in result and "chart_paths" in result["output_files"]:
                    chart_paths = result["output_files"]["chart_paths"]
                    for chart_id, chart_path in chart_paths.items():
                        chart_id_clean = os.path.splitext(os.path.basename(chart_path))[0]
                        existing_paths = [meta["path"] for meta in chart_metadata]
                        if chart_path not in existing_paths:
                            chart_metadata.append({
                                "id": chart_id_clean,
                                "path": chart_path
                            })

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

    # task message no longer needed but commented out in case it needs to be added back in
    # task_message = HumanMessage(content=state['task'])

    prompt = simulation_prompt.format(
        task=state["task"],
        tools=simulation_tools,
        tool_names=[t.name for t in simulation_tools]
    )
    response = simulation_model.invoke([prompt] + state["raw_simulation"])

    return {"raw_simulation": state["raw_simulation"] + [response]}

def simulation_clean(state: AgentState):
    simulation_output = "\n\n".join(str(m.content) for m in state["raw_simulation"])

    messages = simulation_clean_prompt.format_messages(simulation_output=simulation_output)

    response = model.invoke(messages)

    return {"clean_simulation": response}


def simulation_should_continue(state: AgentState):
    messages = state.get("raw_simulation", [])
    if not messages:
        return "end"
    last = messages[-1]
    tool_calls = getattr(last, "tool_calls", None)
    return "continue" if tool_calls else "end"


# initialise the graph with the agent state
subgraph = StateGraph(AgentState)

# add all nodes
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

simulation_agent = subgraph.compile()

output_graph_path = os.path.join(REPORTS_DIR, "simulation_agent_langgraph.png")
with open(output_graph_path, "wb") as f:
    f.write(simulation_agent.get_graph().draw_mermaid_png())

if __name__ == "__main__":
    import asyncio
    import traceback

    async def run_simulation_test():
        # Point these to actual test files if analyze_tariff_impact() depends on them
        articles_path = os.path.join(os.getcwd(), "Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
        parts_path = os.path.join(os.getcwd(), "Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")

        # Minimal viable state for simulation_agent
        initial_state: AgentState = {
            "task": "Run a tariff shock simulation for Japan with 20%, 40%, and 70% rates.",
            "plan": "",
            "draft": "",
            "critique": "",
            "web_content": [],
            "db_content": [],
            "db_summary": "",
            "trajectory": [],
            "raw_simulation": [],  # start with no prior tool calls
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
            "messages": [],
            "remaining_steps": 10,
        }

        print("\n--- Running Simulation Agent Test ---\n")
        try:
            async for step in simulation_agent.astream(initial_state):
                print("Step Output:", step)
            print("\n--- Simulation Agent Test Completed ---\n")
        except Exception as e:
            print("Error during test run:")
            traceback.print_exc()

    asyncio.run(run_simulation_test())