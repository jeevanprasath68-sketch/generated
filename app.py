import streamlit as st
import streamlit.components.v1 as components
import sqlite3
import datetime
from typing import Dict, Any, List, Optional

# ==========================================
# BUSINESS LOGIC & DATA ENGINE
# ==========================================

DB_NAME = "ping_pong_scores.db"

def _get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def _init_db() -> None:
    """Initialize database and self-heal missing columns if schema evolves."""
    conn = _get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS match_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_score INTEGER NOT NULL,
            ai_score INTEGER NOT NULL,
            difficulty TEXT NOT NULL,
            winner TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )
    conn.commit()
    
    # Self-healing column check
    cursor.execute("PRAGMA table_info(match_history)")
    columns = [col["name"] for col in cursor.fetchall()]
    if "difficulty" not in columns:
        cursor.execute("ALTER TABLE match_history ADD COLUMN difficulty TEXT DEFAULT 'Medium'")
        conn.commit()
    conn.close()

class GameEngine:
    """Handles business logic for game statistics and rules."""
    
    @staticmethod
    def record_match(player_score: int, ai_score: int, difficulty: str) -> Dict[str, Any]:
        _init_db()
        winner = "Player" if player_score > ai_score else ("AI" if ai_score > player_score else "Tie")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO match_history (player_score, ai_score, difficulty, winner, timestamp) VALUES (?, ?, ?, ?, ?)",
            (player_score, ai_score, difficulty, winner, timestamp)
        )
        conn.commit()
        conn.close()
        return {"player_score": player_score, "ai_score": ai_score, "winner": winner, "timestamp": timestamp}

    @staticmethod
    def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
        _init_db()
        try:
            conn = _get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT player_score, ai_score, difficulty, winner, timestamp FROM match_history ORDER BY id DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except sqlite3.OperationalError:
            _init_db()
            return []

    @staticmethod
    def clear_database() -> None:
        conn = _get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS match_history")
        conn.commit()
        conn.close()
        _init_db()

    @staticmethod
    def calculate_ai_speed(difficulty: str) -> float:
        mapping = {
            "Easy": 0.05,
            "Medium": 0.08,
            "Hard": 0.12,
            "Insane": 0.18
        }
        if difficulty not in mapping:
            raise ValueError(f"Invalid difficulty: {difficulty}")
        return mapping[difficulty]

# ==========================================
# STREAMLIT UI & EMBEDDED RETRO GAME
# ==========================================

