import warnings
warnings.filterwarnings('ignore')

# import environment variables
from dotenv import load_dotenv
_ = load_dotenv()

import phoenix as px
import os
from phoenix.otel import register

import ast
import json
import re

load_dotenv()
pheonix_key = os.getenv("PHOENIX_API_KEY")
pheonix_collector_endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")

# configure the Phoenix tracer
tracer_provider = register(
  project_name="my-llm-app", # Default is 'default'
  auto_instrument=True, # See 'Trace all calls made to a library' below
)
tracer = tracer_provider.get_tracer(__name__)

px.launch_app()


import ast


import pandas as pd


def extract_message_content(row):
  if isinstance(row, list) and row and isinstance(row[0], dict):
    return row[0].get('message.content')
  return None

# Load all spans
df = px.Client().query_spans(project_name="my-llm-app")

output = df['attributes.llm.output_messages'].iloc[0][0]['message.content']
print("OUTPUT!!!", output)

# Remove rows where 'attributes.llm.output_messages' is NaN or empty/whitespace
df = df[df['attributes.llm.output_messages'].notna()]
df = df[df['attributes.llm.output_messages'].astype(str).str.strip().ne('')]

df['message_content'] = df['attributes.llm.output_messages'].apply(extract_message_content)
print(df['message_content'].head())
