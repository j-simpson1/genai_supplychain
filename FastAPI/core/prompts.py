from dotenv import load_dotenv
load_dotenv()

from FastAPI.core.CoT_prompting import chain_of_thought_planning_examples, chain_of_thought_writing_examples

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
    - Number of parts and their combined price (including and excluding VAT).
    - Most expensive part (£price).
    - Number of taxable parts.
    - Top 3 countries of origin for articles, e.g. [Country1] ([No. articles] articles), [Country2] ([No. articles] articles), [Country3] ([No. articles] articles).
  - Bullet points:
    - Top 3 parts by average price, e.g. [Part1] (£lineItemTotalExclVAT, % of total cost), [Part2] (£lineItemTotalExclVAT, % of total cost), [Part3] (£lineItemTotalExclVAT, % of total cost).
    - Top 3 suppliers by article count, e.g. [Supplier1] ([No. articles] articles), [Supplier2] ([No. articles] articles), [Supplier3] ([No. articles] articles).
  - Include the combination chart showing number of articles per part (bars) with bottom quartile average price overlaid (line). As well as the bar chart showing distribution of articles by country of origin.
  - Include the parts summary table.


4. Tariff Simulation
  - Use only Simulation Results content.
  - Write a paragraph (150–250 words) including:
    - The three tariff rates tested in the simulation and the target country applying the tariffs.
    - Number of articles imported from the target country.
    - VAT rate being applied by the manufacturing country
  - Bullet Points:
    - Cost breakdown before the tariff shock, e.g. Base Cost (£cost), Tariff Cost (£cost), VAT Cost (£cost) and Total Cost (£cost).
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
</Structure>

<Guidelines>
- Can specify in the plan for information to be bullet-pointed, e.g. [Part1] (£price, % of total cost)
- If including examples, keep them generic, e.g. Part1, Supplier1, Country1
- Do not include any numbers which are speculative or placeholders.
- Keep the detail shown above, including examples
</Guidelines>

Here are reasoning examples to guide your thought process: \"\"\"{CoT_Examples}\"\"\"
""".format(CoT_Examples=chain_of_thought_planning_examples)



data_call_model_prompt = """You are an expert data assistant for an automotive supply chain report generator using the ReAct (Reasoning + Acting) framework.

## Available Tools
{tools}

## Goal: call database tools to gather data for the implementation of the plan and charts below:

\"\"\"
{plan}
\"\"\"
## Charts
- Combination chart with the number of articles and the average price per part
- Bar chart showing the distribution of articles by country of origin.
- Parts Summary Table.

## ReAct Framework
Use reasoning to guide your tool selection:

**Think**: Before each action, consider:
- What information do I need next?
- Which tool will provide the most relevant data?
- How does this tool call advance the plan?

**Act**: Call exactly ONE tool that will gather the needed data.

**Observe**: After receiving tool results, you'll be called again to decide the next step.

## Instructions
- You are a DATA COLLECTION agent. Your ONLY job is to call database tools.
- You MUST call exactly one tool per turn.
- Use step-by-step reasoning to determine which tool is most appropriate.
- Start by calling the most relevant tool for the first data requirement.
- Note: all prices are in GBP
- When you have gathered sufficient data to implement the plan, STOP making tool calls.
- DO NOT produce summaries, tables, charts, or formatted output.
- A separate data analyst will analyze and summarize the raw tool results.

## Reasoning Example
To implement the plan, I first need comprehensive parts data including pricing and country information. The parts_summary tool provides this foundational data needed for the Component Analysis section.
→ Call parts_summary tool
"""

data_summary_prompt = """You are an expert data analyst.

Analyse the data from the database agent and produce a concise executive summary.

<Guidelines>
- Currency: GBP (£).
- **Important**: don't repeat analysis already shown in the data
- Only use the provided data.
- Structure: have two numbered sections:
  1) Assessing if the input data and prices are valid.
      - Invalid input data refers to records that do not represent valid automotive parts
      - Invalid prices are values that do not conform to expected numeric, positive, and reasonable ranges for automotive parts. Only flag if negative or significantly out (e.g.
order-of-magnitude outliers).
      - Only do this when the data is clearly wrong. Don't speculate if you're unsure.
      - If satisfied, print 'SATISFIED WITH INPUT DATA'
  2) Further analysis
       - Further analysis only has to include ONE point, e.g. the top 3 parts account for x% of the cost, or the top 3 countries account for x% of the articles, or the top 3 suppliers account for x% of the articles
       - Use calculator for exact totals/ratios (e.g., sum([...]), round(a/b*100,2)).
       - Spend rule: use quantity × bottomQuartileAvgPrice. Do NOT use numArticles in spend.
       - Treat numArticles as catalogue diversity only; never multiply it into cost.
