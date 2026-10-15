import pytest
from app import SnakeGameEngine, Direction, GameStatus

def test_game_initialization():
    engine = SnakeGameEngine(width=15, height=15)
    assert engine.width == 15
    assert engine.height == 15
    assert len(engine.snake) == 3
    assert engine.status == GameStatus.IDLE
    assert engine.score == 0
    assert 0 <= engine.food[0] < 15
    assert 0 <= engine.food[1] < 15

def test_snake_movement_and_scoring():
    engine = SnakeGameEngine(width=10, height=10)
    engine.status = GameStatus.RUNNING
    
    initial_head = engine.snake[0]
    # Place food directly in front of the snake
    engine.food = (initial_head[0] + 1, initial_head[1])
    engine.direction = Direction.RIGHT
    engine.next_direction = Direction.RIGHT
    
    engine.step()
    
    assert engine.score == 10
    assert len(engine.snake) == 4
    assert engine.snake[0] == (initial_head[0] + 1, initial_head[1])

def test_direction_change_rules():
    engine = SnakeGameEngine(width=10, height=10)
    engine.direction = Direction.RIGHT
    engine.next_direction = Direction.RIGHT
    
    # Try immediate 180-degree turn (LEFT when moving RIGHT)
    engine.change_direction(Direction.LEFT)
    assert engine.next_direction == Direction.RIGHT
    
    # Valid 90-degree turn (UP)
    engine.change_direction(Direction.UP)
    assert engine.next_direction == Direction.UP

def test_wall_collision():
    engine = SnakeGameEngine(width=5, height=5)
    engine.status = GameStatus.RUNNING
    # Position snake head at rightmost wall
    engine.snake = [(4, 2), (3, 2), (2, 2)]
    engine.direction = Direction.RIGHT
    engine.next_direction = Direction.RIGHT
    
    engine.step()
    assert engine.status == GameStatus.GAME_OVER

def test_self_collision():
    engine = SnakeGameEngine(width=10, height=10)
    engine.status = GameStatus.RUNNING
    # Create a loop where head (5, 5) moving UP will hit segment (5, 4)
    engine.snake = [
        (5, 5),
        (5, 4),
        (4, 4),
        (4, 5),
        (4, 6)
    ]
    engine.direction = Direction.UP
    engine.next_direction = Direction.UP
    
    # Force move into self
    engine.step()
    assert engine.status == GameStatus.GAME_OVER