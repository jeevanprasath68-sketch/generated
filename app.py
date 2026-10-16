import sqlite3
import datetime
import json
import streamlit as st
import streamlit.components.v1 as components

DB_NAME = "ping_pong_scores.db"

class GameEngine:
    """Backend business logic for managing high scores and match statistics."""
    
    @staticmethod
    def get_connection():
        return sqlite3.connect(DB_NAME, check_same_thread=False)

    @staticmethod
    def init_db():
        conn = GameEngine.get_connection()
        cursor = conn.cursor()
        
        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_name TEXT NOT NULL,
                player_score INTEGER NOT NULL,
                ai_score INTEGER NOT NULL,
                difficulty TEXT NOT NULL,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        
        # Ensure schema self-healing (check columns)
        cursor.execute("PRAGMA table_info(matches)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "difficulty" not in columns:
            cursor.execute("ALTER TABLE matches ADD COLUMN difficulty TEXT DEFAULT 'Medium'")
            
        conn.commit()
        conn.close()

    @staticmethod
    def save_match(player_name: str, player_score: int, ai_score: int, difficulty: str) -> bool:
        if not player_name or not player_name.strip():
            player_name = "Anonymous"
        try:
            conn = GameEngine.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO matches (player_name, player_score, ai_score, difficulty, played_at) VALUES (?, ?, ?, ?, ?)",
                (player_name.strip(), int(player_score), int(ai_score), difficulty, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Database error: {e}")
            return False

    @staticmethod
    def get_leaderboard(limit: int = 10):
        try:
            GameEngine.init_db()
            conn = GameEngine.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT player_name, player_score, ai_score, difficulty, played_at FROM matches ORDER BY player_score DESC, played_at DESC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            conn.close()
            return rows
        except Exception:
            return []

    @staticmethod
    def clear_database():
        try:
            conn = GameEngine.get_connection()
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS matches")
            conn.commit()
            conn.close()
            GameEngine.init_db()
            return True
        except Exception:
            return False


def render_ping_pong_html(difficulty: str):
    """Generates the complete HTML, CSS, and JS payload for the retro arcade ping pong game."""
    ai_speed_factor = 0.05
    if difficulty == "Easy":
        ai_speed_factor = 0.035
    elif difficulty == "Hard":
        ai_speed_factor = 0.075
    elif difficulty == "Insane":
        ai_speed_factor = 0.1

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Retro Ping Pong</title>
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
            canvas {{
                border: 4px solid #30363d;
                box-shadow: 0 0 20px rgba(88, 166, 255, 0.3);
                background-color: #010409;
                display: block;
            }}
            .score-board {{
                font-size: 24px;
                margin-bottom: 10px;
                letter-spacing: 2px;
                color: #c9d1d9;
            }}
            .instructions {{
                font-size: 14px;
                color: #8b949e;
                margin-top: 10px;
            }}
            .btn {{
                background-color: #238636;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 16px;
                font-family: 'Courier New', Courier, monospace;
                cursor: pointer;
                border-radius: 6px;
                margin-top: 10px;
                box-shadow: 0 4px #2ea043;
                transition: 0.1s;
            }}
            .btn:active {{
                transform: translateY(2px);
                box-shadow: 0 2px #2ea043;
            }}
        </style>
    </head>
    <body>
        <div id="game-container">
            <div class="score-board">
                PLAYER: <span id="pScore">0</span> &nbsp;&nbsp;|&nbsp;&nbsp; AI ({difficulty}): <span id="aiScore">0</span>
            </div>
            <canvas id="pong" width="700" height="400"></canvas>
            <button class="btn" id="startBtn" onclick="startGame()">START MATCH</button>
            <div class="instructions">Use <b>W / S</b> or <b>Arrow Up / Arrow Down</b> to move paddle. First to 5 wins!</div>
        </div>

        <script>
            const canvas = document.getElementById("pong");
            const ctx = canvas.getContext("2d");

            let gameRunning = false;
            let winningScore = 5;

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
                color: "#f85149"
            }};

            const ball = {{
                x: canvas.width / 2,
                y: canvas.height / 2,
                radius: 8,
                speed: 5,
                velocityX: 5,
                velocityY: 5,
                color: "#f0f6fc"
            }};

            let keys = {{}};
            window.addEventListener('keydown', (e) => {{
                keys[e.key] = true;
                if(["ArrowUp","ArrowDown"," ","w","s"].indexOf(e.key) > -1) {{
                    e.preventDefault();
                }} 
            }});
            window.addEventListener('keyup', (e) => {{
                keys[e.key] = false;
            }});

            function drawRect(x, y, w, h, color) {{
                ctx.fillStyle = color;
                ctx.fillRect(x, y, w, h);
            }};

            function drawCircle(x, y, r, color) {{
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.arc(x, y, r, 0, Math.PI * 2, false);
                ctx.closePath();
                ctx.fill();
            }};

            function drawText(text, x, y, color) {{
                ctx.fillStyle = color;
                ctx.font = "50px 'Courier New'";
                ctx.fillText(text, x, y);
            }};

            function drawNet() {{
                for(let i = 0; i <= canvas.height; i += 15) {{
                    drawRect(canvas.width / 2 - 1, i, 2, 10, "#30363d");
                }}
            }};

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
            }};

            function resetBall() {{
                ball.x = canvas.width / 2;
                ball.y = canvas.height / 2;
                ball.speed = 5;
                ball.velocityX = -ball.velocityX;
            }};

            function update() {{
                if (!gameRunning) return;

                // Player movement
                if ((keys['ArrowUp'] || keys['w'] || keys['W']) && player.y > 0) {{
                    player.y -= 7;
                }} else if ((keys['ArrowDown'] || keys['s'] || keys['S']) && player.y < canvas.height - player.height) {{
                    player.y += 7;
                }}

                // AI movement with factor {ai_speed_factor}
                let aiSpeed = {ai_speed_factor} * canvas.height;
                ai.y += (ball.y - (ai.y + ai.height / 2)) * aiSpeed;
                if (ai.y < 0) ai.y = 0;
                if (ai.y > canvas.height - ai.height) ai.y = canvas.height - ai.height;

                // Move ball
                ball.x += ball.velocityX;
                ball.y += ball.velocityY;

                // Ball collision with top/bottom walls
                if (ball.y - ball.radius < 0 || ball.y + ball.radius > canvas.height) {{
                    ball.velocityY = -ball.velocityY;
                }}

                // Determine active paddle for collision
                let activePaddle = (ball.x < canvas.width / 2) ? player : ai;

                if (collision(ball, activePaddle)) {{
                    let collidePoint = ball.y - (activePaddle.y + activePaddle.height / 2);
                    collidePoint = collidePoint / (activePaddle.height / 2);
                    
                    let angleRad = (Math.PI / 4) * collidePoint;
                    let direction = (ball.x < canvas.width / 2) ? 1 : -1;

                    ball.velocityX = direction * ball.speed * Math.cos(angleRad);
                    ball.velocityY = ball.speed * Math.sin(angleRad);

                    ball.speed += 0.3;
                }}

                // Scoring
                if (ball.x - ball.radius < 0) {{
                    ai.score++;
                    document.getElementById("aiScore").innerText = ai.score;
                    checkGameOver();
                    resetBall();
                }} else if (ball.x + ball.radius > canvas.width) {{
                    player.score++;
                    document.getElementById("pScore").innerText = player.score;
                    checkGameOver();
                    resetBall();
                }}
            }};

            function checkGameOver() {{
                if (player.score >= winningScore || ai.score >= winningScore) {{
                    gameRunning = false;
                    let winner = player.score >= winningScore ? "PLAYER WINS!" : "AI WINS!";
                    document.getElementById("startBtn").innerText = "PLAY AGAIN";
                    document.getElementById("startBtn").style.display = "inline-block";
                    
                    console.log("GAMEOVER|" + player.score + "|" + ai.score);
                }}
            }};

            function render() {{
                drawRect(0, 0, canvas.width, canvas.height, "#010409");
                drawNet();
                drawRect(player.x, player.y, player.width, player.height, player.color);
                drawRect(ai.x, ai.y, ai.width, ai.height, ai.color);
                drawCircle(ball.x, ball.y, ball.radius, ball.color);
            }};

            function gameLoop() {{
                update();
                render();
                if (gameRunning) {{
                    requestAnimationFrame(gameLoop);
                }}
            }};

            function startGame() {{
                player.score = 0;
                ai.score = 0;
                document.getElementById("pScore").innerText = "0";
                document.getElementById("aiScore").innerText = "0";
                player.y = canvas.height / 2 - 40;
                ai.y = canvas.height / 2 - 40;
                ball.x = canvas.width / 2;
                ball.y = canvas.height / 2;
                ball.speed = 5;
                ball.velocityX = 5;
                ball.velocityY = 5;
                gameRunning = true;
                document.getElementById("startBtn").style.display = "none";
                gameLoop();
            }};

            render();
        </script>
    </body>
    </html>
    """
    return html_content


def main():
    st.set_page_config(
        page_title="Retro Arcade Ping Pong",
        page_icon="🏓",
        layout="centered"
    )

    GameEngine.init_db()

    st.markdown(
        """
        <div style='text-align: center;'>
            <h1 style='color: #58a6ff; font-family: monospace;'>🏓 RETRO ARCADE PING PONG</h1>
            <p style='color: #8b949e;'>Classic 2D pong with AI opponent, collision physics, and high score tracking.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.sidebar:
        st.header("🕹️ Game Settings")
        difficulty = st.selectbox("AI Difficulty", ["Easy", "Medium", "Hard", "Insane"], index=1)
        player_name = st.text_input("Player Name", value="RetroGamer", max_chars=20)

        st.markdown("---")
        st.header("💾 Match Saver")
        st.info("Record your completed match to the arcade leaderboard!")
        
        with st.form("score_form"):
            p_score_input = st.number_input("Player Score", min_value=0, max_value=20, value=5)
            ai_score_input = st.number_input("AI Score", min_value=0, max_value=20, value=2)
            submit_score = st.form_submit_button("Save Match Score")

            if submit_score:
                success = GameEngine.save_match(player_name, p_score_input, ai_score_input, difficulty)
                if success:
                    st.success(f"Saved score for {player_name}!")
                else:
                    st.error("Failed to save score.")

        st.markdown("---")
        with st.expander("⚙️ Database Maintenance"):
            if st.button("Reset Leaderboard DB", type="secondary"):
                if GameEngine.clear_database():
                    st.success("Database reset successfully!")
                    st.rerun()
                else:
                    st.error("Error resetting database.")

    tab_game, tab_leaderboard = st.tabs(["🎮 Play Game", "🏆 Leaderboard & History"])

    with tab_game:
        st.markdown(f"**Current Mode:** `{difficulty}` difficulty | **Player:** `{player_name}`")
        
        game_html = render_ping_pong_html(difficulty)
        components.html(game_html, height=540, scrolling=False)

        st.markdown("""
            ### How to Play:
            1. Click **START MATCH** inside the game screen.
            2. Use **W / S** keys or **Arrow Up / Arrow Down** keys to control your paddle (Left).
            3. First player to reach **5 points** wins the match!
            4. Use the sidebar form to log your victories into the permanent leaderboard.
        """)

    with tab_leaderboard:
        st.subheader("🏆 Arcade Hall of Fame")
        leaderboard_data = GameEngine.get_leaderboard(limit=15)
        
        if leaderboard_data:
            formatted_data = []
            for row in leaderboard_data:
                formatted_data.append({
                    "Player": row[0],
                    "Player Score": row[1],
                    "AI Score": row[2],
                    "Difficulty": row[3],
                    "Date / Time": row[4]
                })
            st.dataframe(formatted_data, use_container_width=True)
        else:
            st.info("No matches recorded yet. Play a match or record one via the sidebar!")


if __name__ == "__main__":
    main()