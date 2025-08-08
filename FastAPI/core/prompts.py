from langsmith import Client

from FastAPI.core.CoT_prompting import chain_of_thought_examples

client = Client()

# prompt for the planning node
plan_prompt = client.pull_prompt("plan_prompt", include_model=False).format(
    CoT_Examples=chain_of_thought_examples
)



db_call_model_prompt = client.pull_prompt("db_call_model", include_model=False)

db_summary_prompt = client.pull_prompt("db_summary_prompt", include_model=False)

chart_planning_prompt = client.pull_prompt("chart_planning_prompt", include_model=False)

generate_chart_prompt = client.pull_prompt("generate_chart_prompt", include_model=False)

research_plan_prompt = client.pull_prompt("research_plan_prompt", include_model=False).format()

simulation_prompt = client.pull_prompt("simulation_prompt", include_model=False)

writers_prompt = client.pull_prompt("writer_prompt", include_model=False)

reflection_prompt = client.pull_prompt("reflection_prompt", include_model=False).format()