</Guidelines>
"""

chart_planning_prompt = """You are a supply chain data visualisation expert. Based on the following chart criteria, create a chart plan JSON array.

<Chart1>
Create a combination chart with bars and a line.
- X-axis: Part names
- Left Y-axis (bars): Number of articles per part
- Right Y-axis (line): Average price for each part
- Bars should represent the count of articles for each part.
- A line should be overlaid showing the bottom quartile average price for the same parts.
</Chart1>

<Chart2>
Create a bar chart showing the distribution of articles by country of origin.
- X-axis: Countries of origin
- Y-axis: Number of articles from each country
- Each bar represents a country of origin.
- Display percentage labels above each bar to indicate each country's share of total articles.
</Chart2>

<Chart3>
Create a table summarising all parts with the following columns:
- Product Group ID
- Part Description
- Bottom Quartile Avg Price
- Most Common Country of Origin
- Line Item Total Excl VAT
- Percentage of Total Cost
- For long column headers, split them across multiple lines using \n to fit the table width.
</Chart3>

Database summary: \"\"\"
{db_summary}
\"\"\"

Structured data: \"\"\"
{db_content}
\"\"\"

<Output>
- Return a JSON array of objects (dictionaries), where each object contains both chart_id and chart_description fields.
- In the chart_id, mention CA for the charts at the start.
[
  {{{{
    "chart_id": "CA_combination_chart_articles_count_and_bottom_quartile_avg_price_per_part",
    "chart_description": "Combination chart with bars and a line. The X-axis shows part names. The bars (left Y-axis) represent the number of articles per part. The overlaid line (right Y-axis) shows the bottom quartile average price for each part, allowing comparison between article counts and relative price levels."
  }}}}
]
</Output>
"""

generate_chart_prompt = """You are a data visualisation expert. Generate a Python script using matplotlib to produce the chart described. Always save with: `plt.savefig(chart_path)` and never assign `chart_path` inside the script. Assume it is already defined.

<Guidelines>
- Use Matplotlib only. Do NOT import seaborn.
- Always save the chart with the same name as the chart_id.
- When designing the chart, use professional styling, ideally using Hex colours #4E82B2, #0B2447 or similar.
- For table visualizations:
  * Set figure size to scale with number of rows: figsize=(12, 0.6 * num_rows + 2)
  * Split long column headers across multiple lines using \n (e.g., "Most Common\nCountry of Origin")
  * Use appropriate font size (9-11pt) to ensure all content is visible
  * Adjust column widths if needed to accommodate text
</Guidelines>

Chart requirement: \"\"\"
{chart_description}
\"\"\"

Data: \"\"\"
{tool_data}
\"\"\"
"""

research_plan_prompt = """You are an expert automotive supply chain researcher. Your task is to generate search queries (each under 400 characters) for information to help gather data for an analytical report. This research aims to help understand market dynamics and the impacts of trade policy.

Task: \"\"\"
{task}
\"\"\"

Generate 3-4 search queries covering:
1. Tariff news and policy changes concerning the manufacturing country
2. Automotive sector-specific tariff impacts and trade developments

Guidelines:
- Keep queries focused and specific (avoid multi-topic queries)
- Use keywords related to the automotive supply chain, tariffs, and the target country
- Don't include the simulation rates in any queries
- Don't include specific news source names (e.g., Reuters, Bloomberg) in queries
- Each query should be under 400 characters

Provide a list of search jobs with only the query field populated for each.
"""

simulation_prompt = """System:
You are an expert supply chain analyst specialising in trade and tariff impact simulations, using the ReAct (Reasoning + Acting) framework.

## Goal:
- You are a SIMULATION TOOL CALLER. Your ONLY job is to call the automotive tariff simulation tool.
- Interpret the user's request and call the simulation tool exactly once with valid arguments.
- DO NOT provide summaries, analysis, or formatted output.
- A separate cleaning step will format the simulation results.

