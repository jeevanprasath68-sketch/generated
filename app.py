import random
import time
from typing import List, Tuple
import streamlit as st
import streamlit.components.v1 as components

GRID_SIZE = 20

class SnakeGame:
    def __init__(self, width: int = GRID_SIZE, height: int = GRID_SIZE):
        self.width = width
        self.height = height
        self.reset()

    def reset(self):
        self.snake: List[Tuple[int, int]] = [
            (self.width // 2, self.height // 2),
            (self.width // 2, self.height // 2 + 1),
            (self.width // 2, self.height // 2 + 2)
        ]
        self.direction = "UP"
        self.next_direction = "UP"
        self.score = 0
        self.game_over = False
        self.spawn_food()

    def spawn_food(self):
        while True:
            fx = random.randint(0, self.width - 1)
            fy = random.randint(0, self.height - 1)
            if (fx, fy) not in self.snake:
                self.food = (fx, fy)
                break

    def change_direction(self, new_dir: str):
        opposites = {"UP": "DOWN", "DOWN": "UP", "LEFT": "RIGHT", "RIGHT": "LEFT"}
        if new_dir in opposites and opposites[new_dir] != self.next_direction:
            self.next_direction = new_dir

    def step(self):
        if self.game_over:
            return

        self.direction = self.next_direction
        hx, hy = self.snake[0]

        if self.direction == "UP":
            ny = hy - 1
            nx = hx
        elif self.direction == "DOWN":
            ny = hy + 1
            nx = hx
        elif self.direction == "LEFT":
            nx = hx - 1
            ny = hy
        elif self.direction == "RIGHT":
            nx = hx + 1
            ny = hy
        else:
            nx, ny = hx, hy

        # Wall collision
        if nx < 0 or nx >= self.width or ny < 0 or ny >= self.height:
            self.game_over = True
            return

        # Self collision
        if (nx, ny) in self.snake:
            self.game_over = True
            return

        new_head = (nx, ny)
        self.snake.insert(0, new_head)

        # Food collision
        if new_head == self.food:
            self.score += 10
            self.spawn_food()
        else:
            self.snake.pop()

def get_board_html(game: SnakeGame) -> str:
    cell_size = 20
    board_width = game.width * cell_size
    board_height = game.height * cell_size
    
    cells_html = ""
    for y in range(game.height):
        for x in range(game.width):
            pos = (x, y)
            bg = "#1e1e1e"
            if pos == game.food:
                bg = "#ff5252"
            elif pos == game.snake[0]:
                bg = "#4caf50"
            elif pos in game.snake:
                bg = "#81c784"
            cells_html += f'<div style="position:absolute; left:{x*cell_size}px; top:{y*cell_size}px; width:{cell_size-1}px; height:{cell_size-1}px; background:{bg}; border-radius:3px;"></div>'

    html_code = f"""
    <div id="game-container" tabindex="0" style="width: {board_width}px; height: {board_height}px; position: relative; background: #121212; border: 2px solid #333; outline: none; margin: 0 auto; border-radius: 6px;">
        {cells_html}
    </div>
    <script>
        const container = document.getElementById('game-container');
        container.focus();
        window.addEventListener('keydown', function(e) {{
            if(["Space","ArrowUp","ArrowDown","ArrowLeft","ArrowRight"].indexOf(e.code) > -1) {{
                e.preventDefault();
            }}
            let dir = "";
            if (e.key === "ArrowUp" || e.key === "w") dir = "UP";
            if (e.key === "ArrowDown" || e.key === "s") dir = "DOWN";
            if (e.key === "ArrowLeft" || e.key === "a") dir = "LEFT";
            if (e.key === "ArrowRight" || e.key === "d") dir = "RIGHT";
            
            if (dir !== "") {{
                window.parent.postMessage({{type: 'streamlit:setComponentValue', value: dir}}, '*');
            }}
        }});
    </script>
    """
    return html_code

def main():
    st.set_page_config(page_title="Streamlit Snake Game", page_icon="🐍", layout="centered")
    
    st.title("🐍 Classical Streamlit Snake Game")
    st.markdown("Use your **Arrow Keys** or **W, A, S, D** to control the snake. Eat red food to grow and score points! Avoid walls and yourself.")

    if "game" not in st.session_state:
        st.session_state.game = SnakeGame()

    game: SnakeGame = st.session_state.game

    col1, col2, col3 = st.columns(3)
    col1.metric("Score", game.score)
    col2.metric("Status", "Game Over 💀" if game.game_over else "Playing 🚀")
    col3.metric("Snake Length", len(game.snake))

    # Render keyboard component
    component_value = components.html(get_board_html(game), height=420, scrolling=False)

    # Control buttons fallback / manual triggers
    st.markdown("### Manual Controls")
    b1, b2, b3, b4 = st.columns(4)
    if b1.button("⬆️ Up"):
        game.change_direction("UP")
        game.step()
        st.rerun()
    if b2.button("⬇️ Down"):
        game.change_direction("DOWN")
        game.step()
        st.rerun()
    if b3.button("⬅️ Left"):
        game.change_direction("LEFT")
        game.step()
        st.rerun()
    if b4.button("➡️ Right"):
        game.change_direction("RIGHT")
        game.step()
        st.rerun()

    c_reset, c_step = st.columns(2)
    if c_reset.button("🔄 Reset Game"):
        game.reset()
        st.rerun()

    if not game.game_over:
        if c_step.button("⏩ Step Forward"):
            game.step()
            st.rerun()

if __name__ == "__main__":
    main()