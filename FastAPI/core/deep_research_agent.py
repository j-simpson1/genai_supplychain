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

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "output", "reports")

model = ChatOpenAI(model="gpt-4o-mini")

DEEP_RESEARCH_PROMPT = """
You are a deep research query generator for supply chain analysis.
Formulate a focused research question that uncovers alternative suppliers for the automotive parts listed in the database content below.
- Suppliers must be outside the tariff-affected country.
- Where possible, identify pricing information.
	
Database Content Available:
{db_content}

Task: {task}

Return exactly one concise research question focused on sourcing alternatives for these parts.
Output only the research question.
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

SUMMARY_PROMPT = """
You are an expert research summarizer specializing in supply chain analysis.
Summarize the key deep research findings below into **300-400 words**.

Prioritize:
1. Alternative suppliers and their locations (with company names)
2. Pricing information and cost comparisons
3. Export capabilities and certifications

Deep Research Content:
{research_content}

<Citation Rules - CRITICAL>
- The research content above already contains numbered citations with full URLs (e.g., [1] Title: https://example.com)
- You MUST preserve these exact citations in your summary
- When referencing information, use the same citation numbers from the source content
- Include inline citations [1], [2], etc. throughout your summary when referencing specific information
- At the end of your summary, include a "## References" section with ALL citations from the source content
- Keep the exact format: [1] Source Title: Full URL
- DO NOT create placeholder citations like "[1] Source Title: URL" - use the actual URLs from the research content
- Number sources sequentially without gaps (1,2,3,4...)
- Include at least 10-15 citations to ensure comprehensive coverage

EXAMPLE FORMAT:
The deep research identifies alternative suppliers for automotive braking components. In the UK, **Winnard** supplies ECE R90-approved brake discs and pads with 99% vehicle coverage [1], while **EBC Brakes** manufactures high-performance components with global distribution [2].

## References
[1] Winnard official site: https://winnard.co.uk/
[2] EBC Brakes official website: https://www.ebcbrakes.com/
</Citation Rules>
"""

@traceable(name="deep_research.query_generation")
async def generate_deep_research_query(task: str, db_content: list) -> str:
    """Generate an optimized research query for deep research using database content."""
    # Format db_content for the prompt - extract content from message objects
    if db_content:
        db_text = "\n".join([
            msg.content if hasattr(msg, 'content') else str(msg)
            for msg in db_content
        ])
    else:
        db_text = "No database content available"

    prompt_content = DEEP_RESEARCH_PROMPT.format(
        db_content=db_text,
        task=task
    )

    response = await model.ainvoke([
        SystemMessage(content=prompt_content)
    ])
    return response.content

@traceable(name="deep_research.clarification")
async def generate_clarification(question: str, task: str) -> str:
    """Generate a clarification response based on the original task context."""
    response = await model.ainvoke([
        SystemMessage(content=CLARIFICATION_PROMPT.format(task=task, question=question))
    ])
    return response.content

@traceable(name="deep_research.summary")
async def generate_research_summary(research_content: str) -> str:
    """Generate a 300-400 word summary of deep research findings with preserved citations."""
    response = await model.ainvoke([
        SystemMessage(content=SUMMARY_PROMPT.format(research_content=research_content))
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
        max_iterations = 2  # Reduced from 3 to 2

        # Configuration to moderately reduce research depth
        config = {
            "configurable": {
                "allow_clarification": False,  # Skip clarification questions for faster research
                "max_concurrent_research_units": 2,  # Reduced from 5 to 2
                "max_researcher_iterations": 1,  # Reduced from 3 to 1 (single-pass, no follow-ups)
                "max_react_tool_calls": 2,  # Reduced from 5 to 2 (fewer searches per topic)
            }
        }

        for i in range(max_iterations):
            response = await deep_researcher.ainvoke(
                {"messages": conversation},
                config=config
            )

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

async def deep_research_summary_node(state: AgentState):
    """Generate a 300-400 word summary of all deep research findings with preserved citations."""
    try:
        deep_research_content = state.get('deep_research_content', [])

        if not deep_research_content:
            return {"deep_research_summary": "No deep research content available to summarize."}

        # Combine all deep research content
        combined_content = "\n\n".join(deep_research_content)

        # Generate summary
        summary = await generate_research_summary(combined_content)

        return {"deep_research_summary": summary}

    except Exception as e:
        return {"deep_research_summary": f"[Deep research summary error: {str(e)}]"}

async def deep_research_node(state: AgentState):
    """Execute deep research analysis for supply chain insights."""
    print('\nDeep Research Agent is running and finding alternative suppliers. Expect to wait at least 5 - 10 minutes.\n')
    try:
        db_content = state.get('db_content', [])
        query = await generate_deep_research_query(state['task'], db_content)

        research_content = await execute_deep_research(query, state['task'])

        content = state.get('deep_research_content', [])
        content.append(
            f"=== DEEP RESEARCH ANALYSIS ===\n"
            f"Query: {query}\n"
            f"Results:\n{research_content}"
        )

        return {"deep_research_content": content}

    except Exception as e:
        content = state.get('deep_research_content', [])
        content.append(f"[Deep research agent error: {str(e)}]")
        return {"deep_research_content": content}

subgraph = StateGraph(AgentState)
subgraph.add_node("deep_research_agent", deep_research_node)
subgraph.add_node("deep_research_summary", deep_research_summary_node)

subgraph.add_edge(START, "deep_research_agent")
subgraph.add_edge("deep_research_agent", "deep_research_summary")
subgraph.add_edge("deep_research_summary", END)

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
        articles_path = os.path.join(os.getcwd(), "test-data/Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
        parts_path = os.path.join(os.getcwd(), "test-data/Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")

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
            "deep_research_content": [],
            "deep_research_summary": "",
            "db_content": [],
            "db_summary": "",
            "trajectory": [],
            "raw_simulation": [],
            "clean_simulation": "",
            "draft_number": 0,
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
            "tariff_path": "",
            "messages": [],
            "remaining_steps": 10,
            "coordination_decision": "",
            "current_db_step": 0,
            "total_db_steps": 0,
            "db_plan_complete": False,
            "task_ledger": {"facts": [], "hypotheses": [], "current_plan": {}},
            "progress_ledger": [],
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