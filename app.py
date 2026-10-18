"""
Cyberpunk Neon Snake Arcade Game & Streamlit Web App
"""

import sqlite3
import os
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components

DB_PATH = "snake_leaderboard.db"

class GameConfig:
    """Manages game configurations, speeds, and score multipliers."""
    DIFFICULTIES = {
        "Casual": {"speed": 1.0, "multiplier": 1.0, "wall_collision": False},
        "Standard": {"speed": 1.3, "multiplier": 1.5, "wall_collision": True},
        "Pro": {"speed": 1.7, "multiplier": 2.5, "wall_collision": True},
        "Impossible": {"speed": 2.2, "multiplier": 4.0, "wall_collision": True}
    }

    @staticmethod
    def get_difficulty(name: str) -> dict:
        return GameConfig.DIFFICULTIES.get(name, GameConfig.DIFFICULTIES["Standard"])


class LeaderboardDB:
    """Resilient SQLite database manager for high scores with auto-schema healing."""
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    player_name TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    difficulty TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            conn.commit()
            self._inspect_and_heal(conn)

    def _inspect_and_heal(self, conn):
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(scores)")
        columns = {row["name"] for row in cursor.fetchall()}
        required = {"id", "player_name", "score", "difficulty", "created_at"}
        for col in required:
            if col not in columns:
                if col == "difficulty":
                    cursor.execute("ALTER TABLE scores ADD COLUMN difficulty TEXT DEFAULT 'Standard'")
                elif col == "created_at":
                    cursor.execute("ALTER TABLE scores ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                conn.commit()

    def add_score(self, player_name: str, score: int, difficulty: str) -> int:
        if not player_name.strip():
            player_name = "Anonymous Cyber-Runner"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO scores (player_name, score, difficulty) VALUES (?, ?, ?)",
                (player_name.strip()[:30], int(score), difficulty)
            )
            conn.commit()
            return cursor.lastrowid

    def get_top_scores(self, limit: int = 10) -> list:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT player_name, score, difficulty, created_at FROM scores ORDER BY score DESC LIMIT ?",
                    (limit,)
                )
                return [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            self.init_db()
            return []

    def get_stats(self) -> dict:
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*), MAX(score), AVG(score) FROM scores")
                row = cursor.fetchone()
                if row and row[0] > 0:
                    return {"total_games": row[0], "max_score": row[1] or 0, "avg_score": int(row[2] or 0)}
        except sqlite3.OperationalError:
            self.init_db()
        return {"total_games": 0, "max_score": 0, "avg_score": 0}

    def reset_database(self):
        with self.get_connection() as conn:
            conn.execute("DROP TABLE IF EXISTS scores")
            conn.commit()
        self.init_db()


# HTML5 Game Canvas Component
GAME_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Cyberpunk Neon Snake</title>
    <style>
        body {
            margin: 0;
            padding: 0;
            background: #060814;
            color: #00f3ff;
            font-family: 'Courier New', Courier, monospace;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            height: 100vh;
        }
        #game-container {
            position: relative;
            box-shadow: 0 0 25px rgba(0, 243, 255, 0.3);
            border: 2px solid #00f3ff;
            border-radius: 8px;
            background: #0a0e1a;
        } 
        canvas {
            display: block;
            background: #0a0e1a;
        }
        .hud {
            position: absolute;
            top: 10px;
            left: 15px;
            right: 15px;
            display: flex;
            justify-content: space-between;
            font-size: 14px;
            font-weight: bold;
            pointer-events: none;
            text-shadow: 0 0 8px #00f3ff;
            letter-spacing: 1px;
        }
        #mute-btn {
            position: absolute;
            bottom: 12px;
            right: 15px;
            background: rgba(10, 14, 26, 0.8);
            border: 1px solid #ff007f;
            color: #ff007f;
            padding: 5px 12px;
            font-family: 'Courier New', Courier, monospace;
            font-weight: bold;
            cursor: pointer;
            border-radius: 4px;
            box-shadow: 0 0 8px rgba(255, 0, 127, 0.4);
            transition: all 0.2s;
            z-index: 10;
        }
        #mute-btn:hover {
            background: #ff007f;
            color: #060814;
            box-shadow: 0 0 15px #ff007f;
        }
    </style>
