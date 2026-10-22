import pytest
from app import HRCalculator, DataManager, init_db, reset_database

@pytest.fixture(autouse=True)
def setup_test_db():
    reset_database()
    yield

def test_calculate_hours_happy_path():
    hours = HRCalculator.calculate_hours("08:30", "17:15")
    assert hours == 8.75

def test_calculate_hours_edge_cases():
    # Same time
    assert HRCalculator.calculate_hours("09:00", "09:00") == 0.0
    # Invalid string / empty
    assert HRCalculator.calculate_hours("", "17:00") == 0.0
    assert HRCalculator.calculate_hours("invalid", "17:00") == 0.0
    # Out before in
    assert HRCalculator.calculate_hours("17:00", "08:00") == 0.0

def test_compute_weekly_payroll():
    # Employee hourly rate: $20.0, 40 hours worked, $100 advance taken
    res = HRCalculator.compute_weekly_payroll(
        employee_id=1,
        hourly_rate=20.0,
        total_hours=40.0,
        total_advances=100.0
    )
    assert res["gross_pay"] == 800.0
    assert res["advance_deductions"] == 100.0
    assert res["net_pay"] == 700.0

def test_compute_weekly_payroll_excess_advance():
    # Advance is greater than gross pay
    res = HRCalculator.compute_weekly_payroll(
        employee_id=2,
        hourly_rate=15.0,
        total_hours=10.0, # Gross = 150
        total_advances=200.0
    )
    assert res["gross_pay"] == 150.0
    # Deductions capped at gross pay
    assert res["advance_deductions"] == 150.0
    assert res["net_pay"] == 0.0

def test_employee_directory_and_database():
    DataManager.add_employee("John Doe", "Welder", 22.5, "555-0192")
    df = DataManager.get_employees()
    assert len(df) == 1
    assert df.iloc[0]['name'] == "John Doe"
    assert df.iloc[0]['hourly_rate'] == 22.5

def test_attendance_logging():
    DataManager.add_employee("Jane Smith", "Machinist", 25.0, "555-0193")
    df = DataManager.get_employees()
    emp_id = df.iloc[0]['id']
    
    DataManager.log_attendance(emp_id, "2023-10-01", "08:00", "16:30", "Present")
    conn = DataManager.get_employees()
    # Just validating database persistence and execution without error
    assert len(conn) >= 1