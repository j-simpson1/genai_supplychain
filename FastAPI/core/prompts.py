from langsmith import Client

from FastAPI.core.CoT_prompting import chain_of_thought_examples

client = Client()

# prompt for the planning node
plan_prompt = client.pull_prompt("plan_prompt").format(
    CoT_Examples=chain_of_thought_examples
)

research_plan_prompt = client.pull_prompt("research_plan_prompt").format()
