from typing import Annotated, Sequence, TypedDict

from autogen.agentchat.contrib.text_analyzer_agent import system_message
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from FastAPI.data.auto_parts.tecdoc import fetch_manufacturers

load_dotenv()

# global variable to store document content
document_content = ""

class AgentState(TypedDict, total=False):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    tool_calls: list

@tool
def update(content: str) -> str:
    """Updates the document with the provided content."""
    global document_content
    document_content = content
    return f"Document has been updated successfully! The current content is:\n{document_content}"

@tool
def save(filename: str) -> str:
    """Save the current document to a text file and finish the process.
    Arg:
        filename: Name for the text file.
    """
    global document_content

    if not filename.endswith('.txt'):
        filename = f"{filename}.txt"

    try:
        with open(filename, 'w') as file:
            file.write(document_content)
        print(f"\nDocument has been saved to: {filename}")
        return f"Document has been saved successfully to '{filename}'."

    except Exception as e:
        return f"Error saving document: {str(e)}"

@tool
def retrieve_manufacturers():
    """Calls the API retrieving the manufacturers by calling the TecDoc API."""
    result = fetch_manufacturers()
    brands = [m['brand'] for m in result.get('manufacturers', [])]
    for brand in brands:
        print(brand)

tools = [update, save, retrieve_manufacturers]

model = ChatOpenAI(model="gpt-4o").bind_tools(tools)

drafting_model = ChatOpenAI(model="gpt-4o")

def initial_drafter(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(content=f"""
        You are a report generator. Create a draft of a report on recent news regarding tariffs, sanctions, inflation, 
        and global supply chains, analysing the impact on automotive supply chains.
        """
    )
    user_message = HumanMessage(content="Please generate the draft report now.")

    all_messages = [system_prompt, user_message]

    response = drafting_model.invoke(all_messages)

    print("\n===== INITIAL DRAFT CREATED =====\n")
    print(response.content)
    print("\n=================================\n")

    return {
        "messages": [response],
        "tool_calls": [
            {
                "name": "update",
                "args": {"content": response.content}
            }
        ]
    }



def our_agent(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(content=f"""
        You are Drafter, a helpful writing assistant. You are going to help the user update and modify documents.

        - If the user wants to update or modify content, use the 'update' tool with the complete updated content.
        - If the user wants to save and finish, you need to use the 'save' tool.
        - Make sure to always show the current document state after modifications.

        The current document content is:{document_content}
        """)

    if not state["messages"]:
        user_input = "I'm ready to help you update a document. What would you like to create?"
        user_message = HumanMessage(content=user_input)

    else:
        user_input = input("\nWhat would you like to do with the document? ")
        print(f"\n👤 USER: {user_input}")
        user_message = HumanMessage(content=user_input)

    all_messages = [system_prompt] + list(state["messages"]) + [user_message]

    response = model.invoke(all_messages)

    print(f"\n🤖 AI: {response.content}")
    if hasattr(response, "tool_calls") and response.tool_calls:
        print(f"🔧 USING TOOLS: {[tc['name'] for tc in response.tool_calls]}")

    return {"messages": list(state["messages"]) + [user_message, response]}


def should_continue(state: AgentState) -> str:
    """Determine if we should continue or end the conversation."""

    messages = state["messages"]

    if not messages:
        return "continue"

    # This looks for the most recent tool message....
    for message in reversed(messages):
        # ... and checks if this is a ToolMessage resulting from save
        if (isinstance(message, ToolMessage) and
                "saved" in message.content.lower() and
                "document" in message.content.lower()):
            return "end"  # goes to the end edge which leads to the endpoint

    return "continue"


def print_messages(messages):
    """Function I made to print the messages in a more readable format"""
    if not messages:
        return

    for message in messages[-3:]:
        if isinstance(message, ToolMessage):
            print(f"\n🛠️ TOOL RESULT: {message.content}")


graph = StateGraph(AgentState)

graph.add_node("report_drafter", initial_drafter)
graph.add_node("agent", our_agent)
graph.add_node("tools", ToolNode(tools))

graph.set_entry_point("report_drafter")

graph.add_edge("report_drafter", "agent")
graph.add_edge("agent", "tools")

graph.add_conditional_edges(
    "tools",
    should_continue,
    {
        "continue": "agent",
        "end": END,
    },
)

app = graph.compile()


def run_document_agent():
    print("\n ===== DRAFTER =====")

    state = {"messages": []}

    for step in app.stream(state, stream_mode="values"):
        if "messages" in step:
            print_messages(step["messages"])

    print("\n ===== DRAFTER FINISHED =====")

def load_document(filename: str) -> str:
    global document_content
    try:
        with open(filename, 'r') as file:
            document_content = file.read()
        print(f"\nDocument loaded from: {filename}")
        return f"Document loaded successfully from '{filename}'."
    except Exception as e:
        return f"Error loading document: {str(e)}"


if __name__ == "__main__":
    load_document('../../exports/parts_data.csv')
    run_document_agent()
