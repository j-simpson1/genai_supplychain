from typing import Annotated, Sequence, TypedDict
from dotenv import load_dotenv
import os

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_community.tools import TavilySearchResults

from FastAPI.data.auto_parts.tecdoc import fetch_manufacturers

load_dotenv()

# Global variable to store document content
document_content = ""


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


@tool
def update(content: str) -> str:
    """Updates the document with the provided content."""
    global document_content
    document_content = content
    return f"Document has been updated successfully! The current content is:\n{document_content}"


@tool
def save(filename: str) -> str:
    """Save the current document to a text file and finish the process.
    Args:
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
    return f"Retrieved {len(brands)} manufacturers"


tools = [update, save, retrieve_manufacturers]

# Models
model = ChatOpenAI(model="gpt-4o").bind_tools(tools)
drafting_model = ChatOpenAI(model="gpt-4o")
search_tool = TavilySearchResults(api_key=os.environ["TAVILY_API_KEY"])


def researcher(state: AgentState) -> AgentState:
    """Research node - gathers information about tariffs and supply chains"""
    print("\n🔍 Starting research phase...")

    query = (
        "Find recent news about tariffs, sanctions, inflation, "
        "and automotive supply chains. Summarize in 3-5 bullet points "
        "with publication dates and URLs."
    )

    # Use search tool directly
    search_results = search_tool.invoke({"query": query})

    # Create a prompt for the model to summarize the results
    summary_prompt = f"""
    Based on the following search results, create a summary about recent news regarding tariffs, sanctions, inflation, and automotive supply chains. 
    Summarize in 3-5 bullet points with publication dates and URLs where available.

    Search Results:
    {search_results}
    """

    # Get summary from the model
    summary_response = drafting_model.invoke([HumanMessage(content=summary_prompt)])
    summary = summary_response.content

    # Log the research results
    print("\n===== RESEARCH COMPLETED =====")
    print(f"{summary}")
    print("===== END OF RESEARCH =====\n")

    # Create AI message with the research summary
    ai_msg = AIMessage(content=summary)

    return {
        "messages": [
            HumanMessage(content=query),
            ai_msg
        ]
    }


def initial_drafter(state: AgentState) -> AgentState:
    """Draft the initial report based on research"""
    print("\n📝 Creating initial draft...")

    # Get the research summary from the last AI message
    research_summary = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, AIMessage):
            research_summary = msg.content
            break

    system_prompt = SystemMessage(content=f"""
        You are a report generator. Create a draft of a report on recent news regarding tariffs, sanctions, inflation,
        and global supply chains, analyzing the impact on automotive supply chains.

        Use the following research summary as your main source:
        {research_summary}
        """)

    user_message = HumanMessage(content="Please generate the draft report now.")
    all_messages = [system_prompt, user_message]

    response = drafting_model.invoke(all_messages)

    # Log the draft creation
    print("\n===== INITIAL DRAFT CREATED =====")
    print(response.content)
    print("===== END OF INITIAL DRAFT =====\n")

    # Return the response message AND trigger the update tool
    return {
        "messages": [
            user_message,
            AIMessage(
                content=response.content,
                tool_calls=[{
                    "name": "update",
                    "args": {"content": response.content},
                    "id": "update_call_1"
                }]
            )
        ]
    }


def agent_node(state: AgentState) -> AgentState:
    """Interactive agent for document editing"""
    print("\n💬 Ready for user interaction...")

    system_prompt = SystemMessage(content=f"""
        You are Drafter, a helpful writing assistant. You help users update and modify documents.

        IMPORTANT INSTRUCTIONS:
        - Unless the user specifically asks to change or remove other sections, preserve existing content exactly.
        - When requested, integrate only the requested changes and indicate which section was changed.
        - Output the complete updated document text (including unchanged parts) after applying edits.
        - If the user only asks to review or comment, do not make changes—only provide comments.

        The current document content is:
        {document_content}
        """)

    # Get user input
    user_input = input("\nWhat would you like to do with the document? ")
    print(f"\n👤 USER: {user_input}")

    user_message = HumanMessage(content=user_input)

    # Get all messages and add the system prompt
    all_messages = [system_prompt] + list(state.get("messages", [])) + [user_message]

    # Get response from the model
    response = model.invoke(all_messages)

    # Log the interaction
    print(f"\n🤖 AI: {response.content}")
    if hasattr(response, "tool_calls") and response.tool_calls:
        print(f"🔧 USING TOOLS: {[tc['name'] for tc in response.tool_calls]}")

    return {"messages": [user_message, response]}


def should_continue(state: AgentState) -> str:
    """Determine if we should continue or end the conversation."""
    messages = state.get("messages", [])

    if not messages:
        return "continue"

    # Check for save tool usage in recent messages
    for message in reversed(messages[-3:]):  # Check last 3 messages
        if isinstance(message, ToolMessage):
            if "saved" in message.content.lower() and "document" in message.content.lower():
                return "end"
        elif isinstance(message, AIMessage) and hasattr(message, 'tool_calls'):
            if any(tc.get('name') == 'save' for tc in message.tool_calls or []):
                return "end"

    return "continue"


def load_document(filename: str) -> str:
    """Load a document from file"""
    global document_content
    try:
        with open(filename, 'r') as file:
            document_content = file.read()
        print(f"\nDocument loaded from: {filename}")
        return f"Document loaded successfully from '{filename}'."
    except Exception as e:
        return f"Error loading document: {str(e)}"


# Build the graph
def create_graph():
    """Create and compile the LangGraph"""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("researcher", researcher)
    graph.add_node("report_drafter", initial_drafter)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))

    # Set entry point
    graph.set_entry_point("researcher")

    # Add edges
    graph.add_edge("researcher", "report_drafter")
    graph.add_edge("report_drafter", "tools")
    graph.add_edge("tools", "agent")

    # Add conditional edges
    graph.add_conditional_edges(
        "agent",
        lambda state: "tools" if any(
            hasattr(msg, 'tool_calls') and msg.tool_calls
            for msg in state.get("messages", [])[-1:]
        ) else "continue",
        {
            "tools": "tools",
            "continue": "agent"
        }
    )

    graph.add_conditional_edges(
        "tools",
        should_continue,
        {
            "continue": "agent",
            "end": END,
        },
    )

    return graph.compile()


def run_document_agent():
    """Main execution function"""
    print("\n===== STARTING DOCUMENT AGENT =====")

    # Create the graph
    app = create_graph()

    # Initial state
    state = {"messages": []}

    # Run the graph
    try:
        final_state = app.invoke(state)
        print("\n===== DOCUMENT AGENT COMPLETED =====")
        return final_state
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        return None


if __name__ == "__main__":
    # Load initial document if needed
    # load_document('../../exports/parts_data.csv')

    # Run the agent
    run_document_agent()