</head>
<body>
    <div id="game-container">
        <div class="hud">
            <div id="hud-score">SCORE: 0</div>
            <div id="hud-combo">COMBO: x1</div>
            <div id="hud-hi">HI: __HIGH_SCORE__</div>
        </div>
        <canvas id="cvs" width="720" height="520"></canvas>
        <button id="mute-btn">AUDIO: ON</button>
    </div>

    <script>
        const canvas = document.getElementById('cvs');
        const ctx = canvas.getContext('2d');
        const muteBtn = document.getElementById('mute-btn');

        const CONFIG_SPEED = __CONFIG_SPEED__;
        const CONFIG_MULTIPLIER = __CONFIG_MULTIPLIER__;
        const CONFIG_WALL = __CONFIG_WALL__;

        // Web Audio Synthesizer
        const AudioEngine = {
            ctx: null,
            muted: false,
            init() {
                if (!this.ctx) {
                    const AC = window.AudioContext || window.webkitAudioContext;
                    if (AC) this.ctx = new AC();
                }
                if (this.ctx && this.ctx.state === 'suspended') {
                    this.ctx.resume();
                }
            },
            playTone(freq, type, duration, endFreq) {
                if (this.muted) return;
                try {
                    this.init();
                    if (!this.ctx) return;
                    const osc = this.ctx.createOscillator();
                    const gain = this.ctx.createGain();
                    osc.type = type || 'sine';
                    osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
                    if (endFreq) osc.frequency.exponentialRampToValueAtTime(endFreq, this.ctx.currentTime + duration);
                    gain.gain.setValueAtTime(0.12, this.ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.001, this.ctx.currentTime + duration);
                    osc.connect(gain);
                    gain.connect(this.ctx.destination);
                    osc.start();
                    osc.stop(this.ctx.currentTime + duration);
                } catch(e) {}
            },
            eat() { this.playTone(523, 'sine', 0.08); setTimeout(() => this.playTone(784, 'sine', 0.12), 60); },
            turn() { this.playTone(220, 'triangle', 0.04, 150); },
            crash() { this.playTone(150, 'sawtooth', 0.3, 50); },
            combo() { this.playTone(880, 'sine', 0.15, 1200); }
        };

        muteBtn.addEventListener('click', () => {
            AudioEngine.muted = !AudioEngine.muted;
            muteBtn.innerText = AudioEngine.muted ? "AUDIO: OFF" : "AUDIO: ON";
            muteBtn.style.borderColor = AudioEngine.muted ? "#666" : "#ff007f";
            muteBtn.style.color = AudioEngine.muted ? "#666" : "#ff007f";
        });

        // Game States: 0=START, 1=PLAYING, 2=PAUSED, 3=GAMEOVER
        let gameState = 0;
        let score = 0;
        let highScore = __HIGH_SCORE__;
        let combo = 1;
        let comboTimer = 0;

        const gridSize = 20;
        const cols = canvas.width / gridSize;
        const rows = canvas.height / gridSize;

        let snake = [];
        let dx = 1;
        let dy = 0;
        let nextDx = 1;
        let nextDy = 0;
        let food = { x: 5, y: 5, type: 'normal', color: '#00ff66', points: 10 };
        let particles = [];
        let gridOffset = 0;
        let shakeTimer = 0;
        let shakeIntensity = 0;
        let stepInterval = 110 / CONFIG_SPEED;
        let stepAccumulator = 0;
        let lastTime = performance.now();

        function initGame() {
            snake = [
                { x: 10, y: 12 },
                { x: 9, y: 12 },
                { x: 8, y: 12 }
            ];
            dx = 1; dy = 0;
            nextDx = 1; nextDy = 0;
            score = 0;
            combo = 1;
            comboTimer = 0;
            spawnFood();
            particles = [];
        }

        function spawnFood() {
            let valid = false;
            let fx, fy;
            while (!valid) {
                fx = Math.floor(Math.random() * cols);
                fy = Math.floor(Math.random() * rows);
                valid = true;
                for (let seg of snake) {
                    if (seg.x === fx && seg.y === fy) {
                        valid = false;
                        break;
                    }
                }
            }
            const rand = Math.random();
            let ftype = 'normal';
            let fcolor = '#00ff66';
            let fpts = 10;
            if (rand < 0.15) {
                ftype = 'golden';
                fcolor = '#ffe600';
                fpts = 50;
            } else if (rand < 0.35) {
                ftype = 'plasma';
                fcolor = '#ff007f';
                fpts = 25;
            }
            food = { x: fx, y: fy, type: ftype, color: fcolor, points: fpts };
        }

        function addParticles(x, y, color, count = 15) {
            const px = x * gridSize + gridSize / 2;
            const py = y * gridSize + gridSize / 2;
            for (let i = 0; i < count; i++) {
                const angle = Math.random() * Math.PI * 2;
                const speed = 2 + Math.random() * 5;
                particles.push({
                    x: px,
                    y: py,
                    vx: Math.cos(angle) * speed,
                    vy: Math.sin(angle) * speed,
                    alpha: 1.0,
                    decay: 0.02 + Math.random() * 0.03,
                    color: color,
                    size: 2 + Math.random() * 3
                });
            }
        }

        function triggerShake(intensity = 6, duration = 0.25) {
            shakeIntensity = intensity;
            shakeTimer = duration;
        }

        // Keyboard Input
        window.addEventListener('keydown', e => {
            AudioEngine.init();
            if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " "].includes(e.key)) {
                e.preventDefault();
            }

            if (e.key === ' ' || e.key === 'Enter') {
                if (gameState === 0 || gameState === 3) {
                    initGame();
                    gameState = 1;
                } else if (gameState === 2) {
                    gameState = 1;
                }
            } else if (e.key === 'p' || e.key === 'P') {
                if (gameState === 1) gameState = 2;
                else if (gameState === 2) gameState = 1;
            }

            if (gameState !== 1) return;

            if ((e.key === 'ArrowUp' || e.key === 'w' || e.key === 'W') && dy === 0) {
                nextDx = 0; nextDy = -1; AudioEngine.turn();
            } else if ((e.key === 'ArrowDown' || e.key === 's' || e.key === 'S') && dy === 0) {
                nextDx = 0; nextDy = 1; AudioEngine.turn();
            } else if ((e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') && dx === 0) {
                nextDx = -1; nextDy = 0; AudioEngine.turn();
            } else if ((e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') && dx === 0) {
                nextDx = 1; nextDy = 0; AudioEngine.turn();
            }
        });

        // Mouse / Touch click handler
        canvas.addEventListener('click', () => {
            AudioEngine.init();
            if (gameState === 0 || gameState === 3) {
                initGame();
                gameState = 1;
            } else if (gameState === 2) {
                gameState = 1;
            }
        });

        function updateGame(dt) {
            if (gameState !== 1) return;

            // Combo countdown
            if (comboTimer > 0) {
                comboTimer -= dt;
                if (comboTimer <= 0) {
                    combo = 1;
                }
            }

            // Shake timer
            if (shakeTimer > 0) {
                shakeTimer -= dt;
            }

            gridOffset = (gridOffset + dt * 20) % gridSize;

            stepAccumulator += dt * 1000;
            if (stepAccumulator >= stepInterval) {
                stepAccumulator = 0;
                dx = nextDx;
                dy = nextDy;

                const head = { x: snake[0].x + dx, y: snake[0].y + dy };

                // Wall Collision
                if (head.x < 0 || head.x >= cols || head.y < 0 || head.y >= rows) {
                    if (CONFIG_WALL) {
                        AudioEngine.crash();
                        triggerShake(10, 0.4);
                        addParticles(snake[0].x, snake[0].y, '#ff007f', 30);
                        gameState = 3;
                        return;
                    } else {
                        // Wrap around
                        if (head.x < 0) head.x = cols - 1;
                        if (head.x >= cols) head.x = 0;
                        if (head.y < 0) head.y = rows - 1;
                        if (head.y >= rows) head.y = 0;
                    }
                }

                // Self collision
                for (let seg of snake) {
                    if (seg.x === head.x && seg.y === head.y) {
                        AudioEngine.crash();
                        triggerShake(10, 0.4);
                        addParticles(head.x, head.y, '#ff007f', 30);
                        gameState = 3;
                        return;
                    }
                }

                snake.unshift(head);

                // Food eaten
                if (head.x === food.x && head.y === food.y) {
                    AudioEngine.eat();
                    if (combo > 1) AudioEngine.combo();
                    addParticles(food.x, food.y, food.color, 20);
                    
                    score += Math.round(food.points * combo * CONFIG_MULTIPLIER);
                    if (score > highScore) {
                        highScore = score;
                    }
                    combo++;
                    comboTimer = 4.0; // 4 second combo window
                    spawnFood();
                } else {
                    snake.pop();
                }
            }

            // Update particles
            for (let i = particles.length - 1; i >= 0; i--) {
                let p = particles[i];
                p.x += p.vx;
                p.y += p.vy;
                p.alpha -= p.decay;
                if (p.alpha <= 0) {
                    particles.splice(i, 1);
                }
            }
        }

        function draw() {
            ctx.save();
            if (shakeTimer > 0) {
                const sx = (Math.random() - 0.5) * shakeIntensity;
                const sy = (Math.random() - 0.5) * shakeIntensity;
                ctx.translate(sx, sy);
            }

            // Clear background
            ctx.fillStyle = '#0a0e1a';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Draw neon grid lines
            ctx.strokeStyle = 'rgba(0, 243, 255, 0.05)';
            ctx.lineWidth = 1;
            for (let x = 0; x <= canvas.width; x += gridSize) {
                ctx.beginPath();
                ctx.moveTo(x, 0);
                ctx.lineTo(x, canvas.height);
                ctx.stroke();
            }
            for (let y = 0; y <= canvas.height; y += gridSize) {
                ctx.beginPath();
                ctx.moveTo(0, y);
                ctx.lineTo(canvas.width, y);
                ctx.stroke();
            }

            // Draw Particles
            for (let p of particles) {
                ctx.save();
                ctx.globalAlpha = Math.max(0, p.alpha);
                ctx.shadowBlur = 10;
                ctx.shadowColor = p.color;
                ctx.fillStyle = p.color;
                ctx.fillRect(p.x, p.y, p.size, p.size);
                ctx.restore();
            }

            if (gameState === 1 || gameState === 2) {
                // Draw Food
                ctx.save();
                ctx.shadowBlur = 15;
                ctx.shadowColor = food.color;
                ctx.fillStyle = food.color;
                ctx.fillRect(food.x * gridSize + 2, food.y * gridSize + 2, gridSize - 4, gridSize - 4);
                ctx.restore();

                // Draw Snake
                for (let i = 0; i < snake.length; i++) {
                    const seg = snake[i];
                    ctx.save();
                    if (i === 0) {
                        ctx.shadowBlur = 15;
                        ctx.shadowColor = '#00f3ff';
                        ctx.fillStyle = '#00f3ff';
                    } else {
                        const alpha = Math.max(0.4, 1 - (i / snake.length) * 0.6);
                        ctx.globalAlpha = alpha;
                        ctx.shadowBlur = 8;
                        ctx.shadowColor = '#0099ff';
                        ctx.fillStyle = '#0099ff';
                    }
                    ctx.fillRect(seg.x * gridSize + 1, seg.y * gridSize + 1, gridSize - 2, gridSize - 2);
                    ctx.restore();
                }
            }

            // HUD updates
            document.getElementById('hud-score').innerText = "SCORE: " + score;
            document.getElementById('hud-combo').innerText = combo > 1 ? ("COMBO: x" + combo + " (" + comboTimer.toFixed(1) + "s)") : "COMBO: x1";
            document.getElementById('hud-hi').innerText = "HI: " + highScore;

            // Overlay States
            if (gameState === 0) {
                ctx.fillStyle = 'rgba(6, 8, 20, 0.85)';
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                ctx.textAlign = 'center';
                ctx.shadowBlur = 20;
                ctx.shadowColor = '#00f3ff';
                ctx.fillStyle = '#00f3ff';
                ctx.font = 'bold 36px Courier New';
                ctx.fillText('CYBERPUNK NEON SNAKE', canvas.width / 2, canvas.height / 2 - 40);

                ctx.shadowBlur = 10;
                ctx.shadowColor = '#ff007f';
                ctx.fillStyle = '#ff007f';
                ctx.font = 'bold 18px Courier New';
                ctx.fillText('[ PRESS SPACE OR CLICK TO START ]', canvas.width / 2, canvas.height / 2 + 20);

                ctx.shadowBlur = 5;
                ctx.shadowColor = '#ffe600';
                ctx.fillStyle = '#ffe600';
                ctx.font = '14px Courier New';
                ctx.fillText('Use ARROWS or WASD to navigate. Eat glowing data nodes.', canvas.width / 2, canvas.height / 2 + 70);
            } else if (gameState === 2) {
                ctx.fillStyle = 'rgba(6, 8, 20, 0.7)';
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                ctx.textAlign = 'center';
                ctx.shadowBlur = 20;
                ctx.shadowColor = '#ffe600';
                ctx.fillStyle = '#ffe600';
                ctx.font = 'bold 36px Courier New';
                ctx.fillText('PAUSED', canvas.width / 2, canvas.height / 2 - 10);

                ctx.shadowBlur = 10;
                ctx.shadowColor = '#00f3ff';
                ctx.fillStyle = '#00f3ff';
                ctx.font = '16px Courier New';
                ctx.fillText('Press P or Click to Resume', canvas.width / 2, canvas.height / 2 + 35);
            } else if (gameState === 3) {
                ctx.fillStyle = 'rgba(6, 8, 20, 0.85)';
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                ctx.textAlign = 'center';
                ctx.shadowBlur = 20;
                ctx.shadowColor = '#ff007f';
                ctx.fillStyle = '#ff007f';
                ctx.font = 'bold 38px Courier New';
                ctx.fillText('SYSTEM FAILURE', canvas.width / 2, canvas.height / 2 - 50);

                ctx.shadowBlur = 10;
                ctx.shadowColor = '#00f3ff';
                ctx.fillStyle = '#00f3ff';
                ctx.font = '22px Courier New';
                ctx.fillText('FINAL SCORE: ' + score, canvas.width / 2, canvas.height / 2);

                ctx.shadowBlur = 10;
                ctx.shadowColor = '#ffe600';
                ctx.fillStyle = '#ffe600';
                ctx.font = '16px Courier New';
                ctx.fillText('[ PRESS SPACE OR CLICK TO REBOOT ]', canvas.width / 2, canvas.height / 2 + 50);
            }

            ctx.restore();
        }

        function gameLoop(now) {
            const dt = Math.min((now - lastTime) / 1000, 0.1);
            lastTime = now;
            updateGame(dt);
            draw();
            requestAnimationFrame(gameLoop);
        }

        requestAnimationFrame(gameLoop);
    </script>
