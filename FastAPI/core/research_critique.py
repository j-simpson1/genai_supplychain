from dotenv import load_dotenv
load_dotenv()

import os

from typing import List, Literal, Optional
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langsmith import traceable

from FastAPI.core.state import AgentState
from FastAPI.core.prompts import research_critique_prompt

from tavily import TavilyClient

class ResearchQueries(BaseModel):
    queries: List[str]

# importing taviliy as using it in a slightly unconventional way
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

model = ChatOpenAI(
    model="o4-mini"
)

class TavilyJob(BaseModel):
    # ≤400 chars, focused, single-topic
    query: str = Field(..., max_length=400)
    # Planner may set; we also enforce via enrich_job()
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
    # Enforce ≤4 parametrized jobs
    jobs: List[TavilyJob] = Field(default_factory=list, max_items=4)

# --- NEW: Domain policies & guardrails ---

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

# --- replace inside enrich_job ---
def enrich_job(job: TavilyJob, focus_area: str) -> TavilyJob:
    j = job.model_copy(deep=True)

    # Sane bounds
    j.search_depth = j.search_depth if j.search_depth in ("basic", "advanced") else "advanced"
    j.chunks_per_source = min(max(j.chunks_per_source or 2, 1), 3)
    j.max_results = min(max(j.max_results or 1, 1), 2)

    # Merge denylist
    j.exclude_domains = list(set((j.exclude_domains or []) + DEFAULT_DENYLIST))

    # Focus-specific allowlists / freshness
    if "Tariff news" in focus_area:
        j.topic = "news"
        j.time_range = j.time_range or "month"
        if not j.include_domains:
            j.include_domains = TARIFF_NEWS_DOMAINS
    elif "Supply chain" in focus_area:
        j.topic = "general"
        if not j.include_domains:
            j.include_domains = AUTO_SUPPLY_DOMAINS

    return j

# --- NEW: Structured planner (model emits TavilyPlan) ---

planner = model.with_structured_output(TavilyPlan)

# --- UPDATED: research_plan_node using parametrized searches ---

@traceable(name="tavily.search")
def traced_tavily_search(params: dict):
    # LangSmith gets a single dict[str, Any]; Tavily gets kwargs.
    return tavily.search(**params)

async def research_critique_node(state: AgentState):
    # 1) Ask the model for a parametrized plan
    plan: TavilyPlan = planner.invoke([
        SystemMessage(content=research_critique_prompt),
        HumanMessage(content=state['critique'])
    ])

    # 2) Map jobs to your three Focus Areas (+ optional 4th misc)
    focus_labels = [
        "Supply chain of the manufacturer",
        "Tariff news – target country",
        "Tariff news – automotive sector",
        "Misc – supporting",
    ]

    jobs: List[TavilyJob] = []
    for i, job in enumerate(plan.jobs[:4]):
        area = focus_labels[i] if i < len(focus_labels) else "Misc – supporting"
        jobs.append(enrich_job(job, area))

    # 3) Execute searches with parameters and append to web_content
    content = state.get('web_content') or []
    for j in jobs:
        try:
            params = {
                "query": j.query,
                "topic": j.topic,
                "search_depth": j.search_depth,
                "chunks_per_source": j.chunks_per_source,
                "include_raw_content": j.include_raw_content,
                "include_answer": j.include_answer,
                "max_results": j.max_results,
                "time_range": j.time_range,
                "include_domains": j.include_domains or [],
                "exclude_domains": j.exclude_domains or [],
            }

            response = traced_tavily_search(params)

            for r in response.get("results", []):
                content.append(
                    f"Source: {r.get('url')}\n"
                    f"Title: {r.get('title', '')}\n"
                    f"{r.get('content', '')}"
                )

        except Exception as e:
            content.append(f"[Tavily error on '{j.query}': {e}]")

    return {"web_content": content}


# initialise the graph with the agent state
subgraph = StateGraph(AgentState)

# add all nodes
subgraph.add_node("research_critique", research_critique_node)

subgraph.add_edge(START, "research_critique")
subgraph.add_edge("research_critique", END)

research_critique_agent = subgraph.compile()

output_graph_path = "../reports_and_graphs/research_agent_langgraph.png"
with open(output_graph_path, "wb") as f:
    f.write(research_critique_agent.get_graph().draw_mermaid_png())

if __name__ == "__main__":
    import asyncio
    import traceback

    async def run_research_test():
        # Point these to actual test files if analyze_tariff_impact() depends on them
        articles_path = os.path.join(os.getcwd(), "Toyota_RAV4_brake_dummy_data/RAV4_brake_articles_data.csv")
        parts_path = os.path.join(os.getcwd(), "Toyota_RAV4_brake_dummy_data/RAV4_brake_parts_data.csv")

        # Minimal viable state for simulation_agent
        initial_state: AgentState = {
            "task": "Write me a report on the supply chain of the Toyota RAV4 braking system. Include a tariff shock simulation for Japan with rates of 20%, 50%, 80%. "
                    "Assume the following:"
                    "- VAT Rate: 20%"
                    "- Manufacturing country: United Kingdom",
            "plan": "",
            "draft": "",
            "critique": "Your submission demonstrates strong structuring and coverage, but it needs greater depth, consistency, and integration of data. Key improvements include expanding the Executive Summary with precise quantitative insights and clear implications for Toyota, reorganizing Key Points into focused highlights, and ensuring data alignment with short tables and a methodology note. The analysis should also incorporate deeper web research, sensitivity testing (e.g. FX swings), and prioritized recommendations with ownership, timelines, and ROI estimates. Finally, standardize references, refine visuals, and target a polished 10–12 page report plus appendix for a more professional finish.",
            "web_content": [],
            "db_content": [],
            "db_summary": "",
            "trajectory": [],
            "raw_simulation": [],  # start with no prior tool calls
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

        print("\n--- Running Research Critique Test ---\n")
        try:
            async for step in research_critique.astream(initial_state):
                print("Step Output:", step)
            print("\n--- Research Critique Test Completed ---\n")
        except Exception as e:
            print("Error during test run:")
            traceback.print_exc()

    asyncio.run(run_research_test())

# script to run open_deep_researcher

# # using open-deep-research
# query = await model.ainvoke([
#     SystemMessage(content=RESEARCH_CRITIQUE_PROMPT),
#     HumanMessage(content=state['critique'])
# ])
# # get the original content and append with new queries
# content = state['web_content'] or []
#
# response = await deep_researcher.ainvoke({
#     "messages": [HumanMessage(content=query.content)],
# })
#
# output = response['messages'][-1].content
# content.append(output)