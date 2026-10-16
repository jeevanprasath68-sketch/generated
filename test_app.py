import os
import pytest
import pandas as pd
import datetime
from app import FinanceEngine

@pytest.fixture
def py_test_db(tmp_path):
    db_file = tmp_path / "test_finance.db"
    engine = FinanceEngine(str(db_file))
    return engine

def test_init_database(py_test_db):
    """Test that database initializes correctly with empty tables."""
    df_trans = py_test_db.get_transactions()
    df_budgets = py_test_db.get_budgets()
    assert isinstance(df_trans, pd.DataFrame)
    assert isinstance(df_budgets, pd.DataFrame)
    assert len(df_trans) == 0
    assert len(df_budgets) == 0

def test_add_and_get_transaction(py_test_db):
    """Test adding a valid income and expense transaction and retrieving them."""
    today_str = str(datetime.date.today())
    
    trans_id_1 = py_test_db.add_transaction(today_str, "Income", "Salary", 5000.0, "Monthly Pay")
    trans_id_2 = py_test_db.add_transaction(today_str, "Expense", "Groceries", 150.50, "Supermarket")
    
    assert trans_id_1 > 0
    assert trans_id_2 > 0
    
    df = py_test_db.get_transactions()
    assert len(df) == 2
    assert df.loc[df['type'] == 'Income', 'amount'].values[0] == 5000.0
    assert df.loc[df['type'] == 'Expense', 'amount'].values[0] == 150.50

def test_invalid_transaction_amount(py_test_db):
    """Test that adding zero or negative amounts raises ValueError."""
    today_str = str(datetime.date.today())
    with pytest.raises(ValueError):
        py_test_db.add_transaction(today_str, "Expense", "Groceries", 0.0, "Zero amount")
    with pytest.raises(ValueError):
        py_test_db.add_transaction(today_str, "Expense", "Groceries", -50.0, "Negative amount")

def test_invalid_transaction_type(py_test_db):
    """Test that invalid transaction type raises ValueError."""
    today_str = str(datetime.date.today())
    with pytest.raises(ValueError):
        py_test_db.add_transaction(today_str, "Transfer", "Bank", 100.0, "Invalid type")

def test_budget_creation_and_retrieval(py_test_db):
    """Test setting and retrieving monthly category budgets."""
    py_test_db.set_budget("Groceries", 600.0)
    py_test_db.set_budget("Entertainment", 200.0)
    
    df = py_test_db.get_budgets()
    assert len(df) == 2
    groceries_limit = df.loc[df['category'] == 'Groceries', 'monthly_limit'].values[0]
    assert groceries_limit == 600.0

def test_calculate_summary(py_test_db):
    """Test accurate calculation of total income, expense, and savings rate."""
    today_str = str(datetime.date.today())
    py_test_db.add_transaction(today_str, "Income", "Salary", 4000.0)
    py_test_db.add_transaction(today_str, "Expense", "Rent", 1500.0)
    py_test_db.add_transaction(today_str, "Expense", "Groceries", 500.0)
    
    df = py_test_db.get_transactions()
    summary = py_test_db.calculate_summary(df)
    
    assert summary["total_income"] == 4000.0
    assert summary["total_expense"] == 2000.0
    assert summary["net_savings"] == 2000.0
    assert summary["savings_rate"] == 50.0

def test_delete_transaction(py_test_db):
    """Test transaction deletion functionality."""
    today_str = str(datetime.date.today())
    trans_id = py_test_db.add_transaction(today_str, "Expense", "Dining Out", 45.0)
    
    df_before = py_test_db.get_transactions()
    assert len(df_before) == 1
    
    py_test_db.delete_transaction(trans_id)
    df_after = py_test_db.get_transactions()
    assert len(df_after) == 0