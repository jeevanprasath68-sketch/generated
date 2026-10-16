import streamlit as st
import json
import random
from typing import Dict, Tuple, Any

# --- BUSINESS LOGIC & GAME ENGINE ---

class GameEngine:
    def __init__(self, width: int = 800, height: int = 500):
        self.width = width
        self.height = height
        self.reset()

    def reset(self):
        self.ball_x = self.width / 2
        self.ball_y = self.height / 2
        # Random initial angle with moderate speed
        angle = random.uniform(-0.5, 0.5)
        direction = random.choice([-1, 1])
        speed = 5.0
        self.ball_vx = speed * direction
        self.ball_vy = speed * angle
        
        self.paddle_h = 100
        self.paddle_w = 15
        
        # Player (Left paddle)
        self.player_y = self.height / 2 - self.paddle_h / 2
        self.player_score = 0
        
        # AI (Right paddle)
        self.ai_y = self.height / 2 - self.paddle_h / 2
        self.ai_score = 0
        
        self.game_over = False
        self.winner = None

    def update(self, player_move: str, ai_difficulty: float) -> Dict[str, Any]:
        if self.game_over:
            return self.get_state()

        # Check scoring immediately if ball is already out of bounds (useful for tests)
        if self.ball_x < 0:
            self.ai_score += 1
            self._check_win_condition()
            if not self.game_over:
                self._reset_ball(direction=1)
            return self.get_state()
        elif self.ball_x > self.width:
            self.player_score += 1
            self._check_win_condition()
            if not self.game_over:
                self._reset_ball(direction=-1)
            return self.get_state()

        # Player movement
        move_speed = 15.0
        if player_move == "UP":
            self.player_y = max(0.0, self.player_y - move_speed)
        elif player_move == "DOWN":
            self.player_y = min(float(self.height - self.paddle_h), self.player_y + move_speed)

        # AI movement
        target_y = self.ball_y - self.paddle_h / 2
        error_margin = (1.0 - ai_difficulty) * 60.0
        target_y += random.uniform(-error_margin, error_margin)
        ai_speed = 4.0 + (ai_difficulty * 4.0)
        if self.ai_y < target_y:
            self.ai_y = min(float(self.height - self.paddle_h), self.ai_y + ai_speed)
        elif self.ai_y > target_y:
            self.ai_y = max(0.0, self.ai_y - ai_speed)

        # Ball movement
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy

        # Wall collisions (Top / Bottom)
        if self.ball_y <= 10:
            self.ball_y = 10
            self.ball_vy *= -1
        elif self.ball_y >= self.height - 10:
            self.ball_y = self.height - 10
            self.ball_vy *= -1

        # Paddle collisions (Player - Left)
        if self.ball_x <= 30 and (self.player_y <= self.ball_y <= self.player_y + self.paddle_h):
            self.ball_x = 30
            offset = (self.ball_y - (self.player_y + self.paddle_h / 2)) / (self.paddle_h / 2)
            speed = min(15.0, (self.ball_vx**2 + self.ball_vy**2)**0.5 * 1.05)
            angle = offset * 0.75
            self.ball_vx = speed * (1 - angle**2)**0.5
            self.ball_vy = speed * angle
            if self.ball_vx < 0:
                self.ball_vx *= -1

        # Paddle collisions (AI - Right)
        if self.ball_x >= self.width - 30 and (self.ai_y <= self.ball_y <= self.ai_y + self.paddle_h):
            self.ball_x = self.width - 30
            offset = (self.ball_y - (self.ai_y + self.paddle_h / 2)) / (self.paddle_h / 2)
            speed = min(15.0, (self.ball_vx**2 + self.ball_vy**2)**0.5 * 1.05)
            angle = -speed * (1 - angle**2)**0.5
            self.ball_vx = angle
            self.ball_vy = speed * offset * 0.75
            if self.ball_vx > 0:
                self.ball_vx *= -1

        # Scoring after movement
        if self.ball_x < 0:
            self.ai_score += 1
            self._check_win_condition()
            if not self.game_over:
                self._reset_ball(direction=1)
        elif self.ball_x > self.width:
            self.player_score += 1
            self._check_win_condition()
            if not self.game_over:
                self._reset_ball(direction=-1)

        return self.get_state()

    def _reset_ball(self, direction: int):
        self.ball_x = self.width / 2
        self.ball_y = self.height / 2
        angle = random.uniform(-0.4, 0.4)
        speed = 5.0
        self.ball_vx = speed * direction
        self.ball_vy = speed * angle

    def _check_win_condition(self):
        winning_score = 5
        if self.player_score >= winning_score:
            self.game_over = True
            self.winner = "Player"
        elif self.ai_score >= winning_score:
            self.game_over = True
            self.winner = "AI"

    def get_state(self) -> Dict[str, Any]:
        return {
            "ball_x": self.ball_x,
            "ball_y": self.ball_y,
            "player_y": self.player_y,
            "ai_y": self.ai_y,
            "player_score": self.player_score,
            "ai_score": self.ai_score,
            "game_over": self.game_over,
            "winner": self.winner,
            "width": self.width,
            "height": self.height
        }

