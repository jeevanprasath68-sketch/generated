import pytest
from app import KangorooGameEngine, render_game_canvas

def test_engine_initialization():
    engine = KangorooGameEngine()
    assert engine.kangaroo_y == 0.0
    assert engine.is_jumping is False
    assert engine.score == 0
    assert engine.game_over is False
    assert len(engine.obstacles) == 0

def test_kangaroo_jump():
    engine = KangorooGameEngine()
    engine.jump()
    assert engine.is_jumping is True
    assert engine.kangaroo_vy < 0.0  # Moving upwards

    # Test update simulation after jump
    engine.update(dt=1.0)
    assert engine.kangaroo_y < 0.0  # Off the ground

def test_ground_collision():
    engine = KangorooGameEngine()
    engine.jump()
    # Simulate multiple ticks until kangaroo lands back on ground
    for _ in range(50):
        engine.update(dt=1.0)
    
    assert engine.kangaroo_y == 0.0
    assert engine.is_jumping is False

def test_obstacle_spawn_and_collision():
    engine = KangorooGameEngine()
    # Force an obstacle right at kangaroo position (x=50)
    engine.obstacles.append({
        'x': 55.0,
        'y': 0.0,
        'width': 20.0,
        'height': 20.0,
        'type': 'rock'
    })
    
    # Update should detect collision
    engine.update(dt=0.1)
    assert engine.game_over is True

def test_score_progression():
    engine = KangorooGameEngine()
    engine.update(dt=2.0)
    assert engine.score == 20
    assert engine.high_score == 20

def test_render_game_canvas_svg():
    engine = KangorooGameEngine()
    state = engine.get_render_state()
    svg_output = render_game_canvas(state)
    assert '<svg' in svg_output
    assert '</svg>' in svg_output
    assert 'HI 00000  00000' in svg_output