import streamlit as st
import sqlite3
import pandas as pd
import random
import datetime
from typing import List, Dict, Any, Optional

# ==========================================
# 1. BUSINESS LOGIC & DATA ENGINES
# ==========================================

DB_NAME = "chatbot_app.db"

class DatabaseManager:
    @staticmethod
    def get_connection() -> sqlite3.Connection:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    @classmethod
    def init_db(cls):
        conn = cls.get_connection()
        cursor = conn.cursor()
        
        # Create tables if not exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS personas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                system_prompt TEXT NOT NULL,
                description TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                persona_id INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (persona_id) REFERENCES personas(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        ''')
        
        conn.commit()
        
        # Self-healing check for columns in messages
        cursor.execute("PRAGMA table_info(messages)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "tokens_used" not in columns:
            cursor.execute("ALTER TABLE messages ADD COLUMN tokens_used INTEGER DEFAULT 0")
            conn.commit()
            
        # Seed default personas if empty
        cursor.execute("SELECT COUNT(*) as cnt FROM personas")
        if cursor.fetchone()["cnt"] == 0:
            default_personas = [
                ("Friendly Assistant", "You are a warm, helpful, and cheerful AI assistant.", "Friendly and conversational."),
                ("Senior Software Architect", "You are a pragmatic, expert Principal Software Architect focused on clean code, testability, and resilience.", "Technical and architectural advisor."),
                ("Socratic Tutor", "You are a wise tutor who guides users to answers by asking thoughtful, probing questions rather than just giving solutions.", "Educational and reflective."),
                ("Poetic Bard", "You respond to every prompt with poetic flair, metaphor, and lyrical verse.", "Creative and artistic.")
            ]
            cursor.executemany("INSERT INTO personas (name, system_prompt, description) VALUES (?, ?, ?)", default_personas)
            conn.commit()
            
        conn.close()

    @classmethod
    def reset_database(cls):
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS messages")
        cursor.execute("DROP TABLE IF EXISTS sessions")
        cursor.execute("DROP TABLE IF EXISTS personas")
        conn.commit()
        conn.close()
        cls.init_db()


class ChatEngine:
    @staticmethod
    def generate_response(prompt: str, persona_system_prompt: str, temperature: float, model_name: str) -> Dict[str, Any]:
        """
        Simulates an intelligent response based on the persona, prompt, and parameters.
        """
        prompt_lower = prompt.lower()
        
        # Generate contextual simulation based on persona
        if "architect" in persona_system_prompt.lower():
            responses = [
                f"From an architectural standpoint regarding '{prompt}', we must prioritize modularity, decoupling, and high test coverage. Let's design a clean interface.",
                f"That's a solid engineering challenge. To address '{prompt}', I recommend starting with a robust data model and defensive error handling (like schema auto-healing).",
                f"When scaling systems like '{prompt}', separation of concerns is paramount. Ensure your business logic is entirely decoupled from the UI framework."
            ]
        elif "socratic" in persona_system_prompt.lower():
            responses = [
                f"That is a fascinating inquiry about '{prompt}'. What principles do you think underpin this challenge?",
                f"Before we solve '{prompt}', let us ask: what would failure look like in this scenario, and how might we prevent it?",
                f"Why do you suppose '{prompt}' is structured this way? What alternatives have you considered?"
            ]
        elif "poetic" in persona_system_prompt.lower():
            responses = [
                f"Ah, whispering winds of '{prompt}' arise,\nA dance of logic under starry skies...\nCode flows like rivers to the endless sea,\nIn search of truth and calm serenity.",
                f"Like autumn leaves upon a digital stream,\n'{prompt}' unfolds into a waking dream.\nBytes intertwine where quiet thoughts belong,\nA silent stanza in an ancient song."
            ]
        else:
            responses = [
                f"I've processed your request regarding '{prompt}'. Here is what you need to know: everything is running smoothly!",
                f"That's a great question about '{prompt}'. Let me assist you by breaking down the key points step by step.",
                f"I understand you are asking about '{prompt}'. Based on my analysis, here are three actionable recommendations..."
            ]
            
        reply_text = random.choice(responses)
        # Add a bit of flavor if temperature is high
        if temperature > 0.8:
            reply_text += f" [Temp: {temperature:.1f}, Model: {model_name}]"
            
        tokens = len(prompt.split()) + len(reply_text.split()) + random.randint(5, 20)
        return {
            "content": reply_text,
            "tokens_used": tokens
        }


class SessionManager:
    @staticmethod
    def create_session(title: str, persona_id: int) -> int:
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (title, persona_id, created_at) VALUES (?, ?, ?)",
            (title, persona_id, datetime.datetime.now().isoformat())
        )
        conn.commit()
        session_id = cursor.lastrowid
        conn.close()
        return session_id

    @staticmethod
    def get_sessions() -> List[Dict[str, Any]]:
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.id, s.title, s.created_at, p.name as persona_name, p.id as persona_id
            FROM sessions s
            LEFT JOIN personas p ON s.persona_id = p.id
            ORDER BY s.id DESC
        """)
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_messages(session_id: int) -> List[Dict[str, Any]]:
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, timestamp, tokens_used FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,)
        )
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def add_message(session_id: int, role: str, content: str, tokens_used: int = 0):
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO messages (session_id, role, content, timestamp, tokens_used) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, datetime.datetime.now().isoformat(), tokens_used)
        )
        conn.commit()
        conn.close()

    @staticmethod
    def get_personas() -> List[Dict[str, Any]]:
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, system_prompt, description FROM personas")
        rows = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def add_persona(name: str, system_prompt: str, description: str):
        conn = DatabaseManager.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO personas (name, system_prompt, description) VALUES (?, ?, ?)",
            (name, system_prompt, description)
        )
        conn.commit()
        conn.close()


# ==========================================
# 2. STREAMLIT WEB INTERFACE
# ==========================================

def main():
    st.set_page_config(
        page_title="OmniChat Pro - Advanced AI Chatbot",
        page_icon="💬",
        layout="wide"
    )

    # Initialize Database
    DatabaseManager.init_db()

    # Session state initialization
    if "current_session_id" not in st.session_state:
        sessions = SessionManager.get_sessions()
        if sessions:
            st.session_state.current_session_id = sessions[0]["id"]
        else:
            personas = SessionManager.get_personas()
            default_pid = personas[0]["id"] if personas else 1
            st.session_state.current_session_id = SessionManager.create_session("New Chat", default_pid)

    # --- SIDEBAR CONFIGURATION --- 
    st.sidebar.title("💬 OmniChat Pro")
    st.sidebar.markdown("Your intelligent, multi-persona AI assistant hub.")

    # Navigation mode
    nav_mode = st.sidebar.radio("Navigation", ["Chat", "Analytics & History", "Persona Manager"])

    st.sidebar.markdown("--- ✨ Model Settings ---")
    
    # Model Settings
    model_name = st.sidebar.selectbox("AI Engine", ["OmniBot-v4-Turbo", "DeepLogic-Pro", "CreativeGen-7B"], index=0)
    temperature = st.sidebar.slider("Temperature", min_value=0.0, max_value=1.0, value=0.7, step=0.1)
    
    # Persona Selector for current or new chat
    personas = SessionManager.get_personas()
    persona_dict = {p["name"]: p for p in personas}
    selected_persona_name = st.sidebar.selectbox("Active Persona", list(persona_dict.keys()))
    active_persona = persona_dict[selected_persona_name]

    st.sidebar.divider()
    st.sidebar.subheader("📂 Chat Sessions")
    
    if st.sidebar.button("➕ Start New Chat", use_container_width=True):
        new_id = SessionManager.create_session(f"Chat {datetime.datetime.now().strftime('%H:%M:%S')}", active_persona["id"])
        st.session_state.current_session_id = new_id
        st.rerun()

    sessions = SessionManager.get_sessions()
    for sess in sessions:
        sess_label = f"{sess['title']} ({sess['persona_name'] or 'Default'})"
        if sess['id'] == st.session_state.current_session_id:
            sess_label = f"👉 {sess_label}"
        if st.sidebar.button(sess_label, key=f"sess_{sess['id']}", use_container_width=True):
            st.session_state.current_session_id = sess['id']
            st.rerun()

    # Database Reset Utility
    with st.sidebar.expander("⚙️ Advanced Settings"):
        if st.button("Reset Database & Clear All", type="primary"):
            DatabaseManager.reset_database()
            st.success("Database reset successfully!")
            st.rerun()

    # ==========================================
    # PAGE: CHAT INTERFACE
    # ==========================================
    if nav_mode == "Chat":
        st.title("🤖 Chat Workspace")
        st.markdown(f"**Active Persona:** `{active_persona['name']}` — *{active_persona['description']}*")
        
        # Fetch messages for current session
        messages = SessionManager.get_messages(st.session_state.current_session_id)
        
        # Display chat history
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("tokens_used", 0) > 0:
                    st.caption(f"Tokens: {msg['tokens_used']} | {msg['timestamp'][:19]}")

        # Quick Prompt Suggestions
        st.markdown("**💡 Quick Prompts:**")
        col_q1, col_q2, col_q3 = st.columns(3)
        quick_prompt = None
        with col_q1:
            if st.button("Explain Clean Architecture", use_container_width=True):
                quick_prompt = "Explain the principles of clean architecture in Python."
        with col_q2:
            if st.button("Write a Python Decorator", use_container_width=True):
                quick_prompt = "Write a robust Python decorator for retry logic with exponential backoff."
        with col_q3:
            if st.button("Debug a SQLite Issue", use_container_width=True):
                quick_prompt = "How do I safely handle schema migrations in SQLite without data loss?"

        # Chat Input
        user_prompt = st.chat_input("Message OmniChat...") or quick_prompt
        
        if user_prompt:
            # Render user message immediately
            with st.chat_message("user"):
                st.markdown(user_prompt)
            SessionManager.add_message(st.session_state.current_session_id, "user", user_prompt)
            
            # Generate assistant response
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    res = ChatEngine.generate_response(
                        prompt=user_prompt,
                        persona_system_prompt=active_persona["system_prompt"],
                        temperature=temperature,
                        model_name=model_name
                    )
                    st.markdown(res["content"])
                    st.caption(f"Tokens: {res['tokens_used']}")
            
            SessionManager.add_message(
                st.session_state.current_session_id,
                "assistant",
                res["content"],
                tokens_used=res["tokens_used"]
            )
            st.rerun()

    # ==========================================
    # PAGE: ANALYTICS & HISTORY
    # ==========================================
    elif nav_mode == "Analytics & History":
        st.title("📊 Chat Analytics & History")
        st.markdown("Review your conversation statistics, token usage, and message logs across all sessions.")
        
        conn = DatabaseManager.get_connection()
        df_sessions = pd.read_sql_query("SELECT * FROM sessions", conn)
        df_messages = pd.read_sql_query("SELECT * FROM messages", conn)
        df_personas = pd.read_sql_query("SELECT * FROM personas", conn)
        conn.close()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Sessions", len(df_sessions))
        with col2:
            st.metric("Total Messages", len(df_messages))
        with col3:
            total_tokens = int(df_messages["tokens_used"].sum()) if not df_messages.empty else 0
            st.metric("Total Tokens Consumed", total_tokens)
            
        st.subheader("📈 Message Distribution by Role")
        if not df_messages.empty:
            role_counts = df_messages["role"].value_counts().reset_index()
            role_counts.columns = ["Role", "Count"]
            st.dataframe(role_counts, use_container_width=True)
        else:
            st.info("No message data available yet.")
            
        st.subheader("📂 All Sessions Log")
        if not df_sessions.empty:
            st.dataframe(df_sessions, use_container_width=True)
        else:
            st.info("No sessions recorded.")

    # ==========================================
    # PAGE: PERSONA MANAGER
    # ==========================================
    elif nav_mode == "Persona Manager":
        st.title("🎭 AI Persona Manager")
        st.markdown("Create custom AI personalities with tailored system instructions.")
        
        with st.form("new_persona_form"):
            st.subheader("Create New Persona")
            p_name = st.text_input("Persona Name")
            p_desc = st.text_input("Short Description")
            p_prompt = st.text_area("System Prompt / Instructions", placeholder="You are an expert in...")
            submitted = st.form_submit_button("Save Persona")
            
            if submitted:
                if p_name and p_prompt:
                    try:
                        SessionManager.add_persona(p_name, p_prompt, p_desc)
                        st.success(f"Persona '{p_name}' created successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating persona: {e}")
                else:
                    st.warning("Please provide both a Name and System Prompt.")
                    
        st.subheader("Existing Personas")
        personas = SessionManager.get_personas()
        for p in personas:
            with st.expander(f"{p['name']} - {p['description']}"):
                st.markdown(f"**System Prompt:**\n> {p['system_prompt']}")


if __name__ == "__main__":
    main()