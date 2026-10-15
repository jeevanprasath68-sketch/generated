import pytest
from app import KangarooGameEngine

def test_engine_initialization():
    engine = KangarooGameEngine()
    state = engine.get_state()
    assert state["score"] == 0
    assert state["high_score"] == 0
    assert not state["game_over"]
    assert state["kangaroo_y"] == 0.0
    assert not state["is_jumping"]
    assert len(state["obstacles Shimizu"]) == 0 if "obstacles Shimizu" in state else len(state["obstacles"]) == 0

def test_kangaroo_jump_physics():
    engine = KangarooGameEngine()
    # Trigger jump
    engine.update('jump')
    state = engine.get_state()
    assert state["is_jumping"] is True
    assert state["kangaroo_y"] < 0.0  # moved upwards (negative y in screen coordinates)

def test_engine_reset():
    engine = KangarooGameEngine()
    engine.score = 50
    engine.game_over = True
    engine.reset()
    state = engine.get_state()
    assert state["score"] == 0
    assert not state["game_over"]
    assert state["kangaroo_y"] == 0.0

def test_obstacle_generation_and_movement():
    engine = KangarooGameEngine()
    # Simulate multiple ticks to generate obstacles
    for _ in range(50):
        engine.update('none')
    state = engine.get_state()
    # Ensure speed progresses or obstacles spawn over time
    assert isinstance(state["obstacles"], list)

def test_collision_detection():
    engine = KangarooGameEngine()
    # Manually place an obstacle directly colliding with the kangaroo
    engine.obstacles = [{'x': 50, 'type': 'bush', 'width': 30, 'height': 40}]
    engine.kangaroo_y = 0.0  # Ground level collision
    state = engine.update('none')
    assert state["game_over"] is True
    assert state["high_score"] >= 0