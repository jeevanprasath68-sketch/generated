import sqlite3
import datetime
import pandas as pd
import streamlit as st
from typing import List, Dict, Any, Tuple, Optional

DB_FILE = "ssi_hr_payroll.sqlite"

# ==========================================
# BUSINESS LOGIC & DATA ENGINE
# ==========================================

class HREngine:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create tables if they do not exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                hourly_rate REAL NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS time_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                log_date TEXT NOT NULL,
                login_time TEXT NOT NULL,
                logout_time TEXT NOT NULL,
                hours_worked REAL NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS advances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                request_date TEXT NOT NULL,
                amount REAL NOT NULL,
                reason TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees (id)
            )
        """)
        
        conn.commit()
        
        # Defensive migration check: ensure columns exist
        self._ensure_column(cursor, "employees", "hourly_rate", "REAL DEFAULT 10.0")
        self._ensure_column(cursor, "time_logs", "hours_worked", "REAL DEFAULT 0.0")
        self._ensure_column(cursor, "advances", "reason", "TEXT DEFAULT ''")
        conn.commit()
        conn.close()

    def _ensure_column(self, cursor: sqlite3.Cursor, table_name: str, column_name: str, column_def: str):
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row["name"] for row in cursor.fetchall()]
        if column_name not in columns:
            try:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
            except Exception:
                pass

    def reset_database(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS time_logs")
        cursor.execute("DROP TABLE IF EXISTS advances")
        cursor.execute("DROP TABLE IF EXISTS employees")
        conn.commit()
        conn.close()
        self._init_db()

    def add_employee(self, name: str, role: str, hourly_rate: float) -> int:
        if not name.strip():
            raise ValueError("Employee name cannot be empty.")
        if hourly_rate < 0:
            raise ValueError("Hourly rate cannot be negative.")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO employees (name, role, hourly_rate, created_at) VALUES (?, ?, ?, ?)",
            (name.strip(), role.strip(), float(hourly_rate), datetime.date.today().isoformat())
        )
        conn.commit()
        emp_id = cursor.lastrowid
        conn.close()
        return emp_id

    def get_employees(self) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees ORDER BY name ASC")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def log_time(self, employee_id: int, log_date: str, login_time: str, logout_time: str) -> int:
        # Validate times
        t_in = datetime.datetime.strptime(login_time, "%H:%M")
        t_out = datetime.datetime.strptime(logout_time, "%H:%M")
        if t_out <= t_in:
            raise ValueError("Logout time must be strictly after login time.")
        
        delta = t_out - t_in
        hours_worked = round(delta.total_seconds() / 3600.0, 2)

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO time_logs (employee_id, log_date, login_time, logout_time, hours_worked) VALUES (?, ?, ?, ?, ?)",
            (employee_id, log_date, login_time, logout_time, hours_worked)
        )
        conn.commit()
        log_id = cursor.lastrowid
        conn.close()
        return log_id

    def get_time_logs(self, employee_id: Optional[int] = None) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        if employee_id:
            cursor.execute(
                "SELECT t.*, e.name FROM time_logs t JOIN employees e ON t.employee_id = e.id WHERE t.employee_id = ? ORDER BY t.log_date DESC",
                (employee_id,)
            )
        else:
            cursor.execute(
                "SELECT t.*, e.name FROM time_logs t JOIN employees e ON t.employee_id = e.id ORDER BY t.log_date DESC"
            )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def add_advance(self, employee_id: int, request_date: str, amount: float, reason: str) -> int:
        if amount <= 0:
            raise ValueError("Advance payment amount must be greater than zero.")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO advances (employee_id, request_date, amount, reason) VALUES (?, ?, ?, ?)",
            (employee_id, request_date, float(amount), reason.strip())
        )
        conn.commit()
        adv_id = cursor.lastrowid
        conn.close()
        return adv_id

    def get_advances(self, employee_id: Optional[int] = None) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        if employee_id:
            cursor.execute(
                "SELECT a.*, e.name FROM advances a JOIN employees e ON a.employee_id = e.id WHERE a.employee_id = ? ORDER BY a.request_date DESC",
                (employee_id,)
            )
        else:
            cursor.execute(
                "SELECT a.*, e.name FROM advances a JOIN employees e ON a.employee_id = e.id ORDER BY a.request_date DESC"
            )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    def calculate_weekly_payroll(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Calculates gross wages, total advances, and net weekly payment for each employee
        within a specified date range [start_date, end_date].
        """
        employees = self.get_employees()
        payroll_summary = []

        conn = self.get_connection()
        cursor = conn.cursor()

        for emp in employees:
            emp_id = emp["id"]
            rate = emp["hourly_rate"]

            # Sum hours worked in range
            cursor.execute(
                "SELECT SUM(hours_worked) as total_hours FROM time_logs WHERE employee_id = ? AND log_date BETWEEN ? AND ?",
                (emp_id, start_date, end_date)
            )
            row_hours = cursor.fetchone()
            total_hours = row_hours["total_hours"] if row_hours and row_hours["total_hours"] is not None else 0.0
            gross_wage = round(total_hours * rate, 2)

            # Sum advances in range
            cursor.execute(
                "SELECT SUM(amount) as total_advances FROM advances WHERE employee_id = ? AND request_date BETWEEN ? AND ?",
                (emp_id, start_date, end_date)
            )
            row_adv = cursor.fetchone()
            total_advances = row_adv["total_advances"] if row_adv and row_adv["total_advances"] is not None else 0.0

            net_pay = round(gross_wage - total_advances, 2)

            payroll_summary.append({
                "employee_id": emp_id,
                "name": emp["name"],
                "role": emp["role"],
                "hourly_rate": rate,
                "total_hours": total_hours,
                "gross_wage": gross_wage,
                "total_advances": total_advances,
                "net_pay": net_pay
            })

        conn.close()
        return payroll_summary


