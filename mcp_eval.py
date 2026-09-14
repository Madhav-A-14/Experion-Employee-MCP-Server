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
from config import QA_FILE,MODEL_NAME,RUN_REPORT
from server import mcp,datastore # uses the already built MCP + Datafiles from server.py
from deepeval.test_case import LLMTestCase,ToolCall
from deepeval.test_case.mcp import MCPToolCall
from deepeval.metrics import MCPUseMetric, ToolCorrectnessMetric
from deepeval import evaluate
from mcp.types import CallToolResult, TextContent
from cosine_metric import CosineSimilarityMetric
from report import export_mcp_report

# Setting Open Ai Key from .env
client = OpenAI()

# Creates the OpenAI client, and sets a safety cap of 6 turns on the multi-step agent loop, 
# so a confused model can't loop forever. 
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
    
    messages=[{"role":"user","content":user_query}]
    tool_calls = []
    called_tool_names = []
    final_text = None
    
    for _ in range(MAX_TURNS):
        
        response = client.chat.completions.create(
                model= MODEL_NAME,
                tools = tools,
                messages=messages
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
       
            tool_calls.append(
                MCPToolCall(
                    name = call.function.name,
                    args = args,
                    result = mcp_result
                )
            )
            called_tool_names.append(call.function.name)
            
            #Feeds the real result back into the conversation, so the model can decide its next move 
            # based on real data.
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(raw_result),
            })
        
    else:
            
        final_text = "Max turns reached without final answer"
        
        #Returns the final answer text, the detailed DeepEval-ready tool call records, 
        # and the plain ordered name list.
    return final_text,tool_calls,called_tool_names
    
   

def load_goldens():
    """
    Reads the manual test queries from data/mcp_goldens.json.
    
    """
    with open(QA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def build_report_data(results, metric_labels):
    """
    Turns DeepEval's final results in CLI to a .csv file for easier review,
    sharing, and comparison across test runs -- since the terminal output
    disappears once the console clears. 
    """
    report_results = {label: [] for label in metric_labels}
    for test_result in results.test_results:
        for label, metric_data in zip(metric_labels, test_result.metrics_data):
            report_results[label].append(metric_data.score)

    total_tests  = len(results.test_results)
    passed_tests = sum(1 for tr in results.test_results if tr.success)
    failed_tests = total_tests - passed_tests
    pass_rate    = (passed_tests / total_tests * 100) if total_tests else 0

    overall_stats = {
        "total":     total_tests,
        "passed":    passed_tests,
        "failed":    failed_tests,
        "pass_rate": round(pass_rate, 1),
    }

    return report_results, overall_stats   



if __name__ == "__main__":
    goldens = load_goldens()
    test_cases = []
    
    # Runs every golden (from mcp_goldens.json file) and sends it to the LLM, it returns back the result
    # and the result is then packaged into LLMTestCase format -- so that DeepEval Framework can score the
    #results.
    
    for golden in goldens:
        query = golden["query"]
        expected_tools = golden.get("expected_tools", [])
        expected_output = golden.get("expected_output","")
        print(f"Evaluation in progress ......... ")
        
        actual_output,tools_called,called_tool_names = run_agent(query)

        test_cases.append(
            LLMTestCase(
                input=query,
                actual_output=actual_output,
                expected_output=expected_output,
                mcp_servers=[mcp],
                mcp_tools_called=tools_called,
                tools_called=[ToolCall(name=n) for n in called_tool_names], 
                expected_tools=[ToolCall(name=t) for t in expected_tools], 
                
            )
        )
        
        
        
    # Three metrics, each answering a different question:
    #   - MCPUseMetric: checks query, whether all tools are called, their arguments, how the collected
    #                    results are used by LLM in final answer generation.
     
    #   - ToolCorrectnessMetric (exact match): were exactly the right tools used —
    #                                          checks for any tools being missed to call and for any
    #                                          tools that has been called but not needed.
    
    #   - ToolCorrectnessMetric (ordering): were the tools called in the right sequence?
    
    
    metrics_list = [
        MCPUseMetric(),
        ToolCorrectnessMetric(should_exact_match=True,include_reason=True,threshold=1.0),
        ToolCorrectnessMetric(should_consider_ordering=True,include_reason=True,threshold=1.0),
        CosineSimilarityMetric(threshold=0.75),
    ]
        
    
    results = evaluate(
        test_cases=test_cases,
        metrics = metrics_list,
    
    )
    if RUN_REPORT:
        metric_labels = ["MCP_Use", "Tool_Correctness(Tool-Exact-Match)", "Tool_Correctness(Tool-Ordering)", "Cosine_Similarity"]
        thresholds = {label: metric.threshold for label, metric in zip(metric_labels, metrics_list)}
        report_results, overall_stats = build_report_data(results, metric_labels)
        export_mcp_report(test_cases, report_results, overall_stats=overall_stats, thresholds=thresholds)
    
    
    
         
        
    