import json

from mcp.server import MCPServer
from config import HR_DEPT_FILE,FINANCE_DEPT_FILE,SERVER_NAME
from data_store import Experion_DataStore



mcp = MCPServer(SERVER_NAME)

datastore = Experion_DataStore(hr_file = HR_DEPT_FILE,finance_file = FINANCE_DEPT_FILE)


@mcp.tool()
def get_all_employees() -> str:
    """ 
    List all employees with just their EmpId and Employee Name,
    sourced from HR_Dept.json.
    """

    return json.dumps(datastore.get_all_employees())

@mcp.tool()
def get_employee_data(emp_id:int) -> dict:
    """ 
    Return the full HR record (EmpId, Employee Name, Dept, Work Location,
    Email, Mobile) for a given EmpId, sourced from HR_Dept.json.
        
    """
    
    return datastore.get_employee_data(emp_id)


@mcp.tool()
def get_salary_breakup(emp_id:int) -> dict:
    """
    Return CTC and Total Allowance for a given EmpId,
    sourced from FINANCE_Dept.json.
    
    """
    return datastore.get_salary_breakup(emp_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")
    
    