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


import phoenix as px


# Download all spans from a specific project
df = px.Client().get_spans_dataframe(project_name='my-llm-app')
print(df)

