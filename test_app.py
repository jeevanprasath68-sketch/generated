import pytest
import sqlite3
import os
from app import DatabaseManager, ChatEngine, SessionManager, DB_NAME

@pytest.fixture(autouse=True)
def setup_test_db():
    # Setup fresh DB for each test
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)
    DatabaseManager.init_db()
    yield
    if os.path.exists(DB_NAME):
        os.remove(DB_NAME)

def test_database_initialization_and_personas():
    """Test that database initializes and seeds default personas correctly."""
    personas = SessionManager.get_personas()
    assert len(personas) >= 4
    names = [p["name"] for p in personas]
    assert "Friendly Assistant" in names
    assert "Senior Software Architect" in names

def test_session_creation_and_messaging():
    """Test creating sessions, adding messages, and retrieving message history."""
    personas = SessionManager.get_personas()
    persona_id = personas[0]["id"]
    
    session_id = SessionManager.create_session("Test Session", persona_id)
    assert session_id is not None
    
    SessionManager.add_message(session_id, "user", "Hello AI", tokens_used=5)
    SessionManager.add_message(session_id, "assistant", "Hello Human!", tokens_used=8)
    
    messages = SessionManager.get_messages(session_id)
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "Hello AI"
    assert messages[0]["tokens_used"] == 5
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"] == "Hello Human!"

def test_chat_engine_responses():
    """Test that ChatEngine returns correctly structured response dict with content and tokens."""
    prompt = "How do I optimize database queries?"
    system_prompt = "You are an expert Principal Software Architect"
    
    response = ChatEngine.generate_response(prompt, system_prompt, temperature=0.5, model_name="OmniBot-v4-Turbo")
    
    assert isinstance(response, dict)
    assert "content" in response
    assert "tokens_used" in response
    assert isinstance(response["content"], str)
    assert len(response["content"]) > 0
    assert response["tokens_used"] > 0

def test_add_custom_persona():
    """Test adding a custom persona and retrieving it."""
    SessionManager.add_persona("Chef Gordon", "You are a passionate culinary master.", "Kitchen expert")
    personas = SessionManager.get_personas()
    
    chef = next((p for p in personas if p["name"] == "Chef Gordon"), None)
    assert chef is not None
    assert "culinary master" in chef["system_prompt"]

def test_database_reset():
    """Test that reset_database wipes sessions and messages while keeping schema valid."""
    personas = SessionManager.get_personas()
    session_id = SessionManager.create_session("Wipe Test", personas[0]["id"])
    SessionManager.add_message(session_id, "user", "Test message")
    
    assert len(SessionManager.get_sessions()) == 1
    
    DatabaseManager.reset_database()
    
    # Sessions should be empty, but personas re-seeded
    assert len(SessionManager.get_sessions()) == 0
    assert len(SessionManager.get_personas()) >= 4