import os
import sqlite3
from datetime import date, datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ======================================================================
# DATABASE LAYER
# ======================================================================
class SQLiteDatabase:
    def __init__(self, db_path="focusflow.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subjects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    color TEXT NOT NULL
                )
            """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    subject_id INTEGER,
                    task_type TEXT NOT NULL,
                    deadline TEXT,
                    priority TEXT NOT NULL,
                    estimated_hours REAL NOT NULL,
                    completed INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE
                )
            """
            )
            conn.commit()

    def execute(self, query, params=()):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid

    def fetch_all(self, query, params=()):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]


# ======================================================================
# DOMAIN LOGIC & ENGINE
# ======================================================================
class StudyPlannerEngine:
    PRIORITY_WEIGHTS = {"High": 3.0, "Medium": 2.0, "Low": 1.0}

    @staticmethod
    def calculate_priority_score(
        priority: str,
        deadline_str: str | None,
        current_date: date | None = None,
    ) -> float:
        if current_date is None:
            current_date = date.today()

        base_weight = StudyPlannerEngine.PRIORITY_WEIGHTS.get(
            priority, 1.0
        )

        if not deadline_str:
            # No deadline tasks get a baseline urgency penalty
            return base_weight * 10.0

        try:
            dl = datetime.strptime(deadline_str, "%Y-%m-%d").date()
            days_left = (dl - current_date).days
        except (ValueError, TypeError):
            return base_weight * 10.0

        if days_left < 0:
            # Overdue tasks get extreme priority
            urgency_factor = 100.0 + abs(days_left) * 10
        elif days_left == 0:
            urgency_factor = 90.0
        else:
            urgency_factor = max(1.0, 50.0 / (days_left + 1))

        return round(base_weight * urgency_factor, 2)

    @staticmethod
    def generate_schedule(tasks: list[dict], available_hours_per_day: float) -> list[dict]:
        if available_hours_per_day <= 0:
            raise ValueError("Available study hours per day must be greater than zero.")

        # Filter out completed tasks
        active_tasks = [t for t in tasks if not t.get("completed", 0)]

        # Compute priority scores
        today = date.today()
        scored_tasks = []
        for t in active_tasks:
            score = StudyPlannerEngine.calculate_priority_score(
                t.get("priority", "Medium"), t.get("deadline"), today
            )
            t_copy = dict(t)
            t_copy["score"] = score
            scored_tasks.append(t_copy)

        # Sort descending by score, then ascending by deadline
        def sort_key(task):
            dl = task.get("deadline") or "9999-12-31"
            return (-task["score"], dl)

        scored_tasks.sort(key=sort_key)

        schedule = []
        current_day_offset = 0
        remaining_hours_today = available_hours_per_day

        for task in scored_tasks:
            est_hours = float(task.get("estimated_hours", 0))
            if est_hours <= 0:
                continue

            # Allocate task across days if it exceeds remaining hours today
            task_remaining = est_hours
            while task_remaining > 0:
                allocated = min(task_remaining, remaining_hours_today)
                scheduled_date = today + timedelta(days=current_day_offset)

                schedule.append({
                    "task_id": task.get("id"),
                    "title": task.get("title"),
                    "subject": task.get("subject", "General"),
                    "priority": task.get("priority"),
                    "deadline": task.get("deadline"),
                    "scheduled_date": scheduled_date.strftime("%Y-%m-%d"),
                    "allocated_hours": round(allocated, 2),
                })

                task_remaining -= allocated
                remaining_hours_today -= allocated

                if remaining_hours_today <= 1e-5:
                    current_day_offset += 1
                    remaining_hours_today = available_hours_per_day

        return schedule

    @staticmethod
    def detect_conflicts(tasks: list[dict], available_hours_per_day: float) -> list[dict]:
        conflicts = []
        for t in tasks:
            if not t.get("completed", 0):
                est = float(t.get("estimated_hours", 0))
                if est > available_hours_per_day:
                    conflicts.append({
                        "date": t.get("deadline") or date.today().strftime("%Y-%m-%d"),
                        "allocated_hours": round(est, 2),
                        "limit_hours": available_hours_per_day,
                        "excess": round(est - available_hours_per_day, 2)
                    })
        return conflicts

    @staticmethod
    def calculate_progress_stats(tasks: list[dict]) -> dict:
        total = len(tasks)
        if total == 0:
            return {
                "total_tasks": 0,
                "completed_tasks": 0,
                "completion_rate": 0.0,
                "overdue_tasks": 0,
                "subject_progress": {},
            }

        completed = sum(1 for t in tasks if t.get("completed", 0) == 1)
        today = date.today().strftime("%Y-%m-%d")

        overdue = 0
        for t in tasks:
            dl = t.get("deadline")
            if not t.get("completed", 0) and dl and dl < today:
                overdue += 1

        subject_progress = {}
        # Group by subject
        subjects = set(t.get("subject", "General") for t in tasks)
        for subj in subjects:
            subj_tasks = [t for t in tasks if t.get("subject", "General") == subj]
            s_total = len(subj_tasks)
            s_completed = sum(1 for t in subj_tasks if t.get("completed", 0) == 1)
            rate = (s_completed / s_total * 100) if s_total > 0 else 0.0
            subject_progress[subj] = {
                "total": s_total,
                "completed": s_completed,
                "rate": round(rate, 1),
            }

        return {
            "total_tasks": total,
            "completed_tasks": completed,
            "completion_rate": round((completed / total) * 100, 1),
            "overdue_tasks": overdue,
            "subject_progress": subject_progress,
        }


