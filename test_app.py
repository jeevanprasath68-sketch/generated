import pytest
import os
from app import GameConfig, LeaderboardDB

@pytest.fixture

def temp_db(tmp_path):
    db_file = tmp_path / "test_leaderboard.db"
    db = LeaderboardDB(db_path=str(db_file))
    return db

def test_game_config_difficulties():
    casual = GameConfig.get_settings("Casual")
    assert casual["grid_size"] == 3
    assert casual["time_limit"] == 120
    assert casual["score_multiplier"] == 1.0

    pro = GameConfig.get_settings("Pro")
    assert pro["grid_size"] == 5
    assert pro["score_multiplier"] == 2.2

    # Fallback default test
    unknown = GameConfig.get_settings("NonExistent")
    assert unknown["grid_size"] == 4

def test_leaderboard_init_and_add(temp_db):
    success = temp_db.add_score("CyberZero", 1500, "Standard")
    assert success is True

    top = temp_db.get_top_scores(limit=5)
    assert len(top) == 1
    assert top[0]["player_name"] == "CyberZero"
    assert top[0]["score"] == 1500
    assert top[0]["difficulty"] == "Standard"

def test_leaderboard_sorting_and_limit(temp_db):
    temp_db.add_score("PlayerA", 500, "Casual")
    temp_db.add_score("PlayerB", 2500, "Pro")
    temp_db.add_score("PlayerC", 1200, "Standard")

    top = temp_db.get_top_scores(limit=2)
    assert len(top) == 2
    assert top[0]["score"] == 2500
    assert top[0]["player_name"] == "PlayerB"
    assert top[1]["score"] == 1200

def test_leaderboard_stats(temp_db):
    temp_db.add_score("Alpha", 1000, "Casual")
    temp_db.add_score("Beta", 3000, "Pro")

    stats = temp_db.get_stats()
    assert stats["total_games"] == 2
    assert stats["high_score"] == 3000
    assert stats["avg_score"] == 2000.0

def test_invalid_score_submission(temp_db):
    success_empty = temp_db.add_score("", 500, "Casual")
    assert success_empty is False

    success_negative = temp_db.add_score("ValidUser", -100, "Casual")
    assert success_negative is False

def test_reset_leaderboard(temp_db):
    temp_db.add_score("TestUser", 800, "Standard")
    assert temp_db.get_stats()["total_games"] == 1

    temp_db.reset_leaderboard()
    assert temp_db.get_stats()["total_games"] == 0
    assert len(temp_db.get_top_scores()) == 0