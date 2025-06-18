import json
from openai import OpenAI
from dotenv import load_dotenv
import os
import pandas as pd

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
            model="gpt-4.1-mini",
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



def generate_price_estimation(df: pd.DataFrame):
    client = OpenAI(api_key=openai_key)

    try:
        # Build a prompt list of part details
        parts_prompt = ""
        for _, row in df.iterrows():
            parts_prompt += (
                f"- Category: {row['categoryName']} | Supplier: {row['supplierName']} | "
                f"Part Name: {row['articleProductName']} | Article No: {row['articleNo']}\n"
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are an automotive parts pricing analyst. "
                    "Based on historical pricing trends, supplier tier, and part type, estimate realistic wholesale prices for each part below. "
                    "Do not speculate beyond the data given. Assume standard EU pricing levels. Return the result in JSON format as a list of objects."
                )
            },
            {
                "role": "user",
                "content": f"""
Estimate the price (in GBP) for each of the following parts. Use the part type, supplier name, and any hints from the product name.

Return in the following JSON format:

[
  {{
    "articleNo": "XXX",
    "estimatedPriceGBP": 12.34
  }},
  ...
]

Here is the part list:

{parts_prompt}
"""
            }
        ]

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.3
        )

        print("Raw response:")
        print(response.choices[0].message.content)

        return json.loads(response.choices[0].message.content)

    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        return []
    except Exception as e:
        print(f"Error in generate_price_estimation: {e}")
        return []