import pytest
from app import GameEngine

def test_game_initialization():
    engine = GameEngine(width=800, height=500)
    state = engine.get_state()
    assert state["player_score"] == 0
    assert state["ai_score"] == 0
    assert not state["game_over"]
    assert state["width"] == 800
    assert state["height"] == 500

def test_player_movement():
    engine = GameEngine()
    initial_y = engine.player_y
    
    # Move DOWN
    engine.update("DOWN", 0.5)
    assert engine.player_y > initial_y

    # Move UP
    engine.update("UP", 0.5)
    engine.update("UP", 0.5)
    assert engine.player_y < initial_y + 15.0

    # Test boundary constraints (Top)
    engine.player_y = 5.0
    engine.update("UP", 0.5)
    assert engine.player_y >= 0.0

    # Test boundary constraints (Bottom)
    engine.player_y = float(engine.height - engine.paddle_h - 5)
    engine.update("DOWN", 0.5)
    assert engine.player_y <= float(engine.height - engine.paddle_h)

def test_ai_movement():
    engine = GameEngine()
    initial_ai_y = engine.ai_y
    # Set ball below AI paddle to test downward tracking
    engine.ball_y = initial_ai_y + 200
    engine.update("NONE", 1.0)
    assert engine.ai_y > initial_ai_y

def test_scoring_and_reset():
    engine = GameEngine()
    # Force ball out of bounds on the left (AI scores)
    engine.ball_x = -10
    engine.update("NONE", 0.5)
    assert engine.ai_score == 1
    assert engine.player_score == 0

    # Force ball out of bounds on the right (Player scores)
    engine.ball_x = engine.width + 10
    engine.update("NONE", 0.5)
    assert engine.player_score == 1

def test_win_condition():
    engine = GameEngine()
    engine.player_score = 4
    # Trigger winning point for player
    engine.ball_x = engine.width + 10
    engine.update("NONE", 0.5)
    
    state = engine.get_state()
    assert state["game_over"]
    assert state["winner"] == "Player"