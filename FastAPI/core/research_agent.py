from dotenv import load_dotenv
load_dotenv()

import os

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from typing import List
from pydantic import BaseModel

from FastAPI.core.state import AgentState
from FastAPI.core.prompts import research_plan_prompt

from tavily import TavilyClient

class ResearchQueries(BaseModel):
    queries: List[str]

# importing taviliy as using it in a slightly unconventional way
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

model = ChatOpenAI(
    model="o4-mini"
)


# takes in the plan and does some research
async def research_plan_node(state: AgentState):

    # using Tavily by creating a finite list of queries
    # response with what we will invoke this with is the
    # response will be pydantic model which has the list of queries
    queries = model.with_structured_output(ResearchQueries).invoke([
        # researching planning prompt and planning prompt
        SystemMessage(content=research_plan_prompt),
        HumanMessage(content=state['task'])
    ])
    # original content
    content = state['web_content'] or []
    # loop over the queries and search for them in Tavily
    for q in queries.queries:
        response = tavily.search(query=q, max_results=2)
        for r in response['results']:
            # get the list of results and append them to the content
            content.append(f"Source: {r['url']}\n{r['content']}")

    # # using open-deep-research
    # query = await model.ainvoke([
    #     SystemMessage(content=RESEARCH_PLAN_PROMPT),
    #     HumanMessage(content=state['task'])
    # ])
    # # original content
    # content = state['web_content'] or []
    #
    # response = await deep_researcher.ainvoke({
    #     "messages": [HumanMessage(content=query.content)],
    # })
    #
    # output = response['messages'][-1].content
    # print(output)
    #
    # content.append(output)

    # return the content key which is equal to the original content plus the accumulated content
    return {"web_content": content}


# initialise the graph with the agent state
subgraph = StateGraph(AgentState)

# add all nodes
subgraph.add_node("research_agent", research_plan_node)

subgraph.add_edge(START, "research_agent")
subgraph.add_edge("research_agent", END)

research_agent = subgraph.compile()

output_graph_path = "../reports_and_graphs/research_agent_langgraph.png"
with open(output_graph_path, "wb") as f:
    f.write(research_agent.get_graph().draw_mermaid_png())

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
            "critique": "",
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

        print("\n--- Running Research Agent Test ---\n")
        try:
            async for step in research_agent.astream(initial_state):
                print("Step Output:", step)
            print("\n--- Research Agent Test Completed ---\n")
        except Exception as e:
            print("Error during test run:")
            traceback.print_exc()

    asyncio.run(run_research_test())