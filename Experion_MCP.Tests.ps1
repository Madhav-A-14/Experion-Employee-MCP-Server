function Invoke-MCPTool {
    param(
        [string]$ToolName,
        [string]$ToolArg
    )
    
    $cliArgs = @("@modelcontextprotocol/inspector","--cli","uv","run","server.py",
            "--method","tools/call","--tool-name", $ToolName, "--format", "json")
    if ($ToolArg) {$cliArgs += @("--tool-arg",$ToolArg)}

    $raw = & npx @cliArgs
    return $raw | ConvertFrom-Json

}

Describe "Experion Employee MCP - Tool Tests"{

    Context "get_all_employees"{
        It "Query : 'List all employees with their id and name'"{
            $response = Invoke-MCPTool -ToolName "get_all_employees"
            $employees = $response.result.content[0].text | ConvertFrom-Json

            $employees.Count | Should Be 20
            ($employees | Where-Object {$_.EmpId -eq 384}).'Employee Name' | Should Be "Aryan Nandagopal"
        }
    }

    Context "get_employee_data"{
        It "Query : 'Get employee id and employee name whose eid is 156'"{
            $response = Invoke-MCPTool -ToolName "get_employee_data" -ToolArg "emp_id=156"
            $data = $response.result.content[0].text | ConvertFrom-Json

            $data.EmpId | Should Be 156
            $data.'Employee Name' | Should Be "Priya Nair"
        }

        It "Query : 'Get full details of employee whose eid is 141'"{
            $response = Invoke-MCPTool -ToolName "get_employee_data" -ToolArg "emp_id=141"
            $data = $response.result.content[0].text | ConvertFrom-Json

            $data.Dept | Should Be "DTS"
            $data.Email | Should Be "sam@gmail.com"
        }

        It "Query : 'Get full details for nonexistent eid 460'"{
            $response = Invoke-MCPTool -ToolName "get_employee_data" -ToolArg "emp_id=460"
            $data = $response.result.content[0].text | ConvertFrom-Json

            $data.Error | Should Match "460"
           
        }
    }
    
    Context "get_salary_breakup"{
        It "Query : 'What is the salary breakup of employee whose eid is 305'"{
            $response = Invoke-MCPTool -ToolName "get_salary_breakup" -ToolArg "emp_id=305"
            $data = $response.result.content[0].text | ConvertFrom-Json

            $data.CTC | Should Be 1900000
            $data.'Total Allowance' | Should Be 65000
        }


        It "Query : 'Get salary breakup of nonexistent eid 411'"{
            $response = Invoke-MCPTool -ToolName "get_salary_breakup" -ToolArg "emp_id=411"
            $data = $response.result.content[0].text | ConvertFrom-Json

            $data.Error | Should Match "411"
           
        }
    }

}       