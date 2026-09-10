"""
Single shared config for the Experion Employee MCP server.
Keeps file paths in one place so nothing is hardcoded in server.py.

"""


from pathlib import Path

BASE_DIR = Path(__file__).parent

HR_DEPT_FILE = BASE_DIR/"data"/"hr_dept.json"
FINANCE_DEPT_FILE = BASE_DIR/"data"/"finance_dept.json"
QA_FILE = BASE_DIR/"data"/"mcp_goldens.json"

#----------------------------------------------------------------------------------------------------------------#
SERVER_NAME = "Experion Employee MCP"
MODEL_NAME = "gpt-5-nano"

RUN_REPORT = True

#----------------------------------------------------------------------------------------------------------------#
# Embedding model used by CosineSimilarityMetric
EMBEDDING_MODEL_NAME = "voyageai/voyage-4-nano"
EMBEDDING_TRUNCATE_DIM = 1024  # 2048/1024/512/256 — lower = faster, still strong quality