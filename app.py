import streamlit as st
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional

# ==========================================
# DOMAIN MODELS & BUSINESS LOGIC
# ==========================================

class Transaction:
    def __init__(self, tx_id: str, timestamp: datetime, tx_type: str, amount: float, balance_after: float, description: str):
        self.tx_id = tx_id
        self.timestamp = timestamp
        self.tx_type = tx_type  # 'DEPOSIT', 'WITHDRAWAL', 'TRANSFER_IN', 'TRANSFER_OUT'
        self.amount = amount
        self.balance_after = balance_after
        self.description = description

    def to_dict(self) -> Dict:
        return {
            "Transaction ID": self.tx_id,
            "Timestamp": self.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "Type": self.tx_type,
            "Amount ($)": round(self.amount, 2),
            "Balance After ($)": round(self.balance_after, 2),
            "Description": self.description
        }


class BankAccount:
    def __init__(self, account_number: str, owner_name: str, initial_balance: float = 0.0, overdraft_limit: float = 0.0):
        if initial_balance < 0 and abs(initial_balance) > overdraft_limit:
            raise ValueError("Initial balance exceeds overdraft limit.")
        if overdraft_limit < 0:
            raise ValueError("Overdraft limit cannot be negative.")

        self.account_number = account_number
        self.owner_name = owner_name
        self.balance = float(initial_balance)
        self.overdraft_limit = float(overdraft_limit)
        self.transactions: List[Transaction] = []
        
        # Record initial funding if any
        if initial_balance != 0:
            self._record_transaction("INITIAL_DEPOSIT", initial_balance, "Account opened with initial balance")

    def _record_transaction(self, tx_type: str, amount: float, description: str):
        tx_id = f"TXN-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        tx = Transaction(
            tx_id=tx_id,
            timestamp=datetime.now(),
            tx_type=tx_type,
            amount=amount,
            balance_after=self.balance,
            description=description
        )
        self.transactions.append(tx)

    def deposit(self, amount: float) -> float:
        if amount <= 0:
            raise ValueError("Deposit amount must be positive.")
        self.balance += amount
        self._record_transaction("DEPOSIT", amount, f"Deposited $\f{amount:.2f}")
        return self.balance

    def withdraw(self, amount: float) -> float:
        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive.")
        
        available_funds = self.balance + self.overdraft_limit
        if amount > available_funds:
            raise ValueError(f"Insufficient funds. Requested $\f{amount:.2f} exceeds available limit $\f{available_funds:.2f}.")
            
        self.balance -= amount
        self._record_transaction("WITHDRAWAL", amount, f"Withdrew $\f{amount:.2f}")
        return self.balance

    def transfer(self, target_account: 'BankAccount', amount: float):
        if amount <= 0:
            raise ValueError("Transfer amount must be positive.")
        if self.account_number == target_account.account_number:
            raise ValueError("Cannot transfer to the same account.")
            
        # Withdraw from source
        self.withdraw(amount)
        self.transactions[-1].description = f"Transferred $\f{amount:.2f} to {target_account.account_number}"
        self.transactions[-1].tx_type = "TRANSFER_OUT"

        # Deposit to target
        target_account.balance += amount
        target_account._record_transaction("TRANSFER_IN", amount, f"Received $\f{amount:.2f} from {self.account_number}")


class BankSystem:
    def __init__(self):
        if "accounts" not in st.session_state:
            st.session_state.accounts = {}

    def create_account(self, account_number: str, owner_name: str, initial_balance: float, overdraft_limit: float) -> BankAccount:
        if not account_number.strip():
            raise ValueError("Account number cannot be empty.")
        if not owner_name.strip():
            raise ValueError("Owner name cannot be empty.")
        if account_number in st.session_state.accounts:
            raise ValueError(f"Account {account_number} already exists.")
            
        acc = BankAccount(account_number, owner_name, initial_balance, overdraft_limit)
        st.session_state.accounts[account_number] = acc
        return acc

    def get_account(self, account_number: str) -> Optional[BankAccount]:
        return st.session_state.accounts.get(account_number)

    def list_accounts(self) -> List[BankAccount]:
        return list(st.session_state.accounts.values())


# ==========================================
# STREAMLIT USER INTERFACE
# ==========================================

