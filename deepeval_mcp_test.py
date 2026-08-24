"""
Evaluates whether an LLM correctly chooses and calls Experion MCP Tools 
in response to natural language queries using DeepEval's MCPUseMetric.

Queries are loaded from data/mcp_qa.json.
"""
import asyncio
import json
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from config import QA_FILE
from server import mcp,datastore # uses the already built MCP + Datafiles from server.py
from deepeval.test_case import LLMTestCase
from deepeval.test_case.mcp import MCPToolCall
from deepeval.metrics import MCPUseMetric
from deepeval import evaluate

# Setting Open Ai Key from .env
client = OpenAI()


def build_tools(mcp_server):
    """
    Builds tool list automatically from server.py describing the 3 tools in the format OpenAi's API-
    expects, so the model knows what all tools to call and with what parameters.
    
    """
    mcp_tools = asyncio.run(mcp_server.list_tools())
    OpenAI_tools = []
    for tool in mcp_tools:
        OpenAI_tools.append({
            "type":"function",
            "function":{
                "name":tool.name,
                "description":tool.description,
                "parameters": tool.inputSchema,
            },
        })
    return OpenAI_tools

tools = build_tools(mcp)


def run_agent(user_query:str):
    """
    Sends user query along with the available tools to the LLM, model decides the appropriate tool 
    and arguments to pass. The code then runs that real function(using data_store.py) and the result is
    then stored in MCPUsageMetric format. A second call is made with LLM, wherein 
    
    """
    response = client.chat.completions.create(
        model= "gpt-5-nano"
        
    )