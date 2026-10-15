import streamlit as st
import json
import time
from typing import Dict, Any, List

# --- Core Business Logic ---

class KangarooGameEngine:
    """Core game engine managing state, physics, obstacles, and scoring."""
    def __init__(self, gravity: float = 0.6, jump_strength: float = -12.0):
        self.gravity = gravity
        self.jump_strength = jump_strength
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.high_score = 0
        self.game_over = False
        self.is_jumping = False
        self.kangaroo_y = 0.0
        self.kangaroo_vy = 0.0
        self.obstacles: List[Dict[str, Any]] = []
        self.speed = 5.0
        self.ticks = 0

    def update(self, action: str) -> Dict[str, Any]:
        """Advance game state by one tick given an action ('jump', 'none')."""
        if self.game_over:
            return self.get_state()

        self.ticks += 1
        if self.ticks % 100 == 0:
            self.speed += 0.5  # Increase difficulty over time

        # Handle Jump action
        if action == 'jump' and not self.is_jumping:
            self.is_jumping = True
            self.kangaroo_vy = self.jump_strength

        # Apply gravity physics
        if self.is_jumping:
            self.kangaroo_y += self.kangaroo_vy
            self.kangaroo_vy += self.gravity
            if self.kangaroo_y >= 0.0:
                self.kangaroo_y = 0.0
                self.is_jumping = False
                self.kangaroo_vy = 0.0

        # Update obstacles
        for obs in self.obstacles:
            obs['x'] -= self.speed

        # Remove off-screen obstacles and update score
        self.obstacles = [obs for obs in self.obstacles if obs['x'] > -50]
        
        # Spawn new obstacles
        if not self.obstacles or self.obstacles[-1]['x'] < 400 - 150:
            import random
            if random.random() < 0.03:
                obs_type = random.choice(['bush', 'rock'])
                self.obstacles.append({'x': 600, 'type': obs_type, 'width': 30, 'height': 40})

        # Collision detection
        for obs in self.obstacles:
            # Kangaroo bounding box: x: 50 to 80, y: kangaroo_y to kangaroo_y + 50
            # Obstacle bounding box: x: obs['x'] to obs['x'] + 30, y: 0 to 40
            k_left, k_right = 50, 80
            k_top = 150 + self.kangaroo_y
            k_bottom = k_top + 50

            o_left, o_right = obs['x'], obs['x'] + obs['width']
            o_top = 200 - obs['height']
            o_bottom = 200

            if (k_right > o_left and k_left < o_right and k_bottom > o_top and k_top < o_bottom):
                self.game_over = True
                if self.score > self.high_score:
                    self.high_score = self.score

        if not self.game_over:
            self.score += 1

        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        return {
            "score": self.score,
            "high_score": self.high_score,
            "game_over": self.game_over,
            "kangaroo_y": self.kangaroo_y,
            "is_jumping": self.is_jumping,
            "obstacles": self.obstacles,
            "speed": self.speed
        }


# --- Streamlit UI Application ---

def main():
    st.set_page_config(page_title="Kangaroo Runner Game", page_icon="🦘", layout="centered")
    
    st.title("🦘 Kangaroo Runner Game")
    st.markdown("Help the Kangaroo jump over obstacles across the Australian Outback! Press **Spacebar** or click **Jump** to leap.")

    # Initialize game engine in session state
    if 'engine' not in st.session_state:
        st.session_state.engine = KangarooGameEngine()

    engine: KangarooGameEngine = st.session_state.engine

    # Sidebar controls
    st.sidebar.header("Game Controls & Stats")
    difficulty = st.sidebar.selectbox("Select Difficulty", ["Normal", "Hard", "Extreme"], index=0)
    
    if difficulty == "Hard":
        engine.gravity = 0.8
        engine.jump_strength = -14.0
    elif difficulty == "Extreme":
        engine.gravity = 1.0
        engine.jump_strength = -15.0
    else:
        engine.gravity = 0.6
        engine.jump_strength = -12.0

    if st.sidebar.button("🔄 Reset Game"):
        engine.reset()
        st.success("Game Reset!")
        st.rerun()

    # Metrics display
    col1, col2, col3 = st.columns(3)
    state = engine.get_state()
    col1.metric("Current Score", state["score"])
    col2.metric("High Score", state["high_score"])
    col3.metric("Speed", f"{state['speed']:.1f}x")

    # Game Canvas HTML/JS Component
    game_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
      body {{ margin: 0; background: #f7f9fa; font-family: sans-serif; display: flex; justify-content: center; }}
      canvas {{ background: linear-gradient(to bottom, #87CEEB, #E0F6FF); border-bottom: 4px solid #8B4513; border-radius: 8px; }}
    </style>
    </head>
    <body>
      <canvas id="gameCanvas" width="600" height="250"></canvas>
      <script>
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        
        let kY = {state['kangaroo_y']};
        let isJumping = {'true' if state['is_jumping'] else 'false'};
        let obstacles = {json.dumps(state['obstacles'])};
        let gameOver = {'true' if state['game_over'] else 'false'};
        let score = {state['score']};

        function draw() {{
          ctx.clearRect(0, 0, canvas.width, canvas.height);

          // Draw ground
          ctx.fillStyle = '#DEB887';
          ctx.fillRect(0, 200, canvas.width, 50);

          // Draw Kangaroo
          ctx.font = '35px Arial';
          ctx.fillText('🦘', 50, 200 + kY);

          // Draw obstacles
          obstacles.forEach(obs => {{
            ctx.font = '30px Arial';
            let emoji = obs.type === 'bush' ? '🌵' : '🪨';
            ctx.fillText(emoji, obs.x, 200);
          }});

          // Draw Score on canvas
          ctx.fillStyle = '#333';
          ctx.font = '16px Arial';
          ctx.fillText('Score: ' + score, 480, 30);

          if (gameOver) {{
            ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#fff';
            ctx.font = '30px Arial';
            ctx.fillText('GAME OVER - Press Reset', 130, 130);
          }}
        }}
        draw();
      </script>
    </body>
    </html>
    """

    st.components.v1.html(game_html, height=270)

    # Interactive Game Control Buttons
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🦘 JUMP!", use_container_width=True, type="primary"):
            engine.update('jump')
            st.rerun()
    with col_btn2:
        if st.button("⏩ Step / Run", use_container_width=True):
            engine.update('none')
            st.rerun()

    st.markdown("---")
    st.info("💡 **Tip:** Click **JUMP!** repeatedly or rapidly use **Step / Run** to advance the kangaroo and avoid the outback hazards!")

if __name__ == '__main__':
    main()