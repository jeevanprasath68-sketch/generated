import streamlit as st
import random
from enum import Enum
from typing import List, Tuple, Optional

class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)

class GameStatus(Enum):
    IDLE = "IDLE"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    GAME_OVER = "GAME_OVER"

class SnakeGame:
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
        self.high_score = getattr(self, 'high_score', 0)
        self.status = GameStatus.IDLE

    def _spawn_food(self) -> Tuple[int, int]:
        while True:
            pos = (random.randint(0, self.width - 1), random.randint(0, self.height - 1))
            if not hasattr(self, 'snake') or pos not in self.snake:
                return pos

    def change_direction(self, new_dir: Direction):
        # Prevent 180-degree immediate turns
        current = self.direction
        if (
            (new_dir == Direction.UP and current != Direction.DOWN) or
            (new_dir == Direction.DOWN and current != Direction.UP) or
            (new_dir == Direction.LEFT and current != Direction.RIGHT) or
            (new_dir == Direction.RIGHT and current != Direction.LEFT)
        ):
            self.next_direction = new_dir

    def update(self) -> GameStatus:
        if self.status != GameStatus.PLAYING:
            return self.status

        self.direction = self.next_direction
        head_x, head_y = self.snake[0]
        dx, dy = self.direction.value
        new_head = (head_x + dx, head_y + dy)

        # Check wall collisions
        if not (0 <= new_head[0] < self.width and 0 <= new_head[1] < self.height):
            self.status = GameStatus.GAME_OVER
            self._update_high_score()
            return self.status

        # Check self collisions
        if new_head in self.snake:
            self.status = GameStatus.GAME_OVER
            self._update_high_score()
            return self.status

        self.snake.insert(0, new_head)

        # Check food collision
        if new_head == self.food:
            self.score += 10
            self.food = self._spawn_food()
        else:
            self.snake.pop()

        return self.status

    def _update_high_score(self):
        if self.score > self.high_score:
            self.high_score = self.score


def render_board_html(game: SnakeGame) -> str:
    cell_size = 20
    board_width = game.width * cell_size
    board_height = game.height * cell_size

    html = f'''
    <div style="width: {board_width}px; height: {board_height}px; background-color: #1e1e1e; position: relative; border: 2px solid #333; margin: 0 auto;">
    '''

    # Render food
    fx, fy = game.food
    html += f'''
    <div style="position: absolute; left: {fx * cell_size}px; top: {fy * cell_size}px; width: {cell_size}px; height: {cell_size}px; background-color: #ff5555; border-radius: 50%;"></div>
    '''

    # Render snake
    for i, (sx, sy) in enumerate(game.snake):
        color = '#50fa7b' if i == 0 else '#8be9fd'
        html += f'''
        <div style="position: absolute; left: {sx * cell_size}px; top: {sy * cell_size}px; width: {cell_size - 1}px; height: {cell_size - 1}px; background-color: {color}; border-radius: 4px;"></div>
        '''

    html += '</div>'
    return html


def main():
    st.set_page_config(page_title="Classic Snake Game", page_icon="🐍", layout="centered")

    st.title("🐍 Classic Snake Game in Streamlit")
    st.write("Use the buttons or keyboard shortcuts to control the snake. Eat the red food to grow and score points!")

    # Initialize Game State
    if 'game' not in st.session_state:
        st.session_state.game = SnakeGame(width=20, height=20)

    game: SnakeGame = st.session_state.game

    # Sidebar controls & info
    with st.sidebar:
        st.header("🎮 Controls")
        col1, col2, col3 = st.columns(3)
        with col2:
            if st.button("⬆️ UP", use_container_width=True):
                game.change_direction(Direction.UP)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("⬅️ LEFT", use_container_width=True):
                game.change_direction(Direction.LEFT)
        with col2:
            if st.button("⏸️ PAUSE", use_container_width=True):
                game.status = GameStatus.PAUSED if game.status == GameStatus.PLAYING else GameStatus.PLAYING
        with col3:
            if st.button("➡️ RIGHT", use_container_width=True):
                game.change_direction(Direction.RIGHT)

        col1, col2, col3 = st.columns(3)
        with col2:
            if st.button("⬇️ DOWN", use_container_width=True):
                game.change_direction(Direction.DOWN)

        st.markdown("---")
        if st.button("🚀 Start / Restart Game", use_container_width=True):
            game.reset()
            game.status = GameStatus.PLAYING
            st.rerun()

        st.markdown("---")
        st.metric("Current Score", game.score)
        st.metric("High Score", game.high_score)
        st.metric("Game Status", game.status.value)

    # Main panel game rendering
    cols = st.columns([3, 1])
    with cols[0]:
        board_html = render_board_html(game)
        st.markdown(board_html, unsafe_allow_html=True)

    with cols[1]:
        st.subheader("Instructions")
        st.markdown(""")
        1. Click **Start / Restart Game**.
        2. Use directional buttons to steer.
        3. Avoid hitting walls and yourself!
        """)

    # Auto-tick loop for game progression when playing
    if game.status == GameStatus.PLAYING:
        import time
        time.sleep(0.15)  # Tick speed
        game.update()
        st.rerun()

if __name__ == '__main__':
    main()