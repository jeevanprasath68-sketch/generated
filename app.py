import streamlit as st
import random
import time
import json
from typing import List, Tuple, Dict, Any
from enum import Enum

# --- DOMAIN MODELS & BUSINESS LOGIC ---

class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

class GameStatus(Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    GAME_OVER = "GAME_OVER"

class SnakeGameEngine:
    def __init__(self, width: int = 20, height: int = 20):
        self.width = width
        self.height = height
        self.reset()

    def reset(self):
        self.snake: List[Tuple[int, int]] = [
            (self.width // 2, self.height // 2),
            (self.width // 2 - 1, self.height // 2),
            (self.width // 2 - 2, self.height // 2)
        ]
        self.direction = Direction.RIGHT
        self.next_direction = Direction.RIGHT
        self.food = self._spawn_food()
        self.score = 0
        self.status = GameStatus.IDLE

    def _spawn_food(self) -> Tuple[int, int]:
        while True:
            fx = random.randint(0, self.width - 1)
            fy = random.randint(0, self.height - 1)
            if (fx, fy) not in self.snake:
                return (fx, fy)

    def change_direction(self, new_dir: Direction):
        # Prevent 180-degree immediate turns
        curr_v = self.direction.value
        new_v = new_dir.value
        if curr_v[0] + new_v[0] != 0 or curr_v[1] + new_v[1] != 0:
            self.next_direction = new_dir

    def step(self):
        if self.status != GameStatus.RUNNING:
            return

        self.direction = self.next_direction
        head_x, head_y = self.snake[0]
        dx, dy = self.direction.value
        new_head = (head_x + dx, head_y + dy)

        # Wall collision
        if not (0 <= new_head[0] < self.width and 0 <= new_head[1] < self.height):
            self.status = GameStatus.GAME_OVER
            return

        # Self collision
        if new_head in self.snake:
            self.status = GameStatus.GAME_OVER
            return

        self.snake.insert(0, new_head)

        # Food collision
        if new_head == self.food:
            self.score += 10
            self.food = self._spawn_food()
        else:
            self.snake.pop()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "width": self.width,
            "height": self.height,
            "snake": self.snake,
            "food": self.food,
            "score": self.score,
            "status": self.status.value,
            "direction": self.direction.name
        }

# --- STREAMLIT WEB INTERFACE ---

def main():
    st.set_page_config(
        page_title="Classic Snake Game - Streamlit",
        page_icon="🐍",
        layout="centered"
    )

    st.title("🐍 Classic Snake Game in Streamlit")
    st.markdown(
        """
        Use the **Arrow Keys** (or **W, A, S, D**) on your keyboard to control the snake.
        Make sure you click inside the game canvas area or use the control buttons below if needed.
        """
    )

    # Initialize session state for game engine
    if "engine" not in st.session_state:
        st.session_state.engine = SnakeGameEngine(width=20, height=20)
        st.session_state.speed = 0.15

    engine: SnakeGameEngine = st.session_state.engine

    # Sidebar controls
    with st.sidebar:
        st.header("⚙️ Game Controls")
        
        speed_option = st.selectbox("Difficulty / Speed", ["Easy", "Normal", "Hard", "Expert"], index=1)
        speed_map = {"Easy": 0.25, "Normal": 0.15, "Hard": 0.09, "Expert": 0.05}
        st.session_state.speed = speed_map[speed_option]

        st.markdown("---")
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("▶️ Start / Resume", use_container_width=True):
                if engine.status in [GameStatus.IDLE, GameStatus.PAUSED, GameStatus.GAME_OVER]:
                    if engine.status == GameStatus.GAME_OVER:
                        engine.reset()
                    engine.status = GameStatus.RUNNING
                    st.rerun()
        with col_btn2:
            if st.button("⏸️ Pause", use_container_width=True):
                if engine.status == GameStatus.RUNNING:
                    engine.status = GameStatus.PAUSED
                    st.rerun()

        if st.button("🔄 Reset Game", use_container_width=True):
            engine.reset()
            st.rerun()

        st.markdown("---")
        st.markdown("### 🏆 Scorecard")
        st.metric(label="Current Score", value=engine.score)
        st.metric(label="Status", value=engine.status.value)

    # Handle directional button clicks from UI fallback if keyboard isn't preferred
    col_c1, col_c2, col_c3 = st.columns([1, 1, 1])
    with col_c2:
        sub_c1, sub_c2, sub_c3 = st.columns(3)
        with sub_c2:
            if st.button("⬆️"):
                engine.change_direction(Direction.UP)
        sub_c1, sub_c2, sub_c3 = st.columns(3)
        with sub_c1:
            if st.button("⬅️"):
                engine.change_direction(Direction.LEFT)
        with sub_c2:
            if st.button("⬇️"):
                engine.change_direction(Direction.DOWN)
        with sub_c3:
            if st.button("➡️"):
                engine.change_direction(Direction.RIGHT)

    # Render HTML Canvas for game grid
    grid_html = render_game_grid(engine)
    st.markdown(grid_html, unsafe_allow_html=True)

    # JavaScript keyboard event bridge
    js_code = """
    <script>
    const doc = window.parent.document;
    
    window.addEventListener('keydown', function(e) {
        if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight', ' '].indexOf(e.key) > -1) {
            e.preventDefault();
        }
    }, false);

    doc.addEventListener('keydown', function(e) {
        const key = e.key;
        let btnText = '';
        if (key === 'ArrowUp' || key === 'w' || key === 'W') btnText = '⬆️';
        if (key === 'ArrowDown' || key === 's' || key === 'S') btnText = '⬇️';
        if (key === 'ArrowLeft' || key === 'a' || key === 'A') btnText = '⬅️';
        if (key === 'ArrowRight' || key === 'd' || key === 'D') btnText = '➡️';

        if (btnText !== '') {
            const buttons = doc.querySelectorAll('button');
            for (let b of buttons) {
                if (b.innerText.includes(btnText)) {
                    b.click();
                    break;
                }
            }
        }
    });
    </script>
    """
    st.components.v1.html(js_code, height=0)

    # Game loop handling
    if engine.status == GameStatus.RUNNING:
        time.sleep(st.session_state.speed)
        engine.step()
        st.rerun()

def render_game_grid(engine: SnakeGameEngine) -> str:
    cell_size = 22
    width_px = engine.width * cell_size
    height_px = engine.height * cell_size

    board = [[ "empty" for _ in range(engine.width)] for _ in range(engine.height)]
    
    # Mark food
    fx, fy = engine.food
    board[fy][fx] = "food"

    # Mark snake
    for i, (sx, sy) in enumerate(engine.snake):
        if 0 <= sx < engine.width and 0 <= sy < engine.height:
            board[sy][sx] = "head" if i == 0 else "body"

    css = """
    <style>
    .snake-board {
        display: grid;
        grid-template-columns: repeat(%d, %dpx);
        grid-template-rows: repeat(%d, %dpx);
        gap: 1px;
        background-color: #1e1e1e;
        padding: 10px;
        border-radius: 10px;
        width: fit-content;
        margin: 0 auto;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    .snake-cell {
        width: %dpx;
        height: %dpx;
        border-radius: 3px;
    }
    .cell-empty { background-color: #2d2d2d; }
    .cell-head { background-color: #4CAF50; border: 1px solid #81C784; }
    .cell-body { background-color: #81C784; }
    .cell-food { background-color: #FF5252; border-radius: 50%%; }
    </style>
    <div class="snake-board">
    """ % (engine.width, cell_size, engine.height, cell_size, cell_size, cell_size)

    for row in board:
        for cell in row:
            css += f'<div class="snake-cell cell-{cell}"></div>'

    css += "</div>"
    return css

if __name__ == "__main__":
    main()