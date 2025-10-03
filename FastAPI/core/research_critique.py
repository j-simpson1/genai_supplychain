from dotenv import load_dotenv
load_dotenv()

import asyncio
import os
import traceback
from typing import List, Literal, Optional

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langsmith import traceable
from pydantic import BaseModel, Field
from tavily import TavilyClient

from FastAPI.core.prompts import research_critique_prompt
from FastAPI.core.state import AgentState

# Configuration
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "output", "reports")

# Initialize clients and model
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
model = ChatOpenAI(model="o4-mini")

class SimpleTavilyJob(BaseModel):
    """Simple job schema for query generation - only contains the search query."""
    query: str = Field(max_length=400, description="Search query (≤400 chars)")

class TavilyPlan(BaseModel):
    """A simple research plan containing only search queries."""
    jobs: List[SimpleTavilyJob] = Field(default_factory=list, max_items=6)

class TavilyJob(BaseModel):
    """Configuration for a single Tavily search job."""
    query: str = Field(max_length=400, description="Search query (≤400 chars)")
    topic: Literal["general", "news"] = "general"
    search_depth: Literal["basic", "advanced"] = "advanced"
    max_results: int = 1
    time_range: Optional[Literal["day", "week", "month", "year"]] = None
    include_domains: Optional[List[str]] = None
    exclude_domains: Optional[List[str]] = None
    chunks_per_source: int = 2
    include_raw_content: bool = True
    include_answer: Literal[False, "basic", "advanced"] = False

class TavilyPlan(BaseModel):
    """A research plan containing multiple Tavily search jobs."""
    jobs: List[TavilyJob] = Field(default_factory=list, max_items=6)

TARIFF_NEWS_DOMAINS = [
    # Major Financial & Business News
    "reuters.com",
    "bloomberg.com",
    "wsj.com",
    "ft.com",
    "economist.com",
    "cnbc.com",
    "barrons.com",
    "marketwatch.com",

    # Government & International Organizations
    "trade.gov",
    "oecd.org",
    "wto.org",
    "imf.org",
    "worldbank.org",
    "ustr.gov",
    "census.gov",
    "bea.gov",

    # Asia-Pacific News
    "japantimes.co.jp",
    "nikkei.com",
    "asia.nikkei.com",
    "scmp.com",
    "business-standard.com",
    "economictimes.indiatimes.com",
    "straitstimes.com",
    "channelnewsasia.com",

    # European News
    "euractiv.com",
    "ec.europa.eu",

    # Trade & Supply Chain Focused
    "joc.com",
    "freightwaves.com",
    "supplychaindive.com",
    "logistics-manager.com",
    "americanshipper.com",
    "inboundlogistics.com",

    # Business & Policy
    "politico.com",
    "forbes.com",
    "fortune.com",
    "businessinsider.com",
    "axios.com",
]


DEFAULT_DENYLIST = [
    "wikipedia.org", "reddit.com", "quora.com", "pinterest."
]

def enrich_job(job: TavilyJob) -> TavilyJob:
    """Enrich a Tavily job with tariff news configuration."""
    enriched_job = job.model_copy(deep=True)

    enriched_job.search_depth = enriched_job.search_depth if enriched_job.search_depth in ("basic", "advanced") else "advanced"
    enriched_job.chunks_per_source = min(max(enriched_job.chunks_per_source or 2, 1), 3)
    enriched_job.max_results = min(max(enriched_job.max_results or 1, 1), 2)
    enriched_job.exclude_domains = list(set((enriched_job.exclude_domains or []) + DEFAULT_DENYLIST))

    # Configure for tariff news
    enriched_job.topic = "news"
    enriched_job.time_range = enriched_job.time_range or "month"
    # Append tariff news domains, removing duplicates
    existing_domains = enriched_job.include_domains or []
    enriched_job.include_domains = list(set(existing_domains + TARIFF_NEWS_DOMAINS))

    return enriched_job

planner = model.with_structured_output(TavilyPlan)