## Task you are supporting  \"\"\"
{task}
\"\"\"

Tools available:
{tools}

Tool names: {tool_names}

## ReAct Framework:
Before calling the simulation tool, think through:

**Thought**: Analyze the simulation requirements
- Which country is the target for tariff shocks? (Look for phrases like "applied to parts from [country]" or "tariffs on [country]")
- What tariff rates should be tested? (Extract percentages or rates from the task)
- Are the parameters valid and reasonable for automotive supply chain analysis?

**Action**: Call the simulation tool with the validated parameters

**Observation**: The tool will execute and return results - do not summarize them

## Guidelines:
- Think step-by-step about the simulation parameters before making the tool call
- Validate that the target country and tariff rates are clearly specified in the task
- Call exactly one tool
- After receiving tool results, STOP - do not produce summaries or analysis

## Example Reasoning:
Thought: The task asks for a tariff shock simulation on parts from Japan. I can see three tariff rates mentioned: 20%, 40%, and 70%. These are reasonable test scenarios for trade policy analysis. I'll call the automotive_tariff_simulation tool with target_country="Japan" and tariff_rates=[20, 40, 70].
Action: [Call automotive_tariff_simulation tool]
"""

simulation_clean_prompt = """All the above messages are from a supply chain simulation tool. Please clean up these findings.
DO NOT summarise the information. Return the raw information, just in a cleaner format.
Make sure all relevant information is preserved - you can rewrite findings verbatim.
"""

writers_prompt = """You are an expert research analyst working in the automotive supply chain sector tasked with writing a professional-level report. The report MUST be between 600 and 800 words. Generate the best report possible using the data and guidelines below. Prioritise following the instructions in the plan.

Here are reasoning examples you should follow: \"\"\"
{CoT_writing_examples}
\"\"\"

Before writing, work through this reasoning process systematically:

STEP 1 - Extract and Verify Critical Numbers:
From Database Insights:
- How many parts total? What's the combined cost (excl/incl VAT)?
- Most expensive part and its price?
- How many parts are taxable vs non-taxable?
- Top 3 countries by article count with specific numbers?
- Top 3 suppliers by article count?

From Simulation Results:
- What are the three tariff rates tested (extract exact percentages)?
- What's the target country for tariffs?
- What's the VAT rate and how many parts does it affect?
- For EACH scenario: Initial cost, Final cost, Absolute increase, Percentage increase?
- How many suppliers total vs affected?

From Web Research:
- What specific tariff news is mentioned (dates, countries, rates)?
- Are there any policy changes or trade negotiations relevant to the target country?

From Deep Research:
- Which alternative suppliers are identified with pricing?
- What regions/countries offer alternatives?

Cross-check: Do simulation costs align with database totals? Any contradictions?

STEP 2 - Classify Impact According to Plan:
Calculate the highest percentage increase from simulation.
Assign category:
- Small: <5%
- Moderate: 5-10%
- Large: 10-20%
- Severe: >20%

STEP 3 - Map Data to Plan Sections:
Review the plan section-by-section:
- Executive Summary: What are the 2-3 most important findings?
- Key Points: Extract the 4 required bullets with exact figures
- Component Analysis: Which database stats belong here? Which charts support this?
- Tariff Simulation: Which simulation results belong here? Which charts support this?
- Tariff News: Which web sources are relevant? Plan citations.
- Alternative Suppliers: Which deep research findings fit? Plan citations.
- Impact Assessment: Use classification from Step 2
- Recommendations: Based on impact level, what actions make sense?

STEP 4 - Plan Chart Placement:
You have multiple charts that MUST all be included:
- Which charts go in Component Analysis section?
- Which charts go in Tariff Simulation section?
- Verify every chart ID from the charts list will be placed in a figures array

STEP 5 - Plan Citations:
List all Web Research and Deep Research sources.
Assign sequential numbers (1, 2, 3, ...) with NO gaps.
Map each citation to specific claims in your planned text.

STEP 6 - Structure Check:
- Does your planned structure follow the plan exactly?
- Are all required elements present (bullet points, charts, citations)?
- Will the word count fall between 600-800 words?
- Have you avoided repeating figures between main text and bullet points?
- Have you avoided speculation and stuck to provided data?

