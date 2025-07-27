from dotenv import load_dotenv
_ = load_dotenv()

import os
import json
from pydantic import BaseModel
from typing import Annotated, List
from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage
)
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI

# --- Import custom tools ---
from FastAPI.core.database_agent_3 import (
    parts_summary,
    top_5_parts_by_price,
    top_5_part_distribution_by_country,
    parts_average_price,
    total_component_price
)

# --- Pydantic State ---
class AgentState(BaseModel):
    db_content: Annotated[List[AnyMessage], add_messages]
    articles_path: str
    parts_path: str

# --- Tools & Model ---
tools = [
    parts_summary,
    top_5_parts_by_price,
    top_5_part_distribution_by_country,
    parts_average_price,
    total_component_price
]

model = ChatOpenAI(model="gpt-4o").bind_tools(tools)
tools_by_name = {tool.name: tool for tool in tools}

# --- Tool Node ---
def tool_node(state: AgentState):
    outputs = []
    last_message = state.db_content[-1]
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        args = dict(tool_call["args"])
        # Inject paths
        args["articles_path"] = state.articles_path
        args["parts_path"] = state.parts_path

        if tool_name not in tools_by_name:
            result = "Unknown tool, please retry."
        else:
            result = tools_by_name[tool_name].invoke(args)

        outputs.append(ToolMessage(
            content=json.dumps(result),
            name=tool_name,
            tool_call_id=tool_call["id"]
        ))
    return {"db_content": outputs}

# --- Model Node ---
def call_model(state: AgentState, config=None):
    system_prompt = SystemMessage(content="""
You are a parts database assistant. Use the available tools to summarize parts,
analyze prices, and retrieve distribution information.
The file paths required by the tools are available from state:
- articles_path - path to the articles CSV file
- parts_path - path to the parts CSV file
""")
    response = model.invoke([system_prompt] + state.db_content, config)
    return {"db_content": [response]}

# --- Branching ---
def should_continue(state: AgentState):
    last_message = state.db_content[-1]
    return "continue" if last_message.tool_calls else "end"

# --- Graph Build ---
workflow = StateGraph(AgentState)
workflow.add_node("db_agent", call_model)
workflow.add_node("db_tools", tool_node)
workflow.set_entry_point("db_agent")
workflow.add_conditional_edges("db_agent", should_continue, {"continue": "db_tools", "end": END})
workflow.add_edge("db_tools", "db_agent")
graph = workflow.compile()

# --- Visualization (optional) ---
output_graph_path = "db_langgraph.png"
with open(output_graph_path, "wb") as f:
    f.write(graph.get_graph().draw_mermaid_png())

# --- Example Run ---
if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    articles_path = os.path.join(BASE_DIR, "Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
    parts_path = os.path.join(BASE_DIR, "Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")

    state = AgentState(
        db_content=[HumanMessage(content="Give me the parts summary as well as the total price of the component.")],
        articles_path=articles_path,
        parts_path=parts_path
    )

    result = graph.invoke(state)
    print(result["db_content"][-1].content)