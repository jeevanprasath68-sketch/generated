import sqlite3
import pandas as pd
import numpy as np
import datetime
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from typing import List, Dict, Any, Tuple, Optional

DB_FILE = "finance_dashboard.db"

# ==========================================
# BUSINESS LOGIC & DATA ENGINE
# ==========================================

class FinanceEngine:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initializes the database and performs self-healing schema migration for robustness."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Create transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT
            )
        ''')
        
        # Create budgets table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL UNIQUE,
                monthly_limit REAL NOT NULL
            )
        ''')
        
        # Defensive schema migration: check columns for transactions
        cursor.execute("PRAGMA table_info(transactions)")
        existing_cols = {row["name"] for row in cursor.fetchall()}
        required_trans_cols = {
            "date": "TEXT",
            "type": "TEXT",
            "category": "TEXT",
            "amount": "REAL",
            "description": "TEXT"
        }
        for col, col_type in required_trans_cols.items():
            if col not in existing_cols:
                try:
                    cursor.execute(f"ALTER TABLE transactions ADD COLUMN {col} {col_type}")
                except Exception:
                    pass

        # Defensive schema migration: check columns for budgets
        cursor.execute("PRAGMA table_info(budgets)")
        existing_budget_cols = {row["name"] for row in cursor.fetchall()}
        required_budget_cols = {
            "category": "TEXT",
            "monthly_limit": "REAL"
        }
        for col, col_type in required_budget_cols.items():
            if col not in existing_budget_cols:
                try:
                    cursor.execute(f"ALTER TABLE budgets ADD COLUMN {col} {col_type}")
                except Exception:
                    pass

        conn.commit()
        conn.close()

    def reset_database(self) -> None:
        """Wipes all tables and re-initializes schema."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS transactions")
        cursor.execute("DROP TABLE IF EXISTS budgets")
        conn.commit()
        conn.close()
        self._init_db()

    def add_transaction(self, date: str, trans_type: str, category: str, amount: float, description: str = "") -> int:
        if amount <= 0:
            raise ValueError("Transaction amount must be greater than zero.")
        if trans_type not in ["Income", "Expense"]:
            raise ValueError("Transaction type must be 'Income' or 'Expense'.")
            
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (date, type, category, amount, description) VALUES (?, ?, ?, ?, ?)",
            (date, trans_type, category, amount, description)
        )
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id

    def delete_transaction(self, trans_id: int) -> None:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transactions WHERE id = ?", (trans_id,))
        conn.commit()
        conn.close()

    def get_transactions(self) -> pd.DataFrame:
        try:
            conn = self._get_connection()
            df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date DESC, id DESC", conn)
            conn.close()
            if not df.empty:
                df['date'] = pd.to_datetime(df['date']).dt.date
            return df
        except sqlite3.OperationalError:
            self._init_db()
            return pd.DataFrame(columns=["id", "date", "type", "category", "amount", "description"])

    def set_budget(self, category: str, monthly_limit: float) -> None:
        if monthly_limit < 0:
            raise ValueError("Budget limit cannot be negative.")
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO budgets (category, monthly_limit) VALUES (?, ?) ON CONFLICT(category) DO UPDATE SET monthly_limit = ?",
            (category, monthly_limit, monthly_limit)
        )
        conn.commit()
        conn.close()

    def get_budgets(self) -> pd.DataFrame:
        try:
            conn = self._get_connection()
            df = pd.read_sql_query("SELECT * FROM budgets", conn)
            conn.close()
            return df
        except sqlite3.OperationalError:
            self._init_db()
            return pd.DataFrame(columns=["id", "category", "monthly_limit"])

    def calculate_summary(self, df: pd.DataFrame) -> Dict[str, float]:
        if df.empty:
            return {"total_income": 0.0, "total_expense": 0.0, "net_savings": 0.0, "savings_rate": 0.0}
        
        income_df = df[df['type'] == 'Income']
        expense_df = df[df['type'] == 'Expense']
        
        total_income = float(income_df['amount'].sum()) if not income_df.empty else 0.0
        total_expense = float(expense_df['amount'].sum()) if not expense_df.empty else 0.0
        net_savings = total_income - total_expense
        savings_rate = (net_savings / total_income * 100) if total_income > 0 else 0.0
        
        return {
            "total_income": total_income,
            "total_expense": total_expense,
            "net_savings": net_savings,
            "savings_rate": savings_rate
        }

# ==========================================
# STREAMLIT USER INTERFACE
# ==========================================

def main():
    st.set_page_config(
        page_title="Personal Finance Dashboard",
        page_icon="💰",
        layout="wide"
    )

    engine = FinanceEngine(DB_FILE)

    # --- SIDEBAR & CONTROLS ---
    st.sidebar.title("⚙️ Controls & Navigation")
    page = st.sidebar.radio("Select View", ["Dashboard & Analytics", "Log Transaction", "Manage Budgets", "Data Management"])

    st.sidebar.markdown("---")
    st.sidebar.subheader("🛠️ Database Maintenance")
    if st.sidebar.button("⚠️ Reset All Data", type="secondary", help="Wipes all transactions and budgets."):
        engine.reset_database()
        st.sidebar.success("Database reset successfully!")
        st.rerun()

    # --- FETCH DATA ---
    df_trans = engine.get_transactions()
    df_budgets = engine.get_budgets()

    # ==========================================
    # PAGE 1: DASHBOARD & ANALYTICS
    # ==========================================
    if page == "Dashboard & Analytics":
        st.title("📊 Personal Finance Dashboard")
        st.markdown("Get a high-level view of your income, expenses, savings rate, and category breakdowns.")

        # Global Date & Type Filters in expander or top bar
        if not df_trans.empty:
            st.sidebar.markdown("### 🔍 Filters")
            min_date = min(df_trans['date'])
            max_date = max(df_trans['date'])
            
            date_range = st.sidebar.date_input(
                "Filter by Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_d, end_d = date_range
                mask = (df_trans['date'] >= start_d) & (df_trans['date'] <= end_d)
                filtered_df = df_trans.loc[mask]
            else:
                filtered_df = df_trans
        else:
            filtered_df = df_trans

        # Calculate Metrics
        summary = engine.calculate_summary(filtered_df)

        # KPI Metrics Row
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric(label="Total Income", value=f"${summary['total_income']:,.2f}", delta=None)
        with col2:
            st.metric(label="Total Expenses", value=f"${summary['total_expense']:,.2f}", delta=None, delta_color="inverse")
        with col3:
            st.metric(label="Net Savings", value=f"${summary['net_savings']:,.2f}", delta=f"{summary['savings_rate']:.1f}% rate")
        with col4:
            savings_status = "🟢 Healthy" if summary['savings_rate'] >= 20 else ("🟡 Moderate" if summary['savings_rate'] >= 0 else "🔴 Deficit")
            st.metric(label="Savings Status", value=savings_status)

        st.markdown("---")

        if filtered_df.empty:
            st.info("No transaction records found. Add transactions using the 'Log Transaction' tab or sidebar!")
        else:
            # Charts Section
            chart_col1, chart_col2 = st.columns(2)

            with chart_col1:
                st.subheader("📂 Expenses by Category")
                exp_df = filtered_df[filtered_df['type'] == 'Expense']
                if not exp_df.empty:
                    cat_exp = exp_df.groupby('category')['amount'].sum().reset_index()
                    fig_pie = px.pie(cat_exp, names='category', values='amount', hole=0.4, color_discrete_sequence=px.colors.sequential.RdBu)
                    fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=350)
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.info("No expense records in this range.")

            with chart_col2:
                st.subheader("📈 Income vs. Expense Trend")
                trend_df = filtered_df.copy()
                trend_df['month'] = pd.to_datetime(trend_df['date']).dt.to_period('M').astype(str)
                monthly_group = trend_df.groupby(['month', 'type'])['amount'].sum().reset_index()
                if not monthly_group.empty:
                    fig_bar = px.bar(monthly_group, x='month', y='amount', color='type', barmode='group',
                                     color_discrete_map={'Income': '#2ecc71', 'Expense': '#e74c3c'})
                    fig_bar.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=350)
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info("Insufficient data for trend analysis.")

            # Monthly Budget Tracker Section
            st.subheader("🎯 Monthly Budget Performance")
            if not df_budgets.empty:
                current_month_str = datetime.date.today().strftime('%Y-%m')
                current_month_exp = filtered_df[
                    (filtered_df['type'] == 'Expense') &
                    (pd.to_datetime(filtered_df['date']).dt.strftime('%Y-%m') == current_month_str)
                ]
                actual_spend = current_month_exp.groupby('category')['amount'].sum().reset_index()
                
                budget_tracker = pd.merge(df_budgets, actual_spend, on='category', how='left').fillna(0)
                budget_tracker.rename(columns={'amount': 'spent', 'monthly_limit': 'budget'}, inplace=True)
                budget_tracker['remaining'] = budget_tracker['budget'] - budget_tracker['spent']
                budget_tracker['percentage'] = (budget_tracker['spent'] / budget_tracker['budget'] * 100).fillna(0)

                for _, row in budget_tracker.iterrows():
                    cat = row['category']
                    spent = row['spent']
                    limit = row['budget']
                    pct = min(row['percentage'], 100.0)
                    
                    col_b1, col_b2 = st.columns([3, 1])
                    with col_b1:
                        st.text(f"{cat}: ${spent:,.2f} spent of ${limit:,.2f} limit ({row['percentage']:.1f}%)")
                        st.progress(int(pct))
                    with col_b2:
                        if spent > limit:
                            st.error(f"Over by ${spent - limit:,.2f}")
                        else:
                            st.success(f"Left: ${limit - spent:,.2f}")
            else:
                st.info("No budgets configured yet. Set budgets in the 'Manage Budgets' tab.")

            # Recent Transactions Table with Delete Option
            st.markdown("---")
            st.subheader("📋 Transaction History")
            
            # Display editable/deletable dataframe view
            display_df = filtered_df.copy()
            st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ==========================================
    # PAGE 2: LOG TRANSACTION
    # ==========================================
    elif page == "Log Transaction":
        st.title("📝 Log Income or Expense")
        st.markdown("Record your financial inflows and outflows quickly.")

        default_categories = {
            "Income": ["Salary", "Freelance", "Investments", "Gifts", "Other Income"],
            "Expense": ["Housing", "Groceries", "Utilities", "Transportation", "Entertainment", "Healthcare", "Dining Out", "Shopping", "Other Expense"]
        }

        with st.form("transaction_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                trans_type = st.selectbox("Transaction Type", ["Expense", "Income"])
                amount = st.number_input("Amount ($", min_value=0.01, step=1.00, format="%.2f")
            with col2:
                date = st.date_input("Date", value=datetime.date.today())
                categories = default_categories.get(trans_type, ["General"])
                category = st.selectbox("Category", categories)
            
            description = st.text_input("Description / Note (Optional)", placeholder="e.g., Weekly grocery run at Whole Foods")
            
            submitted = st.form_submit_button("💾 Save Transaction", type="primary")
            if submitted:
                try:
                    engine.add_transaction(str(date), trans_type, category, float(amount), description)
                    st.success(f"Successfully logged {trans_type} of ${amount:.2f} under {category}!")
                except ValueError as e:
                    st.error(str(e))

        st.markdown("---")
        st.subheader("🗑️ Delete Recent Transactions")
        if not df_trans.empty:
            trans_to_delete = st.selectbox(
                "Select Transaction to Delete",
                options=df_trans['id'].tolist(),
                format_func=lambda x: f"ID {x}: {df_trans.loc[df_trans['id'] == x, 'date'].values[0]} | {df_trans.loc[df_trans['id'] == x, 'type'].values[0]} | {df_trans.loc[df_trans['id'] == x, 'category'].values[0]} | ${df_trans.loc[df_trans['id'] == x, 'amount'].values[0]:,.2f}"
            )
            if st.button("Delete Selected Transaction"):
                engine.delete_transaction(trans_to_delete)
                st.success(f"Deleted transaction ID {trans_to_delete} successfully!")
                st.rerun()
        else:
            st.info("No transactions available to delete.")

    # ==========================================
    # PAGE 3: MANAGE BUDGETS
    # ==========================================
    elif page == "Manage Budgets":
        st.title("🎯 Monthly Budget Manager")
        st.markdown("Set spending limits for your expense categories to keep your finances on track.")

        expense_categories = ["Housing", "Groceries", "Utilities", "Transportation", "Entertainment", "Healthcare", "Dining Out", "Shopping", "Other Expense"]

        with st.form("budget_form"):
            b_cat = st.selectbox("Category", expense_categories)
            b_limit = st.number_input("Monthly Limit ($", min_value=0.0, step=50.0, format="%.2f")
            b_submitted = st.form_submit_button("💾 Save / Update Budget", type="primary")
            
            if b_submitted:
                try:
                    engine.set_budget(b_cat, float(b_limit))
                    st.success(f"Budget for '{b_cat}' set to ${b_limit:,.2f} / month!")
                    st.rerun()
                except ValueError as e:
                    st.error(str(e))

        st.markdown("### Current Active Budgets")
        if not df_budgets.empty:
            st.dataframe(df_budgets, use_container_width=True, hide_index=True)
        else:
            st.info("No category budgets defined yet.")

    # ==========================================
    # PAGE 4: DATA MANAGEMENT & EXPORT
    # ==========================================
    elif page == "Data Management":
        st.title("📤 Data Export & Management")
        st.markdown("Export your complete financial records to CSV for external analysis or backup.")

        if not df_trans.empty:
            csv_data = df_trans.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Transactions as CSV",
                data=csv_data,
                file_name=f"personal_finance_export_{datetime.date.today()}.csv",
                mime="text/csv",
                type="primary"
            )
            
            st.markdown("### Preview Export Data")
            st.dataframe(df_trans, use_container_width=True)
        else:
            st.info("No transaction data available for export.")

if __name__ == '__main__':
    main()