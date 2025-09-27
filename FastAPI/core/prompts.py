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



db_call_model_prompt = client.pull_prompt("db_call_model", include_model=False)

db_summary_prompt = client.pull_prompt("db_summary_prompt", include_model=False)

chart_planning_prompt = client.pull_prompt("chart_planning_prompt", include_model=False)

generate_chart_prompt = client.pull_prompt("generate_chart_prompt", include_model=False)

research_plan_prompt = client.pull_prompt("research_plan_prompt_2", include_model=False).format()

simulation_prompt = client.pull_prompt("simulation_prompt", include_model=False)

simulation_clean_prompt = client.pull_prompt("simulation_clean_prompt", include_model=False)

writers_prompt = client.pull_prompt("writer_prompt", include_model=False)

reflection_prompt = client.pull_prompt("reflection_prompt", include_model=False).format()

research_critique_prompt = client.pull_prompt("research_critique_prompt_2", include_model=False).format()

