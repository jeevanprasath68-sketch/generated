import pytest
from app import SnakeGame, Direction, GameStatus

def test_game_initialization():
    game = SnakeGame(width=15, height=15)
    assert game.width == 15
    assert game.height == 15
    assert len(game.snake) == 3
    assert game.score == 0
    assert game.status == GameStatus.IDLE
    assert game.food is not None


def test_snake_movement():
    game = SnakeGame(width=20, height=20)
    game.status = GameStatus.PLAYING
    initial_head = game.snake[0]
    
    # Moving RIGHT
    game.change_direction(Direction.RIGHT)
    game.update()
    new_head = game.snake[0]
    assert new_head == (initial_head[0] + 1, initial_head[1])


def test_invalid_direction_reversal():
    game = SnakeGame(width=20, height=20)
    game.direction = Direction.RIGHT
    game.next_direction = Direction.RIGHT
    
    # Attempting 180-degree turn directly opposite (LEFT)
    game.change_direction(Direction.LEFT)
    assert game.next_direction == Direction.RIGHT


def test_wall_collision():
    game = SnakeGame(width=5, height=5)
    game.status = GameStatus.PLAYING
    # Position snake near the right wall heading right
    game.snake = [(4, 2), (3, 2), (2, 2)]
    game.direction = Direction.RIGHT
    game.next_direction = Direction.RIGHT
    
    status = game.update()
    assert status == GameStatus.GAME_OVER


def test_self_collision():
    game = SnakeGame(width=10, height=10)
    game.status = GameStatus.PLAYING
    # Construct a snake configuration that will bite itself
    game.snake = [
        (5, 5),
        (5, 6),
        (4, 6),
        (4, 5),
        (4, 4)
    ]
    game.direction = Direction.DOWN
    game.next_direction = Direction.DOWN
    
    status = game.update()
    assert status == GameStatus.GAME_OVER


def test_food_consumption_and_scoring():
    game = SnakeGame(width=10, height=10)
    game.status = GameStatus.PLAYING
    game.snake = [(5, 5), (4, 5), (3, 5)]
    game.food = (6, 5)  # Right in front of head
    game.direction = Direction.RIGHT
    game.next_direction = Direction.RIGHT
    
    initial_length = len(game.snake)
    game.update()
    
    assert game.score == 10
    assert len(game.snake) == initial_length + 1
    assert game.snake[0] == (6, 5)