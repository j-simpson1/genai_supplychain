import json
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
openai_key = os.getenv("OPENAI_API_KEY")


def rank_suppliers(manufacturer_name, supplier_names):
    client = OpenAI(api_key=openai_key)
    try:
        # Format the list as a readable bullet list for GPT
        supplier_list_str = "\n".join(f"- {name}" for name in supplier_names)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert in global automotive OEM supply chains. "
                    "You know which brands are actually used by each manufacturer to supply factory-installed components."
                )
            },
            {
                "role": "user",
                "content": f"""
Based on real-world supply relationships, rank the following suppliers by how commonly they are used by {manufacturer_name} as OEM suppliers.

Only consider brands that have supplied factory-installed parts (e.g., brakes, filters, electronics, etc.) to {manufacturer_name} for their production vehicles.

Do not change or reformat the supplier names.

Return your result in JSON with this structure:

{{
  "first_choice": ["brand1", "brand2", ...],
  "second_choice": ["brand3", "brand4"],
}}

Limiting results in the second_choice to 15 suppliers.

Suppliers within the same group are considered equally ranked. Focus only on actual historical or current OEM usage by {manufacturer_name}. Avoid speculation or general brand quality.

Here is the supplier list:

{supplier_list_str}
"""
            }
        ]

        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.2
        )

        # Add debugging output
        print(f"Raw response: {response.choices[0].message.content}")

        return json.loads(response.choices[0].message.content)
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Raw response content: {response.choices[0].message.content}")
        return {
            "first_choices": [],
            "second_choices": []
        }
    except Exception as e:
        print(f"Error in rank_suppliers: {e}")
        return {
            "first_choices": [],
            "second_choices": []
        }