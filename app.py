"""
Galaxy Space Shooter Arcade Game
Built with Streamlit, HTML5 Canvas, Web Audio API, and SQLite Persistence.
"""

import os
import sqlite3
import streamlit as st
import streamlit.components.v1 as components

DB_PATH = "leaderboard.sqlite"

# ==========================================
# BACKEND ENGINE & DATABASE CLASSES
# ==========================================

class LeaderboardDB:
    """Handles SQLite persistence for high scores with automatic schema migration."""
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
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
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''')
            conn.commit()
            # Self-healing schema check
            cursor.execute("PRAGMA table_info(scores);")
            columns = [col[1] for col in cursor.fetchall()]
            if "difficulty" not in columns:
                cursor.execute("ALTER TABLE scores ADD COLUMN difficulty TEXT DEFAULT 'Standard';")
                conn.commit()

    def add_score(self, player_name: str, score: int, difficulty: str) -> int:
        if not player_name or not player_name.strip():
            player_name = "Anonymous"
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO scores (player_name, score, difficulty) VALUES (?, ?, ?);",
                (player_name.strip()[:20], int(score), str(difficulty))
            )
            conn.commit()
            return cursor.lastrowid

    def get_top_scores(self, limit=10, difficulty=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if difficulty and difficulty != "All":
                cursor.execute(
                    "SELECT player_name, score, difficulty, date FROM scores WHERE difficulty = ? ORDER BY score DESC LIMIT ?;",
                    (difficulty, limit)
                )
            else:
                cursor.execute(
                    "SELECT player_name, score, difficulty, date FROM scores ORDER BY score DESC LIMIT ?;",
                    (limit,)
                )
            return cursor.fetchall()

    def get_stats(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), MAX(score), AVG(score) FROM scores;")
            row = cursor.fetchone()
            if row and row[0] > 0:
                return {"total_games": row[0], "high_score": row[1] or 0, "avg_score": int(row[2] or 0)}
            return {"total_games": 0, "high_score": 0, "avg_score": 0}

    def reset_database(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS scores;")
            conn.commit()
        self.init_db()


class DifficultyManager:
    """Manages game parameters and multipliers based on difficulty."""
    DIFFICULTIES = {
        "Casual": {"enemy_speed": 1.0, "spawn_rate": 1.5, "score_multiplier": 1.0, "player_lives": 5},
        "Standard": {"enemy_speed": 1.4, "spawn_rate": 1.0, "score_multiplier": 1.5, "player_lives": 3},
        "Pro": {"enemy_speed": 1.9, "spawn_rate": 0.75, "score_multiplier": 2.0, "player_lives": 3},
        "Impossible": {"enemy_speed": 2.5, "spawn_rate": 0.5, "score_multiplier": 3.0, "player_lives": 1}
    }

    @classmethod
    def get_config(cls, name: str):
        return cls.DIFFICULTIES.get(name, cls.DIFFICULTIES["Standard"])


# ==========================================
# HTML5 CANVAS GAME COMPONENT
# ==========================================

def render_arcade_game(difficulty: str, sound_enabled: bool):
    config = DifficultyManager.get_config(difficulty)
    
    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body { 
                margin: 0; 
                background: #060814; 
                font-family: 'Courier New', Courier, monospace; 
                color: #00f3ff; 
                overflow: hidden;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }
            #game-container {
                position: relative;
                box-shadow: 0 0 30px rgba(0, 243, 255, 0.3);
                border: 2px solid #00f3ff;
                border-radius: 8px;
                background: #0a0e1a;
            }
            canvas {
                display: block;
                background: radial-gradient(circle at center, #0f172a 0%, #060814 100%);
            }
            #hud {
                position: absolute;
                top: 10px;
                left: 10px;
                right: 10px;
                display: flex;
                justify-content: space-between;
                pointer-events: none;
                font-size: 14px;
                font-weight: bold;
                text-shadow: 0 0 8px #00f3ff;
                z-index: 10;
            }
            .hud-item { background: rgba(6, 8, 20, 0.8); padding: 4px 10px; border: 1px solid rgba(0,243,255,0.4); border-radius: 4px; }
        </style>
    </head>
    <body>
        <div id="game-container">
            <div id="hud">
                <div class="hud-item" id="hud-score">SCORE: 0</div>
                <div class="hud-item" id="hud-lives">LIVES: __LIVES__</div>
                <div class="hud-item" id="hud-wave">WAVE: 1</div>
                <div class="hud-item" id="hud-shield">SHIELD: OFF</div>
            </div>
            <canvas id="gameCanvas" width="800" height="550"></canvas>
        </div>

        <script>
            const canvas = document.getElementById('gameCanvas');
            const ctx = canvas.getContext('2d');

            // Config from Python
            const DIFF_NAME = "__DIFF_NAME__";
            const ENEMY_SPEED_MULT = __ENEMY_SPEED__;
            const SPAWN_RATE_MULT = __SPAWN_RATE__;
            const SCORE_MULT = __SCORE_MULT__;
            const INITIAL_LIVES = __LIVES__;

            // Web Audio Synthesizer
            const AudioEngine = {
                ctx: null,
                muted: __MUTED__,
                init() {
                    if (!this.ctx) {
                        const AC = window.AudioContext || window.webkitAudioContext;
                        if (AC) this.ctx = new AC();
                    }
                    if (this.ctx && this.ctx.state === 'suspended') this.ctx.resume();
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
                hit() { this.playTone(420, 'square', 0.06, 200); },
                score() { this.playTone(523, 'sine', 0.1); setTimeout(() => this.playTone(659, 'sine', 0.15), 80); },
                laser() { this.playTone(880, 'sawtooth', 0.06, 220); },
                explode() { this.playTone(180, 'triangle', 0.25, 40); },
                powerup() { this.playTone(440, 'sine', 0.1); setTimeout(() => this.playTone(880, 'sine', 0.2), 100); },
                gameOver() { this.playTone(330, 'sawtooth', 0.3, 110); }
            };

            // Game State
            let gameState = 'START'; // START, PLAYING, PAUSED, GAMEOVER
            let score = 0;
            let lives = INITIAL_LIVES;
            let wave = 1;
            let highscore = 0;
            let screenShakeTimer = 0;
            let screenShakeIntensity = 0;

            // Player object
            let player = {
                x: canvas.width / 2,
                y: canvas.height - 60,
                width: 32,
                height: 32,
                speed: 360,
                dx: 0,
                dy: 0,
                shield: false,
                shieldTimer: 0,
                multishot: false,
                multishotTimer: 0,
                color: '#00f3ff'
            };

            let keys = {};
            let bullets = [];
            let enemies = [];
            let particles = [];
            let powerups = [];
            let stardust = [];

            // Init Stardust
            for (let i = 0; i < 70; i++) {
                stardust.push({
                    x: Math.random() * canvas.width,
                    y: Math.random() * canvas.height,
                    size: Math.random() * 2 + 0.5,
                    speed: Math.random() * 30 + 10,
                    alpha: Math.random() * 0.7 + 0.3
                });
            }

            // Controls
            window.addEventListener('keydown', e => {
                AudioEngine.init();
                if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', ' '].includes(e.key)) {
                    e.preventDefault();
                }
                keys[e.key] = true;
                if ((e.key === ' ' || e.key === 'Enter') && (gameState === 'START' || gameState === 'GAMEOVER')) {
                    startGame();
                }
                if (e.key === 'p' || e.key === 'P') {
                    if (gameState === 'PLAYING') gameState = 'PAUSED';
                    else if (gameState === 'PAUSED') gameState = 'PLAYING';
                }
            });

            window.addEventListener('keyup', e => {
                keys[e.key] = false;
            });

            canvas.addEventListener('mousemove', e => {
                AudioEngine.init();
                const rect = canvas.getBoundingClientRect();
                const mouseX = e.clientX - rect.left;
                const mouseY = e.clientY - rect.top;
                if (gameState === 'PLAYING') {
                    player.x += (mouseX - player.x) * 0.2;
                    player.y += (mouseY - player.y) * 0.2;
                }
            });

            canvas.addEventListener('click', () => {
                AudioEngine.init();
                if (gameState === 'START' || gameState === 'GAMEOVER') {
                    startGame();
                } else if (gameState === 'PLAYING') {
                    fireLaser();
                }
            });

            let lastSpawnTime = 0;
            let spawnInterval = 1.8 / SPAWN_RATE_MULT;
            let lastLaserTime = 0;

            function startGame() {
                score = 0;
                lives = INITIAL_LIVES;
                wave = 1;
                enemies = [];
                bullets = [];
                particles = [];
                powerups = [];
                player.x = canvas.width / 2;
                player.y = canvas.height - 60;
                player.shield = false;
                player.multishot = false;
                gameState = 'PLAYING';
            }

            function triggerShake(intensity, duration) {
                screenShakeIntensity = intensity;
                screenShakeTimer = duration;
            }

            function spawnParticle(x, y, color, count = 12, speed = 120) {
                for (let i = 0; i < count; i++) {
                    const angle = Math.random() * Math.PI * 2;
                    const spd = Math.random() * speed + 20;
                    particles.push({
                        x: x,
                        y: y,
                        vx: Math.cos(angle) * spd,
                        vy: Math.sin(angle) * spd,
                        color: color,
                        alpha: 1.0,
                        life: Math.random() * 0.6 + 0.3,
                        size: Math.random() * 3 + 1
                    });
                }
            }

            function fireLaser() {
                const now = performance.now() / 1000;
                if (now - lastLaserTime < 0.15) return;
                lastLaserTime = now;
                AudioEngine.laser();

                if (player.multishot) {
                    bullets.push({x: player.x - 12, y: player.y - 15, vx: 0, vy: -650, color: '#ffe600'});
                    bullets.push({x: player.x, y: player.y - 20, vx: 0, vy: -700, color: '#00f3ff'});
                    bullets.push({x: player.x + 12, y: player.y - 15, vx: 0, vy: -650, color: '#ffe600'});
                } else {
                    bullets.push({x: player.x, y: player.y - 18, vx: 0, vy: -700, color: '#00f3ff'});
                }
            }

            let lastTime = performance.now();

            function gameLoop(now) {
                const dt = Math.min((now - lastTime) / 1000, 0.1);
                lastTime = now;

                update(dt);
                render();

                requestAnimationFrame(gameLoop);
            }

            function update(dt) {
                // Stardust update
                stardust.forEach(s => {
                    s.y += s.speed * dt;
                    if (s.y > canvas.height) {
                        s.y = 0;
                        s.x = Math.random() * canvas.width;
                    }
                });

                if (gameState !== 'PLAYING') return;

                // Screen shake countdown
                if (screenShakeTimer > 0) {
                    screenShakeTimer -= dt;
                }

                // Powerup timers
                if (player.shield) {
                    player.shieldTimer -= dt;
                    if (player.shieldTimer <= 0) player.shield = false;
                }
                if (player.multishot) {
                    player.multishotTimer -= dt;
                    if (player.multishotTimer <= 0) player.multishot = false;
                }

                // Player Keyboard Movement
                let moveX = 0;
                let moveY = 0;
                if (keys['ArrowLeft'] || keys['a'] || keys['A']) moveX -= 1;
                if (keys['ArrowRight'] || keys['d'] || keys['D']) moveX += 1;
                if (keys['ArrowUp'] || keys['w'] || keys['W']) moveY -= 1;
                if (keys['ArrowDown'] || keys['s'] || keys['S']) moveY += 1;

                if (moveX !== 0 && moveY !== 0) {
                    moveX *= 0.7071;
                    moveY *= 0.7071;
                }

                player.x += moveX * player.speed * dt;
                player.y += moveY * player.speed * dt;

                // Bounds
                player.x = Math.max(20, Math.min(canvas.width - 20, player.x));
                player.y = Math.max(30, Math.min(canvas.height - 30, player.y));

                // Auto fire spacebar
                if (keys[' ']) {
                    fireLaser();
                }

                // Enemy Spawning
                lastSpawnTime += dt;
                if (lastSpawnTime >= spawnInterval) {
                    lastSpawnTime = 0;
                    spawnEnemy();
                }

                // Update Bullets
                for (let i = bullets.length - 1; i >= 0; i--) {
                    let b = bullets[i];
                    b.x += (b.vx || 0) * dt;
                    b.y += b.vy * dt;
                    if (b.y < -20 || b.y > canvas.height + 20 || b.x < -20 || b.x > canvas.width + 20) {
                        bullets.splice(i, 1);
                    }
                }

                // Update Enemies
                for (let i = enemies.length - 1; i >= 0; i--) {
                    let e = enemies[i];
                    e.y += e.vy * dt;
                    if (e.behavior === 'zigzag') {
                        e.x += Math.sin(e.y * 0.03) * 3;
                    }

                    // Check collision with player
                    const dist = Math.hypot(player.x - e.x, player.y - e.y);
                    if (dist < 26) {
                        if (player.shield) {
                            player.shield = false;
                            spawnParticle(e.x, e.y, '#00f3ff', 20, 150);
                            AudioEngine.explode();
                            enemies.splice(i, 1);
                        } else {
                            lives--;
                            AudioEngine.hit();
                            triggerShake(8, 0.3);
                            spawnParticle(player.x, player.y, '#ff007f', 25, 180);
                            enemies.splice(i, 1);
                            if (lives <= 0) {
                                gameState = 'GAMEOVER';
                                AudioEngine.gameOver();
                            }
                        }
                        continue;
                    }

                    // Check collision with bullets
                    let enemyDestroyed = false;
                    for (let j = bullets.length - 1; j >= 0; j--) {
                        let b = bullets[j];
                        const bDist = Math.hypot(b.x - e.x, b.y - e.y);
                        if (bDist < e.radius + 8) {
                            bullets.splice(j, 1);
                            e.hp--;
                            if (e.hp <= 0) {
                                enemyDestroyed = true;
                            }
                            break;
                        }
                    }

                    if (enemyDestroyed) {
                        AudioEngine.explode();
                        spawnParticle(e.x, e.y, e.color, 16, 140);
                        score += Math.floor(e.scoreVal * SCORE_MULT);

                        // Chance to drop powerup
                        if (Math.random() < 0.18) {
                            const type = Math.random() < 0.5 ? 'shield' : 'multishot';
                            powerups.push({x: e.x, y: e.y, type: type, radius: 14, vy: 70});
                        }

                        enemies.splice(i, 1);

                        // Wave progress
                        if (score >= wave * 500) {
                            wave++;
                            spawnInterval = Math.max(0.4, spawnInterval * 0.9);
                            AudioEngine.score();
                        }
                        continue;
                    }

                    if (e.y > canvas.height + 40) {
                        enemies.splice(i, 1);
                    }
                }

                // Update Powerups
                for (let i = powerups.length - 1; i >= 0; i--) {
                    let p = powerups[i];
                    p.y += p.vy * dt;
                    const pDist = Math.hypot(player.x - p.x, player.y - p.y);
                    if (pDist < 28) {
                        AudioEngine.powerup();
                        spawnParticle(p.x, p.y, p.type === 'shield' ? '#00f3ff' : '#ffe600', 15, 100);
                        if (p.type === 'shield') {
                            player.shield = true;
                            player.shieldTimer = 10.0;
                        } else {
                            player.multishot = true;
                            player.multishotTimer = 8.0;
                        }
                        powerups.splice(i, 1);
                        continue;
                    }
                    if (p.y > canvas.height + 30) {
                        powerups.splice(i, 1);
                    }
                }

                // Update Particles
                for (let i = particles.length - 1; i >= 0; i--) {
                    let pt = particles[i];
                    pt.x += pt.vx * dt;
                    pt.y += pt.vy * dt;
                    pt.alpha -= dt / pt.life;
                    if (pt.alpha <= 0) {
                        particles.splice(i, 1);
                    }
                }

                // HUD updates
                document.getElementById('hud-score').innerText = "SCORE: " + score;
                document.getElementById('hud-lives').innerText = "LIVES: " + '❤️'.repeat(Math.max(0, lives));
                document.getElementById('hud-wave').innerText = "WAVE: " + wave;
                const shieldStatus = player.shield ? "SHIELD (" + Math.ceil(player.shieldTimer) + "s)" : (player.multishot ? "MULTISHOT (" + Math.ceil(player.multishotTimer) + "s)" : "OFF");
                document.getElementById('hud-shield').innerText = "PWR: " + shieldStatus;
            }

            function spawnEnemy() {
                const types = [
                    {color: '#ff007f', radius: 16, vy: (120 + wave * 15) * ENEMY_SPEED_MULT, hp: 1, scoreVal: 20, behavior: 'straight'},
                    {color: '#9d00ff', radius: 20, vy: (90 + wave * 10) * ENEMY_SPEED_MULT, hp: 2, scoreVal: 40, behavior: 'zigzag'},
                    {color: '#ffe600', radius: 24, vy: (70 + wave * 8) * ENEMY_SPEED_MULT, hp: 3, scoreVal: 70, behavior: 'straight'}
                ];
                const type = types[Math.floor(Math.random() * types.length)];
                enemies.push({
                    x: Math.random() * (canvas.width - 60) + 30,
                    y: -30,
                    radius: type.radius,
                    vy: type.vy,
                    hp: type.hp,
                    color: type.color,
                    scoreVal: type.scoreVal,
                    behavior: type.behavior
                });
            }

            function render() {
                ctx.save();
                if (screenShakeTimer > 0) {
                    const shakeX = (Math.random() - 0.5) * screenShakeIntensity;
                    const shakeY = (Math.random() - 0.5) * screenShakeIntensity;
                    ctx.translate(shakeX, shakeY);
                }

                // Clear background
                ctx.clearRect(0, 0, canvas.width, canvas.height);

                // Draw Stardust
                stardust.forEach(s => {
                    ctx.fillStyle = 'rgba(255, 255, 255, ' + s.alpha + ')';
                    ctx.fillRect(s.x, s.y, s.size, s.size);
                });

                // Draw Particles
                particles.forEach(pt => {
                    ctx.save();
                    ctx.globalAlpha = Math.max(0, pt.alpha);
                    ctx.shadowBlur = 8;
                    ctx.shadowColor = pt.color;
                    ctx.fillStyle = pt.color;
                    ctx.fillRect(pt.x, pt.y, pt.size, pt.size);
                    ctx.restore();
                });

                // Draw Powerups
                powerups.forEach(p => {
                    ctx.save();
                    ctx.shadowBlur = 12;
                    ctx.shadowColor = p.type === 'shield' ? '#00f3ff' : '#ffe600';
                    ctx.fillStyle = p.type === 'shield' ? '#00f3ff' : '#ffe600';
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.fillStyle = '#060814';
                    ctx.font = 'bold 12px Courier New';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(p.type === 'shield' ? 'S' : 'M', p.x, p.y);
                    ctx.restore();
                });

                // Draw Bullets
                bullets.forEach(b => {
                    ctx.save();
                    ctx.shadowBlur = 10;
                    ctx.shadowColor = b.color;
                    ctx.fillStyle = b.color;
                    ctx.fillRect(b.x - 2, b.y - 6, 4, 12);
                    ctx.restore();
                });

                // Draw Enemies
                enemies.forEach(e => {
                    ctx.save();
                    ctx.shadowBlur = 14;
                    ctx.shadowColor = e.color;
                    ctx.strokeStyle = e.color;
                    ctx.lineWidth = 2;
                    ctx.fillStyle = '#060814';

                    ctx.beginPath();
                    ctx.moveTo(e.x, e.y + e.radius);
                    ctx.lineTo(e.x - e.radius, e.y - e.radius);
                    ctx.lineTo(e.x, e.y - e.radius * 0.5);
                    ctx.lineTo(e.x + e.radius, e.y - e.radius);
                    ctx.closePath();
                    ctx.fill();
                    ctx.stroke();
                    ctx.restore();
                });

                // Draw Player Ship
                if (gameState === 'PLAYING' || gameState === 'PAUSED') {
                    ctx.save();
                    ctx.shadowBlur = 16;
                    ctx.shadowColor = player.color;
                    ctx.strokeStyle = player.color;
                    ctx.lineWidth = 2;
                    ctx.fillStyle = '#060814';

                    // Ship vector triangle
                    ctx.beginPath();
                    ctx.moveTo(player.x, player.y - 20);
                    ctx.lineTo(player.x - 16, player.y + 16);
                    ctx.lineTo(player.x, player.y + 8);
                    ctx.lineTo(player.x + 16, player.y + 16);
                    ctx.closePath();
                    ctx.fill();
                    ctx.stroke();

                    // Engine thruster flame
                    ctx.fillStyle = '#ff007f';
                    ctx.beginPath();
                    ctx.moveTo(player.x - 6, player.y + 16);
                    ctx.lineTo(player.x, player.y + 26 + Math.random() * 6);
                    ctx.lineTo(player.x + 6, player.y + 16);
                    ctx.fill();

                    // Shield bubble
                    if (player.shield) {
                        ctx.strokeStyle = '#00f3ff';
                        ctx.lineWidth = 2;
                        ctx.shadowBlur = 20;
                        ctx.shadowColor = '#00f3ff';
                        ctx.beginPath();
                        ctx.arc(player.x, player.y, 28, 0, Math.PI * 2);
                        ctx.stroke();
                    }

                    ctx.restore();
                }

                // Overlays
                if (gameState === 'START') {
                    ctx.fillStyle = 'rgba(6, 8, 20, 0.85)';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);

                    ctx.shadowBlur = 20;
                    ctx.shadowColor = '#00f3ff';
                    ctx.fillStyle = '#00f3ff';
                    ctx.font = 'bold 36px Courier New';
                    ctx.textAlign = 'center';
                    ctx.fillText('GALAXY SPACE SHOOTER', canvas.width / 2, canvas.height / 2 - 50);

                    ctx.shadowBlur = 10;
                    ctx.shadowColor = '#ffe600';
                    ctx.fillStyle = '#ffe600';
                    ctx.font = '18px Courier New';
                    ctx.fillText('PRESS SPACEBAR OR CLICK TO START', canvas.width / 2, canvas.height / 2 + 10);

                    ctx.fillStyle = '#a0aec0';
                    ctx.font = '14px Courier New';
                    ctx.fillText('Move: WASD / Arrows / Mouse | Shoot: Space / Click | Pause: P', canvas.width / 2, canvas.height / 2 + 60);
                } else if (gameState === 'PAUSED') {
                    ctx.fillStyle = 'rgba(6, 8, 20, 0.7)';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);

                    ctx.shadowBlur = 15;
                    ctx.shadowColor = '#ffe600';
                    ctx.fillStyle = '#ffe600';
                    ctx.font = 'bold 32px Courier New';
                    ctx.textAlign = 'center';
                    ctx.fillText('GAME PAUSED', canvas.width / 2, canvas.height / 2);
                    ctx.font = '16px Courier New';
                    ctx.fillStyle = '#00f3ff';
                    ctx.fillText('Press P to Resume', canvas.width / 2, canvas.height / 2 + 40);
                } else if (gameState === 'GAMEOVER') {
                    ctx.fillStyle = 'rgba(6, 8, 20, 0.9)';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);

                    ctx.shadowBlur = 20;
                    ctx.shadowColor = '#ff007f';
                    ctx.fillStyle = '#ff007f';
                    ctx.font = 'bold 40px Courier New';
                    ctx.textAlign = 'center';
                    ctx.fillText('GAME OVER', canvas.width / 2, canvas.height / 2 - 50);

                    ctx.shadowBlur = 12;
                    ctx.shadowColor = '#00f3ff';
                    ctx.fillStyle = '#00f3ff';
                    ctx.font = '22px Courier New';
                    ctx.fillText('FINAL SCORE: ' + score, canvas.width / 2, canvas.height / 2 + 5);

                    ctx.fillStyle = '#ffe600';
                    ctx.font = '16px Courier New';
                    ctx.fillText('PRESS SPACEBAR TO PLAY AGAIN & SUBMIT SCORE', canvas.width / 2, canvas.height / 2 + 55);
                }

                ctx.restore();
            }

            requestAnimationFrame(gameLoop);
        </script>
    </body>
    </html>
    """

    # Inject dynamic configuration values securely
    html_code = html_code.replace("__DIFF_NAME__", difficulty \
        ).replace("__ENEMY_SPEED__", str(config["enemy_speed"]) \
        ).replace("__SPAWN_RATE__", str(config["spawn_rate"]) \
        ).replace("__SCORE_MULT__", str(config["score_multiplier"]) \
        ).replace("__LIVES__", str(config["player_lives"]) \
        ).replace("__MUTED__", "true" if not sound_enabled else "false")

    components.html(html_code, height=600)


# ==========================================
# STREAMLIT UI APPLICATION
# ==========================================

def main():
    st.set_page_config(
        page_title="Galaxy Space Shooter Arcade",
        page_icon="🚀",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    db = LeaderboardDB()

    # Custom Styling
    st.markdown("""
        <style>
            .main-title { font-size: 2.5rem; color: #00f3ff; text-shadow: 0 0 12px rgba(0,243,255,0.6); font-family: 'Courier New', monospace; font-weight: bold; }
            .sub-header { color: #ffe600; font-family: 'Courier New', monospace; }
            .stAlert { background-color: #0a0e1a; color: #00f3ff; border: 1px solid #00f3ff; }
        </style>
    """, unsafe_allow_html=True)

    # Sidebar Controls
    st.sidebar.markdown("### 🕹️ ARCADE CONFIG")
    difficulty = st.sidebar.selectbox("Select Difficulty", ["Casual", "Standard", "Pro", "Impossible"], index=1)
    sound_enabled = st.sidebar.toggle("🔊 Audio Synthesizer", value=True)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🏆 HIGH SCORE SUBMISSION")
    with st.sidebar.form("score_form"):
        player_name = st.text_input("Pilot CallSign", value="", max_chars=20)
        final_score = st.number_input("Recorded Score", min_value=0, max_value=999999, value=0, step=100)
        submitted = st.form_submit_button("Transmit Score")
        if submitted:
            if player_name.strip():
                db.add_score(player_name, final_score, difficulty)
                st.sidebar.success(f"Score transmitted for {player_name}!")
                st.rerun()
            else:
                st.sidebar.error("Please enter a pilot callsign.")

    st.sidebar.markdown("---")
    with st.sidebar.expander("🛠️ Database Management"):
        if st.button("Reset All Leaderboard Data", type="primary"):
            db.reset_database()
            st.sidebar.success("Leaderboard wiped clean!")
            st.rerun()

    # Main Header
    st.markdown('<div class="main-title">🚀 GALAXY SPACE SHOOTER ARCADE</div>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Retro glowing vector combat, progressive waves, power-up shields, and procedural sound synth.</p>', unsafe_allow_html=True)

    stats = db.get_stats()
    col1, col2, col3 = st.columns(3)
    col1.metric("Global High Score", f"{stats['high_score']:,}", delta=difficulty)
    col2.metric("Total Games Played", f"{stats['total_games']:,}")
    col3.metric("Average Score", f"{stats['avg_score']:,}")

    st.markdown("---")

    # Render Game Canvas
    render_arcade_game(difficulty, sound_enabled)

    st.markdown("---")

    # Leaderboard Section
    st.markdown("### 🏆 PILOT LEADERBOARD RANKINGS")
    filter_diff = st.selectbox("Filter by Difficulty", ["All", "Casual", "Standard", "Pro", "Impossible"], key="filter_diff")
    scores_data = db.get_top_scores(limit=10, difficulty=filter_diff)

    if scores_data:
        table_data = []
        for rank, row in enumerate(scores_data, start=1):
            table_data.append({
                "Rank": rank,
                "Pilot": row[0],
                "Score": f"{row[1]:,}",
                "Difficulty": row[2],
                "Timestamp": row[3]
            })
        st.dataframe(table_data, use_container_width=True, hide_index=True)
    else:
        st.info(
            "No high scores recorded yet for this filter. Complete a game and submit your score using the sidebar form!"
        )

    # Instructions expander
    with st.expander("📖 Mission Briefing & Controls"):
        st.markdown("""
        - **Movement**: Use `WASD`, `Arrow Keys`, or trackpad/mouse movement to steer your vector fighter.
        - **Weapons**: Press `Spacebar` or `Left Click` to fire plasma lasers.
        - **Power-ups**: Collect glowing cyan (**S**hield) and yellow (**M**ultishot) power-up pods dropped by elite alien ships.
        - **Pause**: Press `P` anytime during combat to take a breather.
        - **Scoring**: Higher difficulties (`Pro`, `Impossible`) grant higher score multipliers!
        """)


if __name__ == '__main__':
    main()