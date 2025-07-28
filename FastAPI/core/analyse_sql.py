from langchain_community.utilities import SQLDatabase
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import create_sql_agent

import os
from dotenv import load_dotenv

load_dotenv()
OpenAi_key = os.getenv("OPENAI_API_KEY"),

db = SQLDatabase.from_uri("postgresql://devuser:devpass@localhost:5432/devdb")
llm = ChatOpenAI(model="gpt-4")
agent_executor = create_sql_agent(llm, db=db, verbose=True)

question = ("Can you create a summary of the parts with their description, average price, number of articles "
            "and most common country of origin?")
result = agent_executor.invoke({"input": question})
print(result)