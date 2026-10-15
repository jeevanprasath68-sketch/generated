import pytest
from app import SnakeGameEngine, GRID_SIZE

def test_initial_state():
    engine = SnakeGameEngine()
    assert len(engine.snake) == 3
    assert engine.score == 0
    assert engine.game_over is False
    assert engine.food is not None
    assert 0 <= engine.food[0] < GRID_SIZE
    assert 0 <= engine.food[1] < GRID_SIZE

def test_snake_movement():
    engine = SnakeGameEngine()
    initial_head = engine.snake[0]
    engine.set_direction("RIGHT")
    engine.update()
    new_head = engine.snake[0]
    assert new_head == (initial_head[0] + 1, initial_head[1])

def test_invalid_direction_change():
    engine = SnakeGameEngine()
    # Initial direction is RIGHT. Trying to go LEFT shouldn't immediately reverse into itself.
    engine.set_direction("LEFT")
    assert engine.next_direction == "RIGHT"

def test_wall_collision():
    engine = SnakeGameEngine()
    # Force snake head near the left wall and move left
    engine.snake = [(0, 10), (1, 10), (2, 10)]
    engine.set_direction("LEFT")
    engine.update()
    assert engine.game_over is True

def test_self_collision():
    engine = SnakeGameEngine()
    # Create a compact looping snake configuration
    engine.snake = [
        (5, 5),
        (5, 6),
        (4, 6),
        (4, 5),
        (4, 4)
    ]
    engine.set_direction("DOWN")
    engine.update()
    # Moving down from (5,5) puts head at (5,6) which is already occupied by snake[1]
    assert engine.game_over is True

def test_food_consumption_and_scoring():
    engine = SnakeGameEngine()
    initial_length = len(engine.snake)
    # Place food directly in front of the snake
    head_x, head_y = engine.snake[0]
    engine.set_direction("RIGHT")
    engine.food = (head_x + 1, head_y)
    
    engine.update()
    assert engine.score == 10
    assert len(engine.snake) == initial_length + 1