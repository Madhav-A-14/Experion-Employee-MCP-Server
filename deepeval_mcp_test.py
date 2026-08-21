"""
Evaluates whether an LLM correctly chooses and calls Experion MCP Tools 
in response to natural language queries using DeepEval's MCPUseMetric.
"""

import json
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from config import QA_FILE
from server import mcp,datastore

client = OpenAI()