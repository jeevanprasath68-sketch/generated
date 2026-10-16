import pytest
import os
import sqlite3
from app import GameEngine, _init_db, reset_database, DB_NAME

@pytest.fixture(autouse=True)
def setup_test_db():
    """Setup and teardown a clean test database for each test."""
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    _init_db()
    yield
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

def test_ai_choice_generation():
    """Test that AI choice is one of the valid options."""
    choice = GameEngine.get_ai_choice()
    assert choice in GameEngine.CHOICES

def test_determine_winner_ties():
    """Test tie scenarios."""
    assert GameEngine.determine_winner("Rock", "Rock") == "Tie"
    assert GameEngine.determine_winner("Paper", "Paper") == "Tie"
    assert GameEngine.determine_winner("Scissors", "Scissors") == "Tie"

def test_determine_winner_player_wins():
    """Test all player winning scenarios."""
    assert GameEngine.determine_winner("Rock", "Scissors") == "Player"
    assert GameEngine.determine_winner("Paper", "Rock") == "Player"
    assert GameEngine.determine_winner("Scissors", "Paper") == "Player"

def test_determine_winner_ai_wins():
    """Test all AI winning scenarios."""
    assert GameEngine.determine_winner("Scissors", "Rock") == "AI"
    assert GameEngine.determine_winner("Rock", "Paper") == "AI"
    assert GameEngine.determine_winner("Paper", "Scissors") == "AI"

def test_invalid_choice_raises_error():
    """Test invalid inputs throw ValueError."""
    with pytest.raises(ValueError):
        GameEngine.determine_winner("Lizard", "Rock")

def test_database_persistence_and_stats():
    """Test saving matches and calculating stats correctly."""
    # Initially empty
    history = GameEngine.get_match_history()
    stats = GameEngine.calculate_stats(history)
    assert stats["Total"] == 0
    
    # Save some test matches
    GameEngine.save_match("Rock", "Scissors", "Player")
    GameEngine.save_match("Paper", "Scissors", "AI")
    GameEngine.save_match("Rock", "Rock", "Tie")
    
    history = GameEngine.get_match_history()
    assert len(history) == 3
    
    stats = GameEngine.calculate_stats(history)
    assert stats["Player"] == 1
    assert stats["AI"] == 1
    assert stats["Tie"] == 1
    assert stats["Total"] == 3

def test_reset_database():
    """Test database reset wipes all records."""
    GameEngine.save_match("Rock", "Scissors", "Player")
    assert len(GameEngine.get_match_history()) == 1
    
    reset_database()
    assert len(GameEngine.get_match_history()) == 0