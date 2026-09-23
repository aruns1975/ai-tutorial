"""
In-memory employee CRUD store for the employee MCP server.

Each employee is a plain dict with fields id, name, department, dob (an
ISO date string, matching tools/datetime_tools.py's convention), salary,
phone, and email. The private `_employees` dict lives inside
create_employee_store()'s closure — the same build-once-return-a-closure
shape used elsewhere in this project for private mutable state (see the
project root CLAUDE.md) — so nothing outside the five returned functions
can reach or mutate it directly.

Ids are generated server-side (a short uuid4 hex) rather than accepted
as input to create_employee: asking a tool-calling model to invent a
globally-unique id itself is unreliable, and every other CRUD operation
just needs whatever id create_employee already handed back.

This store is in-memory only and resets whenever the employee MCP
server restarts — there's no Redis/Postgres backend for it (unlike this
project's RAG/Memory/Agent concepts). Demonstrating a second,
independent MCP server is the point of employee_mcp_server/, not
another persistence-backend story.
"""

import uuid


def create_employee_store():
    _employees: dict[str, dict] = {}

    def create_employee(
        name: str,
        department: str,
        dob: str,
        salary: float,
        phone: str,
        email: str,
    ) -> dict:
        """
        Create a new employee record and return it, including a
        server-generated id.

        Call this tool for requests like "add a new employee", "hire
        someone new", or "create an employee record for X". Route away
        to update_employee if the request is about changing an existing
        employee rather than adding a new one.

        Few-shot examples (phrase -> tool call):
            "Add a new employee named Jane Doe in Engineering, born
            1990-05-12, salary 95000, phone 555-0100, email
            jane.doe@example.com."
                -> create_employee("Jane Doe", "Engineering", "1990-05-12",
                                    95000, "555-0100", "jane.doe@example.com")
        """
        employee_id = uuid.uuid4().hex[:8]
        employee = {
            "id": employee_id,
            "name": name,
            "department": department,
            "dob": dob,
            "salary": salary,
            "phone": phone,
            "email": email,
        }
        _employees[employee_id] = employee
        return employee

    def get_employee(employee_id: str) -> dict:
        """
        Look up a single employee by id.

        Call this tool for requests like "look up employee X", "show me
        employee <id>", or "what's employee <id>'s email/salary/phone".
        Route away to list_employees if the request wants every
        employee rather than one specific id.

        Few-shot examples (phrase -> tool call):
            "Look up employee a1b2c3d4."       -> get_employee("a1b2c3d4")
        """
        if employee_id not in _employees:
            raise ValueError(f"No employee found with id {employee_id!r}")
        return _employees[employee_id]

    def update_employee(
        employee_id: str,
        name: str | None = None,
        department: str | None = None,
        dob: str | None = None,
        salary: float | None = None,
        phone: str | None = None,
        email: str | None = None,
    ) -> dict:
        """
        Update one or more fields on an existing employee and return the
        updated record. Only the fields provided are changed — omit any
        field that should stay the same.

        Call this tool for requests like "update employee X's
        department/salary/phone/email", "move employee X to a different
        department", or "give employee X a raise". Route away to
        create_employee if the employee doesn't exist yet.

        Few-shot examples (phrase -> tool call):
            "Move employee a1b2c3d4 to the Sales department."
                -> update_employee("a1b2c3d4", department="Sales")
            "Give employee a1b2c3d4 a new salary of 100000."
                -> update_employee("a1b2c3d4", salary=100000)
        """
        if employee_id not in _employees:
            raise ValueError(f"No employee found with id {employee_id!r}")
        employee = _employees[employee_id]
        updates = {
            "name": name,
            "department": department,
            "dob": dob,
            "salary": salary,
            "phone": phone,
            "email": email,
        }
        for field, value in updates.items():
            if value is not None:
                employee[field] = value
        return employee

    def delete_employee(employee_id: str) -> dict:
        """
        Delete an employee record by id and return the deleted record.

        Call this tool for requests like "remove employee X", "delete
        employee <id>", or "let employee X go".

        Few-shot examples (phrase -> tool call):
            "Delete employee a1b2c3d4."        -> delete_employee("a1b2c3d4")
        """
        if employee_id not in _employees:
            raise ValueError(f"No employee found with id {employee_id!r}")
        return _employees.pop(employee_id)

    def list_employees() -> list[dict]:
        """
        Return every employee currently in the store.

        Call this tool for requests like "list all employees", "show me
        everyone in the company", or "how many employees are there".
        Route away to get_employee if the request names one specific
        employee/id instead of wanting the full list.

        Few-shot examples (phrase -> tool call):
            "List all employees."              -> list_employees()
        """
        return list(_employees.values())

    return create_employee, get_employee, update_employee, delete_employee, list_employees


create_employee, get_employee, update_employee, delete_employee, list_employees = create_employee_store()