def main():
    st.set_page_config(
        page_title="Retro Arcade Ping Pong",
        page_icon="🏓",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    _init_db()

    st.title("🏓 Retro Arcade Ping Pong")
    st.markdown(
        "Welcome to the classic **Ping Pong** arcade! Use your keyboard arrow keys or W/S to control the left paddle. "
        "Defeat the AI opponent and check out your match history below!"
    )

    # Sidebar Configuration
    st.sidebar.header("⚙️ Game Settings")
    difficulty = st.sidebar.selectbox("AI Difficulty", ["Easy", "Medium", "Hard", "Insane"], index=1)
    winning_score = st.sidebar.slider("Winning Score Target", min_value=3, max_value=21, value=5)
    
    st.sidebar.divider()
    st.sidebar.subheader("🛠️ Maintenance")
    if st.sidebar.button("Reset All Game Data", type="secondary"):
        GameEngine.clear_database()
        st.sidebar.success("Database successfully reset!")
        st.rerun()

    # Get AI speed factor
    ai_speed = GameEngine.calculate_ai_speed(difficulty)

    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric(label="Difficulty", value=difficulty)
    with col2:
        st.metric(label="Target", value=winning_score)

    # HTML / CSS / JS Embedded Game Component
    # We pass AI speed and winning score via template strings into the JS engine.
    game_html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Ping Pong Arcade</title>
        <style>
            body {{
                background-color: #0d1117;
                color: #58a6ff;
                font-family: 'Courier New', Courier, monospace;
                text-align: center;
                margin: 0;
                padding: 0;
                overflow: hidden;
            }};
            #game-container {{
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
            }}
            canvas {{
                background: #000000;
                border: 4px solid #30363d;
                box-shadow: 0 0 25px rgba(88, 166, 255, 0.3);
                border-radius: 6px;
            }}
            .ui-panel {{
                margin-top: 10px;
                font-size: 18px;
                font-weight: bold;
            }}
            .btn {{
                background-color: #238636;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 16px;
                font-family: 'Courier New', Courier, monospace;
                border-radius: 4px;
                cursor: pointer;
                margin-top: 10px;
                box-shadow: 0 4px #2ea043;
            }}
            .btn:active {{
                background-color: #2ea043;
                box-shadow: 0 2px #2ea043;
                transform: translateY(2px);
            }}
        </style>
    </head>
    <body>
        <div id="game-container">
            <canvas id="pong" width="750" height="450"></canvas>
            <div class="ui-panel" id="status-text">Press Start to Play! (Controls: W/S or Arrow Keys)</div>
            <button class="btn" id="start-btn" onclick="startGame()">START / RESTART</button>
        </div>

        <script>
            const canvas = document.getElementById("pong");
            const ctx = canvas.getContext("2d");
            const statusText = document.getElementById("status-text");

            const aiSpeedFactor = {ai_speed};
            const targetScore = {winning_score};

            let gameRunning = false;

            // Paddle setup
            const paddleWidth = 12;
            const paddleHeight = 90;

            let player = {{
                x: 10,
                y: canvas.height / 2 - paddleHeight / 2,
                width: paddleWidth,
                height: paddleHeight,
                score: 0,
                color: "#58a6ff"
            }};

            let ai = {{
                x: canvas.width - 22,
                y: canvas.height / 2 - paddleHeight / 2,
                width: paddleWidth,
                height: paddleHeight,
                score: 0,
                color: "#ff7b72"
            }};

            // Ball setup
            let ball = {{
                x: canvas.width / 2,
                y: canvas.height / 2,
                radius: 10,
                speed: 5,
                velocityX: 5,
                velocityY: 5,
                color: "#f0f6fc"
            }};

            // Keyboard tracking
            let keys = {{}};
            window.addEventListener('keydown', (e) => {{
                keys[e.key] = true;
                if(["ArrowUp", "ArrowDown", " ", "w", "s", "W", "S"].includes(e.key)) {{
                    e.preventDefault();
                }};
            }});
            window.addEventListener('keyup', (e) => {{
                keys[e.key] = false;
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

            function drawText(text, x, y, color, font = "20px 'Courier New'") {{
                ctx.fillStyle = color;
                ctx.font = font;
                ctx.fillText(text, x, y);
            }}

            function drawNet() {{
                for (let i = 0; i <= canvas.height; i += 15) {{
                    drawRect(canvas.width / 2 - 1, i, 2, 10, "#30363d");
                }}
            }}

            function resetBall() {{
                ball.x = canvas.width / 2;
                ball.y = canvas.height / 2;
                ball.speed = 5;
                ball.velocityX = -ball.velocityX;
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

            function update() {{
                if (!gameRunning) return;

                // Player movement
                if ((keys['ArrowUp'] || keys['w'] || keys['W']) && player.y > 0) {{
                    player.y -= 7;
                }} else if ((keys['ArrowDown'] || keys['s'] || keys['S']) && player.y < canvas.height - player.height) {{
                    player.y += 7;
                }}

                // AI simple tracking
                let aiTarget = ball.y - (ai.height / 2);
                ai.y += (aiTarget - ai.y) * aiSpeedFactor;
                if (ai.y < 0) ai.y = 0;
                if (ai.y > canvas.height - ai.height) ai.y = canvas.height - ai.height;

                // Move ball
                ball.x += ball.velocityX;
                ball.y += ball.velocityY;

                // Wall collision (top & bottom)
                if (ball.y - ball.radius < 0 || ball.y + ball.radius > canvas.height) {{
                    ball.velocityY = -ball.velocityY;
                }}

                // Determine active paddle for collision
                let activePaddle = (ball.x < canvas.width / 2) ? player : ai;

                if (collision(ball, activePaddle)) {{
                    // Calculate hit point
                    let collidePoint = ball.y - (activePaddle.y + activePaddle.height / 2);
                    collidePoint = collidePoint / (activePaddle.height / 2);

                    let angleRad = (Math.PI / 4) * collidePoint;
                    let direction = (ball.x < canvas.width / 2) ? 1 : -1;

                    ball.velocityX = direction * ball.speed * Math.cos(angleRad);
                    ball.velocityY = ball.speed * Math.sin(angleRad);

                    ball.speed += 0.3; // Incremental speed boost
                }}

                // Scoring
                if (ball.x - ball.radius < 0) {{
                    ai.score++;
                    checkWinCondition();
                }} else if (ball.x + ball.radius > canvas.width) {{
                    player.score++;
                    checkWinCondition();
                }}
            }}

            function checkWinCondition() {{
                if (player.score >= targetScore || ai.score >= targetScore) {{
                    gameRunning = false;
                    let winnerName = player.score >= targetScore ? "PLAYER WINS! 🏆" : "AI WINS! 🤖";
                    statusText.innerHTML = "Game Over! " + winnerName + " Final Score: " + player.score + " - " + ai.score;
                    
                    // Send score back to Streamlit via URL fetch or event simulation if required
                    // For simplicity, we trigger visual notification
                }} else {{
                    resetBall();
                }}
            }}

            function render() {{
                // Clear canvas
                drawRect(0, 0, canvas.width, canvas.height, "#000000");
                drawNet();

                // Draw scores
                drawText(player.score, canvas.width / 4, canvas.height / 5, "#58a6ff", "50px 'Courier New'");
                drawText(ai.score, 3 * canvas.width / 4, canvas.height / 5, "#ff7b72", "50px 'Courier New'");

                // Draw paddles & ball
                drawRect(player.x, player.y, player.width, player.height, player.color);
                drawRect(ai.x, ai.y, ai.width, ai.height, ai.color);
                drawCircle(ball.x, ball.y, ball.radius, ball.color);
            }}

            function gameLoop() {{
                update();
                render();
                if (gameRunning) {{
                    requestAnimationFrame(gameLoop);
                }}
            }}

            function startGame() {{
                player.score = 0;
                ai.score = 0;
                player.y = canvas.height / 2 - paddleHeight / 2;
                ai.y = canvas.height / 2 - paddleHeight / 2;
                resetBall();
                gameRunning = true;
                statusText.innerHTML = "Match in progress... Good luck!";
                gameLoop();
            }}

            // Initial render
            render();
        </script>
    </body>
    </html>
    """

    components.html(game_html, height=580, scrolling=False)

    # Match Logging Section
    st.divider()
    st.subheader("📝 Manual Match Log & History")
    st.markdown("Log completed match results here to track your lifetime arcade stats against the AI!")

    with st.form("match_log_form"):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            p_score_input = st.number_input("Your Score", min_value=0, max_value=30, value=5)
        with col_f2:
            ai_score_input = st.number_input("AI Score", min_value=0, max_value=30, value=2)
        with col_f3:
            diff_input = st.selectbox("Recorded Difficulty", ["Easy", "Medium", "Hard", "Insane"], index=1)
        
        submit_match = st.form_submit_button("Save Match Result")
        if submit_match:
            res = GameEngine.record_match(p_score_input, ai_score_input, diff_input)
            st.success(f"Match saved successfully! Winner: {res['winner']} ({res['player_score']} - {res['ai_score']})")

    # Display Match History
    st.subheader("📊 Recent Match Leaderboard")
    history = GameEngine.get_leaderboard(limit=10)
    if history:
        st.dataframe(history, use_container_width=True)
    else:
        st.info(
            "No match history recorded yet. Play a match or record one above to build your arcade legacy!"
        )

if __name__ == '__main__':
    main()