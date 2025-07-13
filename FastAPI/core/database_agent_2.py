from FastAPI.database.database import engine
from sqlalchemy import text
import pandas as pd
import numpy as np
import json

import os
from dotenv import load_dotenv
from openai import AzureOpenAI


load_dotenv()

# Azure OpenAI setup
api_key = os.getenv("AZURE_OPENAI_API_KEY")

client = AzureOpenAI(
  azure_endpoint="https://ucabj-md0rveym-swedencentral.cognitiveservices.azure.com/",
  api_key=api_key,
  api_version="2024-05-01-preview",
)

def parts_summary():
    try:
        query = f"""
        WITH part_article_data AS (
            SELECT
                p."productGroupId",
                p."description" AS "partDescription",
                a."price",
                a."countryOfOrigin",
                s."supplierId"
            FROM
                "parts" AS p
            INNER JOIN "articlevehiclelink" AS avl
                ON p."productGroupId" = avl."productGroupId"
            INNER JOIN "articles" AS a
                ON avl."articleNo" = a."articleNo"
                AND avl."supplierId" = a."supplierId"
            INNER JOIN "suppliers" AS s
                ON a."supplierId" = s."supplierId"
        )
        ,
        country_counts AS (
            SELECT
                pad."productGroupId",
                pad."countryOfOrigin",
                COUNT(DISTINCT pad."supplierId") AS supplier_count,
                ROW_NUMBER() OVER (
                    PARTITION BY pad."productGroupId"
                    ORDER BY COUNT(DISTINCT pad."supplierId") DESC
                ) AS rn
            FROM part_article_data pad
            GROUP BY
                pad."productGroupId",
                pad."countryOfOrigin"
        )
        SELECT
            pad."productGroupId",
            MAX(pad."partDescription") AS "partDescription",
            ROUND(CAST(AVG(pad."price") AS numeric), 2)::float AS "averagePrice",
            COUNT(pad."price") AS "numArticles",
            cc."countryOfOrigin" AS "mostCommonCountryOfOrigin"
        FROM
            part_article_data pad
        LEFT JOIN
            country_counts cc
            ON pad."productGroupId" = cc."productGroupId" AND cc.rn = 1
        GROUP BY
            pad."productGroupId",
            cc."countryOfOrigin"
        ORDER BY
            pad."productGroupId";
        """
        query = text(query)

        with engine.connect() as connection:
            result = pd.read_sql_query(query, connection)
        if not result.empty:
            return result.to_dict('records')
        else:
            return np.nan
    except Exception as e:
        print(e)
        return np.nan

def top_5_parts_by_price():
    try:
        query = f"""
        SELECT
            p."productGroupId",
            p."description" AS "partDescription",
            c."description" AS "categoryDescription",
            ROUND(AVG(a."price")::numeric, 2) AS avg_price,
            COUNT(*) AS num_articles
        FROM
            "articlevehiclelink" AS avl
        INNER JOIN "articles" AS a
            ON avl."articleNo" = a."articleNo"
            AND avl."supplierId" = a."supplierId"
        INNER JOIN "parts" AS p
            ON avl."productGroupId" = p."productGroupId"
        INNER JOIN "category" AS c
            ON p."categoryId" = c."categoryId"
        GROUP BY
            p."productGroupId",
            p."description",
            c."description"
        ORDER BY
            avg_price DESC
        LIMIT 5;
        """
        query = text(query)

        with engine.connect() as connection:
            result = pd.read_sql_query(query, connection)
        if not result.empty:
            return result.to_dict('records')
        else:
            return np.nan
    except Exception as e:
        print(e)
        return np.nan

def top_5_part_distrubution_by_country():
    try:
        query = f"""
        SELECT
          a."countryOfOrigin",
          COUNT(DISTINCT a."articleNo") AS parts_count
        FROM
          "articlevehiclelink" AS avl
        INNER JOIN "articles" AS a
          ON avl."articleNo" = a."articleNo"
          AND avl."supplierId" = a."supplierId"
        GROUP BY
          a."countryOfOrigin"
        ORDER BY
          parts_count DESC
		LIMIT 5;
        """
        query = text(query)

        with engine.connect() as connection:
            result = pd.read_sql_query(query, connection)
        if not result.empty:
            return result.to_dict('records')
        else:
            return np.nan
    except Exception as e:
        print(e)
        return np.nan

messages = [
    {"role": "user",
     "content": """ can I summary of all the automotive parts?"""
    }
]

tools_sql = [
    {
        "type": "function",
        "function": {
            "name": "parts_summary",
            "description": (
                "Generates a summary for each product group, including "
                "average price, number of articles, and the most common country of origin."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "top_5_parts_by_price",
            "description": (
                "Returns the top 5 product groups by average price, including "
                "part and category descriptions, average price, and article count."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "top_5_part_distrubution_by_country",
            "description": (
                "Returns the top 5 countries of origin by number of distinct articles "
                "linked through vehicle-part associations."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
]

response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,
    tools=tools_sql,
    tool_choice="auto",
)

response_message = response.choices[0].message
tool_calls = response_message.tool_calls


if tool_calls:
    print(tool_calls)

    # Map available function names to actual functions
    available_functions = {
        "parts_summary": parts_summary,
        "top_5_parts_by_price": top_5_parts_by_price,
        "top_5_part_distrubution_by_country": top_5_part_distrubution_by_country
    }

    messages.append(response_message)

    for tool_call in tool_calls:
        function_name = tool_call.function.name
        function_to_call = available_functions.get(function_name)

        # These functions don't take any arguments
        function_response = function_to_call()

        messages.append(
            {
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": json.dumps(function_response, indent=2),
            }
        )

    print(messages)

second_response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
        )
print (second_response)