def main():
    st.set_page_config(
        page_title="Enterprise BankAccount System",
        page_icon="🏦",
        layout="wide"
    )

    bank_system = BankSystem()

    st.title("🏦 Secure Bank Account & Ledger System")
    st.markdown("Manage bank accounts, perform deposits, overdraft-enabled withdrawals, account transfers, and audit transaction histories.")

    # Sidebar navigation
    st.sidebar.title("Navigation")
    choice = st.sidebar.selectbox("Choose Action", [
        "Dashboard & Overview",
        "Create Account",
        "Deposit / Withdraw",
        "Transfer Funds",
        "Transaction History"
    ])

    accounts = bank_system.list_accounts()

    if choice == "Dashboard & Overview":
        st.header("📊 Bank Overview Dashboard")
        
        if not accounts:
            st.info("No bank accounts found. Head to 'Create Account' to get started.")
        else:
            col1, col2, col3 = st.columns(3)
            total_deposits = sum(acc.balance for acc in accounts)
            total_overdraft = sum(acc.overdraft_limit for acc in accounts)
            
            col1.metric("Total Accounts", len(accounts))
            col2.metric("Total Capital ($)", f"${total_deposits:,.2f}")
            col3.metric("Total Overdraft Limit ($)", f"${total_overdraft:,.2f}")
            
            st.subheader("Active Accounts Summary")
            data = [{
                "Account Number": acc.account_number,
                "Owner": acc.owner_name,
                "Balance ($)": round(acc.balance, 2),
                "Overdraft Limit ($)": round(acc.overdraft_limit, 2),
                "Available Funds ($)": round(acc.balance + acc.overdraft_limit, 2),
                "Total Transactions": len(acc.transactions)
            } for acc in accounts]
            
            st.dataframe(pd.DataFrame(data), use_container_width=True)

    elif choice == "Create Account":
        st.header("➕ Open New Bank Account")
        
        with st.form("create_account_form"):
            acc_num = st.text_input("Account Number", placeholder="e.g. ACC-1001")
            owner = st.text_input("Owner Full Name", placeholder="e.g. Jane Doe")
            initial_bal = st.number_input("Initial Deposit ($)", value=0.0, step=50.0)
            overdraft = st.number_input("Overdraft Limit ($)", value=100.0, step=50.0, min_value=0.0)
            
            submitted = st.form_submit_button("Create Account")
            if submitted:
                try:
                    bank_system.create_account(acc_num, owner, initial_bal, overdraft)
                    st.success(f"Account {acc_num} successfully created for {owner}!")
                except ValueError as e:
                    st.error(str(e))

    elif choice == "Deposit / Withdraw":
        st.header("💸 Deposit & Withdrawal Operations")
        
        if not accounts:
            st.warning("Please create an account first.")
        else:
            acc_map = {f"{acc.account_number} ({acc.owner_name})": acc for acc in accounts}
            selected_key = st.selectbox("Select Account", list(acc_map.keys()))
            selected_acc = acc_map[selected_key]
            
            st.info(f"Current Balance: **${selected_acc.balance:,.2f}** | Overdraft Limit: **${selected_acc.overdraft_limit:,.2f}** | Available: **${selected_acc.balance + selected_acc.overdraft_limit:,.2f}**")
            
            op_type = st.radio("Operation Type", ["Deposit", "Withdraw"])
            amount = st.number_input("Amount ($)", min_value=0.01, value=50.0, step=10.0)
            
            if st.button("Execute Transaction"):
                try:
                    if op_type == "Deposit":
                        new_bal = selected_acc.deposit(amount)
                        st.success(f"Successfully deposited ${amount:,.2f}. New Balance: **${new_bal:,.2f}**")
                    else:
                        new_bal = selected_acc.withdraw(amount)
                        st.success(f"Successfully withdrew ${amount:,.2f}. New Balance: **${new_bal:,.2f}**")
                except ValueError as e:
                    st.error(str(e))

    elif choice == "Transfer Funds":
        st.header("🔄 Inter-Account Transfer")
        
        if len(accounts) < 2:
            st.warning("At least two accounts are required to perform transfers.")
        else:
            acc_map = {f"{acc.account_number} ({acc.owner_name})": acc for acc in accounts}
            
            col1, col2 = st.columns(2)
            with col1:
                src_key = st.selectbox("Source Account (Sender)", list(acc_map.keys()), key="src")
                src_acc = acc_map[src_key]
            with col2:
                # Filter out source account from target options
                target_options = [k for k in acc_map.keys() if k != src_key]
                target_key = st.selectbox("Target Account (Receiver)", target_options, key="tgt")
                target_acc = acc_map[target_key]
                
            st.info(f"Sender Available Funds: **${src_acc.balance + src_acc.overdraft_limit:,.2f}**")
            transfer_amount = st.number_input("Transfer Amount ($)", min_value=0.01, value=100.0, step=25.0)
            
            if st.button("Transfer Funds"):
                try:
                    src_acc.transfer(target_acc, transfer_amount)
                    st.success(f"Successfully transferred ${transfer_amount:,.2f} from {src_acc.account_number} to {target_acc.account_number}!")
                except ValueError as e:
                    st.error(str(e))

    elif choice == "Transaction History":
        st.header("📜 Audit & Transaction History")
        
        if not accounts:
            st.warning("No accounts available.")
        else:
            acc_map = {f"{acc.account_number} ({acc.owner_name})": acc for acc in accounts}
            selected_key = st.selectbox("Select Account to Audit", list(acc_map.keys()))
            selected_acc = acc_map[selected_key]
            
            st.subheader(f"Ledger for {selected_acc.account_number}")
            st.metric("Current Balance", f"${selected_acc.balance:,.2f}")
            
            if not selected_acc.transactions:
                st.info("No transactions recorded for this account yet.")
            else:
                tx_data = [tx.to_dict() for tx in selected_acc.transactions]
                df_tx = pd.DataFrame(tx_data)
                
                # Filter by type
                tx_types = ["All"] + list(df_tx["Type"].unique())
                selected_type = st.selectbox("Filter by Transaction Type", tx_types)
                
                if selected_type != "All":
                    df_tx = df_tx[df_tx["Type"] == selected_type]
                    
                st.dataframe(df_tx, use_container_width=True)


if __name__ == "__main اصلی" or __name__ == "__main__":
    main()