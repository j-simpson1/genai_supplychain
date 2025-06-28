from typing import Annotated, Sequence, TypedDict

from autogen.agentchat.contrib.text_analyzer_agent import system_message
from dotenv import load_dotenv
import os

from langchain.agents import initialize_agent, AgentType
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_community.tools import TavilySearchResults

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

search_tool = TavilySearchResults(api_key=os.environ["TAVILY_API_KEY"])

search_model = ChatOpenAI(model="gpt-4o").bind_tools([search_tool])

search_agent = initialize_agent(
    [search_tool],
    ChatOpenAI(model="gpt-4o"),
    agent=AgentType.OPENAI_FUNCTIONS,
    verbose=False
)


def researcher(state: AgentState) -> AgentState:
    query = (
        "Find recent news about tariffs, sanctions, inflation, "
        "and automotive supply chains. Summarize in 3-5 bullet points "
        "with publication dates and URLs."
    )

    summary = search_agent.run(query)
    ai_msg = AIMessage(content=summary)

    return {
        "messages": state.get("messages", []) + [
            HumanMessage(content=query),
            ai_msg
        ],
        "tool_calls": [],
    }


def initial_drafter(state: AgentState) -> AgentState:
    system_prompt = SystemMessage(content=f"""
        You are a report generator. Create a draft of a report on recent news regarding tariffs, sanctions, inflation, 
        and global supply chains, analysing the impact on automotive supply chains.
        """
    )
    user_message = HumanMessage(content="Please generate the draft report now.")

    all_messages = [system_prompt, user_message]

    response = drafting_model.invoke(all_messages)

    print("\n\n===== INITIAL DRAFT CREATED =====\n")
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
    
        IMPORTANT INSTRUCTION:
        - Unless the user specifically asks to change or remove other sections, you MUST preserve the existing document content exactly as it is.
        - When the user requests an adjustment, integrate only the requested changes, and clearly indicate which section was changed.
        - You should output the complete updated document text (including unchanged parts) after applying any edits.
        - If the user only asks to review or comment, do not make changes—only provide comments.
    
        The current document content is:
    
        {document_content}
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

    for msg in messages[-3:]:
        if isinstance(msg, ToolMessage):
            print(f"\n🛠️ TOOL RESULT: {msg.content}")
        elif isinstance(msg, AIMessage):
            print(f"\n RESEARCHER: {msg.content}")


graph = StateGraph(AgentState)

graph.add_node("researcher", researcher)
graph.add_node("report_drafter", initial_drafter)
graph.add_node("agent", our_agent)
graph.add_node("tools", ToolNode(tools))

graph.set_entry_point("researcher")

graph.add_edge("researcher", "report_drafter")
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
