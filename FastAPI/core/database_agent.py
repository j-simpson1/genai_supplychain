#!/opt/anaconda3/envs/genai_supplychain/bin/python
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from pydantic import SecretStr

from langchain_openai import AzureChatOpenAI
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase

# Load environment variables
load_dotenv()

# Azure OpenAI setup
api_key = os.getenv("AZURE_OPENAI_API_KEY")

llm = AzureChatOpenAI(
    azure_deployment="gpt-4o",
    api_version="2024-05-01-preview",
    azure_endpoint="https://ucabj-md0rveym-swedencentral.cognitiveservices.azure.com/",
    api_key=SecretStr(api_key),
    temperature=0
)

# PostgreSQL connection setup
postgres_url = "postgresql+psycopg2://devuser:devpass@localhost:5432/devdb"
engine = create_engine(postgres_url)
db = SQLDatabase(engine)

# Create a LangChain SQL agent with better error handling
toolkit = SQLDatabaseToolkit(db=db, llm=llm)

MSSQL_AGENT_PREFIX = """

You are an agent designed to interact with a SQL database.
## Instructions:
- Given an input question, create a syntactically correct {dialect} query
to run, then look at the results of the query and return the answer.
- Unless the user specifies a specific number of examples they wish to
obtain, **ALWAYS** limit your query to at most {top_k} results.
- You can order the results by a relevant column to return the most
interesting examples in the database.
- Never query for all the columns from a specific table, only ask for
the relevant columns given the question.
- You have access to tools for interacting with the database.
- You MUST double check your query before executing it.If you get an error
while executing a query,rewrite the query and try again.
- DO NOT make any DML statements (INSERT, UPDATE, DELETE, DROP etc.)
to the database.
- DO NOT MAKE UP AN ANSWER OR USE PRIOR KNOWLEDGE, ONLY USE THE RESULTS
OF THE CALCULATIONS YOU HAVE DONE.
- Your response should be in Markdown. However, **when running  a SQL Query
in "Action Input", do not include the markdown backticks**.
Those are only for formatting the response, not for executing the command.
- ALWAYS, as part of your final answer, explain how you got to the answer
on a section that starts with: "Explanation:". Include the SQL query as
part of the explanation section.
- If the question does not seem related to the database, just return
"I don\'t know" as the answer.
- Only use the below tools. Only use the information returned by the
below tools to construct your query and final answer.
- Do not make up table names, only use the tables returned by any of the
tools below.

## Tools:

"""

MSSQL_AGENT_FORMAT_INSTRUCTIONS = """

## Use the following format:

Question: the input question you must answer.
Thought: you should always think about what to do.
Action: the action to take, should be one of [{tool_names}].
Action Input: the input to the action.
Observation: the result of the action.
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer.
Final Answer: the final answer to the original input question.

Example of Final Answer:
<=== Beginning of example

Action: query_sql_db
Action Input: 
SELECT
    "articleNo",
    "supplierId",
    "price"
FROM
    "articles"
ORDER BY
    "price" DESC
LIMIT 10;

Observation:
**Article No:** 83-2589, **SupplierId:** 226, **Price:** 263.92
Thought:I now know the final answer
Final Answer: The most expensive articles is 83-2589 which cost £263.92.

Explanation:
I queried the `articles` table for the `prices` column. The query returned a list of articles
sorted from highest to lowest. To answer the question,
I took the most expensive articles, which is 83-2589 with a cost of £263.92.
I used the following query

```sql
SELECT "articleNo", "supplierId", "price" FROM "articles" ORDER BY "price" DESC LIMIT 10;
```
===> End of Example

"""

# Use the create_sql_agent function with AgentType.ZERO_SHOT_REACT_DESCRIPTION
agent_executor = create_sql_agent(
    prefix=MSSQL_AGENT_PREFIX,
    format_instructions = MSSQL_AGENT_FORMAT_INSTRUCTIONS,
    llm=llm,
    toolkit=toolkit,
    top_k=30,
    verbose=True
)

# Use `.invoke()` instead of `.run()`
query = "Can you retrieve all the articles in the database?"

response = agent_executor.invoke({"input": query})
print(response["output"])