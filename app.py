import sqlite3
import streamlit as st
import streamlit.components.v1 as components
import datetime
from typing import List, Dict, Any, Tuple

DB_FILE = "puzzle_game_leaderboard.db"

class GameConfig:
    DIFFICULTIES = {
        "Casual": {"grid_size": 3, "time_limit": 120, "score_multiplier": 1.0},
        "Standard": {"grid_size": 4, "time_limit": 90, "score_multiplier": 1.5},
        "Pro": {"grid_size": 5, "time_limit": 60, "score_multiplier": 2.2},
        "Impossible": {"grid_size": 6, "time_limit": 45, "score_multiplier": 3.5}
    }

    @classmethod
    def get_settings(cls, difficulty: str) -> Dict[str, Any]:
        return cls.DIFFICULTIES.get(difficulty, cls.DIFFICULTIES["Standard"])


class LeaderboardDB:
    def __init__(self, db_path: str = DB_FILE):
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    difficulty TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            self._migrate_table(cursor)

    def _migrate_table(self, cursor: sqlite3.Cursor):
        cursor.execute("PRAGMA table_info(scores)")
        columns = [col[1] for col in cursor.fetchall()]
        if "created_at" not in columns:
            cursor.execute("ALTER TABLE scores ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            cursor.connection.commit()

    def add_score(self, player_name: str, score: int, difficulty: str) -> bool:
        if not player_name or score < 0:
            return False
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO scores (player_name, score, difficulty, created_at) VALUES (?, ?, ?, ?)",
                (player_name.strip()[:20], int(score), difficulty, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()
        return True

    def get_top_scores(self, limit: int = 10) -> List[Dict[str, Any]]:
        self.init_db()
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT player_name, score, difficulty, created_at FROM scores ORDER BY score DESC LIMIT ?",
                    (limit,)
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.OperationalError:
            self.init_db()
            return []

    def get_stats(self) -> Dict[str, Any]:
        self.init_db()
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*), MAX(score), AVG(score) FROM scores")
                row = cursor.fetchone()
                total_games = row[0] or 0
                high_score = row[1] or 0
                avg_score = round(row[2] or 0, 1)
                return {"total_games": total_games, "high_score": high_score, "avg_score": avg_score}
        except sqlite3.OperationalError:
            return {"total_games": 0, "high_score": 0, "avg_score": 0}

    def reset_leaderboard(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS scores")
            conn.commit()
        self.init_db()


def get_game_html(difficulty: str, settings: Dict[str, Any]) -> str:
    grid_size = settings["grid_size"]
    time_limit = settings["time_limit"]
    multiplier = settings["score_multiplier"]

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Neon Slide Puzzle</title>
    <style>
        body {{
            margin: 0;
            background: #060814;
            font-family: 'Courier New', Courier, monospace;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            overflow: hidden;
            color: #00f3ff;
        }} 
        #canvas-container {{
            position: relative;
            box-shadow: 0 0 30px rgba(0, 243, 255, 0.3);
            border: 2px solid #00f3ff;
            border-radius: 12px;
            background: #0a0e1a;
        }} 
        canvas {{
            display: block;
            cursor: pointer;
        }}
    </style>
