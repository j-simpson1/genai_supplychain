from dotenv import load_dotenv
load_dotenv()

import asyncio
import os
import sys
import traceback
from pathlib import Path
from typing import Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langsmith import traceable

from FastAPI.core.state import AgentState

# Add the FastAPI directory to Python path to enable open_deep_research imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from open_deep_research.deep_researcher import deep_researcher
except ImportError as e:
    deep_researcher = None
    print(f"Warning: open_deep_research import failed: {e}")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports_and_graphs")

model = ChatOpenAI(model="gpt-4o-mini")

DEEP_RESEARCH_PROMPT = """
You are a deep research query generator for supply chain analysis.
Transform the user's task into a focused research question that will uncover:
- Alternative suppliers and pricing (if possible) for the parts shown in the data below

Provide a clear, specific research question that will yield actionable supply chain insights.
"""

CLARIFICATION_PROMPT = """
You are a clarification assistant for supply chain research. The deep researcher has asked a clarifying question.
Based on the original task context, provide a reasonable answer that will help the research continue effectively.

Original Task: {task}
Question from Researcher: {question}

Provide a concise, helpful answer based on typical supply chain analysis requirements. If the question involves:
- Geographic scope: Default to global with focus on major markets (US, EU, Asia)
- Time horizon: Default to current + 2-year outlook
- Data specificity: Request both quantitative and qualitative insights
- Industry focus: Stay within automotive/manufacturing context from the original task
"""

@traceable(name="deep_research.query_generation")
async def generate_deep_research_query(task: str) -> str:
    """Generate an optimized research query for deep research."""
    response = await model.ainvoke([
        SystemMessage(content=DEEP_RESEARCH_PROMPT),
        HumanMessage(content=task)
    ])
    return response.content

@traceable(name="deep_research.clarification")
async def generate_clarification(question: str, task: str) -> str:
    """Generate a clarification response based on the original task context."""
    response = await model.ainvoke([
        SystemMessage(content=CLARIFICATION_PROMPT.format(task=task, question=question))
    ])
    return response.content

def is_clarification_question(content: str) -> bool:
    """Check if the content appears to be a clarifying question rather than final results."""
    question_indicators = [
        "?", "could you clarify", "which specific", "what type of",
        "are you looking for", "do you want", "should I focus on",
        "clarification needed", "please specify"
    ]
    return any(indicator in content.lower() for indicator in question_indicators)

@traceable(name="deep_research.execution")
async def execute_deep_research(query: str, task: str) -> str:
    """Execute deep research with automatic clarification handling."""
    if deep_researcher is None:
        return "[Deep research unavailable - open_deep_research not installed]"

    try:
        conversation = [HumanMessage(content=query)]
        max_iterations = 3

        for i in range(max_iterations):
            response = await deep_researcher.ainvoke({
                "messages": conversation
            })

            content = response['messages'][-1].content

            # Check if this is a final result or needs clarification
            if not is_clarification_question(content) or i == max_iterations - 1:
                return content

            # Generate clarification based on original task
            clarification = await generate_clarification(content, task)
            conversation.append(HumanMessage(content=clarification))

        return content
    except Exception as e:
        return f"[Deep research error: {str(e)}]"

async def deep_research_node(state: AgentState):
    """Execute deep research analysis for supply chain insights."""
    try:
        query = await generate_deep_research_query(state['task'])

        research_content = await execute_deep_research(query, state['task'])

        content = state.get('web_content', [])
        content.append(
            f"=== DEEP RESEARCH ANALYSIS ===\n"
            f"Query: {query}\n"
            f"Results:\n{research_content}"
        )

        return {"web_content": content}

    except Exception as e:
        content = state.get('web_content', [])
        content.append(f"[Deep research agent error: {str(e)}]")
        return {"web_content": content}

subgraph = StateGraph(AgentState)
subgraph.add_node("deep_research_agent", deep_research_node)

subgraph.add_edge(START, "deep_research_agent")
subgraph.add_edge("deep_research_agent", END)

deep_research_agent = subgraph.compile()

if __name__ == "__main__":
    output_graph_path = os.path.join(REPORTS_DIR, "deep_research_agent_langgraph.png")
    if not os.path.exists(output_graph_path):
        try:
            with open(output_graph_path, "wb") as f:
                f.write(deep_research_agent.get_graph().draw_mermaid_png())
            print(f"Graph visualization saved to {output_graph_path}")
        except Exception as e:
            print(f"Warning: Could not generate graph visualization: {e}")

    async def run_deep_research_test():
        """Test the deep research agent functionality."""
        articles_path = os.path.join(os.getcwd(), "Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
        parts_path = os.path.join(os.getcwd(), "Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")

        initial_state: AgentState = {
            "task": (
                "Research alternative suppliers for Toyota RAV4 brake components. "
                "Focus on European and North American suppliers that could replace "
                "Japanese suppliers in case of supply chain disruption."
            ),
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
            "messages": [],
            "remaining_steps": 10,
        }

        print("\n--- Running Deep Research Agent Test ---\n")
        try:
            async for step in deep_research_agent.astream(initial_state):
                print("Step Output:", step)
            print("\n--- Deep Research Agent Test Completed ---\n")
        except Exception as e:
            print("Error during test run:")
            traceback.print_exc()

    asyncio.run(run_deep_research_test())