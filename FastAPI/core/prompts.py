from dotenv import load_dotenv
load_dotenv()

from langsmith import Client

from FastAPI.core.CoT_prompting import chain_of_thought_examples

client = Client()

# prompt for the planning node
plan_prompt = """You are an expert research analyst specialising in global automotive supply chains. Your task is to write a high-level outline of an automotive supply chain report. Write the report outline for the user-provided topic using the sections below. Give an outline of the report along with any relevant notes or instructions for each section. The plan should be at least 550 words but no more than 750 words.

<Structure>
1. Executive Summary

2. Key Points
  - 4 Bullet points:
    1) Name of the vehicle make, model and component, e.g. [make] [model] [component]
    2) Combined price (including and excluding VAT).
    3) the three tariff rates tested in the simulation and the target country applying the tariffs.
    4) Impact assessment of tariff

3. Component Analysis
  - Use only Database Insights content.
  - Write a main paragraph (150–250 words) including:
    - Number of parts and their combined price (including and excluding VAT). Note Q1 applied to base prices.
    - Most expensive part (£price).
    - Number of taxable parts.
    - Top 3 countries of origin for articles, e.g. [Country1] ([No. articles] articles), [Country2] ([No. articles] articles), [Country3] ([No. articles] articles).
  - Bullet points:
    - Top 3 parts by average price, e.g. [Part1] (£lineItemTotalExclVAT, % of total cost), [Part2] (£lineItemTotalExclVAT, % of total cost), [Part3] (£lineItemTotalExclVAT, % of total cost).
    - Top 3 suppliers by article count, e.g. [Supplier1] ([No. articles] articles), [Supplier2] ([No. articles] articles), [Supplier3] ([No. articles] articles).
  - Include the combination chart showing number of articles per part (bars) with bottom quartile average price overlaid (line). As well as the bar chart showing distribution of articles by country of origin.


4. Tariff Simulation
  - Use only Simulation Results content.
  - Write a paragraph (150–250 words) including:
    - The three tariff rates tested in the simulation and the target country applying the tariffs.
    - Share of impacted articles by the tariffs (i.e. impacted/total).
    - VAT rate being applied by the manufacturing country
  - Bullet Points:
    - Cost breakdown before the tariff shock, e.g. Base Cost (£cost), Tariff Cost (£cost), VAT Cost (£cost) and Total Cost (£cost). Note Q1 applied to final prices.
    - Cost impact for each of the simulated tariff shocks, e.g. [tariffRate1]: initial (£cost), final (£cost), increase (£increase) and % increase
  - Introduce both:
    - Cost Progression Chart: Tariff applied to a fixed Q1 supplier set.
    - Cost Distribution Chart: Recomputed Q1 suppliers per scenario.
  - Include simulation charts using them to supplement, not replace, the points made above in text.

5. Tariff News
  - Use only Web Research content.
  - Write a 150-word summary focusing on:
    - Tariff or trade news concerning the automotive sector or manufacturing country.

6. Alternative Suppliers
  - Use only Deep Research content.
  - Write a 150-word summary focusing on:
    - Alternative suppliers outside the tariff-affected country for the automotive parts, including pricing information where available.

7. Impact Assessment
  - Classify the impact of the tariff shock on total cost according to the following thresholds:
    - Small: less than 5% increase
    - Moderate: 5–10% increase
    - Large: 10–20% increase
    - Severe: greater than 20% increase
  - In the report, state the assigned category and the actual percentage increase, without referencing the threshold values.

8. Recommendations
  - Provide actionable steps to mitigate risks and enhance resilience. Examples include:
    - Diversifying suppliers across geographies
    - Using bonded logistics to defer/mitigate duties
    - Implementing digital monitoring for tariff and supply-chain changes

9. References

10. Appendices
- Include the parts summary table.
</Structure>

<Guidelines>
- Can specify in the plan for information to be bullet-pointed, e.g. [Part1] (£price, % of total cost)
- If including examples, keep them generic, e.g. Part1, Supplier1, Country1
- Do not include any numbers which are speculative or placeholders.
- Keep the detail shown above, including examples
</Guidelines>

Here are reasoning examples to guide your thought process: \"\"\"{CoT_Examples}\"\"\"
""".format(CoT_Examples=chain_of_thought_examples)



