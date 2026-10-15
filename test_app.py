import pytest
from datetime import datetime
from app import BankAccount, Transaction

def test_account_creation_happy_path():
    acc = BankAccount("ACC-001", "Alice Smith", initial_balance=500.0, overdraft_limit=200.0)
    assert acc.account_number == "ACC-001"
    assert acc.owner_name == "Alice Smith"
    assert acc.balance == 500.0
    assert acc.overdraft_limit == 200.0
    assert len(acc.transactions) == 1
    assert acc.transactions[0].tx_type == "INITIAL_DEPOSIT"

def test_deposit_happy_path():
    acc = BankAccount("ACC-002", "Bob Jones", initial_balance=100.0, overdraft_limit=0.0)
    new_bal = acc.deposit(250.0)
    assert new_bal == 350.0
    assert acc.balance == 350.0
    assert len(acc.transactions) == 2
    assert acc.transactions[-1].tx_type == "DEPOSIT"

def test_withdraw_within_overdraft():
    acc = BankAccount(
        account_number="ACC-003",
        owner_name="Charlie Brown",
        initial_balance=100.0,
        overdraft_limit=200.0
    )
    # Withdraw more than balance but within overdraft limit (balance + overdraft = 300)
    new_bal = acc.withdraw(250.0)
    assert new_bal == -150.0
    assert acc.balance == -150.0
    assert acc.transactions[-1].tx_type == "WITHDRAWAL"

def test_withdraw_exceeds_overdraft_raises_error():
    acc = BankAccount(
        account_number="ACC-004",
        owner_name="Diana Prince",
        initial_balance=100.0,
        overdraft_limit=50.0
    )
    # Available limit is 150. Trying to withdraw 200 should fail.
    with pytest.raises(ValueError, match="Insufficient funds"):
        acc.withdraw(200.0)

def test_transfer_between_accounts():
    acc1 = BankAccount("ACC-A", "Sender", initial_balance=500.0, overdraft_limit=100.0)
    acc2 = BankAccount("ACC-B", "Receiver", initial_balance=100.0, overdraft_limit=0.0)

    acc1.transfer(acc2, 200.0)

    assert acc1.balance == 300.0
    assert acc2.balance == 300.0
    assert acc1.transactions[-1].tx_type == "TRANSFER_OUT"
    assert acc2.transactions[-1].tx_type == "TRANSFER_IN"

def test_invalid_negative_amounts():
    acc = BankAccount("ACC-005", "Test User", initial_balance=100.0, overdraft_limit=50.0)
    with pytest.raises(ValueError, match="Deposit amount must be positive"):
        acc.deposit(-50.0)

    with pytest.raises(ValueError, match="Withdrawal amount must be positive"):
        acc.withdraw(-10.0)

    with pytest.raises(ValueError, match="Overdraft limit cannot be negative"):
        BankAccount("ACC-006", "Bad Limit", initial_balance=0.0, overdraft_limit=-10.0)