STEP 7 - Write the Report:
Now compose the report section-by-section in JSON format, using the reasoning above.
Place charts only in "figures" arrays, never in "content" or "bullet_points".
Include inline citations [1], [2], etc. in the content text.

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
      "content": "<Plain text or markdown content>",
      "figures": ["[[FIGURE:chart1]]", "[[FIGURE:chart2]]"],
      "bullet_points": [
        "<First bullet point>",
        "<Second bullet point>"
      ]
    }}}}
  ]
}}}}
- **Charts must be included in the `figures` field as an array of placeholders like [[FIGURE:chart_id]]. Never put charts in the content field or bullet points. The figures array should contain chart placeholders that will be replaced with actual charts in the final report.
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
{task}
\"\"\"

Plan: **important - please follow** \"\"\"
{plan}
\"\"\"

Database Insights: \"\"\"
{db}
\"\"\"

Web Research: \"\"\"
{web}

\"\"\"

Deep Research: \"\"\"
{deep_research}
\"\"\"

Simulation Results: \"\"\"
{simulation}
\"\"\"

Charts **include ALL in the report**: \"\"\"
{charts}
\"\"\"
"""

revision_writers_prompt = """You are an expert research analyst working in the automotive supply chain sector tasked with revising a professional-level report based on manager feedback. The report MUST be between 600 and 800 words. Generate the best report possible using the feedback, previous draft, and data below. Prioritise addressing the feedback while following the instructions in the plan.

REVISION CONTEXT:

Previous Draft:
\"\"\"
{previous_draft}
\"\"\"

Manager Feedback:
\"\"\"
{critique}
\"\"\"

REVISION INSTRUCTIONS:
1. Review the manager feedback carefully and identify what needs improvement
2. Preserve sections that are working well (unless feedback specifically requests changes)
3. Work through the full reasoning process below to ensure accuracy and completeness
4. Address each point raised in the feedback
5. If new research was requested and provided, incorporate it from the data below
6. Maintain consistency with any preserved sections

Here are reasoning examples you should follow: \"\"\"
{CoT_writing_examples}
\"\"\"

Before writing, work through this reasoning process systematically:

STEP 1 - Extract and Verify Critical Numbers:
From Database Insights:
- How many parts total? What's the combined cost (excl/incl VAT)?
- Most expensive part and its price?
- How many parts are taxable vs non-taxable?
- Top 3 countries by article count with specific numbers?
- Top 3 suppliers by article count?

From Simulation Results:
- What are the three tariff rates tested (extract exact percentages)?
- What's the target country for tariffs?
- What's the VAT rate and how many parts does it affect?
- For EACH scenario: Initial cost, Final cost, Absolute increase, Percentage increase?
- How many suppliers total vs affected?

From Web Research:
- What specific tariff news is mentioned (dates, countries, rates)?
- Are there any policy changes or trade negotiations relevant to the target country?

From Deep Research:
- Which alternative suppliers are identified with pricing?
- What regions/countries offer alternatives?

Cross-check: Do simulation costs align with database totals? Any contradictions?

STEP 2 - Classify Impact According to Plan:
Calculate the highest percentage increase from simulation.
Assign category:
- Small: <5%
- Moderate: 5-10%
- Large: 10-20%
- Severe: >20%

STEP 3 - Map Data to Plan Sections:
Review the plan section-by-section:
- Executive Summary: What are the 2-3 most important findings?
- Key Points: Extract the 4 required bullets with exact figures
- Component Analysis: Which database stats belong here? Which charts support this?
- Tariff Simulation: Which simulation results belong here? Which charts support this?
- Tariff News: Which web sources are relevant? Plan citations.
- Alternative Suppliers: Which deep research findings fit? Plan citations.
- Impact Assessment: Use classification from Step 2
- Recommendations: Based on impact level, what actions make sense?

STEP 4 - Plan Chart Placement:
You have multiple charts that MUST all be included:
- Which charts go in Component Analysis section?
- Which charts go in Tariff Simulation section?
- Verify every chart ID from the charts list will be placed in a figures array

STEP 5 - Plan Citations:
List all Web Research and Deep Research sources.
Assign sequential numbers (1, 2, 3, ...) with NO gaps.
Map each citation to specific claims in your planned text.

STEP 6 - Structure Check:
- Does your planned structure follow the plan exactly?
- Are all required elements present (bullet points, charts, citations)?
- Will the word count fall between 600-800 words?
- Have you avoided repeating figures between main text and bullet points?
- Have you avoided speculation and stuck to provided data?
- Have you addressed all points in the manager feedback?

