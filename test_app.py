"""Test suite for SpendWise Core Logic & Analytics."""

import os
import tempfile
import pytest
import pandas as pd
from datetime import date
from app import ExpenseDB, ExpenseValidator, AnalyticsEngine, export_dataframe_to_csv


@pytest.fixture
def temp_db():
    """Creates a temporary SQLite database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = ExpenseDB(db_path=path)
    yield db
    if os.path.exists(path):
        os.remove(path)


def test_add_and_retrieve_expense(temp_db):
    """Test standard CRUD: adding and fetching expense records."""
    exp_id = temp_db.add_expense(
        amount=25.50,
        category="Food",
        expense_date="2025-02-15",
        payment_method="Credit Card",
        description="Campus cafeteria meal"
    )
    assert exp_id is not None
    assert exp_id > 0

    fetched = temp_db.get_expense_by_id(exp_id)
    assert fetched is not None
    assert fetched["amount"] == 25.50
    assert fetched["category"] == "Food"
    assert fetched["expense_date"] == "2025-02-15"
    assert fetched["payment_method"] == "Credit Card"
    assert fetched["description"] == "Campus cafeteria meal"


def test_update_and_delete_expense(temp_db):
    """Test updating and deleting existing records."""
    exp_id = temp_db.add_expense(10.0, "Transport", "2025-02-01", "Cash", "Bus fare")
    
    # Update
    updated = temp_db.update_expense(exp_id, 12.50, "Transport", "2025-02-01", "Cash", "Bus and Subway")
    assert updated is True
    fetched = temp_db.get_expense_by_id(exp_id)
    assert fetched["amount"] == 12.50
    assert fetched["description"] == "Bus and Subway"

    # Delete
    deleted = temp_db.delete_expense(exp_id)
    assert deleted is True
    assert temp_db.get_expense_by_id(exp_id) is None

    # Delete non-existent
    assert temp_db.delete_expense(9999) is False


def test_budget_persistence(temp_db):
    """Test setting and reading monthly budget."""
    temp_db.set_budget("2025-05", 800.0)
    val = temp_db.get_budget("2025-05")
    assert val == 800.0

    # Update existing
    temp_db.set_budget("2025-05", 950.0)
    assert temp_db.get_budget("2025-05") == 950.0

    # Non-existent month defaults to 0.0
    assert temp_db.get_budget("1990-01") == 0.0


def test_validator_happy_and_edge_cases():
    """Test boundary validations for amounts, categories, and dates."""
    # Valid inputs
    assert ExpenseValidator.validate_amount("45.99") == 45.99
    assert ExpenseValidator.validate_amount(100) == 100.0
    assert ExpenseValidator.validate_category("Food") == "Food"
    assert ExpenseValidator.validate_date("2025-10-31") == "2025-10-31"

    # Invalid amounts: negative, zero, non-numeric
    with pytest.raises(ValueError):
        ExpenseValidator.validate_amount(0)
    with pytest.raises(ValueError):
        ExpenseValidator.validate_amount(-15.0)
    with pytest.raises(ValueError):
        ExpenseValidator.validate_amount("invalid_amt")

    # Invalid category
    with pytest.raises(ValueError):
        ExpenseValidator.validate_category("UnknownCategory")

    # Invalid date format
    with pytest.raises(ValueError):
        ExpenseValidator.validate_date("31-12-2025")


def test_budget_summary_calculations():
    """Test calculation of total spent, remaining budget, and warning thresholds."""
    data = pd.DataFrame([
        {"amount": 100.0, "category": "Food", "expense_date": "2025-03-05"},
        {"amount": 300.0, "category": "Education", "expense_date": "2025-03-12"},
        {"amount": 50.0, "category": "Shopping", "expense_date": "2025-04-01"},  # Different month
    ])

    # Monthly Budget: 500.0, Total Spent in March: 400.0 (80% -> On Track)
    summary = AnalyticsEngine.calculate_budget_summary(data, "2025-03", 500.0)
    assert summary["total_spent"] == 400.0
    assert summary["remaining"] == 100.0
    assert summary["percentage_used"] == 80.0
    assert summary["status"] == "On Track"

    # Warning threshold (>85%)
    summary_warn = AnalyticsEngine.calculate_budget_summary(data, "2025-03", 450.0)
    assert summary_warn["percentage_used"] == pytest.approx(88.9, 0.1)
    assert summary_warn["status"] == "Warning (>85%)"

    # Over budget
    summary_over = AnalyticsEngine.calculate_budget_summary(data, "2025-03", 350.0)
    assert summary_over["remaining"] == -50.0
    assert summary_over["status"] == "Over Budget"


def test_analytics_filter_and_export():
    """Test filtering by category, search text, date bounds, and CSV generation."""
    df = pd.DataFrame([
        {"id": 1, "amount": 20.0, "category": "Food", "expense_date": "2025-01-10", "payment_method": "Cash", "description": "Burger"},
        {"id": 2, "amount": 60.0, "category": "Transport", "expense_date": "2025-01-20", "payment_method": "UPI / Mobile Payment", "description": "Train pass"},
        {"id": 3, "amount": 150.0, "category": "Education", "expense_date": "2025-02-05", "payment_method": "Credit Card", "description": "Textbook"},
    ])

    # Filter by search string "burger"
    res_search = AnalyticsEngine.filter_and_sort(df, search_query="burger")
    assert len(res_search) == 1
    assert res_search.iloc[0]["id"] == 1

    # Filter by category and date range
    res_filtered = AnalyticsEngine.filter_and_sort(
        df,
        categories=["Education", "Transport"],
        start_date=date(2025, 1, 15),
        end_date=date(2025, 2, 28),
        sort_by="Amount",
        sort_order="Ascending"
    )
    assert len(res_filtered) == 2
    assert res_filtered.iloc[0]["amount"] == 60.0
    assert res_filtered.iloc[1]["amount"] == 150.0

    # CSV Export format verification
    csv_str = export_dataframe_to_csv(res_filtered)
    assert "Textbook" in csv_str
    assert "Train pass" in csv_str
    assert "Burger" not in csv_str