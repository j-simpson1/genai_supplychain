# Planning-specific CoT examples
chain_of_thought_planning_examples = """
Task: Plan a supply chain report for the Honda CR-V powertrain system with a tariff shock simulation for Japanese
imports at 15%, 35%, and 60%. VAT is 20% and the manufacturing country is Germany.

Planning Reasoning Process:

STEP 1 - Analyze Task Requirements:
What vehicle/component? Honda CR-V powertrain
What tariff simulation? Japan as target, rates: 15%, 35%, 60%
What context? VAT 20%, manufactured in Germany
What's the goal? Analyze supply chain, simulate tariff impact, recommend mitigation

STEP 2 - Identify Required Data Sources:
- Database: Need part counts, costs (excl/incl VAT), most expensive parts, country origins, supplier info
- Web Research: Need recent tariff news about Japan, Germany, automotive sector
- Deep Research: Need alternative suppliers outside Japan with pricing
- Simulation: Need tariff impact calculations for all three rates (15%, 35%, 60%)

STEP 3 - Structure Logical Flow:
Start broad → drill into specifics → analyze impact → recommend actions
Order: Executive Summary → Key Points → Component Analysis → Tariff Simulation → External Context
(news + alternatives) → Impact Assessment → Recommendations

STEP 4 - Assign Section Requirements:
- Executive Summary: 100-150 words, no bullets, overview of entire analysis
- Key Points: 4 bullets (vehicle/component, prices with/without VAT, tariff rates tested, high-level impact)
- Component Analysis: 150-250 words using DATABASE data, include parts count, combined price, most expensive
  part, taxable count, top 3 countries, top 3 suppliers. Needs bullet points for top 3 parts by price and
  top 3 suppliers. Needs charts: articles per part + price, geographic distribution
- Tariff Simulation: 150-250 words using SIMULATION data, explain rates, affected articles share, VAT application.
  Needs bullet points for cost breakdown (base/tariff/VAT/total) and impact per scenario (initial/final/increase/%).
  Needs charts: cost progression, cost distribution
- Tariff News: 150 words from WEB research, recent developments about Japan/automotive tariffs
- Alternative Suppliers: 150 words from DEEP research, non-Japanese suppliers with pricing where available
- Impact Assessment: Classify impact (Small <5%, Moderate 5-10%, Large 10-20%, Severe >20%), state category and %
- Recommendations: Actionable mitigation strategies (diversification, bonded logistics, monitoring, contracts)

STEP 5 - Identify Chart Requirements:
From Component Analysis: combination chart (articles + price), bar chart (country distribution), parts summary table
From Tariff Simulation: cost progression chart, cost distribution chart
Total: 5 charts minimum

STEP 6 - Set Quality Controls:
- Total word count: 600-800 words
- All prices in GBP (£)
- Cite all web/deep research sources with sequential numbers [1], [2], [3]
- Include ALL charts in appropriate sections
- No speculation - only use provided data
- Don't repeat figures between main text and bullet points

The plan is: Create a 10-section report starting with Executive Summary, followed by 4 Key Points bullets, then detailed
Component Analysis (with 3 database charts), Tariff Simulation analysis (with 2 simulation charts), contextual sections
on Tariff News and Alternative Suppliers (both cited), quantitative Impact Assessment, strategic Recommendations,
References, and Appendices with parts summary table.

---

Task: Plan a report on the Toyota Camry electrical system supply chain. Include a UK tariff simulation on Chinese
parts at 20%, 40%, 80%. Assume 20% UK VAT.

Planning Reasoning Process:

STEP 1 - Analyze Task:
Vehicle: Toyota Camry, Component: Electrical system
Tariff target: China, Rates: 20%, 40%, 80%
Context: UK manufacturing, 20% VAT
Goal: Supply chain analysis + tariff impact + mitigation

STEP 2 - Data Requirements:
Database → Electrical system parts, costs, suppliers, geographic spread
Web → UK-China tariff news, automotive electrical sector developments
Deep Research → Non-Chinese electrical component suppliers with pricing
Simulation → Impact calculations for 20%, 40%, 80% tariff scenarios

STEP 3 - Section Structure:
Executive Summary (overview) → Key Points (4 bullets) → Component Analysis (database details + charts) →
Tariff Simulation (impact analysis + charts) → Tariff News (web context) → Alternative Suppliers (deep research) →
Impact Assessment (classification) → Recommendations (actions) → References → Appendices

STEP 4 - Content Specifications:
Component Analysis needs: total parts count, combined price (±VAT), most expensive component, taxable parts count,
top 3 origin countries with article counts, top 3 suppliers with article counts. Format as main paragraph (150-250 words)
plus bullet points for top parts and suppliers. Include 3 charts.

Tariff Simulation needs: three rates tested (20/40/80%), target country (China), affected articles fraction, VAT rate,
pre-shock cost structure, per-scenario impacts (initial/final/delta/%). Format as main paragraph (150-250 words) plus
bullet points for cost breakdowns. Include 2 charts.

STEP 5 - Chart Planning:
Combination chart showing article count + price per part
Bar chart showing geographic article distribution
Parts summary table
Cost progression chart across tariff scenarios
Cost distribution chart comparing scenarios
= 5 required charts

STEP 6 - Guidelines:
600-800 words total | GBP currency | Sequential citations [1][2][3] | All charts included | Data-driven only |
No figure repetition between text and bullets

The plan is: Structure a comprehensive 10-section report covering Executive Summary, Key Points, detailed Component
Analysis with database insights and 3 charts, Tariff Simulation with impact quantification and 2 charts, external
context via Tariff News and Alternative Suppliers sections (both cited), Impact Assessment with percentage-based
classification, strategic Recommendations, References, and Appendices.
"""

