import pytest
from app import GameEngine, Direction

def test_initial_state():
    engine = GameEngine(10, 10)
    assert len(engine.snake) == 3
    assert engine.score == 0
    assert not engine.game_over
    assert not engine.paused
    assert engine.food is not None

def test_snake_movement():
    engine = GameEngine(10, 10)
    engine.direction = Direction.RIGHT
    engine.next_direction = Direction.RIGHT
    initial_head = engine.snake[0]
    engine.update()
    new_head = engine.snake[0]
    assert new_head == (initial_head[0] + 1, initial_head[1])

def test_direction_change_validation():
    engine = GameEngine(10, 10)
    engine.direction = Direction.RIGHT
    # Trying to go LEFT (180-degree turn) should be ignored
    engine.change_direction(Direction.LEFT)
    assert engine.next_direction == Direction.RIGHT

    # Valid turn to UP
    engine.change_direction(Direction.UP)
    assert engine.next_direction == Direction.UP

def test_wall_collision():
    engine = GameEngine(5, 5)
    # Force snake head near right border heading right
    engine.snake = [(4, 2), (3, 2), (2, 2)]
    engine.direction = Direction.RIGHT
    engine.next_direction = Direction.RIGHT
    
    updated = engine.update()
    assert updated is True
    assert engine.game_over is True

def test_self_collision():
    engine = GameEngine(10, 10)
    # Construct a snake body configuration that wraps into itself
    engine.snake = [
        (5, 5),
        (5, 6),
        (4, 6),
        (4, 5),
        (4, 4)
    ]
    engine.direction = Direction.LEFT
    engine.next_direction = Direction.LEFT
    
    # Moving left from (5,5) hits (4,5)
    engine.update()
    assert engine.game_over is True

def test_food_consumption():
    engine = GameEngine(10, 10)
    engine.snake = [(5, 5), (4, 5), (3, 5)]
    engine.food = (6, 5)
    engine.direction = Direction.RIGHT
    engine.next_direction = Direction.RIGHT
    
    initial_length = len(engine.snake)
    engine.update()
    
    assert engine.score == 10
    assert len(engine.snake) == initial_length + 1
    assert engine.snake[0] == (6, 5)