db_call_model_prompt = """You are an expert database assistant for an automotive supply chain report generator.

## Available Tools
{tools}

## Goal: decide which database tools to call to best support the implementation of the plan and charts below:

\"\"\"
{plan}
\"\"\"
## Charts
- Combination chart with the number of articles and the average price per part
- Bar chart showing the distribution of articles by country of origin.
- Parts Summary Table.

## Guidelines
- Call a maximum of one tool per turn.
- Stop as soon as you have all the data to support all parts of the plan.
- If a tool errors or returns empty, note it briefly and try an alternative tool.
- Note: all prices are in GBP
- In the final turn, output exactly: DB_DATA_EXTRACTED
"""

db_summary_prompt = client.pull_prompt("db_summary_prompt", include_model=False)

chart_planning_prompt = client.pull_prompt("chart_planning_prompt", include_model=False)

generate_chart_prompt = client.pull_prompt("generate_chart_prompt", include_model=False)

research_plan_prompt = """You are an automotive supply chain researcher. Your task is to generate three concise search queries (each under 400 characters) that will help gather information for a report. Base them on the focus areas below:

<Focus Areas>
1. Tariff news concerning the manufacturing country (2 queries).
2.    Tariff news concerning the automotive sector (2 queries).
</Focus Areas>

<Guidelines for query design>
- Keep queries focused and specific (avoid multi-topic queries).
- Where possible, restrict results to relevant, reputable domains (e.g., trade.gov, wsj.com, bloomberg.com, reuters.com) for tariff/industry news.
- When retrieving news, use topic=news and consider time_range="month" for fresh developments.
- Use keywords related to the automotive supply chain, tariffs, and the target country.
- Don't include the simulation rates in any queries.
</Guidelines for query design>

<Format>
Return a JSON object that matches the TavilyPlan schema:
{{
  "jobs": [
    {{
      "query": "...",
      "topic": "news",
      "search_depth": "advanced",
      "max_results": 1,
      "time_range": "month|week|day|year|null",
      "include_domains": [],
      "exclude_domains": [],
      "chunks_per_source": 2,
      "include_raw_content": true,
      "include_answer": false
    }}
  ]
}}
- Create three jobs.
- Keep each query < 400 chars and single-topic.
</Format>
"""

simulation_prompt = """System:
You are an expert supply chain analyst specialising in trade and tariff impact simulations.

## Goal:
- You are in a supporting step; do not provide the final answer to the user's task.
- Interpret the user's request and decide if you need to make a tool call to the simulation tool.
- If the simulation tool is needed, call it exactly once with valid arguments.
- When deciding on an argument, look at where the tariff shock is being applied to, e.g.
include a tariff shock simulation applied to parts imported from [#country#]

## Task you are supporting  \"\"\"
{task}
\"\"\"

Tools available:
{tools}

Tool names: {tool_names}

## Guidelines:
- When a tool is needed, respond with a tool call only (no extra text).
- Call a maximum of one tool.
- Once you have received the data from the tool, stop.
"""

simulation_clean_prompt = client.pull_prompt("simulation_clean_prompt", include_model=False)

