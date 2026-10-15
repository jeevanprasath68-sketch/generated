import streamlit as st
import random
import time
from typing import List, Tuple, Optional

# --- Business Logic & Game Engine ---

class Direction:
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

class GameEngine:
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
        self.game_over = False
        self.paused = False

    def _spawn_food(self) -> Tuple[int, int]:
        while True:
            pos = (random.randint(0, self.width - 1), random.randint(0, self.height - 1))
            if not hasattr(self, 'snake') or pos not in self.snake:
                return pos

    def change_direction(self, new_direction: Tuple[int, int]):
        # Prevent 180-degree immediate turns
        current = self.direction
        if (new_direction[0] == -current[0] and new_direction[1] == -current[1]):
            return
        self.next_direction = new_direction

    def step(self):
        pass

    def update(self) -> bool:
        if self.game_over or self.paused:
            return False

        self.direction = self.next_direction
        head_x, head_y = self.snake[0]
        dir_x, dir_y = self.direction
        new_head = (head_x + dir_x, head_y + dir_y)

        # Check wall collision
        if not (0 <= new_head[0] < self.width and 0 <= new_head[1] < self.height):
            self.game_over = True
            return True

        # Check self collision
        if new_head in self.snake:
            self.game_over = True
            return True

        self.snake.insert(0, new_head)

        # Check food collision
        if new_head == self.food:
            self.score += 10
            self.food = self._spawn_food()
        else:
            self.snake.pop()

        return True

# --- Streamlit Frontend --- 

def render_grid(engine: GameEngine) -> str:
    grid = [[" " for _ in range(engine.width)] for _ in range(engine.height)]
    
    # Place food
    fx, fy = engine.food
    grid[fy][fx] = "🍎"
    
    # Place snake
    for i, (sx, sy) in enumerate(engine.snake):
        if 0 <= sx < engine.width and 0 <= sy < engine.height:
            grid[sy][sx] = "🟩" if i == 0 else "🟢"
            
    html_rows = []
    for row in grid:
        html_rows.append("".join([f"<span style='display:inline-block;width:20px;height:20px;text-align:center;'>{cell}</span>" for cell in row]))
    
    board_html = "<div style='font-family: monospace; line-height: 20px; background-color: #111; padding: 10px; border-radius: 8px; display: inline-block;'>" + "<br>".join(html_rows) + "</div>"
    return board_html

def main():
    st.set_page_config(page_title="Classic Snake Game", page_icon="🐍", layout="centered")
    
    st.title("🐍 Classic Snake Game in Streamlit")
    st.markdown("Use the directional buttons below or keyboard controls to guide the snake. Eat apples to grow and score points!")

    # Initialize session state for game engine
    if 'engine' not in st.session_state:
        st.session_state.engine = GameEngine(15, 15)
    
    engine: GameEngine = st.session_state.engine

    # Sidebar Controls & Settings
    st.sidebar.header("Game Controls")
    speed = st.sidebar.slider("Game Speed (sec/step)", min_value=0.1, max_value=1.0, value=0.3, step=0.05)
    
    if st.sidebar.button("🔄 Reset Game"):
        engine.reset()
        st.rerun()

    # Control Handlers
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("⬆️ UP", use_container_width=True):
            engine.change_direction(Direction.UP)
            engine.update()
            st.rerun()
            
    col4, col5, col6 = st.columns([1, 1, 1])
    with col4:
        if st.button("⬅️ LEFT", use_container_width=True):
            engine.change_direction(Direction.LEFT)
            engine.update()
            st.rerun()
    with col5:
        if st.button("⏸️ PAUSE / RESUME", use_container_width=True):
            engine.paused = not engine.paused
            st.rerun()
    with col6:
        if st.button("➡️ RIGHT", use_container_width=True):
            engine.change_direction(Direction.RIGHT)
            engine.update()
            st.rerun()
            
    with col2:
        if st.button("⬇️ DOWN", use_container_width=True):
            engine.change_direction(Direction.DOWN)
            engine.update()
            st.rerun()

    # Scoreboard metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Score", engine.score)
    m2.metric("Status", "Game Over 💀" if engine.game_over else ("Paused ⏸️" if engine.paused else "Playing 🎮"))
    m3.metric("Snake Length", len(engine.snake))

    # Render Board
    board_container = st.empty()
    board_container.markdown(render_grid(engine), unsafe_allow_html=True)

    if engine.game_over:
        st.error("Game Over! Click 'Reset Game' in the sidebar to play again.")
    elif not engine.paused:
        time.sleep(speed)
        engine.update()
        st.rerun()

if __name__ == '__main__':
    main()