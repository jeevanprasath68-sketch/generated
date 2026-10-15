import pytest
from app import SnakeGameEngine

def test_game_initialization():
    engine = SnakeGameEngine(width=15, height=15)
    assert len(engine.snake) == 3
    assert engine.score == 0
    assert engine.game_over is False
    assert engine.direction == "RIGHT"
    assert engine.food is not None
    assert engine.food not in engine.snake

def test_snake_movement_happy_path():
    engine = SnakeGameEngine(width=20, height=20)
    initial_head = engine.snake[0]
    engine.set_direction("RIGHT")
    state = engine.step()
    
    new_head = state["snake"][0]
    assert new_head == (initial_head[0] + 1, initial_head[1])
    assert state["game_over"] is False

def test_direction_reversal_prevention():
    engine = SnakeGameEngine(width=20, height=20)
    # Initial direction is RIGHT
    assert engine.direction == "RIGHT"
    
    # Attempting to move LEFT immediately should be ignored
    engine.set_direction("LEFT")
    assert engine.next_direction == "RIGHT"
    
    # Valid turn to UP should work
    engine.set_direction("UP")
    assert engine.next_direction == "UP"

def test_wall_collision():
    engine = SnakeGameEngine(width=5, height=5)
    # Place snake near right wall facing right
    engine.snake = [(4, 2), (3, 2), (2, 2)]
    engine.direction = "RIGHT"
    engine.next_direction = "RIGHT"
    
    state = engine.step()
    assert state["game_over"] is True

def test_food_consumption_and_growth():
    engine = SnakeGameEngine(width=10, height=10)
    engine.snake = [(5, 5), (4, 5), (3, 5)]
    engine.direction = "RIGHT"
    engine.next_direction = "RIGHT"
    engine.food = (6, 5) # Directly in front of snake
    
    initial_length = len(engine.snake)
    initial_score = engine.score
    
    state = engine.step()
    
    assert len(state["snake"]) == initial_length + 1
    assert state["score"] == initial_score + 10
    assert state["game_over"] is False

def test_self_collision():
    engine = SnakeGameEngine(width=10, height=10)
    # Create a compact looping snake configuration that will collide with itself
    engine.snake = [
        (5, 5),
        (5, 6),
        (4, 6),
        (4, 5),
        (4, 4)
    ]
    engine.direction = "UP"
    engine.next_direction = "UP"
    
    # Moving UP from (5,5) leads directly to (5,4) which is not occupied, wait let's configure self collision properly:
    # Let's move into (5,6) which is occupied
    engine.snake = [
        (5, 5),
        (6, 5),
        (6, 6),
        (5, 6),
        (5, 4)
    ]
    engine.direction = "DOWN"
    engine.next_direction = "DOWN"
    # Moving DOWN from (5,5) hits (5,6) which is segment index 3
    
    state = engine.step()
    assert state["game_over"] is True