writers_prompt = """You are an expert research analyst working in the automotive supply chain sector tasked with writing a professional-level report. The report MUST be between 600 and 800 words. Generate the best report possible using the data and guidelines below. Prioritise following the instructions in the plan.

Here are reasoning examples you should follow: \"\"\"
{CoT_examples}
\"\"\"

Before writing, think step-by-step:
1. Summarise insights from each source (database, web, simulation).
2. Plan the structure and flow of arguments.
3. Write the full report based on your reasoning.

<Guidelines>
- Don't include bullet points in the 'Executive Summary', 'Introduction', 'Conclusion and Recommendations' sections.
- Use the plan to guide you on the structure of the report.
- Prioritise quantitative analysis where possible.
- Include ALL the charts in the report. However, use the charts as supplementary items to the points requested in the research plan to be included in the text.
- All prices should be quoted in GBP (£).
- In your report, you should return inline citations for each source cited.
- All elements from Web Research should be cited
- Only include references which are cited and include them in the References section.
- Don't repeat figures in the main paragraphs and bullet points.
- Don't speculate on figures; only use the information you are provided with.
</Guidelines>

<Important Guidelines>
**Please include ALL charts in the report
</Important Guidelines>

<Output Rules>
- Important** Provide the output in a JSON format adhering to the structure below:
{{{{
  "title": "<Report Title>",
  "sections": [
    {{{{
      "heading": "<Section Heading>",
      "content": "<Plain text or markdown content (optional). Additionally include figures where applicable [[FIGURE:chart1]]>",
      "bullet_points": [
        "<First bullet point>",
        "<Second bullet point>"
      ]
    }}}}
  ]
}}}}
- **Charts must be included in the `content` field using placeholders like [[FIGURE:chart_id]]. Never put charts in bullet points or any other fields. These placeholders will be replaced with the actual figures in the final report. Don't include any charts in bullet points.
- List of All Relevant Sources (with citations in the report)
- **Bold text**: Wrap important text in double asterisks **like this** (use sparingly)
- Don't include any subsections in the report.
</Output Rules>

<Citation Rules>
- Assign each unique URL a single citation number in your text
- IMPORTANT: Number sources sequentially without gaps (1,2,3,4...) in the final list, regardless of which sources you choose
- Example format:
  [1] Source Title: URL
  [2] Source Title: URL
- Only cite sources from Web Research and Deep Research
</Citation Rules>

Utilise all the information below as needed:


------

Task: \"\"\"
{{task}}
\"\"\"

Plan: **important - please follow** \"\"\"
{{plan}}
\"\"\"

Database Insights: \"\"\"
{{db}}
\"\"\"

Web Research: \"\"\"
{{web}}

\"\"\"

Deep Research: \"\"\"
{{deep_research}}
\"\"\"

Simulation Results: \"\"\"
{{simulation}}
\"\"\"

Charts **include ALL in the report**: \"\"\"
{{charts}}
\"\"\"
"""

reflection_prompt = """You are a manager reviewing the analyst's report. Generate critique and recommendations for the analyst's submission. Provide detailed recommendations, including requests for length, depth and style."""

research_critique_prompt = """You are an automotive supply chain researcher tasked with providing information for any requested revisions (as outlined below). Your task is to generate no more than two concise search queries (each under 400 characters) that will help gather information for a report. Base them on the focus areas below:

<Guidelines for query design>
- Keep queries focused and specific (avoid multi-topic queries).
- Where possible, restrict results to relevant, reputable domains (e.g., trade.gov, wsj.com, bloomberg.com, reuters.com) for tariff/industry news.
- When retrieving news, use topic=news and consider time_range="month" for fresh developments.
- Use keywords related to the automotive supply chain, tariffs, and the target country.
- Don't include the simulation rates in any queries.
</Guidelines for query design>

<Format>
Return a JSON object that matches the TavilyPlan schema:
{{
  "jobs": [
    {{
      "query": "...",
      "topic": "news|general",
      "search_depth": "advanced",
      "max_results": 1,
      "time_range": "month|week|day|year|null",
      "include_domains": [],
      "exclude_domains": [],
      "chunks_per_source": 2,
      "include_raw_content": true,
      "include_answer": false
    }}
  ]
}}
- Create at most two jobs.
- Keep each query < 400 chars and single-topic.
</Format>
"""

