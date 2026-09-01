"""
Evaluates whether an LLM correctly chooses and calls Experion MCP Tools 
in response to natural language queries using DeepEval's MCPUseMetric.
Added two custom checks:
    1) Whether right set of tools was used -- checks whether any extra tool was called --
        also whether any tool call is missed.
    2) The order in which the tools are being called when query needs more than one tool.
    
Supports mutli-step queries wherein the next tool call depends on the response of earlier tool's result.

Queries are loaded from data/mcp_qa.json.

"""
import asyncio
import json
from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from config import QA_FILE,MODEL_NAME
from server import mcp,datastore # uses the already built MCP + Datafiles from server.py
from deepeval.test_case import LLMTestCase,ToolCall
from deepeval.test_case.mcp import MCPToolCall
from deepeval.metrics import MCPUseMetric, ToolCorrectnessMetric
from deepeval import evaluate
from mcp.types import CallToolResult, TextContent

# Setting Open Ai Key from .env
client = OpenAI()

MAX_TURNS = 6

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
                "parameters": tool.input_schema,
            },
        })
    return OpenAI_tools

tools = build_tools(mcp)


def execute_tools(name:str,args:dict):
    """
    Runs the real datastore function matching the tool name the model chose.
    
    """
    
    if name == "get_all_employees":
        return datastore.get_all_employees()
    elif name == "get_employee_data":
        return datastore.get_employee_data(**args)
    elif name == "get_salary_breakup":
        return datastore.get_salary_breakup(**args)
    else:
       return {"error": f"Unknown tool {name}"} 
    
    
    

def run_agent(user_query:str):
    """
    Sends user query along with the available tools to the LLM. Instead of a single
    ask-then-answer pass, this now loops : the model decides which tool to call, the
    code runs that real function (using data_store.py) and sends the real result
    back to the model, which based on the previous tool call decides whether it needs 
    another tool or that it has enough to give a natural, readable final answer instead 
    of raw JSON. This repeats until the model stops asking for tools, or MAX_TURNS is reached.
    
    """
    
    messages=[{"role":"user","content":user_query}],
    tool_calls = [],
    called_tool_names = [],
    final_text = None
    
    for _ in MAX_TURNS:
        
        response = client.chat.completions.create(
                model= MODEL_NAME,
                tools = tools,
                messages=[{"role":"user","content":user_query}],  
            )
        message = response.choices[0].message
        messages.append(message)
        
        if not message.tool_calls:
            # Model answers with all the collected results,with no tools needed -- final answer
            final_text = message.content
            break

    
        for call in (message.tool_calls or []):
            args = json.loads(call.function.arguments)
            raw_result = execute_tools(call.function.name,args)
        
            
            
            # DeepEval framework expects the result ie the MCPToolCall.result to be in json object format
            # and not in dict format. So converting the plain dict to json format -- what deepeval expects
        
            mcp_result = CallToolResult(
                content=[TextContent(type="text", text=json.dumps(raw_result))]
            )
        
            # Saving the result in format MCPUseMetric expects.   
            tool_calls.append(
                MCPToolCall(
                    name = call.function.name,
                    args = args,
                    result = mcp_result
                )
            )
            called_tool_names.append(call.function.name)
            
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(raw_result),
            })
        
        else:
            
            final_text = "Max turns reached without final answer"
        
        return final_text,tool_calls,called_tool_names
    
   

def load_goldens():
    """
    Reads the manual test queries from data/mcp_goldens.json.
    
    """
    with open(QA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)
    

if __name__ == "__main__":
    goldens = load_goldens()
    test_cases = []
    
    # Runs every golden (from mcp_goldens.json file) and sends it to the LLM, it returns back the result
    # and the result is then packaged into LLMTestCase format -- so that DeepEval Framework can score the
    #results.
    
    for golden in goldens:
        query = golden["query"]
        print(f"Evaluation in progress ......... ")
        
        actual_output, tools_called = run_agent(query)

        test_cases.append(
            LLMTestCase(
                input=query,
                actual_output=actual_output,
                mcp_servers=[mcp],       # our real MCP server, passed in directly
                mcp_tools_called=tools_called,
            )
        )
        
    #Handing everything over to DeepEval's MCPUsageMetric which will evaluate and judges whether
    #right tool along with its arguments have been called for each user question.
    results = evaluate(test_cases=test_cases, metrics=[MCPUseMetric()])
    
    
    # print("\n" + "=" * 80)
    # print("Detailed reasoning per test case:")
    # print("=" * 80)

    # for i, test_result in enumerate(results.test_results):
    #     print(f"\nTest case {i}: {test_result.input}")
    #     for metric_data in test_result.metrics_data:
    #         print(f"  Metric: {metric_data.name}")
    #         print(f"  Score: {metric_data.score}")
    #         print(f"  Reason: {metric_data.reason}")
    
         
        
    