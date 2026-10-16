import os
import pytest
from app import GameEngine, DB_NAME, render_ping_pong_html

@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Setup fresh DB for testing
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    GameEngine.init_db()
    yield
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)


def test_init_db_creates_table():
    conn = GameEngine.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='matches'")
    table = cursor.fetchone()
    conn.close()
    assert table is not None
    assert table[0] == 'matches'


def test_save_and_retrieve_match():
    # Happy path test
    success = GameEngine.save_match("TestUser", 5, 2, "Medium")
    assert success is True

    leaderboard = GameEngine.get_leaderboard()
    assert len(leaderboard) == 1
    assert leaderboard[0][0] == "TestUser"
    assert leaderboard[0][1] == 5
    assert leaderboard[0][2] == 2
    assert leaderboard[0][3] == "Medium"


def test_save_match_empty_name_defaults_to_anonymous():
    success = GameEngine.save_match("   ", 3, 5, "Hard")
    assert success is True

    leaderboard = GameEngine.get_leaderboard()
    assert leaderboard[0][0] == "Anonymous"


def test_leaderboard_ordering():
    GameEngine.save_match("PlayerLow", 2, 5, "Easy")
    GameEngine.save_match("PlayerHigh", 5, 1, "Insane")
    GameEngine.save_match("PlayerMid", 4, 3, "Medium")

    leaderboard = GameEngine.get_leaderboard()
    assert len(leaderboard) == 3
    # Ordered by player_score DESC, then played_at DESC
    assert leaderboard[0][0] == "PlayerHigh"
    assert leaderboard[1][0] == "PlayerMid"
    assert leaderboard[2][0] == "PlayerLow"


def test_clear_database():
    GameEngine.save_match("User1", 5, 0, "Easy")
    assert len(GameEngine.get_leaderboard()) == 1

    cleared = GameEngine.clear_database()
    assert cleared is True
    assert len(GameEngine.get_leaderboard()) == 0


def test_render_ping_pong_html_generation():
    html_easy = render_ping_pong_html("Easy")
    html_insane = render_ping_pong_html("Insane")
    
    assert "canvas" in html_easy
    assert "Easy" in html_easy
    assert "Insane" in html_insane
    assert "startGame()" in html_easy