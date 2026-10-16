import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List

# ==========================================
# BUSINESS LOGIC & DATABASE ENGINE
# ==========================================

DB_NAME = "ping_pong_scores.db"

def _init_db():
    """Initializes SQLite database with automatic schema migration and self-healing."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_name TEXT NOT NULL,
            player_score INTEGER NOT NULL,
            ai_score INTEGER NOT NULL,
            difficulty TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    
    # Schema migration check: ensure all columns exist
    cursor.execute("PRAGMA table_info(matches)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "player_name" not in columns:
        cursor.execute("ALTER TABLE matches ADD COLUMN player_name TEXT NOT NULL DEFAULT 'Player'")
    if "player_score" not in columns:
        cursor.execute("ALTER TABLE matches ADD COLUMN player_score INTEGER NOT NULL DEFAULT 0")
    if "ai_score" not in columns:
        cursor.execute("ALTER TABLE matches ADD COLUMN ai_score INTEGER NOT NULL DEFAULT 0")
    if "difficulty" not in columns:
        cursor.execute("ALTER TABLE matches ADD COLUMN difficulty TEXT NOT NULL DEFAULT 'Medium'")
    if "timestamp" not in columns:
        cursor.execute("ALTER TABLE matches ADD COLUMN timestamp TEXT NOT NULL DEFAULT ''")
        
    conn.commit()
    conn.close()

class PingPongEngine:
    """Handles business logic for game state evaluation, scoring, and score persistence."""
    
    @staticmethod
    def save_match(player_name: str, player_score: int, ai_score: int, difficulty: str) -> bool:
        try:
            _init_db()
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO matches (player_name, player_score, ai_score, difficulty, timestamp) VALUES (?, ?, ?, ?, ?)",
                (player_name, player_score, ai_score, difficulty, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Database Error: {e}")
            return False

    @staticmethod
    def get_leaderboard() -> List[Dict[str, Any]]:
        try:
            _init_db()
            conn = sqlite3.connect(DB_NAME)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM matches ORDER BY player_score DESC, timestamp DESC LIMIT 10")
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Leaderboard Error: {e}")
            return []

    @staticmethod
    def reset_database() -> bool:
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS matches")
            conn.commit()
            conn.close()
            _init_db()
            return True
        except Exception as e:
            print(f"Reset DB Error: {e}")
            return False

# ==========================================
# HTML5 / CANVAS GAME COMPONENT
# ==========================================

def render_game_canvas(difficulty: str, target_score: int, player_name: str):
    """Renders the interactive HTML5/JS canvas ping pong game inside Streamlit."""
    
    # Map difficulty to AI speed multiplier
    ai_speed_map = {"Easy": 0.04, "Medium": 0.07, "Hard": 0.11, "Expert": 0.16}
    ai_speed = ai_speed_map.get(difficulty, 0.07)
    
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                margin: 0;
                background: #0f172a;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                color: white;
                overflow: hidden;
            }} 
            #game-container {{
                position: relative;
                box-shadow: 0 10px 25px rgba(0,0,0,0.5);
                border-radius: 12px;
                overflow: hidden;
                border: 2px solid #334155;
            }} 
            canvas {{
                display: block;
                background: #1e293b;
            }}
            .ui-panel {{
                display: flex;
                justify-content: space-between;
                width: 100%;
                max-width: 600px;
                margin-bottom: 10px;
                font-weight: bold;
                font-size: 16px;
            }}
            .score-box {{
                background: #334155;
                padding: 6px 16px;
                border-radius: 8px;
            }}
            #game-over-modal {{
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(15, 23, 42, 0.85);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                text-align: center;
                display: none;
                z-index: 10;
            }} 
            .btn {{
                background: #6366f1;
                color: white;
                border: none;
                padding: 10px 24px;
                font-size: 16px;
                font-weight: bold;
                border-radius: 6px;
                cursor: pointer;
                margin-top: 15px;
                transition: background 0.2s;
            }}
            .btn:hover {{
                background: #4f46e5;
            }}
            .mobile-controls {{
                display: none;
                justify-content: space-between;
                width: 100%;
                max-width: 600px;
                margin-top: 10px;
            }} 
            .mob-btn {{
                background: #334155;
                color: white;
                border: none;
                padding: 15px 30px;
                font-size: 20px;
                border-radius: 8px;
                flex: 1;
                margin: 0 5px;
                cursor: pointer;
            }}
            @media (max-width: 768px) {{
                .mobile-controls {{ display: flex; }}
            }}
        </style>
    </head>
    <body>
        <div class="ui-panel">
            <div class="score-box">{player_name}: <span id="playerScore">0</span></div>
            <div class="score-box">AI ({difficulty}): <span id="aiScore">0</span></div>
        </div>

        <div id="game-container">
            <canvas id="pongCanvas" width="600" height="400"></canvas>
            <div id="game-over-modal">
                <h1 id="modal-title" style="margin: 0 0 10px 0; color: #38bdf8;">Game Over</h1>
                <p id="modal-desc" style="margin: 0; color: #94a3b8;">Final Score</p>
                <button class="btn" onclick="restartGame()">Play Again</button>
            </div>
        </div>

        <div class="mobile-controls">
            <button class="mob-btn" ontouchstart="moveUp()" onmousedown="moveUp()">⬆️ Up</button>
            <button class="mob-btn" ontouchstart="moveDown()" onmousedown="moveDown()">⬇️ Down</button>
        </div>

        <script>
            const canvas = document.getElementById('pongCanvas');
            const ctx = canvas.getContext('2d');

            const targetScore = {target_score};
            const aiSpeed = {ai_speed};

            let playerScore = 0;
            let aiScore = 0;
            let gameIsOver = false;

            const paddleWidth = 12;
            const paddleHeight = 80;

            let player = {{
                x: 15,
                y: canvas.height / 2 - paddleHeight / 2,
                width: paddleWidth,
                height: paddleHeight,
                dy: 0
            }};

            let ai = {{
                x: canvas.width - 27,
                y: canvas.height / 2 - paddleHeight / 2,
                width: paddleWidth,
                height: paddleHeight
            }};

            let ball = {{
                x: canvas.width / 2,
                y: canvas.height / 2,
                radius: 8,
                speed: 5,
                velocityX: 5,
                velocityY: 3
            }};

            // Keyboard controls
            let keys = {{}};
            window.addEventListener('keydown', (e) => {{
                keys[e.key] = true;
                if(['ArrowUp', 'ArrowDown', ' '].includes(e.key)) e.preventDefault();
            }});
            window.addEventListener('keyup', (e) => {{
                keys[e.key] = false;
            }});

            function moveUp() {{
                player.y = Math.max(0, player.y - 35);
            }}
            function moveDown() {{
                player.y = Math.min(canvas.height - player.height, player.y + 35);
            }}

            function collision(b, p) {{
                return b.x - b.radius < p.x + p.width &&
                       b.x + b.radius > p.x &&
                       b.y + b.radius > p.y &&
                       b.y - b.radius < p.y + p.height;
            }}

            function resetBall(scorer) {{
                ball.x = canvas.width / 2;
                ball.y = canvas.height / 2;
                ball.speed = 5;
                ball.velocityX = (scorer === 'player') ? -5 : 5;
                ball.velocityY = (Math.random() * 4) - 2;
            }}

            function update() {{
                if (gameIsOver) return;

                // Player keyboard movement
                if (keys['ArrowUp'] || keys['w'] || keys['W']) {{
                    player.y = Math.max(0, player.y - 7);
                }}
                if (keys['ArrowDown'] || keys['s'] || keys['S']) {{
                    player.y = Math.min(canvas.height - player.height, player.y + 7);
                }}

                // AI tracking logic with smooth interpolation
                let targetY = ball.y - ai.height / 2;
                ai.y += (targetY - ai.y) * ai_speed;
                ai.y = Math.max(0, Math.min(canvas.height - ai.height, ai.y));

                // Move ball
                ball.x += ball.velocityX;
                ball.y += ball.velocityY;

                // Wall collisions (Top/Bottom)
                if (ball.y - ball.radius < 0) {{
                    ball.y = ball.radius;
                    ball.velocityY *= -1;
                }} else if (ball.y + ball.radius > canvas.height) {{
                    ball.y = canvas.height - ball.radius;
                    ball.velocityY *= -1;
                }}

                // Paddle collisions
                let activePaddle = (ball.x < canvas.width / 2) ? player : ai;
                if (collision(ball, activePaddle)) {{
                    let collidePoint = ball.y - (activePaddle.y + activePaddle.height / 2);
                    collidePoint = collidePoint / (activePaddle.height / 2);
                    
                    let angleRad = (Math.PI / 4) * collidePoint;
                    let direction = (ball.x < canvas.width / 2) ? 1 : -1;
                    
                    ball.velocityX = direction * ball.speed * Math.cos(angleRad);
                    ball.velocityY = ball.speed * Math.sin(angleRad);
                    
                    ball.speed += 0.3; // Incremental rally speed
                }}

                // Scoring
                if (ball.x - ball.radius < 0) {{
                    aiScore++;
                    document.getElementById('aiScore').innerText = aiScore;
                    checkGameOver();
                    if (!gameIsOver) resetBall('ai');
                }} else if (ball.x + ball.radius > canvas.width) {{
                    playerScore++;
                    document.getElementById('playerScore').innerText = playerScore;
                    checkGameOver();
                    if (!gameIsOver) resetBall('player');
                }}
            }}

            function checkGameOver() {{
                if (playerScore >= targetScore || aiScore >= targetScore) {{
                    gameIsOver = true;
                    const title = document.getElementById('modal-title');
                    const desc = document.getElementById('modal-desc');
                    
                    if (playerScore > aiScore) {{
                        title.innerText = "🎉 You Won the Match!";
                        title.style.color = "#34d399";
                    }} else {{
                        title.innerText = "🤖 AI Wins the Match!";
                        title.style.color = "#f87171";
                    }}
                    desc.innerText = `Final Score — {playerName}: ${{playerScore}} | AI: ${{aiScore}}`;
                    document.getElementById('game-over-modal').style.display = 'flex';
                    
                    // Notify Streamlit parent component about match completion
                    window.parent.postMessage({{
                        type: 'streamlit:setComponentValue',
                        value: {{ player_score: playerScore, ai_score: aiScore, completed: true }}
                    }}, '*');
                }}
            }}

            function restartGame() {{
                playerScore = 0;
                aiScore = 0;
                document.getElementById('playerScore').innerText = '0';
                document.getElementById('aiScore').innerText = '0';
                document.getElementById('game-over-modal').style.display = 'none';
                gameIsOver = false;
                resetBall('player');
            }}

            function draw() {{
                // Clear canvas
                ctx.fillStyle = '#1e293b';
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                // Draw center net
                ctx.strokeStyle = '#334155';
                ctx.lineWidth = 4;
                ctx.setLineDash([8, 8]);
                ctx.beginPath();
                ctx.moveTo(canvas.width / 2, 0);
                ctx.lineTo(canvas.width / 2, canvas.height);
                ctx.stroke();
                ctx.setLineDash([]);

                // Draw Player Paddle (Cyan)
                ctx.fillStyle = '#38bdf8';
                ctx.shadowColor = '#38bdf8';
                ctx.shadowBlur = 10;
                ctx.fillRect(player.x, player.y, player.width, player.height);

                // Draw AI Paddle (Pink/Red)
                ctx.fillStyle = '#f43f5e';
                ctx.shadowColor = '#f43f5e';
                ctx.shadowBlur = 10;
                ctx.fillRect(ai.x, ai.y, ai.width, ai.height);

                // Draw Ball (White)
                ctx.fillStyle = '#ffffff';
                ctx.shadowColor = '#ffffff';
                ctx.shadowBlur = 12;
                ctx.beginPath();
                ctx.arc(ball.x, ball.y, ball.radius, 0, Math.PI * 2, false);
                ctx.closePath();
                ctx.fill();
                ctx.shadowBlur = 0;
            }}

            function gameLoop() {{
                update();
                draw();
                requestAnimationFrame(gameLoop);
            }}

            resetBall('player');
            gameLoop();
        </script>
    </body>
    </html>
    """
    
    return components.html(html_code, height=480, scrolling=False)

