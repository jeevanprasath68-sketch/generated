import streamlit as st
import sqlite3
import random
from datetime import datetime
from typing import Dict, Tuple, Any, List

# ==========================================
# DATABASE & STORAGE RESILIENCE
# ==========================================
DB_NAME = "rps_game.db"

def _init_db() -> None:
    """Initialize SQLite database and ensure schema includes all required columns with self-healing."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS match_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_choice TEXT NOT NULL,
            ai_choice TEXT NOT NULL,
            result TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )
    
    # Verify columns for schema resilience
    cursor.execute("PRAGMA table_info(match_history)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    required_columns = {
        "player_choice": "TEXT",
        "ai_choice": "TEXT",
        "result": "TEXT",
        "timestamp": "TEXT"
    }
    
    for col, col_type in required_columns.items():
        if col not in existing_columns:
            cursor.execute(f"ALTER TABLE match_history ADD COLUMN {col} {col_type}")
            
    conn.commit()
    conn.close()

def reset_database() -> None:
    """Wipe the database clean for reset controls."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS match_history")
    conn.commit()
    conn.close()
    _init_db()

# ==========================================
# BUSINESS LOGIC & GAME ENGINE
# ==========================================
class GameEngine:
    CHOICES = ["Rock", "Paper", "Scissors"]
    
    @staticmethod
    def get_ai_choice() -> str:
        """Generate a random choice for the AI."""
        return random.choice(GameEngine.CHOICES)

    @staticmethod
    def determine_winner(player: str, ai: str) -> str:
        """
        Determine the winner of a round.
        Returns: 'Player', 'AI', or 'Tie'
        """
        if player not in GameEngine.CHOICES or ai not in GameEngine.CHOICES:
            raise ValueError("Invalid choice provided to game engine.")
            
        if player == ai:
            return "Tie"
        
        winning_combinations = {
            "Rock": "Scissors",
            "Paper": "Rock",
            "Scissors": "Paper"
        }
        
        if winning_combinations[player] == ai:
            return "Player"
        else:
            return "AI"

    @staticmethod
    def save_match(player: str, ai: str, result: str) -> None:
        """Save match result to SQLite database with error handling."""
        try:
            _init_db()
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO match_history (player_choice, ai_choice, result, timestamp) VALUES (?, ?, ?, ?)",
                (player, ai, result, timestamp)
            )
            conn.commit()
            conn.close()
        except sqlite3.OperationalError:
            _init_db()
            GameEngine.save_match(player, ai, result)

    @staticmethod
    def get_match_history() -> List[Dict[str, Any]]:
        """Retrieve match history from SQLite."""
        try:
            _init_db()
            conn = sqlite3.connect(DB_NAME)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT player_choice, ai_choice, result, timestamp FROM match_history ORDER BY id DESC LIMIT 50")
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except sqlite3.OperationalError:
            _init_db()
            return []

    @staticmethod
    def calculate_stats(history: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate win/loss/tie counts from history."""
        stats = {"Player": 0, "AI": 0, "Tie": 0, "Total": len(history)}
        for match in history:
            res = match.get("result")
            if res in stats:
                stats[res] += 1
        return stats

# ==========================================
# STREAMLIT USER INTERFACE
# ==========================================
def main():
    st.set_page_config(
        page_title="Rock Paper Scissors Pro",
        page_icon="🎮",
        layout="centered"
    )
    
    # Ensure DB is ready
    _init_db()

    # Custom CSS for modern styling and animations
    st.markdown(
        """
        <style>
        .main-title {
            text-align: center;
            font-size: 2.8rem;
            font-weight: 800;
            background: linear-gradient(90deg, #FF4B4B, #FF8F00);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.2rem;
        }
        .subtitle {
            text-align: center;
            color: #6c757d;
            font-size: 1.1rem;
            margin-bottom: 2rem;
        }
        .card {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            text-align: center;
            margin-bottom: 1rem;
        }
        .dark-mode .card {
            background-color: #1e1e1e;
        }
        .choice-badge {
            font-size: 2rem;
            font-weight: bold;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="main-title">Rock • Paper • Scissors</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Classic showdown against an intelligent AI bot!</div>', unsafe_allow_html=True)

    # Sidebar controls & stats
    with st.sidebar:
        st.header("⚙️ Game Controls")
        if st.button("🔄 Reset Score & History", use_container_width=True):
            reset_database()
            st.session_state.player_score = 0
            st.session_state.ai_score = 0
            st.session_state.ties = 0
            st.session_state.last_round = None
            st.success("Game data reset successfully!")
            st.rerun()

        st.divider()
        st.info("💡 **Rules**:\n- Rock beats Scissors\n- Scissors beats Paper\n- Paper beats Rock")

    # Initialize session state for active score tracking
    history = GameEngine.get_match_history()
    stats = GameEngine.calculate_stats(history)
    
    if "last_round" not in st.session_state:
        st.session_state.last_round = None

    # Display Metric KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👤 You", stats["Player"])
    col2.metric("🤖 AI", stats["AI"])
    col3.metric("🤝 Ties", stats["Tie"])
    col4.metric("📊 Total", stats["Total"])

    st.divider()

    # Player Choice Section
    st.subheader("Make Your Move!")
    
    cols = st.columns(3)
    player_choice = None
    
    with cols[0]:
        if st.button("🪨 Rock", use_container_width=True):
            player_choice = "Rock"
    with cols[1]:
        if st.button("📄 Paper", use_container_width=True):
            player_choice = "Paper"
    with cols[2]:
        if st.button("✂️ Scissors", use_container_width=True):
            player_choice = "Scissors"

    # Process Round
    if player_choice:
        ai_choice = GameEngine.get_ai_choice()
        winner = GameEngine.determine_winner(player_choice, ai_choice)
        
        # Save to DB
        GameEngine.save_match(player_choice, ai_choice, winner)
        
        # Update session state for instant rendering
        st.session_state.last_round = {
            "player": player_choice,
            "ai": ai_choice,
            "winner": winner
        }
        st.rerun()

    # Display Last Round Result Banner
    if st.session_state.last_round:
        lr = st.session_state.last_round
        st.markdown("### 🏟️ Round Outcome")
        
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.markdown(f"**Your Choice:**\n### {lr['player']}")
        with res_col2:
            st.markdown(f"**AI's Choice:**\n### {lr['ai']}")
            
        if lr['winner'] == "Player":
            st.success("🎉 **Congratulations! You won this round!**")
        elif lr['winner'] == "AI":
            st.error("🤖 **AI wins this round! Better luck next time.**")
        else:
            st.warning("🤝 **It's a Tie! Great minds think alike.**")

    st.divider()

    # Match History Table
    with st.expander("📜 View Match History (Last 50 Games)", expanded=False):
        match_history = GameEngine.get_match_history()
        if match_history:
            st.dataframe(match_history, use_container_width=True)
        else:
            st.info("No matches played yet. Make your first move above!")

if __name__ == "__main__":
    main()