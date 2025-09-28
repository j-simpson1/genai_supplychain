import re
from typing import List
from dataclasses import dataclass, field

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from FastAPI.core.state import AgentState
from FastAPI.core.research_agent import traced_tavily_search, enrich_job  # reuse your guardrails

model = ChatOpenAI(model="o4-mini")

@dataclass
class Thought:
    content: str
    score: float = -1e9
    meta: dict = field(default_factory=dict)

def _select_top_k(thoughts: List[Thought], k: int) -> List[Thought]:
    return sorted(thoughts, key=lambda t: t.score, reverse=True)[:k]

_PROPOSER = """You will generate DIVERSE search queries for the task:

{task}

Produce EXACTLY {n} distinct queries, each ≤ 300 characters, covering different angles 
(e.g., market context, suppliers, tariffs, regulations, recent news).
Format strictly:
1) ...
2) ...
3) ...
"""

_JUDGE = """Score this query 0–10 for this task:

Task:
{task}

Query:
{query}

Criteria (equal weight):
- Coverage of task requirements
- Specificity (not too broad)
- Likelihood of high-quality sources (good domains)
- Freshness potential (news vs evergreen)

Return ONLY a number.
"""

def _propose_queries(task: str, n: int) -> List[str]:
    txt = model.invoke([SystemMessage(content=_PROPOSER.format(task=task, n=n))]).content
    return [m.strip() for m in re.findall(r"^\s*\d+\)\s*(.+)$", txt, flags=re.MULTILINE)][:n]

def _score_query(task: str, q: str) -> float:
    raw = model.invoke([SystemMessage(content=_JUDGE.format(task=task, query=q))]).content.strip()
    m = re.search(r"(\d+(\.\d+)?)", raw)
    try:
        return float(m.group(1)) if m else 0.0
    except:
        return 0.0

def _run_query_with_guardrails(query: str, focus_area: str = "Supply chain") -> List[str]:
    # Reuse your enrich_job() to apply allow/deny lists, freshness, etc.
    from pydantic import BaseModel, Field
    from typing import Optional, Literal

    class QuickJob(BaseModel):
        query: str = Field(..., max_length=400)
        topic: Literal["general","news"] = "general"
        search_depth: Literal["basic","advanced"] = "advanced"
        max_results: int = 1
        time_range: Optional[Literal["day","week","month","year"]] = None
        include_domains: Optional[List[str]] = None
        exclude_domains: Optional[List[str]] = None
        chunks_per_source: int = 2
        include_raw_content: bool = True
        include_answer: Literal[False, "basic", "advanced"] = False

    job = QuickJob(query=query)
    job = enrich_job(job, focus_area)
    params = job.model_dump()
    resp = traced_tavily_search(params)

    out = []
    for r in resp.get("results", []):
        out.append(
            f"Source: {r.get('url')}\n"
            f"Title: {r.get('title','')}\n"
            f"{r.get('content','')}"
        )
    return out

def research_tot_node(state: AgentState):
    width = max(2, int(state.get("tot_width", 3)))
    depth = max(1, int(state.get("tot_depth", 1)))

    # Depth 1: propose & score
    seeds = _propose_queries(state["task"], n=width)
    thoughts = []
    for q in seeds:
        thoughts.append(Thought(content=q, score=_score_query(state["task"], q)))

    top = _select_top_k(thoughts, k=width)
    web = list(state.get("web_content") or [])

    # Execute top@depth-1
    for t in top:
        web.extend(_run_query_with_guardrails(t.content, "Supply chain"))

    # Optional depth 2: follow-ups based on current gaps
    if depth > 1 and top:
        follow_prompt = (
            "Given the task and the evidence gathered so far (below), propose "
            f"{width} SPECIFIC follow-up queries that fill the biggest gaps. "
            "Format strictly as numbered list.\n\n"
            f"TASK:\n{state['task']}\n\n"
            "EVIDENCE (snippets):\n" + "\n\n".join(web[:6])  # keep prompt size modest
        )
        follow_txt = model.invoke([SystemMessage(content=follow_prompt)]).content
        follow = [m.strip() for m in re.findall(r"^\s*\d+\)\s*(.+)$", follow_txt, flags=re.MULTILINE)][:width]
        follow_thoughts = [Thought(content=q, score=_score_query(state["task"], q)) for q in follow]
        for t in _select_top_k(follow_thoughts, k=width):
            web.extend(_run_query_with_guardrails(t.content, "Supply chain"))

    return {"web_content": web}

if __name__ == "__main__":

    initial_state: AgentState = {
        "task": "Write a supply-chain report on Toyota RAV4 braking system with tariff shock for Japan (20%, 50%, 80%). Include recent tariff policy updates and supplier landscape.",
        "web_content": [],
        "tot_width": 3,
        "tot_depth": 1,  # try 2 later
        # ... other required keys you already set in your pipeline ...
    }