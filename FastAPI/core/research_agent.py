from dotenv import load_dotenv
load_dotenv()

import asyncio
import os
import traceback
from typing import List, Literal, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langsmith import traceable
from pydantic import BaseModel, Field
from tavily import TavilyClient

from FastAPI.core.prompts import research_plan_prompt
from FastAPI.core.state import AgentState

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports_and_graphs")

tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
model = ChatOpenAI(model="o4-mini")

class TavilyJob(BaseModel):
    """Configuration for a Tavily search job."""
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
    """A research plan containing multiple Tavily search jobs."""
    jobs: List[TavilyJob] = Field(default_factory=list, max_items=4)

TARIFF_NEWS_DOMAINS = [
    "reuters.com",
    "bloomberg.com",
    "wsj.com",
    "ft.com",
    "trade.gov",
    "oecd.org",
    "wto.org",
    "imf.org",
    "worldbank.org",
    "japantimes.co.jp",
    "nikkei.com",
    "asia.nikkei.com",
    "business-standard.com",
    "economist.com",
    "politico.com",
]

AUTO_SUPPLY_DOMAINS = [
    "oica.net",
    "acea.auto",
    "jama.or.jp",
    "siam.in",
    "vda.de",
    "statista.com",
    "ihsmarkit.com",
    "autonews.com",
    "just-auto.com",
    "wardsauto.com",
    "motortrend.com",
    "carscoops.com",
    "globalsupplychainnews.com",
    "supplychaindigital.com",
    "supplychainquarterly.com",
    "smmt.co.uk",
    "nist.gov",
    "epa.gov",
    "ec.europa.eu",
    "nhtsa.gov",
]

DEFAULT_DENYLIST = [
    "wikipedia.org", "reddit.com", "quora.com", "pinterest.",
    "autodoc.", "made-in-china."
]

def enrich_job(job: TavilyJob, focus_area: str) -> TavilyJob:
    """Enrich a Tavily job with domain-specific configuration based on focus area."""
    enriched_job = job.model_copy(deep=True)

    enriched_job.search_depth = enriched_job.search_depth if enriched_job.search_depth in ("basic", "advanced") else "advanced"
    enriched_job.chunks_per_source = min(max(enriched_job.chunks_per_source or 2, 1), 3)
    enriched_job.max_results = min(max(enriched_job.max_results or 1, 1), 2)
    enriched_job.exclude_domains = list(set((enriched_job.exclude_domains or []) + DEFAULT_DENYLIST))

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

planner = model.with_structured_output(TavilyPlan)

@traceable(name="tavily.search")
def traced_tavily_search(params: dict):
    """Execute a Tavily search with LangSmith tracing."""
    return tavily.search(**params)

async def research_plan_node(state: AgentState):
    """Execute research plan by generating and executing multiple Tavily searches."""
    plan: TavilyPlan = planner.invoke([
        SystemMessage(content=research_plan_prompt),
        HumanMessage(content=state['task'])
    ])

    focus_labels = [
        "Supply chain of the manufacturer",
        "Tariff news – target country",
        "Tariff news – automotive sector",
        "Misc – supporting",
    ]

    jobs = [
        enrich_job(job, focus_labels[i] if i < len(focus_labels) else "Misc – supporting")
        for i, job in enumerate(plan.jobs[:4])
    ]

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
            content.append(f"[Tavily error on '{job.query}': {e}]")

    return {"web_content": content}


subgraph = StateGraph(AgentState)
subgraph.add_node("research_agent", research_plan_node)

subgraph.add_edge(START, "research_agent")
subgraph.add_edge("research_agent", END)

research_agent = subgraph.compile()

if __name__ == "__main__":
    import asyncio
    import traceback

    # Generate graph visualization only when running directly
    output_graph_path = os.path.join(REPORTS_DIR, "research_agent_langgraph.png")
    if not os.path.exists(output_graph_path):
        try:
            with open(output_graph_path, "wb") as f:
                f.write(research_agent.get_graph().draw_mermaid_png())
            print(f"Graph visualization saved to {output_graph_path}")
        except Exception as e:
            print(f"Warning: Could not generate graph visualization: {e}")

    async def run_research_test():
        """Test the research agent functionality."""
        articles_path = os.path.join(os.getcwd(), "Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
        parts_path = os.path.join(os.getcwd(), "Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")

        initial_state: AgentState = {
            "task": (
                "Write me a report on the supply chain of the Toyota RAV4 braking system. "
                "Include a tariff shock simulation for Japan with rates of 20%, 50%, 80%. "
                "Assume the following: - VAT Rate: 20% - Manufacturing country: United Kingdom"
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

        print("\n--- Running Research Agent Test ---\n")
        try:
            async for step in research_agent.astream(initial_state):
                print("Step Output:", step)
            print("\n--- Research Agent Test Completed ---\n")
        except Exception as e:
            print("Error during test run:")
            traceback.print_exc()

    asyncio.run(run_research_test())