@traceable(name="tavily.search")
def traced_tavily_search(params: dict) -> dict:
    """Execute Tavily search with tracing for LangSmith."""
    return tavily.search(**params)

async def research_critique_node(state: AgentState):
    """Execute research plan by generating and executing multiple Tavily searches."""
    try:
        simple_plan: TavilyPlan = planner.invoke([
            HumanMessage(content=research_critique_prompt.format(critique=state['critique']))
        ])

        # Validate that we got valid jobs
        if not simple_plan.jobs or len(simple_plan.jobs) == 0:
            raise ValueError("No search queries generated")

        # Convert SimpleTavilyJob to TavilyJob with default parameters
        jobs = [TavilyJob(query=job.query) for job in simple_plan.jobs]

    except Exception as e:
        print(f"Warning: Research critique query generation failed ({e}). Using fallback queries.")
        traceback.print_exc()
        # Fallback: Generate generic tariff queries for critique research
        jobs = [
            TavilyJob(query="automotive supply chain tariff news recent developments"),
            TavilyJob(query="manufacturing tariffs trade policy automotive sector")
        ]

    jobs = [enrich_job(job) for job in jobs[:6]]

    content = state.get('web_content', [])
    for job in jobs:
        try:
            params = {
                "query": job.query,
                "topic": job.topic,
                "search_depth": job.search_depth,
                "chunks_per_source": job.chunks_per_source,
                "include_raw_content": job.include_raw_content,
                "include_answer": job.include_answer,
                "max_results": job.max_results,
                "time_range": job.time_range,
                "include_domains": job.include_domains or [],
                "exclude_domains": job.exclude_domains or [],
            }

            response = traced_tavily_search(params)

            for result in response.get("results", []):
                content.append(
                    f"Source: {result.get('url')}\n"
                    f"Title: {result.get('title', '')}\n"
                    f"{result.get('content', '')}"
                )

        except Exception as e:
            print(f"Warning: Tavily search error on '{job.query}': {e}")
            content.append(f"[Tavily error on '{job.query}': {e}]")

    return {"web_content": content}


subgraph = StateGraph(AgentState)
subgraph.add_node("research_critique", research_critique_node)

subgraph.add_edge(START, "research_critique")
subgraph.add_edge("research_critique", END)

research_critique_agent = subgraph.compile()

if __name__ == "__main__":
    import asyncio
    import traceback

    # Generate graph visualization only when running directly
    output_graph_path = os.path.join(REPORTS_DIR, "research_critique_langgraph.png")
    if not os.path.exists(output_graph_path):
        try:
            with open(output_graph_path, "wb") as f:
                f.write(research_critique_agent.get_graph().draw_mermaid_png())
            print(f"Graph visualization saved to {output_graph_path}")
        except Exception as e:
            print(f"Warning: Could not generate graph visualization: {e}")

    async def run_research_test():
        """Test the research critique agent functionality."""
        articles_path = os.path.join(os.getcwd(), "test-data/Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
        parts_path = os.path.join(os.getcwd(), "test-data/Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")

        initial_state: AgentState = {
            "task": (
                "Write me a report on the supply chain of the Toyota RAV4 braking system. "
                "Include a tariff shock simulation for Japan with rates of 20%, 50%, 80%. "
                "Assume the following: - VAT Rate: 20% - Manufacturing country: United Kingdom"
            ),
            "plan": "",
            "draft": "",
            "critique": (
                "Your submission needs greater depth and data integration. "
                "Expand the Executive Summary with quantitative insights and "
                "incorporate deeper web research on supply chain dynamics."
            ),
            "web_content": [],
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
            "messages": [],
            "remaining_steps": 10,
        }

        print("\n--- Running Research Critique Agent Test ---\n")
        try:
            async for step in research_critique_agent.astream(initial_state):
                print("Step Output:", step)
            print("\n--- Research Critique Agent Test Completed ---\n")
        except Exception as e:
            print("Error during test run:")
            traceback.print_exc()

    asyncio.run(run_research_test())

