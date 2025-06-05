import requests
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
gnews_key = os.getenv("GNEWS_API_KEY")
openai_key = os.getenv("OPENAI_API_KEY")

if not gnews_key:
    raise ValueError("GNEWS_API_KEY environment variable is not set.")
if not openai_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set.")

client = OpenAI(api_key=openai_key)

# Build GNews query
query = "tariff+OR+tariffs+OR+trade+barrier"
url = f'https://gnews.io/api/v4/search?q={query}&lang=en&max=10&apikey={gnews_key}'

response = requests.get(url)
data = response.json()

articles = data.get('articles', [])

# Process articles using OpenAI's API
for article in articles:
    title = article.get('title', '')
    description = article.get('description', '')
    content = f"{title}\n\n{description}"

    if "tariff" in title.lower() or "tariff" in description.lower():
        print(f"Analyzing article: {title}")

        # Ask ChatGPT if this affects the automotive sector
        prompt = (
            f"Given this news article:\n\n"
            f"Title: {title}\n"
            f"Description: {description}\n\n"
            f"Does this news indicate a new or changing tariff impacting the automotive industry supply chain? "
            f"Respond with 'Yes' or 'No' and briefly explain why."
        )

        messages = [
            {"role": "system", "content": "You are a supply chain and trade expert."},
            {"role": "user", "content": prompt}
        ]

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.2,
                max_tokens=200
            )

            answer = response.choices[0].message.content
            print("OpenAI Assessment:", answer)

            if "yes" in answer.lower():
                print("*** AUTOMOTIVE IMPACT DETECTED ***")

        except Exception as e:
            print(f"Error calling OpenAI API: {e}")

        print("-" * 50)