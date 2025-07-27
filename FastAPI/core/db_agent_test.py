from dotenv import load_dotenv
_ = load_dotenv()

from pydantic import BaseModel
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated, List
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI
import os

# Import your custom tools (already refactored to use file paths)
from FastAPI.core.database_agent_3 import (
    parts_summary,
    top_5_parts_by_price,
    top_5_part_distribution_by_country,
    parts_average_price,
    total_component_price
)

# --- UPDATED STATE ---
class AgentState(BaseModel):
    messages: Annotated[List[AnyMessage], add_messages]
    articles_path: str
    parts_path: str

class Agent:
    def __init__(self, model, tools, system=""):
        self.system = system

        graph_builder = StateGraph(AgentState)

        # --- build graph using new builder API ---
        graph_builder.add_node("llm", self.call_openai)
        graph_builder.add_node("action", self.take_action)
        graph_builder.add_edge(START, "llm")
        graph_builder.add_conditional_edges("llm", self.exists_action, {True: "action", False: END})
        graph_builder.add_edge("action", "llm")

        # compile graph
        self.graph = graph_builder.compile()

        output_graph_path = "db_langgraph.png"
        with open(output_graph_path, "wb") as f:
            f.write(self.graph.get_graph().draw_mermaid_png())

        # tools and model
        self.tools = {t.name: t for t in tools}
        self.model = model.bind_tools(tools)

    def exists_action(self, state: AgentState):
        result = state.messages[-1]
        return len(result.tool_calls) > 0

    def call_openai(self, state: AgentState):
        messages = state.messages
        if self.system:
            messages = [SystemMessage(content=self.system)] + messages
        message = self.model.invoke(messages)
        return {'messages': [message]}

    def take_action(self, state: AgentState):
        tool_calls = state.messages[-1].tool_calls
        results = []
        for t in tool_calls:
            print(f"Calling: {t}")
            if t['name'] not in self.tools:
                print("\n ....bad tool name....")
                result = "bad tool name, retry"
            else:
                # Inject file paths from state into tool call
                args = dict(t['args'])
                args["articles_path"] = state.articles_path
                args["parts_path"] = state.parts_path
                result = self.tools[t['name']].invoke(args)
            results.append(ToolMessage(tool_call_id=t['id'], name=t['name'], content=str(result)))
        print("Back to the model!")
        return {'messages': results}

# --- Prompt ---
prompt = """You are a parts database assistant. Use the available tools to summarize parts, 
analyze prices, and retrieve distribution information. Always return clear, structured data when possible.
The file paths required by the tools are available from AgentState:
- articles_path - path to the articles CSV file
- parts_path - path to the parts CSV file
"""

model = ChatOpenAI(model="gpt-4o")
tools = [
    parts_summary,
    top_5_parts_by_price,
    top_5_part_distribution_by_country,
    parts_average_price,
    total_component_price
]

abot = Agent(model, tools, system=prompt)

if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Build full paths
    articles_path = os.path.join(BASE_DIR, "Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
    parts_path = os.path.join(BASE_DIR, "Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")

    # Pass file paths into state
    state = AgentState(
        messages=[HumanMessage(content="Give me the parts summary as well as the total price of the component.")],
        articles_path=articles_path,
        parts_path=parts_path
    )
    result = abot.graph.invoke(state)

    print(result["messages"][-1].content)