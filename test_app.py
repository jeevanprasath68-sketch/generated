import pytest
from app import SnakeGame, GRID_SIZE

def test_snake_initialization():
    game = SnakeGame(20, 20)
    assert len(game.snake) == 3
    assert game.score == 0
    assert game.game_over is False
    assert game.direction == "UP"

def test_snake_movement():
    game = SnakeGame(20, 20)
    initial_head = game.snake[0]
    game.step()
    new_head = game.snake[0]
    assert new_head == (initial_head[0], initial_head[1] - 1)

def test_direction_change():
    game = SnakeGame(20, 20)
    game.change_direction("LEFT")
    assert game.next_direction == "LEFT"
    # Cannot reverse directly into opposite direction
    game.change_direction("RIGHT")
    assert game.next_direction == "LEFT"

def test_wall_collision():
    game = SnakeGame(10, 10)
    # Place snake at top edge moving up
    game.snake = [(5, 0), (5, 1), (5, 2)]
    game.direction = "UP"
    game.next_direction = "UP"
    game.step()
    assert game.game_over is True

def test_food_consumption():
    game = SnakeGame(10, 10)
    game.snake = [(5, 5), (5, 6), (5, 7)]
    game.direction = "UP"
    game.next_direction = "UP"
    game.food = (5, 4)
    initial_length = len(game.snake)
    game.step()
    assert game.score == 10
    assert len(game.snake) == initial_length + 1
    assert game.snake[0] == (5, 4)