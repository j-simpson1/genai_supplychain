import openai
from dotenv import load_dotenv
import os
import time

from FastAPI.core.database_agent_2 import parts_average_price

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_type = "openai"


def format_data_as_csv(data):
    return "partDescription,averagePrice\n" + "\n".join(
        f"{item['partDescription']},{item['averagePrice']}" for item in data
    )


def create_chart_assistant():
    return openai.beta.assistants.create(
        name="ChartPlotter",
        instructions="You are a data assistant who generates Python code to plot data.",
        tools=[{"type": "code_interpreter"}],
        model="gpt-4o"
    )


def run_chart_assistant(assistant_id, csv_data):
    thread = openai.beta.threads.create()

    openai.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=f"""Here is a list of average part prices in CSV format:

        {csv_data}

        Use Python to plot a bar chart with part description on the x-axis and average price on the y-axis.
        """
    )

    run = openai.beta.threads.runs.create(thread_id=thread.id, assistant_id=assistant_id)

    # Wait for completion
    while True:
        run_status = openai.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run_status.status == "completed":
            break
        elif run_status.status in ["failed", "cancelled", "expired"]:
            raise RuntimeError(f"Run failed: {run_status.status}")
        time.sleep(1)

    return thread.id


def get_image_from_thread(thread_id):
    messages = openai.beta.threads.messages.list(thread_id=thread_id)
    for msg in messages.data:
        print(f"Role: {msg.role}, Content types: {[c.type for c in msg.content]}")
        for content in msg.content:
            if content.type == "image_file":
                return content.image_file.file_id
    raise ValueError("No image found in assistant response.")


def save_image(file_id, output_path="plot.png"):
    image_response = openai.files.with_raw_response.retrieve_content(file_id)
    with open(output_path, "wb") as f:
        f.write(image_response.content)


# === Main Execution ===
data = parts_average_price()
csv_data = format_data_as_csv(data)

assistant = create_chart_assistant()
thread_id = run_chart_assistant(assistant.id, csv_data)
image_file_id = get_image_from_thread(thread_id)

print(f"Chart image file ID: {image_file_id}")
save_image(image_file_id)