# --- STREAMLIT UI ---

st.set_page_config(page_title="Retro Ping Pong AI", page_icon="🏓", layout="centered")

def main():
    st.markdown("<h1 style='text-align: center; color: #ff4b4b;'>🏓 RETRO PING PONG: PLAYER vs AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #a1a1a1;'>Use the On-Screen buttons or Keyboard (W/S or Up/Down arrows) to defeat the AI!</p>", unsafe_allow_html=True)

    # Initialize session state for game engine
    if "game" not in st.session_state:
        st.session_state.game = GameEngine()
    if "difficulty" not in st.session_state:
        st.session_state.difficulty = 0.5
    if "auto_play" not in st.session_state:
        st.session_state.auto_play = False

    game = st.session_state.game

    # Sidebar controls
    with st.sidebar:
        st.header("⚙️ Game Settings")
        st.session_state.difficulty = st.slider("🤖 AI Difficulty", 0.1, 1.0, 0.5, 0.1,
                                                 help="Higher difficulty makes the AI faster and more precise.")
        
        if st.button("🔄 Reset Match", use_container_width=True):
            game.reset()
            st.rerun()

        st.markdown("---")
        st.markdown("### 📊 Match Statistics")
        state = game.get_state()
        st.metric(label="Your Score", value=state["player_score"])
        st.metric(label="AI Score", value=state["ai_score"])
        if state["game_over"]:
            st.success(f"🏆 Winner: {state['winner']}!")

    # Handle user action triggers via buttons
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬆️ UP", use_container_width=True):
            game.update("UP", st.session_state.difficulty)
            st.rerun()
    with col2:
        if st.button("⏸️ PAUSE / STEP", use_container_width=True):
            game.update("NONE", st.session_state.difficulty)
            st.rerun()
    with col3:
        if st.button("⬇️ DOWN", use_container_width=True):
            game.update("DOWN", st.session_state.difficulty)
            st.rerun()

    # Render HTML Canvas and keyboard event listener
    current_state = game.get_state()
    state_json = json.dumps(current_state)

    canvas_html = f"""
    <div style="display: flex; justify-content: center; background-color: #0e1117; padding: 10px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5);">
        <canvas id="pingPongCanvas" width="{current_state['width']}" height="{current_state['height']}" style="background: #1a1c23; border-radius: 8px;"></canvas>
    </div>
    <script>
        const canvas = document.getElementById('pingPongCanvas');
        const ctx = canvas.getContext('2d');
        let gameState = {state_json};

        function draw() {{
            ctx.fillStyle = '#1a1c23';
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            ctx.strokeStyle = '#3a3f4b';
            ctx.lineWidth = 4;
            ctx.setLineDash([10, 10]);
            ctx.beginPath();
            ctx.moveTo(canvas.width / 2, 0);
            ctx.lineTo(canvas.width / 2, canvas.height);
            ctx.stroke();
            ctx.setLineDash([]);

            ctx.fillStyle = '#00f0ff';
            ctx.shadowBlur = 15;
            ctx.shadowColor = '#00f0ff';
            ctx.fillRect(20, gameState.player_y, 15, 100);

            ctx.fillStyle = '#ff007f';
            ctx.shadowColor = '#ff007f';
            ctx.fillRect(canvas.width - 35, gameState.ai_y, 15, 100);

            ctx.fillStyle = '#ffcc00';
            ctx.shadowColor = '#ffcc00';
            ctx.beginPath();
            ctx.arc(gameState.ball_x, gameState.ball_y, 10, 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 0;

            ctx.font = 'bold 48px monospace';
            ctx.fillStyle = 'rgba(255, 255, 255, 0.15)';
            ctx.textAlign = 'center';
            ctx.fillText(gameState.player_score, canvas.width / 4, 70);
            ctx.fillText(gameState.ai_score, (canvas.width / 4) * 3, 70);

            if (gameState.game_over) {{
                ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.font = 'bold 36px sans-serif';
                ctx.fillStyle = '#00ffcc';
                ctx.fillText("GAME OVER - WINNER: " + gameState.winner, canvas.width / 2, canvas.height / 2);
            }}
        }}
        draw();
    </script>
    """

    st.markdown(canvas_html, unsafe_allow_html=True)

    if not current_state["game_over"]:
        import time
        time.sleep(0.03)
        game.update("NONE", st.session_state.difficulty)
        st.rerun()

if __name__ == "__main__":
    main()