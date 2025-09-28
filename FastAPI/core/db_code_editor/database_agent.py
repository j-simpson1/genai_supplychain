from dotenv import load_dotenv
load_dotenv()

import os
import json

from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
import re

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from state import SharedState
from database_tools import parts_summary, top_5_parts_by_price, top_5_part_distribution_by_country, bottom_quartile_average_price, total_component_price, top_5_suppliers_by_articles

tools = [
    parts_summary,
    top_5_parts_by_price,
    top_5_part_distribution_by_country,
    bottom_quartile_average_price,
    total_component_price,
    top_5_suppliers_by_articles
]

# Remove tool binding for ReAct pattern
db_model = ChatOpenAI(
    model="o4-mini"
)

tools_by_name = {tool.name: tool for tool in tools}

# Create tool descriptions for ReAct prompt
tool_descriptions = []
tool_names = []
for tool in tools:
    tool_descriptions.append(f"{tool.name}: {tool.description}")
    tool_names.append(tool.name)

tool_names_str = ", ".join(tool_names)
tool_descriptions_str = "\n".join(tool_descriptions)


# --- Tool Node ---
def tool_node(state: SharedState):
    """Execute tools based on ReAct pattern parsing"""
    last_message = state["db_content"][-1]
    content = last_message.content

    # Parse the last action from the AI message
    action_match = re.search(r'Action: (.+?)\nAction Input: (.+?)(?=\n|$)', content, re.DOTALL)

    if not action_match:
        # No action found, return observation indicating this
        observation = "Observation: No valid action found. Please use the format 'Action: tool_name\nAction Input: arguments'"
        return {"db_content": state["db_content"] + [AIMessage(content=observation)]}

    tool_name = action_match.group(1).strip()
    action_input = action_match.group(2).strip()

    # Parse action input (assuming JSON format)
    try:
        args = json.loads(action_input) if action_input.startswith('{') else {}
    except json.JSONDecodeError:
        args = {}

    # Inject paths
    args["articles_path"] = state["articles_path"]
    args["parts_path"] = state["parts_path"]

    if tool_name not in tools_by_name:
        result = f"Unknown tool '{tool_name}'. Available tools: {tool_names_str}"
    else:
        try:
            result = tools_by_name[tool_name].invoke(args)
        except Exception as e:
            result = f"Error executing tool: {str(e)}"

    # Format as ReAct observation
    observation = f"Observation: {json.dumps(result, indent=2)}"

    return {"db_content": state["db_content"] + [AIMessage(content=observation)]}


# --- Model Node ---
def call_model(state: SharedState, config=None):
    """Generate ReAct-style responses"""

    # Build agent scratchpad from conversation history
    agent_scratchpad = ""
    for msg in state["db_content"]:
        if isinstance(msg, AIMessage):
            agent_scratchpad += msg.content + "\n"

    # Create ReAct prompt
    react_prompt = f"""Answer the following questions as best you can. You have access to the following tools:

{tool_descriptions_str}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names_str}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: You are a database assistant helping with the drafting of an automotive supply chain report. Use the available tools to retrieve the relevant data for the report. Just return a summary of the raw data from the tools. See the following report plan to guide you what data to extract: {state.get('plan', 'No plan provided')}
Thought:{agent_scratchpad}"""

    response = db_model.invoke([HumanMessage(content=react_prompt)], config)
    return {"db_content": state["db_content"] + [response]}

def db_should_continue(state: SharedState):
    """Determine if we should continue based on ReAct pattern"""
    last_message = state["db_content"][-1]
    content = last_message.content

    # Check if the response contains "Final Answer" - if so, we're done
    if "Final Answer:" in content:
        return "end"

    # Check if there's an Action in the response - if so, continue to tools
    if re.search(r'Action: (.+?)\nAction Input:', content, re.DOTALL):
        return "continue"

    # If neither, we should continue to let the model respond
    return "end"

db_builder = StateGraph(SharedState)
db_builder.add_node("db_agent", call_model)
db_builder.add_node("db_tools", tool_node)
# db_builder.add_node("summarize_db", summarize_db_node)
db_builder.set_entry_point("db_agent")
db_builder.add_conditional_edges(
    "db_agent",
    db_should_continue,
    {"continue": "db_tools", "end": END}
)
db_builder.add_edge("db_tools", "db_agent")
database_agent = db_builder.compile(name="database_agent")

if __name__ == "__main__":
    # Example state for testing
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    parts_path = os.path.join(BASE_DIR, "../Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")
    articles_path = os.path.join(BASE_DIR, "../Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")


    state = {
        "db_content": [],
        "articles_path": articles_path,
        "parts_path": parts_path,
        "plan": "Call the total cost tool and parts summary."
    }
    import asyncio
    async def run():
        async for step in database_agent.astream(state):
            print(step)
    asyncio.run(run())