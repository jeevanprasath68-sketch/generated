import os
import pytest
from datetime import date, timedelta
from app import SQLiteDatabase, StudyPlannerEngine

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_focusflow.db"
    db = SQLiteDatabase(db_path=str(db_file))
    return db

def test_database_creation_and_insertion(temp_db):
    sub_id = temp_db.execute("INSERT INTO subjects (name, color) VALUES (?, ?)", ("Mathematics", "#ff0000"))
    assert sub_id == 1

    task_id = temp_db.execute(
        "INSERT INTO tasks (title, subject_id, task_type, deadline, priority, estimated_hours, completed) VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("Calculus Homework", sub_id, "Assignment", "2025-12-31", "High", 3.5, 0)
    )
    assert task_id == 1

    tasks = temp_db.fetch_all("SELECT * FROM tasks")
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Calculus Homework"
    assert tasks[0]["completed"] == 0

def test_priority_score_calculation():
    today = date(2025, 1, 1)
    # Past deadline (overdue)
    score_overdue = StudyPlannerEngine.calculate_priority_score("High", "2024-12-30", current_date=today)
    # Future deadline
    score_future = StudyPlannerEngine.calculate_priority_score("High", "2025-01-10", current_date=today)
    # No deadline
    score_none = StudyPlannerEngine.calculate_priority_score("Medium", None, current_date=today)

    assert score_overdue > score_future
    assert score_none > 0

def test_schedule_generation_and_constraints():
    today_str = date.today().strftime("%Y-%m-%d")
    tasks = [
        {"id": 1, "title": "Task A", "subject": "Math", "priority": "High", "deadline": today_str, "estimated_hours": 3.0, "completed": 0},
        {"id": 2, "title": "Task B", "subject": "Physics", "priority": "Low", "deadline": today_str, "estimated_hours": 3.0, "completed": 0},
    ]

    # Available 4 hours per day. Task A (High) should take 3 hrs today, Task B takes 1 hr today and 2 hrs tomorrow.
    schedule = StudyPlannerEngine.generate_schedule(tasks, available_hours_per_day=4.0)
    
    assert len(schedule) == 3
    assert schedule[0]["title"] == "Task A"
    assert schedule[0]["allocated_hours"] == 3.0
    assert schedule[1]["allocated_hours"] == 1.0
    assert schedule[2]["title"] == "Task B"
    assert schedule[2]["allocated_hours"] == 2.0

def test_schedule_invalid_available_hours():
    tasks = [{"id": 1, "title": "Task A", "priority": "High", "estimated_hours": 2.0, "completed": 0}]
    with pytest.raises(ValueError, match="Available study hours per day must be greater than zero."):
        StudyPlannerEngine.generate_schedule(tasks, available_hours_per_day=0.0)

def test_conflict_detection():
    today_str = date.today().strftime("%Y-%m-%d")
    tasks = [
        {"id": 1, "title": "Massive Task", "subject": "History", "priority": "High", "deadline": today_str, "estimated_hours": 10.0, "completed": 0}
    ]
    # Available 4 hours per day. Massive task requires 10 hours on today_str.
    conflicts = StudyPlannerEngine.detect_conflicts(tasks, available_hours_per_day=4.0)
    assert len(conflicts) > 0
    assert conflicts[0]["excess"] == 6.0

def test_progress_statistics():
    tasks = [
        {"id": 1, "title": "T1", "subject": "Math", "priority": "High", "deadline": "2020-01-01", "completed": 1}, # Completed overdue
        {"id": 2, "title": "T2", "subject": "Math", "priority": "High", "deadline": "2020-01-01", "completed": 0}, # Overdue
        {"id": 3, "title": "T3", "subject": "Science", "priority": "Low", "deadline": "2099-01-01", "completed": 0}, # Active future
    ]
    stats = StudyPlannerEngine.calculate_progress_stats(tasks)
    assert stats["total_tasks"] == 3
    assert stats["completed_tasks"] == 1
    assert stats["completion_rate"] == 33.3
    assert stats["overdue_tasks"] == 1
    assert "Math" in stats["subject_progress"]
    assert stats["subject_progress"]["Math"]["rate"] == 50.0