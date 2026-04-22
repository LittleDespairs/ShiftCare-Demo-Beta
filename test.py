from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from pydantic import BaseModel # For data validation / Для валидации данных

# Tags metadata for API documentation / Метаданные для документации API

tags_metadata = [
    {
        "name": "Pages",
        "description": "Frontend pages (HTML templates) / HTML страницы интерфейса"
    },
    {
        "name": "Employees",
        "description": "Operations related to employee management / Операции, связанные с управлением сотрудниками"
    },
    {
        "name": "Departments",
        "description": "Operations related to department management / Операции, связанные с управлением отделами"
    },
    {
        "name": "Schedules",
        "description": "Operations related to employee schedules / Операции, связанные с графиками сотрудников"
    }
]

app = FastAPI(
    title="Employee Management API",
    description="API for managing employees, departments, and schedules / API для управления сотрудниками, отделами и графиками",
    version="0.1.0",
    openapi_tags=tags_metadata
)

class EmployeeCreate(BaseModel):
    full_name: str
    position: str
    max_shifts_per_week: int
    min_shifts_per_week: int
    can_work_night: bool
    can_work_weekends: bool
    can_work_evenings_after_night: bool
    can_work_morning_and_evening: bool
    can_work_morning_and_night: bool

employee_db = []  # In-memory database for employees / Временная база данных для сотрудников

# Configure templates folder / Указываем папку с HTML-шаблонами
templates = Jinja2Templates(directory="templates") 

@app.get("/", tags=["Pages"])
def read_root(request: Request):
    # Render HTML page / Отдаём HTML страницу
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )

@app.get("/employees", tags=["Pages"])
def employees_page(request: Request):
    # Render employees page / Отдаём страницу сотрудников
    return templates.TemplateResponse(
        request=request,
        name="employees.html",
        context={}
    )

@app.get("/api/employees", tags=["Employees"])
def get_employees(employee: EmployeeCreate):
    # Logic to retrieve employees from database / Логика получения сотрудников из базы данных
    employee_data = employee.model_dump()

    # Simple ID generation / Простая генерация ID
    employee_data["id"] = len(employee_db) + 1

    # Add employee to the in-memory database / Добавляем сотрудника в временную базу данных
    employee_db.append(employee_data)

    return {
        "message": "Employee created successfully / Сотрудник успешно создан",
        "employee": employee_data,
    }

