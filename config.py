"""
Single shared config for the Experion Employee MCP server.
Keeps file paths in one place so nothing is hardcoded in server.py.

"""


from pathlib import Path

BASE_DIR = Path(__file__).parent

HR_DEPT_FILE = BASE_DIR/"data"/"hr_dept.json"
FINANCE_DEPT_FILE = BASE_DIR/"data"/"finance_dept.json"
QA_FILE = BASE_DIR/"data"/"mcp_qa.json"

SERVER_NAME = "Experion Employee MCP"