STEP 7 - Write the Revised Report:
Now compose the revised report section-by-section in JSON format, using the reasoning above.
Place charts only in "figures" arrays, never in "content" or "bullet_points".
Include inline citations [1], [2], etc. in the content text.

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
- Address all feedback points from the manager while maintaining report quality.
</Guidelines>

<Important Guidelines>
**Please include ALL charts in the report
**Address all points raised in the manager feedback
</Important Guidelines>

<Output Rules>
- Important** Provide the output in a JSON format adhering to the structure below:
{{{{
  "title": "<Report Title>",
  "sections": [
    {{{{
      "heading": "<Section Heading>",
      "content": "<Plain text or markdown content>",
      "figures": ["[[FIGURE:chart1]]", "[[FIGURE:chart2]]"],
      "bullet_points": [
        "<First bullet point>",
        "<Second bullet point>"
      ]
    }}}}
  ]
}}}}
- **Charts must be included in the `figures` field as an array of placeholders like [[FIGURE:chart_id]]. Never put charts in the content field or bullet points. The figures array should contain chart placeholders that will be replaced with actual charts in the final report.
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
{task}
\"\"\"

Plan: **important - please follow** \"\"\"
{plan}
\"\"\"

Database Insights: \"\"\"
{db}
\"\"\"

Web Research: \"\"\"
{web}

\"\"\"

Deep Research: \"\"\"
{deep_research}
\"\"\"

Simulation Results: \"\"\"
{simulation}
\"\"\"

Charts **include ALL in the report**: \"\"\"
{charts}
\"\"\"
"""

reflection_prompt = """You are a manager identifying missing elements from the plan and providing feedback on the tariff news section.

Original Task:
\"\"\"
{task}
\"\"\"

Plan (contains placeholder data and structure guidelines):
\"\"\"
{plan}
\"\"\"

Current Draft:
\"\"\"
{draft}
\"\"\"

Charts Available:
\"\"\"
{charts}
\"\"\"

Context: The plan uses placeholders (e.g., "Part1", "£price") to illustrate structure. Compare STRUCTURE and REQUIRED ELEMENTS, not placeholder values.

Your Assessment (4 components):
1. **Quality Score (1-10)**: Writing quality, clarity, professionalism
2. **Completeness Score (1-10)**: All required sections/elements present?
3. **Issues**: Missing plan elements and tariff news section problems (empty list [] if no issues)
4. **Recommendations**: How to address issues (empty string "" if no issues)

Scoring Guide:
- 9-10: All elements present, excellent quality
- 7-8: Nearly all elements present, good quality
- 5-6: Some elements missing
- 3-4: Many elements missing
- 1-2: Most elements missing

Critical Instructions:
- ONLY flag if absolutely certain an element is missing - when in doubt, do NOT flag
- Expect minimal issues (0-3 maximum) - be highly selective
- Flag missing STRUCTURE only, not writing quality/style
- If no issues: Issues = [], Recommendations = ""

Check These Elements:
1. Required sections from plan structure
2. Required bullet points per section
3. Required charts in figures arrays as [[FIGURE:chart_id]]
4. Required data points (part counts, prices, top 3 countries, tariff rates, cost breakdowns)
5. Citations in Tariff News/Alternative Suppliers (only flag if NONE present)
6. Tariff News: Provide improvement points or feedback if required

Notes:
- Charts must be in "figures" arrays, not content
- Word counts are guidelines, not strict limits
- Database and simulation data are internally generated - no citations needed for these sources"""

research_critique_prompt = """You are an expert automotive supply chain researcher. Generate 1-2 concise search queries (under 400 characters each) to support report revisions.

Task: \"\"\"
{task}
\"\"\"

Manager Feedback: \"\"\"
{critique}
\"\"\"

Instructions:
1. Extract from task: manufacturing country, component/vehicle, and tariff-affected country
2. If feedback requests specific information for tariff or trade news → create targeted queries for those gaps
3. If feedback has no specific research requests on tariff or trade news → generate queries for recent tariff/trade news affecting the manufacturing country and automotive sector

Guidelines:
- Keep queries focused and specific
- Don't include simulation rates or news source names
- Each query under 400 characters
- Create 1-2 search jobs maximum with only the query field populated
"""