# Writing-specific CoT examples
chain_of_thought_writing_examples = """
Q: What is the supply chain structure for the powertrain system of the Honda CR-V?
A: The powertrain includes the engine block, transmission, control units, and exhaust system.
Key suppliers: Japan is the leading supplier of engine block, South Korea supplies transmission components, and the
United States supplies control modules. Honda follows a Just-In-Time (JIT) approach, meaning suppliers deliver
components directly to assembly plants with minimal warehousing.
The answer is: a multi-tiered supply chain with critical suppliers in Japan, South Korea, and the United States, all
integrated within Honda's JIT production model.

Q: Which component represents the highest value share in the powertrain system?
A: The total cost of the powertrain system is £1,245.60, and the transmission assembly is the most expensive part,
costing £310.50 each, with two units required per vehicle. Proportion of total cost = (part cost × quantity) / total
cost = (£310.50 × 2) / £1,245.60 = 49.8%.
The answer is: Transmission assemblies account for 49.8% of the total system cost, at £310.50 per unit.

Q: What risks does Honda face in its powertrain supply chain, and how can these risks be mitigated?
A: Automotive supply chains are exposed to risks such as dependency on single suppliers, fluctuating raw material
prices (e.g., steel, rare earths), and geopolitical or tariff disruptions affecting cross-border shipping.
The answer is: mitigating these risks by diversifying supplier networks, securing backup logistics routes, maintaining
strategic inventory reserves, and utilising digital supply chain monitoring to enhance resilience.

--- TARIFF REPORT WRITING EXAMPLE ---

Task: Write Component Analysis section for Nissan Altima cooling system.

STEP 1 - Extract Database Numbers:
- 8 parts total
- £312.45 excl VAT, £374.94 incl VAT (20% VAT rate)
- Most expensive: Radiator Assembly £145.20 (46.48% of cost)
- All 8 parts taxable
- Top 3 countries: South Korea (22 articles), Taiwan (18 articles), Thailand (15 articles)
- Top 3 suppliers: DENSO (12 articles), VALEO (10 articles), MAHLE (8 articles)

STEP 2 - Identify Key Insights:
- Moderate part count (8) suggests standard system
- Radiator Assembly dominates cost at >45%
- Asian sourcing concentration (South Korea + Taiwan + Thailand = 55 articles of 68 total = 81%)
- 100% of parts are taxable = maximum tariff exposure

STEP 3 - Structure Paragraph:
Lead with scope → cost breakdown → highlight dominant part → geographic concentration → tariff exposure

STEP 4 - Write with Specific Numbers:
The Nissan Altima cooling system comprises eight distinct components with a combined cost of £312.45 excluding VAT
(£374.94 including 20% VAT). The radiator assembly represents the most expensive component at £145.20, accounting for
46.48% of the total system cost. All eight parts are subject to import tariffs, creating full exposure to trade policy
changes. Geographic analysis reveals heavy reliance on Asian suppliers, with South Korea providing 22 articles, Taiwan
18 articles, and Thailand 15 articles. The top suppliers by article count are DENSO (12 articles), VALEO (10 articles),
and MAHLE (8 articles), indicating moderate supplier diversification within the Asian manufacturing base.
"""