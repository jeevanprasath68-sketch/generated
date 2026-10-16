import pytest
import sqlite3
import os
from app import GameEngine, DB_NAME, _init_db

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Setup clean test database before each test
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    _init_db()
    yield
    # Teardown after test
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

def test_init_db_creates_table():
    """Test that database and match_history table are correctly initialized."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='match_history';")
    table = cursor.fetchone()
    conn.close()
    assert table is not None
    assert table[0] == 'match_history'

def test_record_match_player_wins():
    """Test recording a match where the player wins."""
    result = GameEngine.record_match(player_score=5, ai_score=3, difficulty="Medium")
    assert result["winner"] == "Player"
    assert result["player_score"] == 5
    assert result["ai_score"] == 3
    
    history = GameEngine.get_leaderboard()
    assert len(history) == 1
    assert history[0]["winner"] == "Player"
    assert history[0]["difficulty"] == "Medium"

def test_record_match_ai_wins():
    """Test recording a match where the AI wins."""
    result = GameEngine.record_match(player_score=1, ai_score=5, difficulty="Hard")
    assert result["winner"] == "AI"
    
    history = GameEngine.get_leaderboard()
    assert len(history) == 1
    assert history[0]["winner"] == "AI"

def test_calculate_ai_speed_valid():
    """Test AI speed calculation returns correct values for valid difficulties."""
    assert GameEngine.calculate_ai_speed("Easy") == 0.05
    assert GameEngine.calculate_ai_speed("Medium") == 0.08
    assert GameEngine.calculate_ai_speed("Hard") == 0.12
    assert GameEngine.calculate_ai_speed("Insane") == 0.18

def test_calculate_ai_speed_invalid():
    """Test that invalid difficulty raises ValueError."""
    with pytest.raises(ValueError):
        GameEngine.calculate_ai_speed("Impossible")

def test_clear_database():
    """Test clearing database wipes all match records."""
    GameEngine.record_match(player_score=5, ai_score=0, difficulty="Easy")
    GameEngine.record_match(player_score=4, ai_score=5, difficulty="Insane")
    
    assert len(GameEngine.get_leaderboard()) == 2
    
    GameEngine.clear_database()
    assert len(GameEngine.get_leaderboard()) == 0