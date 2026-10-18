import pytest
import datetime
import os
from app import HREngine

@pytest.fixture
def py_engine(tmp_path):
    db_file = tmp_path / "test_ssi.sqlite"
    engine = HREngine(db_path=str(db_file))
    return engine

def test_add_employee_happy_path(py_engine):
    emp_id = py_engine.add_employee("Alice Smith", "Machinist", 20.0)
    assert emp_id > 0
    
    employees = py_engine.get_employees()
    assert len(employees) == 1
    assert employees[0]["name"] == "Alice Smith"
    assert employees[0]["hourly_rate"] == 20.0

def test_add_employee_validation_errors(py_engine):
    with pytest.raises(ValueError):
        py_engine.add_employee("   ", "Operator", 15.0)

    with pytest.raises(ValueError):
        py_engine.add_employee("Bob Jones", "Welder", -5.0)

def test_log_time_and_hours_calculation(py_engine):
    emp_id = py_engine.add_employee("Charlie Brown", "Technician", 10.0)
    today_str = datetime.date.today().isoformat()
    
    # 8 hours shift (09:00 to 17:00)
    log_id = py_engine.log_time(emp_id, today_str, "09:00", "17:00")
    assert log_id > 0

    logs = py_engine.get_time_logs(emp_id)
    assert len(logs) == 1
    assert logs[0]["hours_worked"] == 8.0

def test_log_time_invalid_interval(py_engine):
    emp_id = py_engine.add_employee("Diana Prince", "Supervisor", 25.0)
    today_str = datetime.date.today().isoformat()
    
    with pytest.raises(ValueError):
        # Logout before login
        py_engine.log_time(emp_id, today_str, "17:00", "09:00")

def test_advance_payment_handling(py_engine):
    emp_id = py_engine.add_employee(
        name="Eve Adams",
        role="Assembler",
        hourly_rate=12.0
    )
    today_str = datetime.date.today().isoformat()
    
    adv_id = py_engine.add_advance(emp_id, today_str, 50.0, "Medical")
    assert adv_id > 0

    advances = py_engine.get_advances(emp_id)
    assert len(advances) == 1
    assert advances[0]["amount"] == 50.0

    with pytest.raises(ValueError):
        py_engine.add_advance(emp_id, today_str, -10.0, "Invalid")

def test_weekly_payroll_calculation(py_engine):
    emp_id = py_engine.add_employee("Frank White", "Helper", 15.0)
    date_str = "2023-10-10"
    
    # 10 hours work -> Gross: $150
    py_engine.log_time(emp_id, date_str, "08:00", "18:00")
    
    # Advance: $40
    py_engine.add_advance(emp_id, date_str, 40.0, "Uniform")
    
    summary = py_engine.calculate_weekly_payroll("2023-10-01", "2023-10-31")
    assert len(summary) == 1
    rec = summary[0]
    assert rec["total_hours"] == 10.0
    assert rec["gross_wage"] == 150.0
    assert rec["total_advances"] == 40.0
    assert rec["net_pay"] == 110.0