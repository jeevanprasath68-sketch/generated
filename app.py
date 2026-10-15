import random
import time
from typing import List, Tuple
import streamlit as st

# --- Core Business Logic & Models ---

class Direction:
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

class SnakeGameEngine:
    def __init__(self, width: int = 20, height: int = 20):
        self.width = width
        self.height = height
        self.reset()

    def reset(self):
        # Initial snake in the middle
        start_x = self.width // 2
        start_y = self.height // 2
        self.snake: List[Tuple[int, int]] = [
            (start_x, start_y),
            (start_x - 1, start_y),
            (start_x - 2, start_y)
        ]
        self.direction = Direction.RIGHT
        self.next_direction = Direction.RIGHT
        self.score = 0
        self.game_over = False
        self.paused = False
        self.food = self._spawn_food()

    def _spawn_food(self) -> Tuple[int, int]:
        while True:
            fx = random.randint(0, self.width - 1)
            fy = random.randint(0, self.height - 1)
            if (fx, fy) not in self.snake:
                return (fx, fy)

    def change_direction(self, new_direction: Tuple[int, int]):
        # Prevent 180-degree immediate turns
        current = self.direction
        if (new_direction[0] * -1, new_direction[1] * -1) != current:
            self.next_direction = new_direction

    def step(self):
        pass

    def update(self) -> bool:
        if self.game_over or self.paused:
            return False

        self.direction = self.next_direction
        head_x, head_y = self.snake[0]
        dx, dy = self.direction
        new_head = (head_x + dx, head_y + dy)

        # Wall collision
        if not (0 <= new_head[0] < self.width and 0 <= new_head[1] < self.height):
            self.game_over = True
            return False

        # Self collision
        if new_head in self.snake:
            self.game_over = True
            return False

        self.snake.insert(0, new_head)

        # Food collision
        if new_head == self.food:
            self.score += 10
            self.food = self._spawn_food()
        else:
            self.snake.pop()

        return True

    def render_board_grid(self) -> List[List[str]]:
        # Grid representation: '.' for empty, 'S' for snake body, 'H' for head, 'F' for food
        grid = [['.' for _ in range(self.width)] for _ in range(self.height)]
        
        # Place food
        fx, fy = self.food
        grid[fy][fx] = 'F'

        # Place snake body
        for i, (sx, sy) in enumerate(self.snake):
            if 0 <= sx < self.width and 0 <= sy < self.height:
                grid[sy][sx] = 'H' if i == 0 else 'S'

        return grid


# --- Streamlit UI Layer ---

def main():
    st.set_page_config(page_title="Classic Snake Game", page_icon="🐍", layout="centered")

    st.title("🐍 Classic Snake Game in Streamlit")
    st.markdown("Use the control buttons below to steer the snake. Eat the food (`🍎`) to grow and score points! Avoid hitting the walls and yourself (`🟩`).")

    # Initialize game state in session
    if "game" not in st.session_state:
        st.session_state.game = SnakeGameEngine(width=15, height=15)
        st.session_state.speed = 0.4

    game: SnakeGameEngine = st.session_state.game

    # Sidebar settings
    st.sidebar.header("Game Controls & Settings")
    
    if st.sidebar.button("🔄 Restart Game"):
        game.reset()
        st.rerun()

    st.session_state.speed = st.sidebar.slider("Game Speed (sec/step)", 0.1, 1.0, 0.3, 0.05)

    col_k1, col_k2, col_k3 = st.columns([1, 1, 1])
    
    # Button controls handlers
    with col_k2:
        if st.button("⬆️ UP", use_container_width=True):
            game.change_direction(Direction.UP)
            game.update()
            st.rerun()

    col_l1, col_l2, col_l3 = st.columns([1, 1, 1])
    with col_l1:
        if st.button("⬅️ LEFT", use_container_width=True):
            game.change_direction(Direction.LEFT)
            game.update()
            st.rerun()
    with col_l2:
        if st.button("⏸️ PAUSE/STEP", use_container_width=True):
            if not game.game_over:
                game.update()
                st.rerun()
    with col_l3:
        if st.button("➡️ RIGHT", use_container_width=True):
            game.change_direction(Direction.RIGHT)
            game.update()
            st.rerun()

    with col_k2:
        if st.button("⬇️ DOWN", use_container_width=True):
            game.change_direction(Direction.DOWN)
            game.update()
            st.rerun()

    # Score metrics
    metric_col1, metric_col2 = st.columns(2)
    metric_col1.metric("Score", game.score)
    status = "Game Over 💀" if game.game_over else ("Paused ⏸️" if game.paused else "Playing 🟢")
    metric_col2.metric("Status", status)

    if game.game_over:
        st.error("Game Over! Click 'Restart Game' in the sidebar to play again.")

    # Render board visually using colored markdown/HTML grid or text representation
    grid = game.render_board_grid()
    
    # Emoji map for human readability
    mapping = {
        '.': '⬛',
        'S': '🟩',
        'H': '🟢',
        'F': '🍎'
    }

    board_html = "<div style='font-family: monospace; font-size: 24px; line-height: 1.2; text-align: center;'>"
    for row in grid:
        board_html += "".join([mapping.get(cell, '⬛') for cell in row]) + "<br>"
    board_html += "</div>"

    st.markdown(board_html, unsafe_allow_html=True)

if __name__ == "__main__":
    main()