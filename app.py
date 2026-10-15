"""SpendWise — Student Expense & Budget Manager.

A complete personal finance manager built with Streamlit, SQLite, Pandas, and Plotly.
"""

import sqlite3
from datetime import datetime, date
from typing import List, Dict, Any, Optional, Tuple
import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# =====================================================================
# CONSTANTS & CONFIGURATION
# =====================================================================
CATEGORIES: List[str] = ["Food", "Transport", "Education", "Shopping", "Entertainment", "Other"]
PAYMENT_METHODS: List[str] = ["Cash", "Debit Card", "Credit Card", "UPI / Mobile Payment", "Bank Transfer"]
DEFAULT_DB_PATH = "spendwise.db"


# =====================================================================
# DATABASE & STORAGE LAYER
# =====================================================================
class ExpenseDB:
    """Handles SQLite database operations for expenses and monthly budgets."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    expense_date TEXT NOT NULL,
                    payment_method TEXT NOT NULL,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS budgets (
                    month_year TEXT PRIMARY KEY,
                    amount REAL NOT NULL
                )
                """
            )
            conn.commit()

    def add_expense(self, amount: float, category: str, expense_date: str, payment_method: str, description: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO expenses (amount, category, expense_date, payment_method, description)
                VALUES (?, ?, ?, ?, ?)
                """,
                (amount, category, expense_date, payment_method, description.strip())
            )
            conn.commit()
            return cursor.lastrowid

    def update_expense(self, expense_id: int, amount: float, category: str, expense_date: str, payment_method: str, description: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE expenses
                SET amount = ?, category = ?, expense_date = ?, payment_method = ?, description = ?
                WHERE id = ?
                """,
                (amount, category, expense_date, payment_method, description.strip(), expense_id)
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_expense(self, expense_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_expense_by_id(self, expense_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_expenses(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM expenses ORDER BY expense_date DESC, id DESC")
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def set_budget(self, month_year: str, amount: float) -> None:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO budgets (month_year, amount)
                VALUES (?, ?)
                ON CONFLICT(month_year) DO UPDATE SET amount=excluded.amount
                """,
                (month_year, amount)
            )
            conn.commit()

    def get_budget(self, month_year: str) -> float:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT amount FROM budgets WHERE month_year = ?", (month_year,))
            row = cursor.fetchone()
            return float(row["amount"]) if row else 0.0


# =====================================================================
# BUSINESS LOGIC & ANALYTICS LAYER
# =====================================================================
class ExpenseValidator:
    """Validates form fields and parameters."""

    @staticmethod
    def validate_amount(amount: Any) -> float:
        try:
            val = float(amount)
            if val <= 0:
                raise ValueError("Amount must be strictly greater than 0.")
            return round(val, 2)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid amount: {exc}") from exc

    @staticmethod
    def validate_date(date_str: str) -> str:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except Exception as exc:
            raise ValueError(f"Invalid date format (must be YYYY-MM-DD): {date_str}") from exc

    @staticmethod
    def validate_category(cat: str) -> str:
        if not cat or cat.strip() not in CATEGORIES:
            raise ValueError(f"Category must be one of {CATEGORIES}")
        return cat.strip()


class AnalyticsEngine:
    """Performs aggregations, metrics computations, and filtering on expense data."""

    @staticmethod
    def filter_and_sort(
        df: pd.DataFrame,
        search_query: str = "",
        categories: Optional[List[str]] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        sort_by: str = "Date",
        sort_order: str = "Descending",
    ) -> pd.DataFrame:
        if df.empty:
            return df

        res = df.copy()
        res["expense_date_dt"] = pd.to_datetime(res["expense_date"]).dt.date

        if start_date:
            res = res[res["expense_date_dt"] >= start_date]
        if end_date:
            res = res[res["expense_date_dt"] <= end_date]

        if categories:
            res = res[res["category"].isin(categories)]

        if search_query.strip():
            q = search_query.strip().lower()
            desc_match = res["description"].fillna("").str.lower().str.contains(q)
            cat_match = res["category"].fillna("").str.lower().str.contains(q)
            method_match = res["payment_method"].fillna("").str.lower().str.contains(q)
            res = res[desc_match | cat_match | method_match]

        ascending = (sort_order == "Ascending")
        if sort_by == "Amount":
            res = res.sort_values(by="amount", ascending=ascending)
        elif sort_by == "Date":
            res = res.sort_values(by="expense_date_dt", ascending=ascending)
        elif sort_by == "Category":
            res = res.sort_values(by="category", ascending=ascending)

        return res.drop(columns=["expense_date_dt"], errors="ignore")

    @staticmethod
    def calculate_budget_summary(df: pd.DataFrame, target_month_year: str, monthly_budget: float) -> Dict[str, Any]:
        if df.empty:
            return {
                "total_spent": 0.0,
                "budget": monthly_budget,
                "remaining": monthly_budget,
                "percentage_used": 0.0,
                "status": "On Track",
            }

        df_copy = df.copy()
        df_copy["month_year"] = pd.to_datetime(df_copy["expense_date"]).dt.strftime("%Y-%m")
        month_data = df_copy[df_copy["month_year"] == target_month_year]

        total_spent = float(month_data["amount"].sum())
        remaining = monthly_budget - total_spent
        percentage_used = (total_spent / monthly_budget * 100.0) if monthly_budget > 0 else 0.0

        status = "On Track"
        if monthly_budget > 0:
            if total_spent > monthly_budget:
                status = "Over Budget"
            elif total_spent >= 0.85 * monthly_budget:
                status = "Warning (>85%)"

        return {
            "total_spent": round(total_spent, 2),
            "budget": round(monthly_budget, 2),
            "remaining": round(remaining, 2),
            "percentage_used": round(percentage_used, 1),
            "status": status,
        }

    @staticmethod
    def category_breakdown(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=["category", "amount", "percentage"])
        grouped = df.groupby("category")["amount"].sum().reset_index()
        total = grouped["amount"].sum()
        grouped["percentage"] = (grouped["amount"] / total * 100).round(1) if total > 0 else 0.0
        return grouped.sort_values(by="amount", ascending=False)

    @staticmethod
    def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=["month_year", "amount"])
        df_copy = df.copy()
        df_copy["month_year"] = pd.to_datetime(df_copy["expense_date"]).dt.strftime("%Y-%m")
        grouped = df_copy.groupby("month_year")["amount"].sum().reset_index()
        return grouped.sort_values(by="month_year")


def export_dataframe_to_csv(df: pd.DataFrame) -> str:
    if df.empty:
        return "id,amount,category,expense_date,payment_method,description\n"
    clean_df = df.drop(columns=["created_at"], errors="ignore")
    return clean_df.to_csv(index=False)


# =====================================================================
# STREAMLIT UI PRESENTATION LAYER
# =====================================================================
def init_session_state(db: ExpenseDB):
    if "db" not in st.session_state:
        st.session_state.db = db
    if "edit_id" not in st.session_state:
        st.session_state.edit_id = None


def render_ui():
    st.set_page_config(
        page_title="SpendWise — Student Budget Manager",
        page_icon="💳",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
        .main { background-color: #0E1117; color: #FAFAFA; }
        .metric-card {
            background: linear-gradient(135deg, #1E2638 0%, #151A24 100%);
            border: 1px solid #2D3748;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        }
        .metric-label {
            font-size: 0.85rem;
            color: #A0AEC0;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .metric-value {
            font-size: 1.85rem;
            font-weight: 700;
            color: #F7FAFC;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-top: 8px;
        }
        .badge-safe { background-color: #22543D; color: #9AE6B4; }
        .badge-warn { background-color: #744210; color: #FEEBC8; }
        .badge-danger { background-color: #742A2A; color: #FEB2B2; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    db = ExpenseDB()
    init_session_state(db)

    st.sidebar.title("💳 SpendWise")
    st.sidebar.caption("Smart Student Expense & Budget Tracker")
    st.sidebar.divider()

    current_ym = datetime.today().strftime("%Y-%m")
    view_selection = st.sidebar.radio(
        "Navigation",
        ["📊 Dashboard", "➕ Add & Edit Expenses", "📑 Expense History & Export", "⚙️ Budget Settings"],
    )

    expenses = db.get_all_expenses()
    df_expenses = pd.DataFrame(expenses)
    current_budget = db.get_budget(current_ym)

    if view_selection == "📊 Dashboard":
        st.title("Personal Finance Dashboard")
        st.caption(f"Overview for current billing period: **{current_ym}**")

        summary = AnalyticsEngine.calculate_budget_summary(df_expenses, current_ym, current_budget)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                f"""<div class="metric-card">
                    <div class="metric-label">Monthly Budget</div>
                    <div class="metric-value">${summary['budget']:,.2f}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""<div class="metric-card">
                    <div class="metric-label">Month Spending</div>
                    <div class="metric-value">${summary['total_spent']:,.2f}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with c3:
            rem_color = "#FEB2B2" if summary["remaining"] < 0 else "#9AE6B4"
            st.markdown(
                f"""<div class="metric-card">
                    <div class="metric-label">Remaining Budget</div>
                    <div class="metric-value" style="color: {rem_color};">${summary['remaining']:,.2f}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with c4:
            badge_class = "badge-safe"
            if summary["status"] == "Warning (>85%)":
                badge_class = "badge-warn"
            elif summary["status"] == "Over Budget":
                badge_class = "badge-danger"

            st.markdown(
                f"""<div class="metric-card">
                    <div class="metric-label">Budget Used</div>
                    <div class="metric-value">{summary['percentage_used']}%</div>
                    <span class="status-badge {badge_class}">{summary['status']}</span>
                </div>""",
                unsafe_allow_html=True,
            )

        st.divider()

        if df_expenses.empty:
            st.info("No expenses logged yet! Head over to '➕ Add & Edit Expenses' to record your first transaction.")
        else:
            g1, g2 = st.columns(2)

            with g1:
                st.subheader("Spending by Category")
                cat_df = AnalyticsEngine.category_breakdown(df_expenses)
                if not cat_df.empty:
                    fig_pie = px.pie(
                        cat_df,
                        names="category",
                        values="amount",
                        hole=0.45,
                        color_discrete_sequence=px.colors.qualitative.Prism,
                    )
                    fig_pie.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#E2E8F0"),
                        margin=dict(t=20, b=20, l=20, r=20),
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
                else:
                    st.write("No category data available.")

            with g2:
                st.subheader("Monthly Spending Trend")
                trend_df = AnalyticsEngine.monthly_trend(df_expenses)
                if not trend_df.empty:
                    fig_bar = px.bar(
                        trend_df,
                        x="month_year",
                        y="amount",
                        labels={"month_year": "Month", "amount": "Total Spent ($)"},
                        color_discrete_sequence=["#6366F1"],
                    )
                    fig_bar.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#E2E8F0"),
                        xaxis=dict(gridcolor="#2D3748"),
                        yaxis=dict(gridcolor="#2D3748"),
                        margin=dict(t=20, b=20, l=20, r=20),
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.write("No trend data available.")

            st.subheader("Payment Method Distribution")
            pm_df = df_expenses.groupby("payment_method")["amount"].sum().reset_index()
            fig_pm = px.bar(
                pm_df,
                x="payment_method",
                y="amount",
                color="payment_method",
                labels={"payment_method": "Payment Method", "amount": "Amount ($)"},
            )
            fig_pm.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E2E8F0"),
                xaxis=dict(gridcolor="#2D3748"),
                yaxis=dict(gridcolor="#2D3748"),
                showlegend=False,
                margin=dict(t=20, b=20, l=20, r=20),
            )
            st.plotly_chart(fig_pm, use_container_width=True)

    elif view_selection == "➕ Add & Edit Expenses":
        st.title("Manage Expenses")

        is_editing = st.session_state.edit_id is not None
        edit_data = {}
        if is_editing:
            edit_data = db.get_expense_by_id(st.session_state.edit_id) or {}
            if not edit_data:
                st.session_state.edit_id = None
                is_editing = False

        st.subheader("Edit Expense" if is_editing else "Log a New Expense")

        default_amount = float(edit_data.get("amount", 10.0)) if is_editing else 10.0
        default_cat = edit_data.get("category", CATEGORIES[0]) if is_editing else CATEGORIES[0]
        default_date = datetime.strptime(edit_data["expense_date"], "%Y-%m-%d").date() if is_editing else date.today()
        default_method = edit_data.get("payment_method", PAYMENT_METHODS[0]) if is_editing else PAYMENT_METHODS[0]
        default_desc = edit_data.get("description", "") if is_editing else ""

        with st.form("expense_form", clear_on_submit=not is_editing):
            c1, c2 = st.columns(2)
            with c1:
                amount_input = st.number_input("Amount ($", min_value=0.01, max_value=100000.0, value=default_amount, step=1.0, format="%.2f")
                category_input = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(default_cat) if default_cat in CATEGORIES else 0)
                date_input = st.date_input("Expense Date", value=default_date)
            with c2:
                method_input = st.selectbox("Payment Method", PAYMENT_METHODS, index=PAYMENT_METHODS.index(default_method) if default_method in PAYMENT_METHODS else 0)
                desc_input = st.text_area("Description / Notes", value=default_desc, placeholder="e.g., Groceries from Trader Joe's")

            submitted = st.form_submit_button("Update Expense" if is_editing else "Save Expense")
            if submitted:
                try:
                    valid_amt = ExpenseValidator.validate_amount(amount_input)
                    valid_date_str = ExpenseValidator.validate_date(date_input.strftime("%Y-%m-%d"))
                    valid_cat = ExpenseValidator.validate_category(category_input)

                    if is_editing:
                        db.update_expense(st.session_state.edit_id, valid_amt, valid_cat, valid_date_str, method_input, desc_input)
                        st.success(f"Expense #{st.session_state.edit_id} updated successfully!")
                        st.session_state.edit_id = None
                        st.rerun()
                    else:
                        new_id = db.add_expense(valid_amt, valid_cat, valid_date_str, method_input, desc_input)
                        st.success(f"Expense logged successfully with ID #{new_id}!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Submission error: {e}")

        if is_editing:
            if st.button("Cancel Edit"):
                st.session_state.edit_id = None
                st.rerun()

        st.divider()
        st.subheader("Recent Transactions")
        if df_expenses.empty:
            st.write("No transactions logged yet.")
        else:
            for _, row in df_expenses.head(10).iterrows():
                col_info, col_edit, col_del = st.columns([6, 1, 1])
                with col_info:
                    st.markdown(
                        f"**{row['category']}** — ${row['amount']:.2f} &nbsp;|&nbsp; <span style='color:#A0AEC0'>{row['expense_date']}</span> &nbsp;|&nbsp; <em>{row['payment_method']}</em> &nbsp;|&nbsp; {row['description'] or 'No description'}",
                        unsafe_allow_html=True,
                    )
                with col_edit:
                    if st.button("✏️ Edit", key=f"edit_{row['id']}"):
                        st.session_state.edit_id = int(row['id'])
                        st.rerun()
                with col_del:
                    if st.button("🗑️ Delete", key=f"del_{row['id']}"):
                        db.delete_expense(int(row['id']))
                        st.success(f"Deleted expense #{row['id']}")
                        st.rerun()

    elif view_selection == "📑 Expense History & Export":
        st.title("Expense Records & Search")

        if df_expenses.empty:
            st.info("No expenses recorded yet.")
        else:
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                search_text = st.text_input("🔍 Search Notes / Payment", value="")
            with f2:
                selected_cats = st.multiselect("Category", options=CATEGORIES, default=[])
            with f3:
                sort_column = st.selectbox("Sort By", ["Date", "Amount", "Category"], index=0)
            with f4:
                sort_direction = st.selectbox("Order", ["Descending", "Ascending"], index=0)

            d1, d2 = st.columns(2)
            with d1:
                start_d = st.date_input("Start Date", value=date(date.today().year, 1, 1))
            with d2:
                end_d = st.date_input("End Date", value=date.today())

            filtered_df = AnalyticsEngine.filter_and_sort(
                df_expenses,
                search_query=search_text,
                categories=selected_cats if selected_cats else None,
                start_date=start_d,
                end_date=end_d,
                sort_by=sort_column,
                sort_order=sort_direction,
            )

            st.write(f"Found **{len(filtered_df)}** matching expenses.")

            display_df = filtered_df[["id", "amount", "category", "expense_date", "payment_method", "description"]].copy()
            display_df["amount"] = display_df["amount"].apply(lambda x: f"${x:,.2f}")
            display_df.rename(columns={
                "id": "ID",
                "amount": "Amount",
                "category": "Category",
                "expense_date": "Date",
                "payment_method": "Payment Method",
                "description": "Description"
            }, inplace=True)

            st.dataframe(display_df, use_container_width=True, hide_index=True)

            csv_data = export_dataframe_to_csv(filtered_df)
            st.download_button(
                label="📥 Download Filtered Data as CSV",
                data=csv_data,
                file_name=f"spendwise_export_{datetime.today().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )

    elif view_selection == "⚙️ Budget Settings":
        st.title("Monthly Budget Configuration")
        st.write("Set and manage spending targets per month.")

        chosen_month = st.selectbox(
            "Select Target Month",
            options=[
                datetime(datetime.today().year, m, 1).strftime("%Y-%m")
                for m in range(1, 13)
            ],
            index=datetime.today().month - 1,
        )

        saved_budget = db.get_budget(chosen_month)

        with st.form("budget_form"):
            new_budget = st.number_input(
                f"Monthly Spending Budget for {chosen_month} ($",
                min_value=0.0,
                max_value=1000000.0,
                value=float(saved_budget if saved_budget > 0 else 500.0),
                step=50.0,
                format="%.2f",
            )
            save_b_btn = st.form_submit_button("Save Budget Target")
            if save_b_btn:
                db.set_budget(chosen_month, new_budget)
                st.success(f"Budget for {chosen_month} set to ${new_budget:,.2f}!")
                st.rerun()


if __name__ == "__main__":
    render_ui()