import streamlit as st
import sqlite3
from datetime import datetime, date, time, timedelta
import pandas as pd
import math

DB_FILE = "ssi_hr.db"

# ==========================================
# DATABASE & STORAGE ENGINE (Self-Healing)
# ==========================================

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Employees Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            hourly_rate REAL NOT NULL,
            phone TEXT,
            created_at TEXT
        )
    ''')
    
    # Attendance Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            clock_in TEXT,
            clock_out TEXT,
            status TEXT,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        )
    ''')
    
    # Advances Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS advances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        )
    ''')
    
    # Payroll Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payroll (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            week_start TEXT NOT NULL,
            week_end TEXT NOT NULL,
            total_hours REAL,
            gross_pay REAL,
            advance_deductions REAL,
            net_pay REAL,
            status TEXT DEFAULT 'Unpaid',
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        )
    ''')
    
    conn.commit()
    
    # Self-healing schema checks
    _ensure_column(cursor, 'employees', 'phone', 'TEXT')
    _ensure_column(cursor, 'advances', 'status', "TEXT DEFAULT 'Pending'")
    _ensure_column(cursor, 'payroll', 'status', "TEXT DEFAULT 'Unpaid'")
    
    conn.close()

def _ensure_column(cursor, table_name, column_name, column_type):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [info[1] for info in cursor.fetchall()]
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        cursor.connection.commit()

def reset_database():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS payroll")
    cursor.execute("DROP TABLE IF EXISTS advances")
    cursor.execute("DROP TABLE IF EXISTS attendance")
    cursor.execute("DROP TABLE IF EXISTS employees")
    conn.commit()
    conn.close()
    init_db()

# ==========================================
# BUSINESS LOGIC & CALCULATOR ENGINE
# ==========================================

class HRCalculator:
    @staticmethod
    def calculate_hours(clock_in: str, clock_out: str) -> float:
        if not clock_in or not clock_out:
            return 0.0
        try:
            fmt = "%H:%M"
            t_in = datetime.strptime(clock_in, fmt)
            t_out = datetime.strptime(clock_out, fmt)
            diff = t_out - t_in
            hours = diff.total_seconds() / 3600.0
            return max(0.0, round(hours, 2))
        except ValueError:
            return 0.0

    @staticmethod
    def compute_weekly_payroll(employee_id: int, hourly_rate: float, total_hours: float, total_advances: float) -> dict:
        gross_pay = round(total_hours * hourly_rate, 2)
        # Deductions cannot exceed gross pay
        deductions = min(gross_pay, total_advances)
        net_pay = round(gross_pay - deductions, 2)
        
        return {
            "employee_id": employee_id,
            "total_hours": total_hours,
            "gross_pay": gross_pay,
            "advance_deductions": deductions,
            "net_pay": net_pay
        }

class DataManager:
    @staticmethod
    def add_employee(name: str, role: str, hourly_rate: float, phone: str):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO employees (name, role, hourly_rate, phone, created_at) VALUES (?, ?, ?, ?, ?)",
            (name, role, hourly_rate, phone, str(date.today()))
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get_employees():
        conn = get_connection()
        df = pd.read_sql("SELECT * FROM employees", conn)
        conn.close()
        return df

    @staticmethod
    def log_attendance(employee_id: int, attendance_date: str, clock_in: str, clock_out: str, status: str):
        conn = get_connection()
        cursor = conn.cursor()
        # Check if record exists for this employee and date
        cursor.execute(
            "SELECT id FROM attendance WHERE employee_id = ? AND date = ?",
            (employee_id, attendance_date)
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "UPDATE attendance SET clock_in = ?, clock_out = ?, status = ? WHERE id = ?",
                (clock_in, clock_out, status, row[0])
            )
        else:
            cursor.execute(
                "INSERT INTO attendance (employee_id, date, clock_in, clock_out, status) VALUES (?, ?, ?, ?, ?)",
                (employee_id, attendance_date, clock_in, clock_out, status)
            )
        conn.commit()
        conn.close()

    @staticmethod
    def request_advance(employee_id: int, amount: float, reason: str):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO advances (employee_id, amount, date, reason, status) VALUES (?, ?, ?, ?, 'Pending')",
            (employee_id, amount, str(date.today()), reason)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def update_advance_status(advance_id: int, status: str):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE advances SET status = ? WHERE id = ?",
            (status, advance_id)
        )
        conn.commit()
        conn.close()

