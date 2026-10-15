import streamlit as st
import random
import json
from typing import List, Tuple, Dict, Any

GRID_SIZE = 20
CELL_SIZE = 20

class SnakeGameEngine:
    def __init__(self, grid_size: int = GRID_SIZE):
        self.grid_size = grid_size
        self.reset()

    def reset(self):
        mid = self.grid_size // 2
        self.snake: List[Tuple[int, int]] = [
            (mid, mid),
            (mid - 1, mid),
            (mid - 2, mid)
        ]
        self.direction = "RIGHT"
        self.next_direction = "RIGHT"
        self.food = self._spawn_food()
        self.score = 0
        self.high_score = getattr(self, 'high_score', 0)
        self.game_over = False
        self.paused = False

    def _spawn_food(self) -> Tuple[int, int]:
        while True:
            pos = (random.randint(0, self.grid_size - 1), random.randint(0, self.grid_size - 1))
            if not hasattr(self, 'snake') or pos not in self.snake:
                return pos

    def set_direction(self, new_dir: str):
        opposites = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
        if new_dir in opposites and opposites[new_dir] != self.direction:
            self.next_direction = new_dir

    def step(self) -> None:
        pass # placeholder for type hint syntax if needed

    def update(self) -> Dict[str, Any]:
        if self.game_over or self.paused:
            return self.get_state()

        self.direction = self.next_direction
        head_x, head_y = self.snake[0]

        if self.direction == "UP":
            new_head = (head_x, head_y - 1)
        elif self.direction == "DOWN":
            new_head = (head_x, head_y + 1)
        elif self.direction == "LEFT":
            new_head = (head_x - 1, head_y)
        elif self.direction == "RIGHT":
            new_head = (head_x + 1, head_y)
        else:
            new_head = (head_x, head_y)

        # Wall collision
        if not (0 <= new_head[0] < self.grid_size and 0 <= new_head[1] < self.grid_size):
            self.game_over = True
            return self.get_state()

        # Self collision
        if new_head in self.snake:
            self.game_over = True
            return self.get_state()

        self.snake.insert(0, new_head)

        # Food collision
        if new_head == self.food:
            self.score += 10
            if self.score > self.high_score:
                self.high_score = self.score
            self.food = self._spawn_food()
        else:
            self.snake.pop()

        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        return {
            "snake": self.snake,
            "food": self.food,
            "score": self.score,
            "high_score": self.high_score,
            "game_over": self.game_over,
            "paused": self.paused,
            "grid_size": self.grid_size
        }

def render_ui():
    st.set_page_config(page_title="Classic Snake Game", page_icon="🐍", layout="centered")

    st.title("🐍 Classic Snake Game")
    st.markdown("Use your **Arrow Keys** or **W/A/S/D** to guide the snake. Eat red apples to grow and score points! Avoid walls and your own tail.")

    if 'engine' not in st.session_state:
        st.session_state.engine = SnakeGameEngine()

    engine: SnakeGameEngine = st.session_state.engine

    # Sidebar controls & stats
    with st.sidebar:
        st.header("Game Controls")
        speed = st.slider("Game Speed (ms per tick)", min_value=50, max_value=300, value=120, step=10)
        
        if st.button("🔄 Reset Game", use_container_width=True):
            engine.reset()
            st.rerun()

        st.markdown("---")
        st.markdown("### Live Stats")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Score", engine.score)
        with col2:
            st.metric("High Score", engine.high_score)

        st.markdown("---")
        st.markdown("### Instructions")
        st.info("Click inside the game board once to focus keyboard controls. Press Spacebar or toggle pause if supported.")

    # HTML5 Canvas game client
    canvas_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
      body {{
        background-color: #0e1117;
        color: #ffffff;
        font-family: sans-serif;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin: 0;
        padding: 10px;
      }} 
      canvas {{
        border: 4px solid #262730;
        background-color: #1a1c23;
        box-shadow: 0px 4px 20px rgba(0,0,0,0.5);
        border-radius: 8px;
      }} 
      #overlay {{
        position: absolute;
        text-align: center;
      }}
    </style>
    </head>
    <body>
      <div style="position: relative;">
        <canvas id="gameCanvas" width="400" height="400"></canvas>
      </div>
      <script>
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const gridSize = {GRID_SIZE};
        const tileSize = canvas.width / gridSize;

        let gameState = {{
          snake: {json.dumps(engine.snake)},
          food: {json.dumps(engine.food)},
          score: {engine.score},
          high_score: {engine.high_score},
          game_over: {'true' if engine.game_over else 'false'},
          paused: {'true' if engine.paused else 'false'}
        }};

        function draw() {{
          ctx.clearRect(0, 0, canvas.width, canvas.height);

          // Draw grid lines (subtle)
          ctx.strokeStyle = '#222530';
          ctx.lineWidth = 0.5;
          for (let i = 0; i <= gridSize; i++) {{
            ctx.beginPath();
            ctx.moveTo(i * tileSize, 0);
            ctx.lineTo(i * tileSize, canvas.height);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(0, i * tileSize);
            ctx.lineTo(canvas.width, i * tileSize);
            ctx.stroke();
          }}

          // Draw food
          ctx.fillStyle = '#ff4b4b';
          ctx.beginPath();
          let fx = gameState.food[0] * tileSize + tileSize / 2;
          let fy = gameState.food[1] * tileSize + tileSize / 2;
          ctx.arc(fx, fy, tileSize / 2 - 2, 0, Math.PI * 2);
          ctx.fill();

          // Draw snake
          gameState.snake.forEach((seg, index) => {{
            ctx.fillStyle = index === 0 ? '#00cc66' : '#00994d';
            ctx.fillRect(seg[0] * tileSize + 1, seg[1] * tileSize + 1, tileSize - 2, tileSize - 2);
          }});

          // Game Over overlay
          if (gameState.game_over) {{
            ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = '#ffffff';
            ctx.font = 'bold 28px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('GAME OVER', canvas.width / 2, canvas.height / 2 - 10);
            ctx.font = '16px sans-serif';
            ctx.fillText('Use sidebar to Reset', canvas.width / 2, canvas.height / 2 + 25);
          }}
        }}

        draw();

        window.addEventListener('keydown', e => {{
          if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " ", "w", "a", "s", "d"].includes(e.key)) {{
            e.preventDefault();
            window.parent.postMessage({{type: 'streamlit:set_direction', key: e.key}}, '*');
          }}
        }});
      </script>
    </body>
    </html>
    """

    st.components.v1.html(canvas_html, height=440)

    # Server-side tick loop handling
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        if st.button("▶️ Step / Advance Game", use_container_width=True):
            engine.update()
            st.rerun()

if __name__ == '__main__':
    render_ui()