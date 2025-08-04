from langsmith import Client

from FastAPI.core.CoT_prompting import chain_of_thought_examples

client = Client()

# prompt for the planning node
PLAN_PROMPT = client.pull_prompt("plan_prompt").format(
    COT_EXAMPLES=chain_of_thought_examples
)