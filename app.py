import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional

DB_NAME = "ping_pong_arcade.db"

# --- DATABASE ENGINE & SELF-HEALING SCHEMA ---
class DatabaseEngine:
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
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                player_score INTEGER NOT NULL,
                ai_score INTEGER NOT NULL,
                difficulty TEXT NOT NULL,
                winner TEXT NOT NULL,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS high_scores (
                player_name TEXT PRIMARY KEY,
                high_score INTEGER NOT NULL,
                games_played INTEGER NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Defensive column check & migration for matches
        cursor.execute("PRAGMA table_info(matches)")
        columns = [col[1] for col in cursor.fetchall()]
        if "difficulty" not in columns:
            cursor.execute("ALTER TABLE matches ADD COLUMN difficulty TEXT DEFAULT 'Medium'")
            
        conn.commit()
        conn.close()

    @classmethod
    def reset_db(cls):
        conn = cls.get_connection()
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS matches")
        cursor.execute(
            "DROP TABLE IF EXISTS high_scores"
        )
        conn.commit()
        conn.close()
        cls.init_db()

    @classmethod
    def save_match(cls, player_name: str, p_score: int, ai_score: int, difficulty: str) -> bool:
        try:
            conn = cls.get_connection()
            cursor = conn.cursor()
            winner = player_name if p_score > ai_score else ("AI Bot" if ai_score > p_score else "Tie")
            
            cursor.execute(
                "INSERT INTO matches (player_name, player_score, ai_score, difficulty, winner) VALUES (?, ?, ?, ?, ?)",
                (player_name, p_score, ai_score, difficulty, winner)
            )
            
            # Update high scores
            cursor.execute("SELECT high_score, games_played FROM high_scores WHERE player_name = ?", (player_name,))
            row = cursor.fetchone()
            if row:
                new_high = max(row["high_score"], p_score)
                new_games = row["games_played"] + 1
                cursor.execute(
                    "UPDATE high_scores SET high_score = ?, games_played = ?, updated_at = CURRENT_TIMESTAMP WHERE player_name = ?",
                    (new_high, new_games, player_name)
                )
            else:
                cursor.execute(
                    "INSERT INTO high_scores (player_name, high_score, games_played) VALUES (?, ?, 1)",
                    (player_name, p_score)
                )
                
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Database error: {e}")
            return False

    @classmethod
    def get_leaderboard(cls) -> pd.DataFrame:
        try:
            conn = cls.get_connection()
            df = pd.read_sql_query("SELECT player_name, high_score, games_played, updated_at FROM high_scores ORDER BY high_score DESC LIMIT 10", conn)
            conn.close()
            return df
        except Exception:
            return pd.DataFrame(columns=["player_name", "high_score", "games_played", "updated_at"])

    @classmethod
    def get_match_history(cls) -> pd.DataFrame:
        try:
            conn = cls.get_connection()
            df = pd.read_sql_query("SELECT id, player_name, player_score, ai_score, difficulty, winner, played_at FROM matches ORDER BY played_at DESC LIMIT 20", conn)
            conn.close()
            return df
        except Exception:
            return pd.DataFrame(columns=["id", "player_name", "player_score", "ai_score", "difficulty", "winner", "played_at"])


# --- BUSINESS LOGIC / GAME VALIDATOR --- 
class GameValidator:
    @staticmethod
    def validate_score(player_score: int, ai_score: int) -> bool:
        if not isinstance(player_score, int) or not isinstance(ai_score, int):
            return False
        if player_score < 0 or ai_score < 0:
            return False
        return True

    @staticmethod
    def calculate_match_stats(df_matches: pd.DataFrame) -> Dict[str, Any]:
        if df_matches.empty:
            return {"total_matches": 0, "avg_player_score": 0.0, "player_win_rate": 0.0}
        total = len(df_matches)
        avg_score = df_matches["player_score"].mean()
        # Count matches where winner is not AI and not Tie
        wins = len(df_matches[df_matches["winner"].str.contains(r"AI|Tie", case=False, na=False) == False])
        win_rate = (wins / total) * 100 if total > 0 else 0.0
        return {
            "total_matches": total,
            "avg_player_score": round(avg_score, 1),
            "player_win_rate": round(win_rate, 1)
        }


# --- HTML/JS PONG GAME COMPONENT --- 
def get_pong_html(difficulty: str) -> str:
    # Map difficulty to AI speed/reaction
    ai_speeds = {"Easy": 0.04, "Medium": 0.07, "Hard": 0.12, "Legendary": 0.18}
    ai_speed = ai_speeds.get(difficulty, 0.07)
    winning_score = 5

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                background-color: #0d1117;
                color: #58a6ff;
                font-family: 'Courier New', Courier, monospace;
                text-align: center;
                margin: 0;
                padding: 0;
                overflow: hidden;
            }}
            #game-container {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
            }}
            .arcade-header {{
                font-size: 1.5rem;
                font-weight: bold;
                color: #00ffcc;
                text-shadow: 0 0 10px #00ffcc;
                margin-bottom: 5px;
                letter-spacing: 2px;
            }}
            .instructions {{
                font-size: 0.8rem;
                color: #8b949e;
                margin-bottom: 10px;
            }}
            canvas {{
                border: 4px solid #00ffcc;
                box-shadow: 0 0 25px rgba(0, 255, 204, 0.4);
                background: #000;
                border-radius: 6px;
            }}
            .controls-hint {{
                margin-top: 10px;
                font-size: 0.85rem;
                color: #c9d1d9;
            }}
            .key {{
                background: #21262d;
                border: 1px solid #30363d;
                padding: 2px 6px;
                border-radius: 4px;
                color: #58a6ff;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div id="game-container">
            <div class="arcade-header">RETRO PONG ARCADE</div>
            <div class="instructions">Difficulty: {difficulty} | First to {winning_score} wins!</div>
            <canvas id="pongCanvas" width="700" height="400"></canvas>
            <div class="controls-hint">
                Use <span class="key">▲</span> and <span class="key">▼</span> Arrow Keys or W/S keys to move paddle.
            </div>
        </div>

        <script>
            const canvas = document.getElementById("pongCanvas");
            const ctx = canvas.getContext("2d");

            // Game objects
            const ball = {{
                x: canvas.width / 2,
                y: canvas.height / 2,
                radius: 8,
                speed: 5,
                velocityX: 5,
                velocityY: 5,
                color: "#00ffcc"
            }};

            const player = {{
                x: 10,
                y: canvas.height / 2 - 40,
                width: 12,
                height: 80,
                score: 0,
                color: "#58a6ff"
            }};

            const ai = {{
                x: canvas.width - 22,
                y: canvas.height / 2 - 40,
                width: 12,
                height: 80,
                score: 0,
                color: "#ff5555"
            }};

            // Controls
            let upPressed = false;
            let downPressed = false;
            let gameStarted = true;
            let gameOver = false;
            let winnerText = "";

            window.addEventListener("keydown", (e) => {{
                if (e.key === "ArrowUp" || e.key === "w" || e.key === "W") {{
                    upPressed = true;
                    e.preventDefault();
                }}
                if (e.key === "ArrowDown" || e.key === "s" || e.key === "S") {{
                    downPressed = true;
                    e.preventDefault();
                }}
            }});

            window.addEventListener("keyup", (e) => {{
                if (e.key === "ArrowUp" || e.key === "w" || e.key === "W") {{
                    upPressed = false;
                }}
                if (e.key === "ArrowDown" || e.key === "s" || e.key === "S") {{
                    downPressed = false;
                }}
            }});

            function drawRect(x, y, w, h, color) {{
                ctx.fillStyle = color;
                ctx.fillRect(x, y, w, h);
            }}

            function drawCircle(x, y, r, color) {{
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(x, y, r, 0, Math.PI * 2, false);
                ctx.closePath();
                ctx.fill();
            }}

            function drawText(text, x, y, color, font = "20px Courier New") {{
                ctx.fillStyle = color;
                ctx.font = font;
                ctx.textAlign = "center";
                ctx.fillText(text, x, y);
            }}

            function drawNet() {{
                for (let i = 0; i <= canvas.height; i += 15) {{
                    drawRect(canvas.width / 2 - 1, i, 2, 10, "#30363d");
                }}
            }}

            function collision(b, p) {{
                b.top = b.y - b.radius;
                b.bottom = b.y + b.radius;
                b.left = b.x - b.radius;
                b.right = b.x + b.radius;

                p.top = p.y;
                p.bottom = p.y + p.height;
                p.left = p.x;
                p.right = p.x + p.width;

                return b.right > p.left && b.bottom > p.top && b.left < p.right && b.top < p.bottom;
            }}

            function resetBall() {{
                ball.x = canvas.width / 2;
                ball.y = canvas.height / 2;
                ball.velocityX = -ball.velocityX;
                ball.speed = 5;
            }}

            function update() {{
                if (gameOver) return;

                // Player movement
                if (upPressed && player.y > 0) {{
                    player.y -= 7;
                }} else if (downPressed && player.y < canvas.height - player.height) {{
                    player.y += 7;
                }}

                // AI movement with difficulty factor
                let aiSpeedFactor = {ai_speed};
                ai.y += (ball.y - (ai.y + ai.height / 2)) * aiSpeedFactor;
                
                // Restrict AI to canvas
                if (ai.y < 0) ai.y = 0;
                if (ai.y > canvas.height - ai.height) ai.y = canvas.height - ai.height;

                // Ball movement
                ball.x += ball.velocityX;
                ball.y += ball.velocityY;

                // Wall collision (Top and Bottom)
                if (ball.y - ball.radius < 0 || ball.y + ball.radius > canvas.height) {{
                    ball.velocityY = -ball.velocityY;
                }}

                // Paddle collision determination
                let activePaddle = (ball.x < canvas.width / 2) ? player : ai;

                if (collision(ball, activePaddle)) {{
                    let collidePoint = ball.y - (activePaddle.y + activePaddle.height / 2);
                    collidePoint = collidePoint / (activePaddle.height / 2);

                    let angleRad = (Math.PI / 4) * collidePoint;
                    let direction = (ball.x < canvas.width / 2) ? 1 : -1;

                    ball.velocityX = direction * ball.speed * Math.cos(angleRad);
                    ball.velocityY = ball.speed * Math.sin(angleRad);

                    ball.speed += 0.3; // Incremental speed
                }}

                // Scoring
                if (ball.x - ball.radius < 0) {{
                    ai.score++;
                    resetBall();
                }} else if (ball.x + ball.radius > canvas.width) {{
                    player.score++;
                    resetBall();
                }}

                // Check Win Condition
                if (player.score >= {winning_score}) {{
                    gameOver = true;
                    winnerText = "PLAYER WINS! 🏆";
                }} else if (ai.score >= {winning_score}) {{
                    gameOver = true;
                    winnerText = "AI WINS! 🤖";
                }}
            }}

            function render() {{
                // Clear canvas
                drawRect(0, 0, canvas.width, canvas.height, "#050505");
                
                drawNet();
                
                // Draw scores
                drawText(player.score, canvas.width / 4, canvas.height / 5, "#58a6ff", "40px Courier New");
                drawText(ai.score, 3 * canvas.width / 4, canvas.height / 5, "#ff5555", "40px Courier New");

                // Draw paddles and ball
                drawRect(player.x, player.y, player.width, player.height, player.color);
                drawRect(ai.x, ai.y, ai.width, ai.height, ai.color);
                drawCircle(ball.x, ball.y, ball.radius, ball.color);

                if (gameOver) {{
                    drawRect(0, 0, canvas.width, canvas.height, "rgba(0, 0, 0, 0.85)");
                    drawText(winnerText, canvas.width / 2, canvas.height / 2 - 20, "#00ffcc", "32px Courier New");
                    drawText("Match complete! Check Streamlit panel to save score.", canvas.width / 2, canvas.height / 2 + 30, "#8b949e", "14px Courier New");
                }}
            }}

            function gameLoop() {{
                update();
                render();
                requestAnimationFrame(gameLoop);
            }}

            gameLoop();
        </script>
    </body>
    </html>
    """


# --- STREAMLIT USER INTERFACE --- 
def main():
    st.set_page_config(
        page_title="Retro Arcade Ping Pong",
        page_icon="🏓",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize Database
    DatabaseEngine.init_db()

    # Custom Retro Styling
    st.markdown(
        """
        <style>
            .main-title {
                font-size: 2.5rem;
                color: #00ffcc;
                text-shadow: 0 0 12px rgba(0, 255, 204, 0.6);
                font-family: 'Courier New', Courier, monospace;
                font-weight: bold;
                margin-bottom: 0px;
            }
            .subtitle {
                color: #8b949e;
                font-size: 1.1rem;
                margin-bottom: 20px;
            }
            .metric-card {
                background-color: #161b22;
                border: 1px solid #30363d;
                padding: 15px;
                border-radius: 8px;
                text-align: center;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    st.markdown('<div class="main-title">🏓 RETRO ARCADE PING PONG</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">Classic 2-Player arcade showdown against intelligent AI. Built with Streamlit & HTML5 Canvas.</div>', unsafe_allow_html=True)

    # Sidebar Configuration & Controls
    st.sidebar.markdown("## 🎮 Arcade Settings")
    player_name = st.sidebar.text_input("Player Tag / Name", value="Player1", max_chars=20)
    difficulty = st.sidebar.selectbox("AI Difficulty", ["Easy", "Medium", "Hard", "Legendary"], index=1)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💾 Match Saver")
    st.sidebar.info("Finished a game? Log your score to the arcade high-score board below!")
    
    with st.sidebar.form("save_form"):
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            p_score_input = st.number_input("Your Score", min_value=0, max_value=10, value=5)
        with col_s2:
            ai_score_input = st.number_input("AI Score", min_value=0, max_value=10, value=2)
        
        submitted = st.form_submit_button("📥 Save Match Result")
        if submitted:
            if GameValidator.validate_score(p_score_input, ai_score_input):
                success = DatabaseEngine.save_match(player_name, p_score_input, ai_score_input, difficulty)
                if success:
                    st.sidebar.success(f"Score saved for {player_name}!")
                else:
                    st.sidebar.error("Failed to save score.")
            else:
                st.sidebar.error("Invalid score values provided.")

    # Database Maintenance
    with st.sidebar.expander("⚙️ Database & Maintenance"):
        if st.button("🗑️ Reset Arcade Database", type="primary"):
            DatabaseEngine.reset_db()
            st.sidebar.success("Database successfully wiped and re-initialized!")
            st.rerun()

    # Layout: Game Window & Stats Dashboard
    col_game, col_dash = st.columns([2.2, 1])

    with col_game:
        st.markdown("### 🕹️ Live Arena")
        # Embed HTML/JS Game inside Streamlit Component
        from streamlit.components.v1 import html
        html(get_pong_html(difficulty), height=480, scrolling=False)

    with col_dash:
        st.markdown("### 🏆 Arcade Leaderboard")
        df_leaderboard = DatabaseEngine.get_leaderboard()
        if not df_leaderboard.empty:
            st.dataframe(df_leaderboard, use_container_width=True, hide_index=True)
        else:
            st.info("No high scores recorded yet. Be the first!")

        st.markdown("### 📈 Career Statistics")
        df_matches = DatabaseEngine.get_match_history()
        stats = GameValidator.calculate_match_stats(df_matches)
        
        m1, m2 = st.columns(2)
        m1.metric("Total Matches", stats["total_matches"])
        m2.metric(
            "Win Rate", f"{stats['player_win_rate']}%")

    # Full Match History Table
    st.markdown("---")
    st.markdown("### 📜 Recent Match History")
    if not df_matches.empty:
        st.dataframe(df_matches, use_container_width=True, hide_index=True)
    else:
        st.markdown("*No recent match history available.*")


if __name__ == "__mainmain__" or __name__ == "__main__":
    main()