# ======================================================================
# STREAMLIT UI APPLICATION
# ======================================================================
def main():
    st.set_page_config(
        page_title="FocusFlow Study Planner",
        page_icon="⏳",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom Dark Theme CSS
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #0e1117;
            color: #c9d1d9;
        }
        .metric-card {
            background-color: #161b22;
            border: 1px solid #30363d;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .stMetricValue {
            color: #58a6ff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    db = SQLiteDatabase()

    st.title("⏳ FocusFlow — Smart Student Study Planner")
    st.markdown("Organize your academic life, optimize your study schedule, and conquer deadlines effortlessly.")

    # Sidebar Navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        [
            "Dashboard & Analytics",
            "Task Manager",
            "Subject Manager",
            "Smart Schedule",
            "Data Export",
        ],
    )

    # Fetch core data
    subjects_raw = db.fetch_all(
        "SELECT s.id, s.name, s.color FROM subjects s ORDER BY s.name"
    )
    subjects_dict = {s["name"]: s["id"] for s in subjects_raw}

    tasks_raw = db.fetch_all(
        """
        SELECT t.id, t.title, t.subject_id, s.name as subject, t.task_type, 
               t.deadline, t.priority, t.estimated_hours, t.completed
        FROM tasks t
        LEFT JOIN subjects s ON t.subject_id = s.id
        ORDER BY t.deadline ASC
    """
    )

    # ------------------------------------------------------------------
    # 1. DASHBOARD & ANALYTICS
    # ------------------------------------------------------------------
    if page == "Dashboard & Analytics":
        st.header("📊 Performance Dashboard")

        stats = StudyPlannerEngine.calculate_progress_stats(tasks_raw)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Tasks", stats["total_tasks"])
        with col2:
            st.metric("Completed", stats["completed_tasks"])
        with col3:
            st.metric("Completion Rate", f"{stats['completion_rate']}%")
        with col4:
            st.metric("Overdue Tasks", stats["overdue_tasks"], delta=None, delta_color="inverse")

        st.markdown("---")

        # Workload & Subject Charts
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("Subject Completion Rates")
            if stats["subject_progress"]:
                subj_df = pd.DataFrame([
                    {"Subject": k, "Completion Rate (%)": v["rate"]}
                    for k, v in stats["subject_progress"].items()
                ])
                fig = px.bar(
                    subj_df,
                    x="Subject",
                    y="Completion Rate (%)",
                    color="Subject",
                    template="plotly_dark",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No subjects or tasks available for charts.")

        with col_b:
            st.subheader("Task Distribution by Type")
            if tasks_raw:
                task_df = pd.DataFrame(tasks_raw)
                fig_pie = px.pie(
                    task_df,
                    names="task_type",
                    values="estimated_hours",
                    template="plotly_dark",
                    hole=0.4,
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("No tasks available.")

        st.subheader("Upcoming Deadlines")
        upcoming = [t for t in tasks_raw if not t["completed"]]
        if upcoming:
            up_df = pd.DataFrame(upcoming)[["title", "subject", "task_type", "deadline", "priority", "estimated_hours"]]
            st.dataframe(up_df, use_container_width=True)
        else:
            st.success("All tasks completed! Amazing job!")

    # ------------------------------------------------------------------
    # 2. TASK MANAGER
    # ------------------------------------------------------------------
    elif page == "Task Manager":
        st.header("📝 Task & Assignment Manager")

        with st.expander("➕ Add New Task / Assignment", expanded=True):
            with st.form("add_task_form"):
                title = st.text_input("Task Title")
                sub_name = st.selectbox(
                    "Subject", list(subjects_dict.keys()) if subjects_dict else [""]
                )
                task_type = st.selectbox("Type", ["Assignment", "Exam", "Study Task", "Project"])
                deadline = st.date_input("Deadline", value=date.today() + timedelta(days=3))
                priority = st.selectbox("Priority", ["High", "Medium", "Low"])
                est_hours = st.number_input("Estimated Hours", min_value=0.5, max_value=40.0, value=2.0, step=0.5)

                submitted = st.form_submit_button("Create Task")
                if submitted:
                    if not title:
                        st.error("Task title cannot be empty.")
                    elif not sub_name:
                        st.error("Please create a subject first.")
                    else:
                        sub_id = subjects_dict[sub_name]
                        db.execute(
                            "INSERT INTO tasks (title, subject_id, task_type, deadline, priority, estimated_hours, completed) VALUES (?, ?, ?, ?, ?, ?, 0)",
                            (title, sub_id, task_type, deadline.strftime("%Y-%m-%d"), priority, est_hours),
                        )
                        st.success(f"Task '{title}' created successfully!")
                        st.rerun()

        st.markdown("---")
        st.subheader("Existing Tasks")
        if tasks_raw:
            # Filters
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                filter_status = st.selectbox("Filter Status", ["All", "Active", "Completed"])
            with f_col2:
                filter_priority = st.selectbox("Filter Priority", ["All", "High", "Medium", "Low"])

            filtered_tasks = tasks_raw
            if filter_status == "Active":
                filtered_tasks = [t for t in filtered_tasks if not t["completed"]]
            elif filter_status == "Completed":
                filtered_tasks = [t for t in filtered_tasks if t["completed"]]

            if filter_priority != "All":
                filtered_tasks = [t for t in filtered_tasks if t["priority"] == filter_priority]

            for t in filtered_tasks:
                cols = st.columns([0.5, 3, 1.5, 1, 1, 1, 1])
                with cols[0]:
                    is_comp = st.checkbox("", value=bool(t["completed"]), key=f"chk_{t['id']}")
                    if is_comp != bool(t["completed"]):
                        db.execute("UPDATE tasks SET completed = ? WHERE id = ?", (int(is_comp), t["id"]))
                        st.rerun()
                with cols[1]:
                    st.markdown(f"**{t['title']}**")
                    st.caption(f"{t['subject']} | {t['task_type']}")
                with cols[2]:
                    st.text(f"Due: {t['deadline'] or 'None'}")
                with cols[3]:
                    st.text(f"{t['priority']}")
                with cols[4]:
                    st.text(f"{t['estimated_hours']} hrs")
                with cols[5]:
                    # Edit modal trigger substitute
                    if st.button("🗑️ Delete", key=f"del_{t['id']}"):
                        db.execute("DELETE FROM tasks WHERE id = ?", (t['id'],))
                        st.rerun()
        else:
            st.info("No tasks found. Create your first task above!")

    # ------------------------------------------------------------------
    # 3. SUBJECT MANAGER
    # ------------------------------------------------------------------
    elif page == "Subject Manager":
        st.header("📚 Subject Manager")

        with st.form("add_subject_form"):
            sub_name = st.text_input("Subject Name")
            color = st.color_picker("Subject Theme Color", "#58a6ff")
            submitted = st.form_submit_button("Add Subject")
            if submitted:
                if not sub_name:
                    st.error("Subject name cannot be empty.")
                else:
                    try:
                        db.execute("INSERT INTO subjects (name, color) VALUES (?, ?)", (sub_name, color))
                        st.success(f"Subject '{sub_name}' added!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Subject already exists.")

        st.markdown("---")
        st.subheader("Current Subjects")
        if subjects_raw:
            for s in subjects_raw:
                cols = st.columns([3, 1, 1])
                with cols[0]:
                    st.markdown(f"### <span style='color:{s['color']}'>■</span> {s['name']}", unsafe_allow_html=True)
                with cols[2]:
                    if st.button("Delete", key=f"del_sub_{s['id']}"):
                        db.execute("DELETE FROM subjects WHERE id = ?", (s['id'],))
                        st.rerun()
        else:
            st.info("No subjects created yet.")

    # ------------------------------------------------------------------
    # 4. SMART SCHEDULE
    # ------------------------------------------------------------------
    elif page == "Smart Schedule":
        st.header("📅 Smart Study Schedule")
        st.markdown("Generated deterministically based on task priorities, urgency, and available daily study hours.")

        available_hours = st.slider("Available Study Hours Per Day", min_value=1.0, max_value=12.0, value=4.0, step=0.5)

        try:
            schedule = StudyPlannerEngine.generate_schedule(tasks_raw, available_hours)
            conflicts = StudyPlannerEngine.detect_conflicts(tasks_raw, available_hours)

            if conflicts:
                st.warning("⚠️ Schedule Overload / Conflict Detected!")
                for c in conflicts:
                    st.markdown(f"> **Date {c['date']}**: Allocated **{c['allocated_hours']} hrs** exceeds your daily limit of **{c['limit_hours']} hrs** by **{c['excess']} hrs**.")

            if schedule:
                sched_df = pd.DataFrame(schedule)
                st.dataframe(sched_df, use_container_width=True)

                # Gantt or Timeline Chart
                st.subheader("Schedule Timeline")
                fig = px.timeline(
                    sched_df,
                    x_start="scheduled_date",
                    x_end="scheduled_date",
                    y="title",
                    color="subject",
                    template="plotly_dark",
                    title="Daily Allocation Overview"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("No active tasks to schedule! Enjoy your free time.")

        except ValueError as e:
            st.error(str(e))

    # ------------------------------------------------------------------
    # 5. DATA EXPORT
    # ------------------------------------------------------------------
    elif page == "Data Export":
        st.header("💾 Export Study Data")
        st.markdown("Download your tasks and schedule as CSV files for offline use or backup.")

        if tasks_raw:
            tasks_df = pd.DataFrame(tasks_raw)
            csv_tasks = tasks_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="Download Tasks CSV",
                data=csv_tasks,
                file_name="focusflow_tasks.csv",
                mime="text/csv",
            )

        try:
            sched_data = StudyPlannerEngine.generate_schedule(tasks_raw, 4.0)
            if sched_data:
                sched_df = pd.DataFrame(sched_data)
                csv_sched = sched_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Download Generated Schedule CSV",
                    data=csv_sched,
                    file_name="focusflow_schedule.csv",
                    mime="text/csv",
                )
        except Exception:
            pass


if __name__ == "__main__":
    main()