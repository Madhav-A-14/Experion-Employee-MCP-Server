from mcp.server import MCPServer
from config import HR_DEPT_FILE,FINANCE_DEPT_FILE,SERVER_NAME
from data_store import Experion_DataStore


mcp = MCPServer(SERVER_NAME)

datastore = Experion_DataStore(hr_file = HR_DEPT_FILE,finance_file = FINANCE_DEPT_FILE)

