# Generated Application

**Requirement:** Build a functional web application called **FocusFlow — Smart Student Study Planner** using Python and Streamlit.

Features:
- Create, edit, and delete subjects, assignments, exams, and study tasks.
- Record deadlines, priorities, estimated study durations, and completion status.
- Generate a daily study schedule based on task priority, deadlines, and available study hours.
- Detect overdue tasks and conflicting schedule entries.
- Allow users to mark tasks complete and automatically update progress statistics.
- Display upcoming deadlines, workload charts, and subject-wise completion rates.
- Store all data persistently using SQLite.
- Include a calendar-style schedule, task filters, and a modern dark-themed dashboard.
- Allow users to export their tasks and schedules as CSV.

Technical requirements:
- Use Python, Streamlit, SQLite, Pandas, and Plotly.
- Keep scheduling logic separate from the UI.
- Ensure scheduled durations do not exceed the user's available hours.
- Handle missing deadlines, invalid durations, and empty task lists.
- Make the schedule deterministic and explain how tasks are prioritised.

Create automated tests for task management, prioritisation, scheduling constraints, progress calculations, and persistence.

Generate the complete source code, run real tests, inspect failures, attempt up to two repairs, and rerun tests after repairs. Present an honest final report containing test results, known limitations, and launch instructions.

Build a working application rather than a mockup.

**Status:** VERIFIED

## Run Locally
```bash
streamlit run app.py
```