</head>
<body>
    <div id="canvas-container">
        <canvas id="gameCanvas" width="600" height="600"></canvas>
    </div>
    <script>
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');

        const GRID_SIZE = __GRID_SIZE__;
        const TIME_LIMIT = __TIME_LIMIT__;
        const MULTIPLIER = __MULTIPLIER__;
        const TILE_SIZE = Math.floor(400 / GRID_SIZE);
        const OFFSET_X = (600 - (GRID_SIZE * TILE_SIZE)) / 2;
        const OFFSET_Y = 120;

        const AudioEngine = {{
            ctx: null,
            muted: false,
            init() {{
                if (!this.ctx) {{
                    const AC = window.AudioContext || window.webkitAudioContext;
                    if (AC) this.ctx = new AC();
                }}
                if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume();
            }},
            playTone(freq, type, duration, endFreq) {{
                if (this.muted) return;
                try {{
                    this.init();
                    if (!this.ctx) return;
                    const osc = this.ctx.createOscillator();
                    const gain = this.ctx.createGain();
                    osc.type = type || 'sine';
                    osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
                    if (endFreq) osc.frequency.exponentialRampToValueAtTime(endFreq, this.ctx.currentTime + duration);
                    gain.gain.setValueAtTime(0.15, this.ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);
                    osc.connect(gain);
                    gain.connect(this.ctx.destination);
                    osc.start();
                    osc.stop(this.ctx.currentTime + duration);
                }} catch(e) {{}}
            }},
            slide() {{ this.playTone(420, 'square', 0.06, 260); }},
            score() {{ this.playTone(523, 'sine', 0.1); setTimeout(() => this.playTone(659, 'sine', 0.15), 80); }},
            win() {{ this.playTone(440, 'triangle', 0.1, 880); }},
            gameOver() {{ this.playTone(330, 'sawtooth', 0.25, 120); }}
        }};

        let gameState = 'START'; // START, PLAYING, PAUSED, GAMEOVER, VICTORY
        let score = 0;
        let moves = 0;
        let timeLeft = TIME_LIMIT;
        let timerInterval = null;
        let board = [];
        let emptyCell = {{ r: GRID_SIZE - 1, c: GRID_SIZE - 1 }};
        let particles = [];
        let stars = [];

        for (let i = 0; i < 40; i++) {{
            stars.push({{
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                size: Math.random() * 2 + 1,
                speed: Math.random() * 0.5 + 0.2
            }});
        }}

        function initBoard() {{
            board = [];
            let count = 1;
            for (let r = 0; r < GRID_SIZE; r++) {{
                let row = [];
                for (let c = 0; c < GRID_SIZE; c++) {{
                    row.push(count++);
                }}
                board.push(row);
            }}
            board[GRID_SIZE - 1][GRID_SIZE - 1] = 0;
            emptyCell = {{ r: GRID_SIZE - 1, c: GRID_SIZE - 1 }};
            
            // Shuffle valid moves
            let shuffleMoves = GRID_SIZE * GRID_SIZE * 20;
            for (let i = 0; i < shuffleMoves; i++) {{
                let neighbors = getNeighbors(emptyCell.r, emptyCell.c);
                let randN = neighbors[Math.floor(Math.random() * neighbors.length)];
                board[emptyCell.r][emptyCell.c] = board[randN.r][randN.c];
                board[randN.r][randN.c] = 0;
                emptyCell = randN;
            }}
            moves = 0;
        }}

        function getNeighbors(r, c) {{
            let res = [];
            if (r > 0) res.push({{ r: r - 1, c: c }});
            if (r < GRID_SIZE - 1) res.push({{ r: r + 1, c: c }});
            if (c > 0) res.push({{ r: r, c: c - 1 }});
            if (c < GRID_SIZE - 1) res.push({{ r: r, c: c + 1 }});
            return res;
        }}

        function checkWin() {{
            let count = 1;
            for (let r = 0; r < GRID_SIZE; r++) {{
                for (let c = 0; c < GRID_SIZE; c++) {{
                    if (r === GRID_SIZE - 1 && c === GRID_SIZE - 1) {{
                        if (board[r][c] !== 0) return false;
                    }} else {{
                        if (board[r][c] !== count++) return false;
                    }}
                }}
            }}
            return true;
        }}

        function addParticles(x, y, color) {{
            for (let i = 0; i < 15; i++) {{
                let angle = Math.random() * Math.PI * 2;
                let speed = Math.random() * 4 + 1;
                particles.push({{
                    x: x,
                    y: y,
                    vx: Math.cos(angle) * speed,
                    vy: Math.sin(angle) * speed,
                    alpha: 1.0,
                    color: color,
                    size: Math.random() * 4 + 2
                }});
            }}
        }}

        function startGame() {{
            initBoard();
            score = 0;
            timeLeft = TIME_LIMIT;
            gameState = 'PLAYING';
            if (timerInterval) clearInterval(timerInterval);
            timerInterval = setInterval(() => {{
                if (gameState === 'PLAYING') {{
                    timeLeft--;
                    if (timeLeft <= 0) {{
                        timeLeft = 0;
                        gameState = 'GAMEOVER';
                        AudioEngine.gameOver();
                        clearInterval(timerInterval);
                        notifyStreamlitScore(0);
                    }}
                }}
            }}, 1000);
        }}

        function notifyStreamlitScore(finalScore) {{
            try {{
                window.parent.postMessage({{
                    type: 'streamlit:setComponentValue',
                    value: {{ score: finalScore, status: gameState, difficulty: '__DIFFICULTY__' }}
                }}, '*');
            }} catch(e) {{}}
        }}

        canvas.addEventListener('click', (e) => {{
            AudioEngine.init();
            const rect = canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            if (gameState === 'START' || gameState === 'GAMEOVER' || gameState === 'VICTORY') {{
                // Check click on start button
                if (x >= 200 && x <= 400 && y >= 380 && y <= 450) {{
                    startGame();
                    AudioEngine.score();
                }}
                return;
            }}

            if (gameState === 'PLAYING') {{
                if (x >= OFFSET_X && x <= OFFSET_X + GRID_SIZE * TILE_SIZE &&
                    y >= OFFSET_Y && y <= OFFSET_Y + GRID_SIZE * TILE_SIZE) {{
                    let c = Math.floor((x - OFFSET_X) / TILE_SIZE);
                    let r = Math.floor((y - OFFSET_Y) / TILE_SIZE);

                    let neighbors = getNeighbors(emptyCell.r, emptyCell.c);
                    let clickedNeighbor = neighbors.find(n => n.r === r && n.c === c);

                    if (clickedNeighbor) {{
                        board[emptyCell.r][emptyCell.c] = board[r][c];
                        board[r][c] = 0;
                        emptyCell = {{ r: r, c: c }};
                        moves++;
                        AudioEngine.slide();
                        addParticles(OFFSET_X + c * TILE_SIZE + TILE_SIZE/2, OFFSET_Y + r * TILE_SIZE + TILE_SIZE/2, '#00f3ff');

                        if (checkWin()) {{
                            gameState = 'VICTORY';
                            AudioEngine.win();
                            clearInterval(timerInterval);
                            let bonus = Math.max(100, timeLeft * 10) * MULTIPLIER;
                            score = Math.floor(1000 + bonus - (moves * 5));
                            if (score < 100) score = 100;
                            addParticles(300, 300, '#ffe600');
                            notifyStreamlitScore(score);
                        }}
                    }}
                }}
            }}
        }});

        window.addEventListener('keydown', (e) => {{
            if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', ' '].includes(e.key)) {{
                e.preventDefault();
            }}
            AudioEngine.init();
            if (gameState === 'PLAYING') {{
                let tr = emptyCell.r;
                let tc = emptyCell.c;
                if (e.key === 'ArrowUp' || e.key === 'w') tr++;
                if (e.key === 'ArrowDown' || e.key === 's') tr--;
                if (e.key === 'ArrowLeft' || e.key === 'a') tc++;
                if (e.key === 'ArrowRight' || e.key === 'd') tc--;

                if (tr >= 0 && tr < GRID_SIZE && tc >= 0 && tc < GRID_SIZE) {{
                    board[emptyCell.r][emptyCell.c] = board[tr][tc];
                    board[tr][tc] = 0;
                    emptyCell = {{ r: tr, c: tc }};
                    moves++;
                    AudioEngine.slide();
                    if (checkWin()) {{
                        gameState = 'VICTORY';
                        AudioEngine.win();
                        clearInterval(timerInterval);
                        let bonus = Math.max(100, timeLeft * 10) * MULTIPLIER;
                        score = Math.floor(1000 + bonus - (moves * 5));
                        if (score < 100) score = 100;
                        notifyStreamlitScore(score);
                    }}
                }}
            }} else if (e.key === ' ' || e.key === 'Enter') {{
                if (gameState === 'START' || gameState === 'GAMEOVER' || gameState === 'VICTORY') {{
                    startGame();
                }}
            }}
        }});

        function update() {{
            for (let s of stars) {{
                s.y += s.speed;
                if (s.y > canvas.height) s.y = 0;
            }}
            for (let i = particles.length - 1; i >= 0; i--) {{
                let p = particles[i];
                p.x += p.vx;
                p.y += p.vy;
                p.alpha -= 0.03;
                if (p.alpha <= 0) particles.splice(i, 1);
            }}
        }}

        function draw() {{
            ctx.fillStyle = '#060814';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Stars
            ctx.fillStyle = '#ffffff';
            for (let s of stars) {{
                ctx.globalAlpha = 0.5;
                ctx.fillRect(s.x, s.y, s.size, s.size);
            }}
            ctx.globalAlpha = 1.0;

            // HUD
            ctx.font = 'bold 20px "Courier New", monospace';
            ctx.fillStyle = '#00f3ff';
            ctx.shadowBlur = 10;
            ctx.shadowColor = '#00f3ff';
            ctx.fillText("MODE: " + '__DIFFICULTY__'.toUpperCase(), 30, 40);
            ctx.fillText("MOVES: " + moves, 30, 75);
            ctx.fillText("TIME: " + timeLeft + "s", 450, 40);
            ctx.shadowBlur = 0;

            if (gameState === 'START') {{
                ctx.fillStyle = '#ff007f';
                ctx.shadowBlur = 15;
                ctx.shadowColor = '#ff007f';
                ctx.font = 'bold 36px "Courier New", monospace';
                ctx.textAlign = 'center';
                ctx.fillText("NEON SLIDE PUZZLE", canvas.width / 2, 180);

                ctx.fillStyle = '#00f3ff';
                ctx.font = '16px "Courier New", monospace';
                ctx.fillText("Slide tiles into numerical order (1 to N²-1)", canvas.width / 2, 230);
                ctx.fillText("Use Mouse Clicks or Arrow Keys / WASD", canvas.width / 2, 260);

                // Button
                ctx.fillStyle = '#0a0e1a';
                ctx.strokeStyle = '#00ff66';
                ctx.lineWidth = 3;
                ctx.shadowBlur = 12;
                ctx.shadowColor = '#00ff66';
                ctx.fillRect(200, 380, 200, 60);
                ctx.strokeRect(200, 380, 200, 60);

                ctx.fillStyle = '#00ff66';
                ctx.font = 'bold 22px "Courier New", monospace';
                ctx.fillText("START GAME", canvas.width / 2, 418);
                ctx.textAlign = 'left';
                ctx.shadowBlur = 0;

            }} else if (gameState === 'PLAYING' || gameState === 'PAUSED') {{
                // Draw board
                for (let r = 0; r < GRID_SIZE; r++) {{
                    for (let c = 0; c < GRID_SIZE; c++) {{
                        let val = board[r][c];
                        let tx = OFFSET_X + c * TILE_SIZE;
                        let ty = OFFSET_Y + r * TILE_SIZE;

                        if (val !== 0) {{
                            ctx.fillStyle = '#101830';
                            ctx.strokeStyle = '#00f3ff';
                            ctx.lineWidth = 2;
                            ctx.shadowBlur = 8;
                            ctx.shadowColor = '#00f3ff';
                            ctx.fillRect(tx + 4, ty + 4, TILE_SIZE - 8, TILE_SIZE - 8);
                            ctx.strokeRect(tx + 4, ty + 4, TILE_SIZE - 8, TILE_SIZE - 8);

                            ctx.fillStyle = '#ffffff';
                            ctx.font = 'bold ' + Math.floor(TILE_SIZE * 0.4) + 'px "Courier New", monospace';
                            ctx.textAlign = 'center';
                            ctx.textBaseline = 'middle';
                            ctx.fillText(val, tx + TILE_SIZE / 2, ty + TILE_SIZE / 2);
                            ctx.textAlign = 'left';
                            ctx.textBaseline = 'alphabetic';
                            ctx.shadowBlur = 0;
                        }} else {{
                            ctx.fillStyle = '#04060d';
                            ctx.fillRect(tx + 4, ty + 4, TILE_SIZE - 8, TILE_SIZE - 8);
                        }}
                    }}
                }}

            }} else if (gameState === 'GAMEOVER' || gameState === 'VICTORY') {{
                ctx.fillStyle = 'rgba(6, 8, 20, 0.85)';
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                ctx.textAlign = 'center';
                ctx.shadowBlur = 20;
                if (gameState === 'VICTORY') {{
                    ctx.fillStyle = '#00ff66';
                    ctx.shadowColor = '#00ff66';
                    ctx.font = 'bold 36px "Courier New", monospace';
                    ctx.fillText("VICTORY!", canvas.width / 2, 200);

                    ctx.fillStyle = '#ffffff';
                    ctx.font = '22px "Courier New", monospace';
                    ctx.fillText("Final Score: " + score, canvas.width / 2, 260);
                    ctx.fillText("Moves: " + moves + " | Time Left: " + timeLeft + "s", canvas.width / 2, 300);
                }} else {{
                    ctx.fillStyle = '#ff007f';
                    ctx.shadowColor = '#ff007f';
                    ctx.font = 'bold 36px "Courier New", monospace';
                    ctx.fillText("TIME'S UP!", canvas.width / 2, 200);

                    ctx.fillStyle = '#ffffff';
                    ctx.font = '22px "Courier New", monospace';
                    ctx.fillText("Better luck next time!", canvas.width / 2, 260);
                }}
                ctx.shadowBlur = 0;

                // Play Again Button
                ctx.fillStyle = '#0a0e1a';
                ctx.strokeStyle = '#00f3ff';
                ctx.lineWidth = 3;
                ctx.shadowBlur = 12;
                ctx.shadowColor = '#00f3ff';
                ctx.fillRect(200, 380, 200, 60);
                ctx.strokeRect(200, 380, 200, 60);

                ctx.fillStyle = '#00f3ff';
                ctx.font = 'bold 20px "Courier New", monospace';
                ctx.fillText("PLAY AGAIN", canvas.width / 2, 417);
                ctx.textAlign = 'left';
                ctx.shadowBlur = 0;
            }}

            // Particles
            for (let p of particles) {{
                ctx.save();
                ctx.globalAlpha = p.alpha;
                ctx.fillStyle = p.color;
                ctx.shadowBlur = 10;
                ctx.shadowColor = p.color;
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                ctx.fill();
                ctx.restore();
            }}
        }}

        function loop() {{
            update();
            draw();
            requestAnimationFrame(loop);
        }}

        requestAnimationFrame(loop);
    </script>