# ==========================================
# STREAMLIT USER INTERFACE
# ==========================================

def main():
    st.set_page_config(
        page_title="Retro Ping Pong Arena",
        page_icon="🏓",
        layout="centered"
    )
    
    _init_db()
    
    # Custom Styling
    st.markdown(
        """
        <style>
            .main-title {
                font-size: 2.8rem;
                font-weight: 800;
                background: linear-gradient(90deg, #38bdf8, #818cf8, #f43f5e);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                text-align: center;
                margin-bottom: 0px;
            }
            .subtitle {
                text-align: center;
                color: #94a3b8;
                font-size: 1.1rem;
                margin-bottom: 25px;
            }
            .stMetric {
                background: #1e293b;
                padding: 15px;
                border-radius: 10px;
                border: 1px solid #334155;
            }
        </style>
        <h1 class="main-title">🏓 RETRO PING PONG ARENA</h1>
        <p class="subtitle">Play live against the AI in real time. Use W/S or Arrow Keys (or mobile buttons).</p>
        """,
        unsafe_allow_html=True
    )
    
    # Sidebar Configuration
    with st.sidebar:
        st.header("⚙️ Game Settings")
        player_name = st.text_input("Player Name", value="Champion", max_chars=15)
        difficulty = st.selectbox("AI Difficulty", ["Easy", "Medium", "Hard", "Expert"], index=1)
        target_score = st.slider("Target Score to Win", min_value=3, max_value=21, value=5)
        
        st.markdown("---")
        st.subheader("🛠️ Database Controls")
        if st.button("🗑️ Reset All Game Data", type="secondary", use_container_width=True):
            if PingPongEngine.reset_database():
                st.success("Database cleared successfully!")
                st.rerun()
            else:
                st.error("Failed to reset database.")

    # Session state for tracking last completed match submission
    if "last_submitted" not in st.session_state:
        st.session_state.last_submitted = None

    # Game Area
    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        render_game_canvas(difficulty, target_score, player_name)

    st.markdown("---")
    
    # Leaderboard & Match History
    st.subheader("🏆 Leaderboard & Match History")
    leaderboard_data = PingPongEngine.get_leaderboard()
    
    if leaderboard_data:
        st.dataframe(
            leaderboard_data,
            column_config={
                "id": "ID",
                "player_name": "Player",
                "player_score": "Player Score",
                "ai_score": "AI Score",
                "difficulty": "Difficulty",
                "timestamp": "Match Time"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No matches recorded yet. Play a match to populate the leaderboard!")

    # Quick save helper form if user wants to log score manually or test backend
    with st.expander("📝 Manual Score Log (Testing & Backup)"):
        with st.form("manual_score_form"):
            m_col1, m_col2, m_col3 = st.columns(3)
            with m_col1:
                p_score = st.number_input("Player Score", min_value=0, max_value=21, value=3)
            with m_col2:
                a_score = st.number_input("AI Score", min_value=0, max_value=21, value=5)
            with m_col3:
                m_diff = st.selectbox("Difficulty Level", ["Easy", "Medium", "Hard", "Expert"], index=1)
            
            submit_btn = st.form_submit_button("Save Match to Database")
            if submit_btn:
                success = PingPongEngine.save_match(player_name, p_score, a_score, m_diff)
                if success:
                    st.success("Match successfully recorded!")
                    st.rerun()
                else:
                    st.error("Error saving match.")

if __name__ == "__main__":
    main()