</body>
</html>
"""


def main():
    st.set_page_config(
        page_title="Cyberpunk Neon Snake",
        page_icon="🐍",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    db = LeaderboardDB(DB_PATH)

    # Custom Styling
    st.markdown(
        """
        <style>
            .main-title {
                font-size: 2.8rem;
                font-weight: 800;
                color: #00f3ff;
                text-shadow: 0 0 15px rgba(0, 243, 255, 0.6);
                font-family: 'Courier New', Courier, monospace;
                margin-bottom: 0px;
            }
            .subtitle {
                color: #ff007f;
                font-size: 1.1rem;
                text-shadow: 0 0 8px rgba(255, 0, 127, 0.5);
                font-family: 'Courier New', Courier, monospace;
                margin-bottom: 20px;
            }
            .stTextInput>div>div>input {
                background-color: #0a0e1a;
                color: #00f3ff;
                border: 1px solid #00f3ff;
            }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Sidebar controls
    with st.sidebar:
        st.markdown("### 🕹️ ARCADE CONFIG")
        difficulty_name = st.selectbox(
            "Select Difficulty",
            options=list(GameConfig.DIFFICULTIES.keys()),
            index=1
        )
        diff_cfg = GameConfig.get_difficulty(difficulty_name)

        st.markdown("---")
        st.markdown("### 🏆 STATS & DATABASE")
        stats = db.get_stats()
        st.metric("Total Runs", stats["total_games"])
        st.metric("Global Top Score", stats["max_score"])
        st.metric("Average Score", stats["avg_score"])

        st.markdown("---")
        with st.expander("⚙️ Admin Control"):
            if st.button("Reset Database / Wipe Scores", type="primary"):
                db.reset_database()
                st.success("Database wiped clean!")
                st.rerun()

        st.markdown("---")
        st.markdown("**Instructions:**")
        st.markdown("- **Arrow Keys / WASD**: Steer")
        st.markdown("- **Space / Enter / Click**: Start / Reboot")
        st.markdown("- **P**: Pause / Resume")

    # Main Header
    st.markdown('<div class="main-title">CYBERPUNK NEON SNAKE</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="subtitle">DIFFICULTY: {difficulty_name.upper()} | MULTIPLIER: {diff_cfg["multiplier"]}x | WALL COLLISION: {"ON" if diff_cfg["wall_collision"] else "OFF"}</div>', unsafe_allow_html=True)

    # Top scores for JS injection
    top_scores = db.get_top_scores(1)
    high_score = top_scores[0]["score"] if top_scores else 100

    # Inject game HTML
    rendered_html = (
        GAME_HTML
        .replace("__HIGH_SCORE__", str(high_score))
        .replace("__CONFIG_SPEED__", str(diff_cfg["speed"]))
        .replace("__CONFIG_MULTIPLIER__", str(diff_cfg["multiplier"]))
        .replace("__CONFIG_WALL__", "true" if diff_cfg["wall_collision"] else "false")
    )

    components.html(rendered_html, height=560)

    st.markdown("---")

    # Score Submission Section
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 💾 RECORD YOUR SCORE TO LEADERBOARD")
        with st.form("score_form"):
            player_name = st.text_input("Cyber-Runner Handle", value="NeonViper", max_chars=30)
            recorded_score = st.number_input("Final Score Achieved", min_value=0, max_value=999999, value=0)
            submitted = st.form_submit_button("Upload Score to Net")

            if submitted:
                db.add_score(player_name, recorded_score, difficulty_name)
                st.success(f"Score {recorded_score} uploaded successfully for {player_name}!")
                st.rerun()

    with col2:
        st.markdown("### 🏆 GLOBAL HALL OF FAME")
        top_list = db.get_top_scores(10)
        if top_list:
            table_data = [
                {
                    "Rank": idx + 1,
                    "Runner": row["player_name"],
                    "Score": row["score"],
                    "Difficulty": row.get("difficulty", "Standard"),
                    "Date": row.get("created_at", "--")
                }
                for idx, row in enumerate(top_list)
            ]
            st.dataframe(table_data, use_container_width=True, hide_index=True)
        else:
            st.info("No high scores recorded yet. Be the first cyber-runner in the database!")


if __name__ == '__main__':
    main()