</body>
</html>
""".replace("__GRID_SIZE__", str(grid_size)).replace("__TIME_LIMIT__", str(time_limit)).replace("__MULTIPLIER__", str(multiplier)).replace("__DIFFICULTY__", difficulty)


def main():
    st.set_page_config(
        page_title="Neon Slide & Match Puzzle",
        page_icon="🧩",
        layout="centered"
    )

    db = LeaderboardDB()

    st.sidebar.title("🧩 Arcade Settings")
    difficulty = st.sidebar.selectbox("Select Difficulty", list(GameConfig.DIFFICULTIES.keys()), index=1)
    settings = GameConfig.get_settings(difficulty)

    st.sidebar.markdown("---")
    st.sidebar.subheader("Database Manager")
    if st.sidebar.button("Reset Leaderboard DB"):
        db.reset_leaderboard()
        st.sidebar.success("Leaderboard wiped clean!")
        st.rerun()

    st.title("⚡ NEON SLIDE PUZZLE ⚡")
    st.markdown(f"*Cyberpunk 15-Puzzle Arcade Experience ({difficulty} Mode)*")

    # Render HTML Game Component
    game_html = get_game_html(difficulty, settings)
    components.html(game_html, height=640, scrolling=False)

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏆 Submit Your Score")
        stats = db.get_stats()
        with st.form("score_form"):
            player_name = st.text_input("Player Handle", max_chars=20, placeholder="CyberGamer99")
            reported_score = st.number_input("Final Score (from game victory)", min_value=0, value=0, step=10)
            submit_btn = st.form_submit_button("Record to Global Leaderboard")

            if submit_btn:
                if db.add_score(player_name, reported_score, difficulty):
                    st.success(f"Score {reported_score} successfully recorded for {player_name}!")
                    st.rerun()
                else:
                    st.error("Please provide a valid player handle and score.")

    with col2:
        st.subheader("📊 Arcade Statistics")
        st.metric("Total Games Played", stats["total_games"])
        st.metric("All-Time High Score", stats["high_score"])
        st.metric("Average Score", stats["avg_score"])

    st.markdown("---")
    st.subheader("🌟 Global Neon Leaderboard")
    top_scores = db.get_top_scores(10)
    if top_scores:
        st.dataframe(
            top_scores,
            column_config={
                "player_name": "Player",
                "score": "Score",
                "difficulty": "Difficulty",
                "created_at": "Timestamp"
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("No high scores recorded yet. Be the first on the grid!")


if __name__ == '__main__':
    main()