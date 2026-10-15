import os
import pytest
from app import GameScoreManager

@pytest.fixture
def score_manager(tmp_path):
    temp_file = tmp_path / "test_scores.json"
    manager = GameScoreManager(storage_file=str(temp_file))
    return manager

def test_load_empty_scores(score_manager):
    """Test that loading scores from a non-existent file returns an empty list."""
    scores = score_manager.load_scores()
    assert scores == []

def test_save_and_load_scores(score_manager):
    """Test saving a score correctly persists and returns sorted scores."""
    score_manager.save_score("Alice", 120)
    score_manager.save_score("Bob", 250)
    score_manager.save_score("Charlie", 80)

    scores = score_manager.load_scores()
    assert len(scores) == 3
    # Check sorting (descending by score)
    assert scores[0]["player_name"] == "Bob"
    assert scores[0]["score"] == 250
    assert scores[1]["player_name"] == "Alice"
    assert scores[1]["score"] == 120
    assert scores[2]["player_name"] == "Charlie"
    assert scores[2]["score"] == 80

def test_get_high_score(score_manager):
    """Test high score retrieval returns the maximum score or 0 when empty."""
    assert score_manager.get_high_score() == 0

    score_manager.save_score("Player1", 50)
    score_manager.save_score(
        "Player2", 300
    )
    score_manager.save_score("Player3", 150)

    assert score_manager.get_high_score() == 300

def test_max_scores_limit(score_manager):
    """Test that leaderboard truncates to top 10 scores."""
    for i in range(15):
        score_manager.save_score(f"Player{i}", i * 10)

    scores = score_manager.load_scores()
    assert len(scores) == 10
    # Highest score should be 140
    assert score_manager.get_high_score() == 140