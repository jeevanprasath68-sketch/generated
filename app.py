import streamlit as st
import streamlit.components.v1 as components
import json
import os
from datetime import datetime
from typing import Dict, Any, List

# --- Business Logic & State Management ---

class GameScoreManager:
    """Manages game scores, high scores, and statistics persistence."""
    def __init__(self, storage_file: str = "game_scores.json"):
        self.storage_file = storage_file

    def load_scores(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.storage_file):
            return []
        try:
            with open(self.storage_file, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def save_score(self, player_name: str, score: int) -> List[Dict[str, Any]]:
        scores = self.load_scores()
        scores.append({
            "player_name": player_name,
            "score": score,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        # Sort descending by score and keep top 10
        scores = sorted(scores, key=lambda x: x["score"], reverse=True)[:10]
        try:
            with open(self.storage_file, "w") as f:
                json.dump(scores, f)
        except Exception:
            pass
        return scores

    def get_high_score(self) -> int:
        scores = self.load_scores()
        if not scores:
            return 0
        return max(s["score"] for s in scores)


# --- HTML5 / JS Kangaroo Game Component ---

KANGAROO_GAME_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Kangaroo Hopper Game</title>
    <style>
        body {
            margin: 0;
            background: #f7f7f7;
            font-family: 'Courier New', Courier, monospace;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100vh;
            overflow: hidden;
        }
        #game-container {
            text-align: center;
            background: #ffffff;
            padding: 10px;
            border-radius: 8px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        }
        canvas {
            background: #fdfdfd;
            border-bottom: 2px solid #535353;
            display: block;
            margin: 0 auto;
        }
        .instructions {
            margin-top: 10px;
            font-size: 14px;
            color: #535353;
        }
    </style>
</head>
<body>
    <div id="game-container">
        <canvas id="gameCanvas" width="800" height="250"></canvas>
        <div class="instructions">
            Press <strong>SPACEBAR</strong> or <strong>UP ARROW</strong> to Jump | <strong>DOWN ARROW</strong> to Duck
        </div>
    </div>

    <script>
        const canvas = document.getElementById("gameCanvas");
        const ctx = canvas.getContext("2d");

        let gameSpeed = 6;
        let score = 0;
        let highScore = 0;
        let isGameOver = false;
        let isPlaying = false;

        // Kangaroo Object
        const kangaroo = {
            x: 50,
            y: 160,
            width: 40,
            height: 50,
            vy: 0,
            gravity: 0.6,
            jumpPower: -11,
            isJumping: false,
            isDucking: false,
            originalHeight: 50,
            duckHeight: 30
        };

        let obstacles = [];
        let clouds = [];
        let frameCount = 0;

        class Obstacle {
            constructor() {
                this.width = 25 + Math.random() * 20;
                this.height = 35 + Math.random() * 25;
                this.x = canvas.width;
                this.y = 210 - this.height;
                this.passed = false;
            }
            draw() {
                ctx.fillStyle = "#535353";
                // Draw cactus / bush obstacle
                ctx.fillRect(this.x, this.y, this.width, this.height);
                // Add cute spikes
                ctx.fillStyle = "#fff";
                ctx.fillRect(this.x + 5, this.y + 5, 3, 6);
            }
            update() {
                this.x -= gameSpeed;
            }
        }

        class Cloud {
            constructor() {
                this.x = canvas.width + Math.random() * 100;
                this.y = 30 + Math.random() * 50;
                this.width = 50;
                this.height = 20;
                this.speed = 1.5;
            }
            draw() {
                ctx.fillStyle = "#e0e0e0";
                ctx.fillRect(this.x, this.y, this.width, this.height);
            }
            update() {
                this.x -= this.speed;
            }
        }

        function resetGame() {
            score = 0;
            gameSpeed = 6;
            obstacles = [];
            clouds = [];
            kangaroo.y = 160;
            kangaroo.vy = 0;
            kangaroo.isJumping = false;
            isGameOver = false;
            isPlaying = true;
            loop();
        }

        // Input listeners
        window.addEventListener("keydown", function(e) {
            if (e.code === "Space" || e.code === "ArrowUp") {
                e.preventDefault();
                if (!isPlaying && !isGameOver) {
                    resetGame();
                } else if (isPlaying && !kangaroo.isJumping && !kangaroo.isDucking) {
                    kangaroo.vy = kangaroo.jumpPower;
                    kangaroo.isJumping = true;
                } else if (isGameOver) {
                    resetGame();
                }
            }
            if (e.code === "ArrowDown") {
                e.preventDefault();
                if (isPlaying && !kangaroo.isJumping) {
                    kangaroo.isDucking = true;
                    kangaroo.height = kangaroo.duckHeight;
                    kangaroo.y = 180;
                }
            }
        });

        window.addEventListener("keyup", function(e) {
            if (e.code === "ArrowDown") {
                if (isPlaying && kangaroo.isDucking) {
                    kangaroo.isDucking = false;
                    kangaroo.height = kangaroo.originalHeight;
                    kangaroo.y = 160;
                }
            }
        });

        canvas.addEventListener("click", function() {
            if (!isPlaying || isGameOver) {
                resetGame();
            }
        });

        function spawnObstacles() {
            if (frameCount % Math.max(70, 140 - Math.floor(gameSpeed * 5)) === 0) {
                obstacles.push(new Obstacle());
            }
        }

        function spawnClouds() {
            if (frameCount % 180 === 0) {
                clouds.push(new Cloud());
            }
        }

        function drawGround() {
            ctx.strokeStyle = "#535353";
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(0, 210);
            ctx.lineTo(canvas.width, 210);
            ctx.stroke();
        }

        function drawKangaroo() {
            ctx.fillStyle = "#ff8c00"; // Kangaroo orange/brown color
            // Body
            ctx.fillRect(kangaroo.x, kangaroo.y, kangaroo.width, kangaroo.height);
            // Head & Ears
            ctx.fillRect(kangaroo.x + kangaroo.width - 15, kangaroo.y - 20, 20, 25);
            ctx.fillStyle = "#535353";
            ctx.fillRect(kangaroo.x + kangaroo.width - 10, kangaroo.y - 28, 5, 10);
            // Tail
            ctx.fillRect(kangaroo.x - 12, kangaroo.y + 10, 12, 12);
        }

        function checkCollision(rect1, rect2) {
            return (
                rect1.x < rect2.x + rect2.width &&
                rect1.x + rect1.width > rect2.x &&
                rect1.y < rect2.y + rect2.height &&
                rect1.y + rect1.height > rect2.y
            );
        }

        function drawStartScreen() {
            ctx.fillStyle = "#535353";
            ctx.font = "20px 'Courier New'";
            ctx.textAlign = "center";
            ctx.fillText("PRESS SPACEBAR OR CLICK TO START", canvas.width / 2, canvas.height / 2);
        }

        function loop() {
            if (!isPlaying) return;

            frameCount++;
            gameSpeed += 0.001; // Gradual difficulty increase

            ctx.clearRect(0, 0, canvas.width, canvas.height);

            // Clouds update and draw
            spawnClouds();
            clouds.forEach((cloud, index) => {
                cloud.update();
                cloud.draw();
                if (cloud.x + cloud.width < 0) clouds.splice(index, 1);
            });

            drawGround();

            // Kangaroo physics
            kangaroo.vy += kangaroo.gravity;
            kangaroo.y += kangaroo.vy;

            const groundLevel = kangaroo.isDucking ? 180 : 160;
            if (kangaroo.y > groundLevel) {
                kangaroo.y = groundLevel;
                kangaroo.vy = 0;
                kangaroo.isJumping = false;
            }

            drawKangaroo();

            // Obstacles update and draw

            spawnObstacles();
            obstacles.forEach((obs, index) => {
                obs.update();
                obs.draw();

                if (checkCollision(kangaroo, obs)) {
                    isGameOver = true;
                    isPlaying = false;
                }

                if (obs.x + obs.width < 0) {
                    obstacles.splice(index, 1);
                    score += 10;
                    if (score > highScores) highScore = score;
                }
            });

            // Scoreboard UI on canvas
            ctx.fillStyle = "#535353";
            ctx.font = "16px 'Courier New'";
            ctx.textAlign = "right";
            ctx.fillText("HI: " + Math.floor(highScore) + "  SC: " + Math.floor(score), canvas.width - 20, 30);

            if (isGameOver) {
                ctx.fillStyle = "rgba(0, 0, 0, 0.6)";
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = "#ffffff";
                ctx.font = "24px 'Courier New'";
                ctx.textAlign = "center";
                ctx.fillText("GAME OVER - PRESS SPACE TO RESTART", canvas.width / 2, canvas.height / 2);
                return;
            }

            requestAnimationFrame(loop);
        }

        // Initial Render
        drawGround();
        drawKangaroo();
        drawStartScreen();
    </script>
</body>
</html>
"""


# --- Streamlit Application UI ---

def main():
    st.set_page_config(
        page_title="Kangaroo Hopper (Dino Game Clone)",
        page_icon="🦘",
        layout="centered"
    )

    st.title("🦘 Kangaroo Hopper Game")
    st.markdown(
        "A classic infinite runner game inspired by the legendary Google Chrome Dino game, "
        "featuring a jumping kangaroo avoiding obstacles in the outback!"
    )

    score_manager = GameScoreManager()

    # Sidebar controls & comparison
    with st.sidebar:
        st.header("🎮 Game Controls")
        st.info(
            "**How to Play:**\n"
            "- Click inside the game window first to focus.\n"
            "- Press **SPACEBAR** or **UP ARROW** to Jump.\n"
            "- Press **DOWN ARROW** to Duck.\n"
            "- Avoid incoming bushes and obstacles!"
        )

        st.markdown("---")
        st.subheader("📊 Google Dino vs Kangaroo")
        st.markdown(
            "| Feature | Google Dino | Kangaroo Hopper |\n"
            "| :--- | :--- | :--- |\n"
            "| **Protagonist** | T-Rex Dinosaur | Australian Kangaroo |\n"
            "| **Environment** | Desert / Night | Outback / Clouds |\n"
            "| **Controls** | Space / Down | Space / Up / Down |\n"
            "| **Engine** | HTML5 Canvas | HTML5 Canvas |\n"
            "| **Difficulty** | Progressive | Progressive |"
        )

        st.markdown("---")
        st.subheader("🏆 High Scores")
        high_score = score_manager.get_high_score()
        st.metric(label="Global Best Score", value=high_score)

        with st.form("score_submit_form"):
            st.markdown("**Record Your Score**")
            player_name = st.text_input("Player Name", "Outback Explorer")
            recorded_score = st.number_input("Score Achieved", min_value=0, step=10, value=0)
            submit_score = st.form_submit_button("Save Score")

            if submit_score:
                score_manager.save_score(player_name, int(recorded_score))
                st.success(f"Score of {recorded_score} saved for {player_name}!")

    # Main Game Area
    st.subheader("Play Area")
    components.html(KANGAROO_GAME_HTML, height=310, scrolling=False)

    # Leaderboard section
    st.markdown("---")
    st.subheader("Leaderboard")
    scores = score_manager.load_scores()
    if scores:
        st.dataframe(scores, use_container_width=True)
    else:
        st.info(
            "No scores recorded yet! Play the game, achieve a high score, "
            "and record it using the sidebar form."
        )

if __name__ == "__main__":
    main()