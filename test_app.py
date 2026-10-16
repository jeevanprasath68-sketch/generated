import pytest
import os
import sqlite3
from app import PingPongEngine, DB_NAME, _init_db

@pytest.fixture(autouse=True)
def setup_database():
    """Setup and teardown a clean test database before and after each test."""
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    _init_db()
    yield
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

def test_init_db_creates_table():
    """Test that database initialization creates the matches table with required columns."""
    _init_db()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(matches)")
    columns = [col[1] for col in cursor.fetchall()]
    conn.close()

    assert "id" in columns
    assert "player_name" in columns
    assert "player_score" in columns
    assert "ai_score" in columns
    assert "difficulty" in columns
    assert "timestamp" in columns

def test_save_match_happy_path():
    """Test successfully saving a match record to the database."""
    success = PingPongEngine.save_match("TestUser", 5, 3, "Medium")
    assert success is True

    leaderboard = PingPongEngine.get_leaderboard()
    assert len(leaderboard) == 1
    assert leaderboard[0]["player_name"] == "TestUser"
    assert leaderboard[0]["player_score"] == 5
    assert leaderboard[0]["ai_score"] == 3
    assert leaderboard[0]["difficulty"] == "Medium"

def test_get_leaderboard_ordering():
    """Test leaderboard returns matches ordered by player score descending."""
    PingPongEngine.save_match("Alice", 2, 5, "Hard")
    PingPongEngine.save_match(
        "Bob", 7, 1, "Expert"
    )  # Higher score
    PingPongEngine.save_match("Charlie", 5, 5, "Easy")

    leaderboard = PingPongEngine.get_leaderboard()
    assert len(leaderboard) == 3
    assert leaderboard[0]["player_name"] == "Bob"
    assert leaderboard[0]["player_score"] == 7
    assert leaderboard[1]["player_name"] == "Charlie"
    assert leaderboard[2]["player_name"] == "Alice"

def test_reset_database():
    """Test wiping all records from the database."""
    PingPongEngine.save_match("TestUser", 5, 2, "Easy")
    assert len(PingPongEngine.get_leaderboard()) == 1

    reset_success = PingPongEngine.reset_database()
    assert reset_success is True
    assert len(PingPongEngine.get_leaderboard()) == 0

def test_database_schema_self_healing():
    """Test that database schema automatically handles missing tables/columns gracefully."""
    # Corrupt or drop table
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE matches")
    conn.commit()
    conn.close()

    # Calling get_leaderboard should trigger _init_db and self-heal without raising exceptions
    leaderboard = PingPongEngine.get_leaderboard()
    assert isinstance(leaderboard, list)
    assert len(leaderboard) == 0