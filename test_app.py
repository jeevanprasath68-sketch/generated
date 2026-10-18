"""
Exhaustive pytest test suite for Cyberpunk Neon Snake backend.
"""

import os
import pytest
from app import GameConfig, LeaderboardDB

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_snake.db"
    db = LeaderboardDB(str(db_file))
    return db

def test_game_config_difficulties():
    """Test difficulty configurations and multipliers."""
    casual = GameConfig.get_difficulty("Casual")
    assert casual["speed"] == 1.0
    assert casual["multiplier"] == 1.0
    assert casual["wall_collision"] is False

    impossible = GameConfig.get_difficulty("Impossible")
    assert impossible["speed"] == 2.2
    assert impossible["multiplier"] == 4.0
    assert impossible["wall_collision"] is True

    # Test fallback for invalid difficulty
    unknown = GameConfig.get_difficulty("NonExistent")
    assert unknown["multiplier"] == 1.5

def test_leaderboard_init_and_add(temp_db):
    """Test score insertion and retrieval."""
    temp_db.add_score("CyberKnight", 1250, "Standard")
    temp_db.add_score("NeonQueen", 2500, "Pro")

    scores = temp_db.get_top_scores(10)
    assert len(scores) == 2
    assert scores[0]["player_name"] == "NeonQueen"
    assert scores[0]["score"] == 2500
    assert scores[1]["player_name"] == "CyberKnight"
    assert scores[1]["score"] == 1250

def test_leaderboard_stats(temp_db):
    """Test database statistics calculations."""
    temp_db.add_score("Player1", 100, "Casual")
    temp_db.add_score("Player2", 300, "Standard")

    stats = temp_db.get_stats()
    assert stats["total_games"] == 2
    assert stats["max_score"] == 300
    assert stats["avg_score"] == 200

def test_empty_leaderboard_stats(temp_db):
    """Test stats when database has no records."""
    stats = temp_db.get_stats()
    assert stats["total_games"] == 0
    assert stats["max_score"] == 0
    assert stats["avg_score"] == 0

def test_anonymous_and_long_name_sanitization(temp_db):
    """Test edge cases for player names (empty strings, truncation)."""
    temp_db.add_score("   ", 500, "Casual")
    long_name = "A" * 50
    temp_db.add_score(long_name, 800, "Pro")

    scores = temp_db.get_top_scores(10)
    assert len(scores) == 2
    assert scores[1]["player_name"] == "Anonymous Cyber-Runner"
    assert len(scores[0]["player_name"]) <= 30

def test_database_reset(temp_db):
    """Test wiping the database table."""
    temp_db.add_score("TestUser", 999, "Standard")
    assert len(temp_db.get_top_scores()) == 1

    temp_db.reset_database()
    assert len(temp_db.get_top_scores()) == 0