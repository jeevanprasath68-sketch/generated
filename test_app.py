"""
Exhaustive pytest suite for Galaxy Space Shooter backend components.
"""

import os
import pytest
from app import LeaderboardDB, DifficultyManager, DB_PATH

@pytest.fixture(autouse=True)
def clean_test_db():
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except PermissionError:
            pass
    yield
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except PermissionError:
            pass


def test_leaderboard_initialization():
    db = LeaderboardDB(db_path=DB_PATH)
    stats = db.get_stats()
    assert stats["total_games"] == 0
    assert stats["high_score"] == 0
    assert stats["avg_score"] == 0


def test_add_score_and_retrieve():
    db = LeaderboardDB(db_path=DB_PATH)
    db.add_score("ViperOne", 1500, "Standard")
    db.add_score("Maverick", 3400, "Pro")

    top = db.get_top_scores(limit=5)
    assert len(top) == 2
    assert top[0][0] == "Maverick"
    assert top[0][1] == 3400
    assert top[0][2] == "Pro"

    stats = db.get_stats()
    assert stats["total_games"] == 2
    assert stats["high_score"] == 3400
    assert stats["avg_score"] == 2450


def test_difficulty_filtering():
    db = LeaderboardDB(db_path=DB_PATH)
    db.add_score("PilotA", 1000, "Casual")
    db.add_score("PilotB", 2500, "Impossible")

    casual_scores = db.get_top_scores(difficulty="Casual")
    assert len(casual_scores) == 1
    assert casual_scores[0][0] == "PilotA"

    impossible_scores = db.get_top_scores(difficulty="Impossible")
    assert len(impossible_scores) == 1
    assert impossible_scores[0][0] == "PilotB"


def test_anonymous_and_empty_names():
    db = LeaderboardDB(db_path=DB_PATH)
    db.add_score("   ", 800, "Standard")
    top = db.get_top_scores()
    assert len(top) == 1
    assert top[0][0] == "Anonymous"
    assert top[0][1] == 800


def test_difficulty_manager_bounds():
    casual = DifficultyManager.get_config("Casual")
    assert casual["player_lives"] == 5
    assert casual["score_multiplier"] == 1.0

    impossible = DifficultyManager.get_config("Impossible")
    assert impossible["player_lives"] == 1
    assert impossible["score_multiplier"] == 3.0

    unknown = DifficultyManager.get_config("NonExistent")
    assert unknown["player_lives"] == 3


def test_database_reset():
    db = LeaderboardDB(db_path=DB_PATH)
    db.add_score("Ace", 5000, "Pro")
    assert db.get_stats()["total_games"] == 1

    db.reset_database()
    assert db.get_stats()["total_games"] == 0
    assert db.get_stats()["high_score"] == 0