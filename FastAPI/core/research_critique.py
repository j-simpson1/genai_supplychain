from dotenv import load_dotenv
load_dotenv()

import os

from typing import List, Literal, Optional
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable
from tavily import TavilyClient

from FastAPI.core.state import AgentState
from FastAPI.core.prompts import research_critique_prompt

# Configuration
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports_and_graphs")

# Initialize clients and model
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
model = ChatOpenAI(model="o4-mini")

class TavilyJob(BaseModel):
    """Configuration for a single Tavily search job."""
    query: str = Field(..., max_length=400, description="Search query (≤400 chars)")
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
    """Plan containing multiple Tavily search jobs (max 4)."""
    jobs: List[TavilyJob] = Field(default_factory=list, max_length=4)

# Domain policies and guardrails
TARIFF_NEWS_DOMAINS = [
    "reuters.com", "bloomberg.com", "wsj.com", "ft.com", "trade.gov",
    "oecd.org", "wto.org", "imf.org", "worldbank.org", "japantimes.co.jp",
    "nikkei.com", "asia.nikkei.com", "business-standard.com", "economist.com",
    "politico.com"
]

AUTO_SUPPLY_DOMAINS = [
    "oica.net", "acea.auto", "jama.or.jp", "siam.in", "vda.de", "statista.com",
    "ihsmarkit.com", "autonews.com", "just-auto.com", "wardsauto.com",
    "motortrend.com", "carscoops.com", "globalsupplychainnews.com",
    "supplychaindigital.com", "supplychainquarterly.com", "smmt.co.uk",
    "nist.gov", "epa.gov", "ec.europa.eu", "nhtsa.gov"
]

DEFAULT_DENYLIST = [
    "wikipedia.org", "reddit.com", "quora.com", "pinterest.",
    "autodoc.", "made-in-china."
]

def enrich_job(job: TavilyJob, focus_area: str) -> TavilyJob:
    """Enrich a Tavily job with focus area-specific settings and constraints."""
    enriched_job = job.model_copy(deep=True)

    # Apply sensible bounds
    enriched_job.search_depth = (
        enriched_job.search_depth if enriched_job.search_depth in ("basic", "advanced")
        else "advanced"
    )
    enriched_job.chunks_per_source = min(max(enriched_job.chunks_per_source or 2, 1), 3)
    enriched_job.max_results = min(max(enriched_job.max_results or 1, 1), 2)

    # Merge with default denylist
    enriched_job.exclude_domains = list(
        set((enriched_job.exclude_domains or []) + DEFAULT_DENYLIST)
    )

    # Apply focus-specific settings
    if "Tariff news" in focus_area:
        enriched_job.topic = "news"
        enriched_job.time_range = enriched_job.time_range or "month"
        if not enriched_job.include_domains:
            enriched_job.include_domains = TARIFF_NEWS_DOMAINS
    elif "Supply chain" in focus_area:
        enriched_job.topic = "general"
        if not enriched_job.include_domains:
            enriched_job.include_domains = AUTO_SUPPLY_DOMAINS

    return enriched_job

# Structured planner

planner = model.with_structured_output(TavilyPlan)


@traceable(name="tavily.search")
def traced_tavily_search(params: dict) -> dict:
    """Execute Tavily search with tracing for LangSmith."""
    return tavily.search(**params)

async def research_critique_node(state: AgentState) -> dict:
    # Generate research plan from critique
    plan: TavilyPlan = planner.invoke([
        SystemMessage(content=research_critique_prompt),
        HumanMessage(content=state['critique'])
    ])

    # Define focus areas for research
    focus_areas = [
        "Supply chain of the manufacturer",
        "Tariff news – target country",
        "Tariff news – automotive sector",
        "Misc – supporting",
    ]

    # Enrich jobs with focus area context
    enriched_jobs: List[TavilyJob] = []
    for i, job in enumerate(plan.jobs[:4]):
        focus_area = focus_areas[i] if i < len(focus_areas) else "Misc – supporting"
        enriched_jobs.append(enrich_job(job, focus_area))

    # Execute searches and collect results
    web_content = state.get('web_content') or []
    for job in enriched_jobs:
        try:
            search_params = {
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

            search_response = traced_tavily_search(search_params)

            for result in search_response.get("results", []):
                web_content.append(
                    f"Source: {result.get('url')}\n"
                    f"Title: {result.get('title', '')}\n"
                    f"{result.get('content', '')}"
                )

        except Exception as e:
            web_content.append(f"[Tavily search error for '{job.query}': {e}]")

    return {"web_content": web_content}


# Initialize the graph with the agent state
subgraph = StateGraph(AgentState)

# Add nodes and edges
subgraph.add_node("research_critique", research_critique_node)

subgraph.add_edge(START, "research_critique")
subgraph.add_edge("research_critique", END)

research_critique_agent = subgraph.compile()

# output_graph_path = os.path.join(REPORTS_DIR, "research_critique_langgraph.png")
# with open(output_graph_path, "wb") as f:
#     f.write(research_critique_agent.get_graph().draw_mermaid_png())

if __name__ == "__main__":
    import asyncio
    from typing import cast

    async def run_research_test() -> None:
        """Test the research critique agent with sample data."""
        test_state = {
            "task": "Research Toyota RAV4 braking system supply chain.",
            "critique": (
                "Your submission needs greater depth and data integration. "
                "Expand the Executive Summary with quantitative insights and "
                "incorporate deeper web research on supply chain dynamics."
            ),
            "web_content": [],
        }

        print("\n--- Running Research Critique Test ---\n")
        try:
            async for step in research_critique_agent.astream(cast(AgentState, test_state)):
                print(f"Step Output: {step}")
            print("\n--- Research Critique Test Completed ---\n")
        except Exception as e:
            print(f"Error during test run: {e}")

    asyncio.run(run_research_test())

