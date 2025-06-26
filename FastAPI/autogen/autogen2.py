import asyncio
from importlib.metadata import always_iterable

from autogen_agentchat.agents import AssistantAgent, MessageFilterAgent, MessageFilterConfig, PerSourceFilter
from autogen_agentchat.teams import (
    DiGraphBuilder,
    GraphFlow,
)
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

import os
from dotenv import load_dotenv

from FastAPI.autogen.save_pdf import save_text_to_pdf

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")

async def main():

    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

    # Agents

    # manufacturing_origin = AssistantAgent(
    #     "manufacturing_origin",
    #     model_client=model_client,
    #     system_message="When required to run the simulation with the inputs provided by the user."
    # )
    #
    # simulation_runner = AssistantAgent(
    #     "simulation_runner",
    #     model_client=model_client,
    #     system_message="When required to run the simulation with the inputs provided by the user."
    # )
    #
    # simulation_analyst = AssistantAgent(
    #     "simulation_analyst",
    #     model_client=model_client,
    #     system_message="To analyse the data produced from the simulation."
    # )

    researcher = AssistantAgent(
        "researcher_agents",
        model_client=model_client,
        system_message="To look for recent news on tariffs, sanctions, inflation and global supply chains."
    )

    report_writer = AssistantAgent(
        "report_writer_agent",
        model_client=model_client,
        system_message="To structure and write the final report from analysis and research."
    )

    report_critic = AssistantAgent(
        "report_critic",
        model_client=model_client,
        system_message="To review the report for clarity, correctness and style providing feedback. If happy 'APPROVE' for final approval."
    )

    presenter = AssistantAgent(
        "presenter", model_client=model_client, system_message="Prepare the report for final submission."
    )

    filtered_presenter = MessageFilterAgent(
        name="presenter",
        wrapped_agent=presenter,
        filter=MessageFilterConfig(per_source=[PerSourceFilter(source="report_critic", position="last", count=1)]),
    )

    # Build graph with conditional loop
    builder = DiGraphBuilder()
    builder.add_node(researcher).add_node(report_writer).add_node(report_critic).add_node(filtered_presenter)

    builder.add_edge(researcher, report_writer)
    builder.add_edge(report_writer, report_critic)
    builder.add_edge(report_critic, filtered_presenter)

    builder.set_entry_point(researcher)  # Set entry point to generator. Required if there are no source nodes.
    graph = builder.build()

    # Create the flow
    flow = GraphFlow(
        participants=builder.get_participants(),
        graph=graph,
    )

    graph = builder.build()
    print(graph)

    task = "Analyse the current state of automotive supply chains."

    # Option 2: Run without streaming (simpler for getting the final result)
    result = await flow.run(task=task)

    # Access the final message from the result
    # Method 1: Get all messages from the result
    all_messages = result.messages
    if all_messages:
        final_message = all_messages[-2]
        final_text = final_message.content
        print("\n\n--- Final output ---\n")
        print(f"From: {final_message.source}")
        print(f"Content: {final_text}")

    # # Extract final text from result
    # text_output = result.messages[-1].content
    #
    # # Save to PDF
    # save_text_to_pdf(text_output, filename="supply_chain_report.pdf")

if __name__ == "__main__":
    asyncio.run(main())