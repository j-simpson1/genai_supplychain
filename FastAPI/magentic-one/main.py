from dotenv import load_dotenv
import os
import asyncio

# Load environment variables from .env
load_dotenv()

# --- App-specific Imports ---
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.agents.web_surfer import MultimodalWebSurfer

# --- Prompt Templates ---
PLAN_PROMPT = """You are an expert research analyst tasked with writing a high level outline of an automotive supply \
chain report. Write such an outline for the user provided topic using the sections below...

1. Executive Summary
2. Introduction
...
"""

WRITER_PROMPT = """You are a research analyst tasked with writing a report of at least 800 words and at most 1000...
Provide the output in JSON using the structure:

{
  "title": "...",
  "sections": [...]
}
"""

print("Testing...")

REFLECTION_PROMPT = """You are a manager reviewing the analyst's report. Generate critique and recommendations..."""
RESEARCH_PLAN_PROMPT = """You are a researcher. Generate 3 search queries to inform the following report task..."""
RESEARCH_CRITIQUE_PROMPT = """Generate 3 new search queries to assist with the critique below..."""

async def main() -> None:

    # --- LLM Setup ---
    model_client = OpenAIChatCompletionClient(model="gpt-4o")

    # --- Define Agents ---
    planner = AssistantAgent("Planner", model_client, system_message=PLAN_PROMPT)
    db_agent = AssistantAgent("DatabaseAnalyst", model_client, system_message="Access database insights and recommend figures.")
    researcher = MultimodalWebSurfer("Researcher", model_client=model_client)
    writer = AssistantAgent("Writer", model_client, system_message=WRITER_PROMPT)
    critic = AssistantAgent("Critic", model_client, system_message=REFLECTION_PROMPT)
    revision_researcher = AssistantAgent("RevisionResearcher", model_client, system_message=RESEARCH_CRITIQUE_PROMPT)

    # --- Define Team ---
    team = MagenticOneGroupChat(
        participants=[planner, db_agent, researcher, writer, critic, revision_researcher],
        model_client=model_client,
        max_turns=5,
    )

    task = "Write a report on Toyota RAV4 supply chains."

    result = await Console(team.run_stream(task=task))
    print(result)


asyncio.run(main())
