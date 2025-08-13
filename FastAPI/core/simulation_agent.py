import matplotlib
matplotlib.use("Agg")

from dotenv import load_dotenv
load_dotenv()

import os
from pydantic import BaseModel, Field
import json
from typing import List, Union

from langchain_core.messages import ToolMessage
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain.agents import tool

from FastAPI.core.state import AgentState
from FastAPI.core.prompts import simulation_prompt
from FastAPI.core.utils import convert_numpy
from FastAPI.automotive_simulation.simulation import analyze_tariff_impact
from FastAPI.core.prompts import simulation_clean_prompt


class SimulationResultsInput(BaseModel):
    simulation_result: dict

class simulation_inputs(BaseModel):
    target_country: str = Field(..., description="Country to simulate tariff shock for")
    tariff_rates: List[Union[int, float]] = Field(..., description="Tariff rates; either decimals (0.1) or integers (10).")


@tool(args_schema=simulation_inputs)
def automotive_tariff_simulation(target_country: str, tariff_rates: List[Union[int, float]]) -> dict:
    """
    Run an automotive tariff shock simulation for the given country at the specified rates.
    Accepts decimals (e.g., 0.1 for 10%) or integers (e.g., 10 for 10%) and normalizes
    everything to decimals in [0, 1]. Returns a JSON-serializable dict from analyze_tariff_impact().
    """
    normalized_rates = []
    for r in tariff_rates:
        if isinstance(r, (int, float)):
            if 0 <= r <= 1:
                normalized_rates.append(float(r))
            elif 1 < r <= 100:
                normalized_rates.append(float(r) / 100.0)
            elif r == 1:
                # Treat 1 as 1% to match user expectations
                normalized_rates.append(0.01)
            else:
                raise ValueError(f"Invalid rate {r}. Use 0–1 or 0–100.")
        else:
            raise ValueError(f"Non-numeric rate {r!r}")
    response = analyze_tariff_impact(target_country, normalized_rates)
    return convert_numpy(response)


simulation_tools = [automotive_tariff_simulation]

# create models
simulation_model = ChatOpenAI(model="o4-mini").bind_tools(simulation_tools)
model = ChatOpenAI(model="o4-mini")


def simulation_tool_node(state: AgentState):
    """
    Enhanced tool node that handles both automotive_tariff_simulation and simulation_results_analyst
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
                # Execute the tariff simulation tool
                try:
                    result = automotive_tariff_simulation.invoke(args)
                except Exception as e:
                    result = {"error": str(e)}

                # Extract chart metadata from simulation results
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

                # Create the tool message with full result
                outputs.append(ToolMessage(
                    content=json.dumps(result),
                    name=tool_name,
                    tool_call_id=tool_call_id
                ))
            else:
                # Handle unknown tools
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