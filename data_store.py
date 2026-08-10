import json
from pathlib import Path
from typing import Any

class Experion_DataStore:
    
    def __init__(self, hr_file:Path, finance_file:Path):
        
        self.hr_file  = hr_file
        self.finance_file  = finance_file
    
    
    def _load(self, path:Path) -> list[dict[str,Any]]:
        
        with open(path, "r", encoding = "utf-8") as f:
            return json.load(f)

    def get_all_employees(self) -> list[dict[str,Any]]:
        
        """EmpId + Employee Name only, for every employee -> From HR_Dept.json"""
        employees = self._load(self.hr_file)
        for e in employees:
            return[
                {"EmpId" : e["EmpId"], "Employee Name" : e["Employee Name"]}
            ]
            
    def get_employee_data(self, emp_id:int) -> dict[str,Any]:
        
        """ Extract HR record for the specified EmpId -> From HR_Dept.json"""
        employees = self._load(self.hr_file)
        for e in employees:
            if e["EmpId"] == emp_id:
                return e 
            return {"error": f"No employee found with EmpId {emp_id}"}
        
        
    def get_salary_breakup(self, emp_id:int) -> dict[str,Any]:
        
        """ CTC + Total Allowance for one EmpId - From Finance_Dept.json"""
        records = self._load(self.finance_file)

        for r in records:
            if r["EmpId"] == emp_id:
                return{
                    "EmpId" : r["EmpId"],
                    "CTC" : r["CTC"],
                    "Total Allowance" : r["Total Allowance"],
                }
            return {"error": f"No salary data found with EmpId {emp_id}"}
        
    