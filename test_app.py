import pytest
from app import SnakeGameEngine, Direction

def test_game_initialization():
    game = SnakeGameEngine(width=10, height=10)
    assert game.width == 10
    assert game.height == 10
    assert len(game.snake) == 3
    assert game.score == 0
    assert not game.game_over

def test_snake_movement():
    game = SnakeGameEngine(width=10, height=10)
    initial_head = game.snake[0]
    game.change_direction(Direction.RIGHT)
    game.update()
    new_head = game.snake[0]
    assert new_head == (initial_head[0] + 1, initial_head[1])

def test_invalid_reverse_direction():
    game = SnakeGameEngine(width=10, height=10)
    # Default direction is RIGHT. Trying to move LEFT immediately should be ignored.
    game.change_direction(Direction.LEFT)
    assert game.next_direction == Direction.RIGHT

def test_wall_collision():
    game = SnakeGameEngine(width=5, height=5)
    # Move snake right until it hits wall
    game.change_direction(Direction.RIGHT)
    for _ in range(10):
        if game.game_over:
            break
        game.update()
    assert game.game_over is True

def test_food_eating_and_scoring():
    game = SnakeGameEngine(width=10, height=10)
    # Force food right in front of head
    head_x, head_y = game.snake[0]
    game.food = (head_x + 1, head_y)
    initial_length = len(game.snake)
    
    game.change_direction(Direction.RIGHT)
    game.update()
    
    assert len(game.snake) == initial_length + 1
    assert game.score == 10