# ==========================================
# STREAMLIT UI APPLICATION
# ==========================================

def main():
    st.set_page_config(
        page_title="SSI Human Resource Management",
        page_icon="🏭",
        layout="wide"
    )
    
    init_db()
    
    st.sidebar.title("🏭 SSI HR Manager")
    menu = st.sidebar.selectbox(
        "Navigation",
        [
            "Dashboard",
            "Employee Directory",
            "Attendance & Time Tracking",
            "Advance Payments",
            "Weekly Payroll"
        ]
    )
    
    st.sidebar.markdown("---")
    with st.sidebar.expander("⚙️ System Settings"):
        if st.button("⚠️ Reset Database", help="Wipes all records and resets schema"):
            reset_database()
            st.success("Database reset successfully!")
            st.rerun()

    # --- DASHBOARD ---
    if menu == "Dashboard":
        st.title("🏭 Small Scale Industry HR Dashboard")
        st.markdown("Welcome to your centralized human resources, time tracking, and payroll management portal.")
        
        emp_df = DataManager.get_employees()
        conn = get_connection()
        att_df = pd.read_sql("SELECT * FROM attendance", conn)
        adv_df = pd.read_sql("SELECT * FROM advances WHERE status = 'Approved'", conn)
        payroll_df = pd.read_sql("SELECT * FROM payroll", conn)
        conn.close()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Employees", len(emp_df))
        with col2:
            today_str = str(date.today())
            today_att = att_df[att_df['date'] == today_str] if not att_df.empty else pd.DataFrame()
            st.metric("Present Today", len(today_att))
        with col3:
            pending_adv = pd.read_sql("SELECT * FROM advances WHERE status = 'Pending'", get_connection())
            st.metric("Pending Advances", len(pending_adv))
        with col4:
            total_payroll_disbursed = payroll_df['net_pay'].sum() if not payroll_df.empty else 0.0
            st.metric("Total Payroll Paid", f"${total_payroll_disbursed:,.2f}")
            
        st.markdown("---")
        st.subheader("Quick Workforce Overview")
        if not emp_df.empty:
            st.dataframe(emp_df, use_container_width=True)
        else:
            st.info("No employees registered yet. Head to the Employee Directory to add staff.")

    # --- EMPLOYEE DIRECTORY ---
    elif menu == "Employee Directory":
        st.title("👥 Employee Directory")
        
        with st.form("add_employee_form", clear_on_submit=True):
            st.subheader("Add New Employee")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full Name")
                role = st.text_input("Job Role / Designation (e.g. Machinist, Welder)")
            with col2:
                hourly_rate = st.number_input("Hourly Wage Rate ($)", min_value=0.0, step=0.5, value=15.0)
                phone = st.text_input("Phone Number")
                
            submitted = st.form_submit_button("Register Employee")
            if submitted:
                if name.strip() and role.strip():
                    DataManager.add_employee(name, role, hourly_rate, phone)
                    st.success(f"Successfully registered {name}!")
                    st.rerun()
                else:
                    st.error("Please provide both Name and Role.")
                    
        st.markdown("---")
        st.subheader("Current Staff List")
        emp_df = DataManager.get_employees()
        if not emp_df.empty:
            st.dataframe(emp_df, use_container_width=True)
        else:
            st.info("No employees found.")

    # --- ATTENDANCE & TIME TRACKING ---
    elif menu == "Attendance & Time Tracking":
        st.title("⏱️ Log-in & Log-out Time Tracking")
        
        emp_df = DataManager.get_employees()
        if emp_df.empty:
            st.warning("Please add employees to the directory before tracking attendance.")
            return
            
        with st.form("attendance_form"):
            st.subheader("Record Daily Attendance")
            col1, col2, col3 = st.columns(3)
            with col1:
                selected_emp = st.selectbox(
                    "Select Employee",
                    options=emp_df['id'].tolist(),
                    format_func=lambda x: emp_df.loc[emp_df['id'] == x, 'name'].values[0]
                )
            with col2:
                att_date = st.date_input("Attendance Date", value=date.today())
            with col3:
                status = st.selectbox("Status", ["Present", "Absent", "Half-Day", "Leave"])
                
            col4, col5 = st.columns(2)
            with col4:
                clock_in = st.text_input("Clock-in Time (HH:MM format 24h)", value="08:00")
            with col5:
                clock_out = st.text_input("Clock-out Time (HH:MM format 24h)", value="17:00")
                
            submit_att = st.form_submit_button("Save Attendance Record")
            if submit_att:
                # Validate time formats
                hrs = HRCalculator.calculate_hours(clock_in, clock_out)
                if status == "Present" and hrs <= 0:
                    st.error("Invalid time range! Clock-out must be after clock-in.")
                else:
                    DataManager.log_attendance(selected_emp, str(att_date), clock_in, clock_out if status == "Present" else "", status)
                    st.success(f"Attendance recorded successfully! Calculated Hours: {hrs} hrs")
                    st.rerun()
                    
        st.markdown("---")
        st.subheader("Attendance Logs")
        conn = get_connection()
        logs_df = pd.read_sql("""
            SELECT a.id, e.name, a.date, a.clock_in, a.clock_out, a.status 
            FROM attendance a 
            JOIN employees e ON a.employee_id = e.id
            ORDER BY a.date DESC
        """, conn)
        conn.close()
        
        if not logs_df.empty:
            st.dataframe(logs_df, use_container_width=True)
        else:
            st.info("No attendance logs recorded yet.")

    # --- ADVANCE PAYMENTS ---
    elif menu == "Advance Payments":
        st.title("💵 Employee Advance Payments")
        
        emp_df = DataManager.get_employees()
        if emp_df.empty:
            st.warning("Please add employees first.")
            return
            
        with st.form("advance_form", clear_on_submit=True):
            st.subheader("Request Salary Advance")
            col1, col2 = st.columns(2)
            with col1:
                adv_emp = st.selectbox(
                    "Employee",
                    options=emp_df['id'].tolist(),
                    format_func=lambda x: emp_df.loc[emp_df['id'] == x, 'name'].values[0]
                )
                adv_amount = st.number_input("Advance Amount ($)", min_value=1.0, step=10.0, value=50.0)
            with col2:
                adv_reason = st.text_input("Reason for Advance")
                
            submit_adv = st.form_submit_button("Submit Advance Request")
            if submit_adv:
                DataManager.request_advance(adv_emp, adv_amount, adv_reason)
                st.success("Advance request submitted for approval!")
                st.rerun()
                
        st.markdown("---")
        st.subheader("All Advance Requests & History")
        conn = get_connection()
        adv_logs = pd.read_sql("""
            SELECT adv.id, e.name, adv.amount, adv.date, adv.reason, adv.status
            FROM advances adv
            JOIN employees e ON adv.employee_id = e.id
            ORDER BY adv.date DESC
        """, conn)
        conn.close()
        
        if not adv_logs.empty:
            for idx, row in adv_logs.iterrows():
                cols = st.columns([2, 2, 2, 2, 2])
                cols[0].write(f"**{row['name']}**")
                cols[1].write(f"${row['amount']:,.2f}")
                cols[2].write(f"{row['date']}")
                cols[3].write(f"{row['status']}")
                if row['status'] == 'Pending':
                    if cols[4].button("Approve", key=f"app_{row['id']}"):
                        DataManager.update_advance_status(row['id'], 'Approved')
                        st.rerun()
                else:
                    cols[4].write("-")
        else:
            st.info("No advance payment records found.")

    # --- WEEKLY PAYROLL ---
    elif menu == "Weekly Payroll":
        st.title("💰 Weekly Wages & Payroll Calculator")
        
        emp_df = DataManager.get_employees()
        if emp_df.empty:
            st.warning("No employees available for payroll calculation.")
            return
            
        st.subheader("Generate Weekly Paysheet")
        col1, col2 = st.columns(2)
        with col1:
            week_start = st.date_input("Week Start Date", value=date.today() - timedelta(days=6))
        with col2:
            week_end = st.date_input("Week End Date", value=date.today())
            
        if st.button("Calculate Weekly Payroll for All Employees"):
            conn = get_connection()
            
            # Fetch attendance between week_start and week_end
            att_q = pd.read_sql("""
                SELECT employee_id, clock_in, clock_out, status 
                FROM attendance 
                WHERE date BETWEEN ? AND ?
            """, conn, params=(str(week_start), str(week_end)))
            
            # Fetch approved advances that haven't been factored
            adv_q = pd.read_sql("""
                SELECT employee_id, SUM(amount) as total_adv 
                FROM advances 
                WHERE status = 'Approved' AND date BETWEEN ? AND ?
                GROUP BY employee_id
            """, conn, params=(str(week_start), str(week_end)))
            
            conn.close()
            
            payroll_records = []
            for idx, emp in emp_df.iterrows():
                e_id = emp['id']
                rate = emp['hourly_rate']
                
                # Calculate hours for this employee in timeframe
                emp_atts = att_q[att_q['employee_id'] == e_id]
                total_hrs = 0.0
                for _, att in emp_atts.iterrows():
                    total_hrs += HRCalculator.calculate_hours(att['clock_in'], att['clock_out'])
                    
                # Get advances
                emp_adv = adv_q[adv_q['employee_id'] == e_id]
                adv_val = float(emp_adv['total_adv'].values[0]) if not emp_adv.empty else 0.0
                
                computed = HRCalculator.compute_weekly_payroll(e_id, rate, total_hrs, adv_val)
                computed["name"] = emp['name']
                computed["role"] = emp['role']
                computed["hourly_rate"] = rate
                computed["advances"] = adv_val
                payroll_records.append(computed)
                
            if payroll_records:
                res_df = pd.DataFrame(payroll_records)
                st.success("Weekly Payroll Calculated Successfully!")
                
                st.dataframe(
                    res_df[["name", "role", "hourly_rate", "total_hours", "gross_pay", "advance_deductions", "net_pay"]],
                    use_container_width=True
                )
                
                # Option to save payroll
                if st.button("💾 Save Payroll Records to Database"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    for rec in payroll_records:
                        cursor.execute(
                            "INSERT INTO payroll (employee_id, week_start, week_end, total_hours, gross_pay, advance_deductions, net_pay, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'Generated')",
                            (rec['employee_id'], str(week_start), str(week_end), rec['total_hours'], rec['gross_pay'], rec['advance_deductions'], rec['net_pay'])
                        )
                    conn.commit()
                    conn.close()
                    st.success("Payroll saved successfully!")
            else:
                st.info(
                    "No hours logged for the selected period."
                )
                
        st.markdown("---")
        st.subheader("Saved Payroll History")
        conn = get_connection()
        saved_p = pd.read_sql("""
            SELECT p.id, e.name, p.week_start, p.week_end, p.total_hours, p.gross_pay, p.advance_deductions, p.net_pay, p.status
            FROM payroll p
            JOIN employees e ON p.employee_id = e.id
            ORDER BY p.week_start DESC
        """, conn)
        conn.close()
        
        if not saved_p.empty:
            st.dataframe(saved_p, use_container_width=True)
        else:
            st.info("No saved payroll records.")

if __name__ == '__main__':
    main()