# ==========================================
# STREAMLIT UI INTERFACE
# ==========================================

def main():
    st.set_page_config(
        page_title="SSI HR & Payroll Manager",
        page_icon="🏭",
        layout="wide"
    )

    engine = HREngine()

    st.title("🏭 Small Scale Industries HR & Payroll Hub")
    st.markdown("Manage employee attendance (Login/Logout), hourly wages, advance payments, and weekly net payouts efficiently.")

    # Sidebar Navigation & Maintenance
    st.sidebar.title("Navigation")
    app_mode = st.sidebar.selectbox(
        "Choose Module",
        ["Dashboard", "Employee Management", "Time & Attendance", "Advance Payments", "Weekly Payroll"]
    )

    st.sidebar.markdown("---")
    with st.sidebar.expander("🛠️ Database Maintenance"):
        if st.button("Reset All Data", type="primary"):
            engine.reset_database()
            st.sidebar.success("Database reset successfully!")
            st.rerun()

    # 1. DASHBOARD
    if app_mode == "Dashboard":
        st.header("📊 SSI Operations Dashboard")
        employees = engine.get_employees()
        logs = engine.get_time_logs()
        advances = engine.get_advances()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(label="Total Employees", value=len(employees))
        with col2:
            st.metric(label="Total Shifts Logged", value=len(logs))
        with col3:
            total_adv_amt = sum([a["amount"] for a in advances])
            st.metric(label="Total Advances Issued", value=f"${total_adv_amt:,.2f}")

        st.markdown("---")
        st.subheader("Recent Attendance Logs")
        if logs:
            df_logs = pd.DataFrame(logs)
            st.dataframe(df_logs[["name", "log_date", "login_time", "logout_time", "hours_worked"]], use_container_width=True)
        else: 
            st.info("No time logs recorded yet.")

        st.subheader("Recent Advance Requests")
        if advances:
            df_adv = pd.DataFrame(advances)
            st.dataframe(df_adv[["name", "request_date", "amount", "reason"]], use_container_width=True)
        else:
            st.info("No advance payments recorded yet.")

    # 2. EMPLOYEE MANAGEMENT
    elif app_mode == "Employee Management":
        st.header("👥 Employee Directory & Setup")
        
        with st.form("add_employee_form"):
            st.subheader("Register New Employee")
            col1, col2, col3 = st.columns(3)
            with col1:
                emp_name = st.text_input("Full Name")
            with col2:
                emp_role = st.text_input("Role / Department", value="Operator")
            with col3:
                hourly_rate = st.number_input("Hourly Wage Rate ($)", min_value=0.0, value=15.0, step=0.5)
            
            submit_emp = st.form_submit_button("Register Employee")
            if submit_emp:
                try:
                    engine.add_employee(emp_name, emp_role, hourly_rate)
                    st.success(f"Successfully registered employee: {emp_name}!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        st.markdown("---")
        st.subheader("Active Employee Roster")
        employees = engine.get_employees()
        if employees:
            st.dataframe(pd.DataFrame(employees), use_container_width=True)
        else:
            st.info("No employees registered yet. Use the form above to add one.")

    # 3. TIME & ATTENDANCE
    elif app_mode == "Time & Attendance":
        st.header("⏱️ Shift Login & Logout Time Tracker")
        
        employees = engine.get_employees()
        if not employees:
            st.warning("Please register employees first before logging time.")
            return

        emp_dict = {f"{e['name']} (ID: {e['id']})": e['id'] for e in employees}

        with st.form("time_log_form"):
            st.subheader("Record Daily Shift")
            selected_emp_str = st.selectbox("Select Employee", list(emp_dict.keys()))
            log_date = st.date_input("Work Date", value=datetime.date.today())
            
            col1, col2 = st.columns(2)
            with col1:
                login_time_str = st.text_input("Login Time (HH:MM 24-hr format)", value="08:00")
            with col2:
                logout_time_str = st.text_input("Logout Time (HH:MM 24-hr format)", value="17:00")
            
            submit_time = st.form_submit_button("Save Shift Log")
            if submit_time:
                try:
                    emp_id = emp_dict[selected_emp_str]
                    engine.log_time(emp_id, log_date.isoformat(), login_time_str.strip(), logout_time_str.strip())
                    st.success("Shift logged successfully and hours calculated!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Validation Error: {e}")

        st.markdown("---")
        st.subheader("All Shift Logs")
        logs = engine.get_time_logs()
        if logs:
            st.dataframe(pd.DataFrame(logs), use_container_width=True)
        else:
            st.info("No shift logs available.")

    # 4. ADVANCE PAYMENTS
    elif app_mode == "Advance Payments":
        st.header("💸 Employee Advance Payment Management")
        
        employees = engine.get_employees()
        if not employees:
            st.warning("Please register employees first.")
            return

        emp_dict = {f"{e['name']} (ID: {e['id']})": e['id'] for e in employees}

        with st.form("advance_form"):
            st.subheader("Issue Advance Payment")
            selected_emp_str = st.selectbox("Select Employee", list(emp_dict.keys()))
            req_date = st.date_input("Advance Date", value=datetime.date.today())
            amount = st.number_input("Advance Amount ($)", min_value=0.0, value=50.0, step=10.0)
            reason = st.text_input("Reason / Note", value="Emergency Medical")
            
            submit_adv = st.form_submit_button("Record Advance")
            if submit_adv:
                try:
                    emp_id = emp_dict[selected_emp_str]
                    engine.add_advance(emp_id, req_date.isoformat(), amount, reason)
                    st.success("Advance payment recorded successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        st.markdown("---")
        st.subheader("Advance Payments History")
        advances = engine.get_advances()
        if advances:
            st.dataframe(pd.DataFrame(advances), use_container_width=True)
        else:
            st.info("No advance payments recorded.")

    # 5. WEEKLY PAYROLL
    elif app_mode == "Weekly Payroll":
        st.header("💰 Weekly Payroll & Net Wages Settlement")
        st.markdown("Calculate gross wages based on hours worked and deduct any cash advances taken during the week.")

        col1, col2 = st.columns(2)
        with col1:
            default_start = datetime.date.today() - datetime.timedelta(days=7)
            start_date = st.date_input("Payroll Start Date", value=default_start)
        with col2:
            end_date = st.date_input("Payroll End Date", value=datetime.date.today())

        if start_date > end_date:
            st.error("Start date cannot be after end date.")
            return

        if st.button("Generate Weekly Payroll Summary", type="primary"):
            summary = engine.calculate_weekly_payroll(start_date.isoformat(), end_date.isoformat())
            
            if summary:
                df_payroll = pd.DataFrame(summary)
                st.success(f"Payroll calculated for period: {start_date} to {end_date}")
                
                # Display metrics
                tot_gross = df_payroll["gross_wage"].sum()
                tot_adv = df_payroll["total_advances"].sum()
                tot_net = df_payroll["net_pay"].sum()
                
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Total Gross Wages", f"${tot_gross:,.2f}")
                with m2:
                    st.metric("Total Deducted Advances", f"${tot_adv:,.2f}")
                with m3:
                    st.metric("Total Net Payout", f"${tot_net:,.2f}")

                st.markdown("---")
                st.subheader("Detailed Employee Settlement Sheet")
                st.dataframe(df_payroll, use_container_width=True)
            else:
                st.info("No employee records found for calculation.")

if __name__ == "__main__":
    main()