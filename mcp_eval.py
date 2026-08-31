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
from config import QA_FILE,MODEL_NAME
from server import mcp,datastore # uses the already built MCP + Datafiles from server.py
from deepeval.test_case import LLMTestCase
from deepeval.test_case.mcp import MCPToolCall
from deepeval.metrics import MCPUseMetric
from deepeval import evaluate
from mcp.types import CallToolResult, TextContent

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
                "parameters": tool.input_schema,
            },
        })
    return OpenAI_tools

tools = build_tools(mcp)


def run_agent(user_query:str):
    """
    Sends user query along with the available tools to the LLM, model decides the appropriate tool 
    and arguments to pass. The code then runs that real function(using data_store.py) and the result is
    then stored in MCPUsageMetric format.A second call is made with LLM, wherein the real tool result
    is passed back so the model can turn it into a natural, readable answer instead of raw JSON. 
    
    """
    
    # Step-1 : Sends the model, the user query along with the list of tools available.Recieves back the
    # models response as well as which tool to use.
    response = client.chat.completions.create(
        model= MODEL_NAME,
        tools = tools,
        messages=[{"role":"user","content":user_query}],  
    )
    message = response.choices[0].message
    tool_calls = []
    results_by_id = {}
    
    # Step-2 : The model decides which tool to use (from tool_call) and what all arguments to pass.
    # the code then runs the real function (inside data_store.py) and the result is recorded in 
    # format MCPUsageMetric expects. 
    
    for call in (message.tool_calls or []):
        args = json.loads(call.function.arguments)
    
        if call.function.name == "get_all_employees":
            raw_result = datastore.get_all_employees()
        elif call.function.name == "get_employee_data":
            raw_result = datastore.get_employee_data(**args)
        elif call.function.name == "get_salary_breakup":
            raw_result = datastore.get_salary_breakup(**args)
        else:
            raw_result = {"error": f"Unknown tool {call.function.name}"}
            
        # DeepEva; framework expects the result ie the MCPToolCall.result to be in json object format
        # and not in dict format. So converting the plain dict to json format -- what deepeval expects
        
        mcp_result = CallToolResult(
            content=[TextContent(type="text", text=json.dumps(raw_result))]
        )
    
        # Saving the result in format MCPUsgaeMetric expects.   
        tool_calls.append(
            MCPToolCall(
                name = call.function.name,
                args = args,
                result = mcp_result
            )
        )
        results_by_id[call.id] = raw_result
    
        
    # Step-3 : The result is then sent to the LLM once again, so that the LLM can turn that result into
    # actual readable format rather than printing it in JSON format.
    
    if tool_calls:
        final_result =client.chat.completions.create(
        model= MODEL_NAME,
        messages=[{"role":"user","content":user_query},
        message,
                    *[
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(results_by_id[tc.id]),
                    }
                    for tc in message.tool_calls
                ],
            ],
        )
        final_text = final_result.choices[0].message.content
    else:
        # Model answered directly without needing a tool
        final_text = message.content
        
    return final_text, tool_calls

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
    
         
        
    