import streamlit as st
import streamlit.components.v1 as components
import random
from typing import List, Tuple, Dict, Any

class SnakeGameEngine:
    """Core business logic engine for the Classical Snake Game."""
    def __init__(self, width: int = 20, height: int = 20):
        self.width = width
        self.height = height
        self.reset()

    def reset(self):
        """Resets the game state to initial values."""
        start_x = self.width // 2
        start_y = self.height // 2
        self.snake = [
            (start_x, start_y),
            (start_x - 1, start_y),
            (start_x - 2, start_y)
        ]
        self.direction = "RIGHT"
        self.next_direction = "RIGHT"
        self.score = 0
        self.game_over = False
        self.spawn_food()

    def spawn_food(self):
        """Spawns food at a random unoccupied grid coordinate."""
        while True:
            fx = random.randint(0, self.width - 1)
            fy = random.randint(0, self.height - 1)
            if (fx, fy) not in self.snake:
                self.food = (fx, fy)
                break

    def set_direction(self, new_dir: str):
        """Queues a new direction, preventing immediate 180-degree reversals."""
        opposites = {
            "UP": "DOWN",
            "DOWN": "UP",
            "LEFT": "RIGHT",
            "RIGHT": "LEFT"
        }
        if new_dir in opposites and opposites[new_dir] != self.direction:
            self.next_direction = new_dir

    def step(self) -> Dict[str, Any]:
        """Advances the game state by one tick."""
        if self.game_over:
            return self.get_state()

        self.direction = self.next_direction
        head_x, head_y = self.snake[0]

        dx, dy = 0, 0
        if self.direction == "UP":
            dy = -1
        elif self.direction == "DOWN":
            dy = 1
        elif self.direction == "LEFT":
            dx = -1
        elif self.direction == "RIGHT":
            dx = 1

        new_head = (head_x + dx, head_y + dy)

        # Wall collision
        if not (0 <= new_head[0] < self.width and 0 <= new_head[1] < self.height):
            self.game_over = True
            return self.get_state()

        # Self collision
        if new_head in self.snake:
            self.game_over = True
            return self.get_state()

        self.snake.insert(0, new_head)

        # Food consumption
        if new_head == self.food:
            self.score += 10
            self.spawn_food()
        else:
            self.snake.pop()

        return self.get_state()

    def get_state(self) -> Dict[str, Any]:
        """Returns the current state dictionary of the game."""
        return {
            "snake": self.snake,
            "food": self.food,
            "score": self.score,
            "game_over": self.game_over,
            "width": self.width,
            "height": self.height
        }

def render_game_component(game_state: Dict[str, Any], speed_ms: int):
    """Renders the interactive HTML5 Canvas game with real-time keyboard controls."""
    html_code = f"""
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
            height: 100vh;
            margin: 0;
        }} 
        canvas {{
            border: 4px solid #4e8cff;
            background-color: #1a1c23;
            box-shadow: 0px 0px 20px rgba(78, 140, 255, 0.4);
            border-radius: 8px;
        }}
        #info {{
            margin-top: 10px;
            font-size: 16px;
            color: #a0aec0;
        }}
    </style>
    </head>
    <body>
        <canvas id="gameCanvas" width="400" height="400"></canvas>
        <div id="info">Use Arrow Keys to Move | Space to Restart</div>

    <script>
        const canvas = document.getElementById("gameCanvas");
        const ctx = canvas.getContext("2d");
        
        const gridWidth = {game_state['width']};
        const gridHeight = {game_state['height']};
        const tileSize = canvas.width / gridWidth;

        let gameState = {str(game_state).replace("'", '"')};
        let speed = {speed_ms};

        function draw() {{
            ctx.fillStyle = "#1a1c23";
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            // Draw Grid Lines (subtle)
            ctx.strokeStyle = "#262938";
            ctx.lineWidth = 0.5;
            for (let i = 0; i <= gridWidth; i++) {{
                ctx.beginPath();
                ctx.moveTo(i * tileSize, 0);
                ctx.lineTo(i * tileSize, canvas.height);
                ctx.stroke();
            }}
            for (let j = 0; j <= gridHeight; j++) {{
                ctx.beginPath();
                ctx.moveTo(0, j * tileSize);
                ctx.lineTo(canvas.width, j * tileSize);
                ctx.stroke();
            }}

            // Draw Food
            ctx.fillStyle = "#ff4d4d";
            ctx.shadowBlur = 10;
            ctx.shadowColor = "#ff4d4d";
            ctx.fillRect(gameState.food[0] * tileSize + 2, gameState.food[1] * tileSize + 2, tileSize - 4, tileSize - 4);
            
            // Draw Snake
            ctx.shadowBlur = 5;
            gameState.snake.forEach((segment, index) => {{
                ctx.fillStyle = index === 0 ? "#4e8cff" : "#2ecc71";
                ctx.shadowColor = index === 0 ? "#4e8cff" : "#2ecc71";
                ctx.fillRect(segment[0] * tileSize + 1, segment[1] * tileSize + 1, tileSize - 2, tileSize - 2);
            }});

            ctx.shadowBlur = 0;

            if (gameState.game_over) {{
                ctx.fillStyle = "rgba(0, 0, 0, 0.75)";
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.fillStyle = "#ffffff";
                ctx.font = "bold 30px sans-serif";
                ctx.textAlign = "center";
                ctx.fillText("GAME OVER", canvas.width / 2, canvas.height / 2 - 10);
                ctx.font = "16px sans-serif";
                ctx.fillText("Press SPACE to restart", canvas.width / 2, canvas.height / 2 + 25);
            }}
        }}

        window.addEventListener("keydown", e => {{
            if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " "].includes(e.key)) {{
                e.preventDefault();
            }}
            
            let dir = null;
            if (e.key === "ArrowUp") dir = "UP";
            if (e.key === "ArrowDown") dir = "DOWN";
            if (e.key === "ArrowLeft") dir = "LEFT";
            if (e.key === "ArrowRight") dir = "RIGHT";
            
            if (dir) {{
                window.parent.postMessage({type: "streamlit:setComponentValue", value: {action: "dir", direction: dir}}, "*");
            }}

            if (e.key === " " && gameState.game_over) {{
                window.parent.postMessage({type: "streamlit:setComponentValue", value: {action: "restart"}}, "*");
            }}
        }});

        // Auto tick interval loop
        setInterval(() => {{
            if (!gameState.game_over) {{
                window.parent.postMessage({type: "streamlit:setComponentValue", value: {action: "tick"}}, "*");
            }}
        }}, speed);

        draw();
    </script>
    </body>
    </html>
    """
    return components.html(html_code, height=450, width=420)

def main():
    st.set_page_config(page_title="Classical Snake Game", page_icon="🐍", layout="centered")

    st.title("🐍 Classical Snake Game")
    st.markdown("Experience the retro arcade classic built with Streamlit. Use your **Keyboard Arrow Keys** to steer the snake. Eat food, grow longer, and avoid walls and your own tail!")

    # Sidebar Configuration
    st.sidebar.header("Game Controls & Settings")
    speed_setting = st.sidebar.selectbox("Difficulty / Speed", ["Normal", "Fast", "Expert"], index=0)
    speed_map = {"Normal": 150, "Fast": 100, "Expert": 70}
    current_speed = speed_map[speed_setting]

    if st.sidebar.button("Restart Game"):
        st.session_state.game = SnakeGameEngine()
        st.rerun()

    # Initialize Game State in Streamlit session
    if "game" not in st.session_state:
        st.session_state.game = SnakeGameEngine()

    game: SnakeGameEngine = st.session_state.game

    # Metrics KPI Display
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Current Score", value=game.score)
    with col2:
        st.metric(label="Snake Length", value=len(game.snake))
    with col3:
        status = "Game Over ❌" if game.game_over else "Playing 🟢"
        st.metric(label="Status", value=status)

    # Render the interactive component and catch client events
    val = render_game_component(game.get_state(), current_speed)

    # Event handler bridge from JS component
    if val and isinstance(val, dict):
        action = val.get("action")
        if action == "dir":
            game.set_direction(val.get("direction"))
            st.rerun()
        elif action == "tick":
            game.step()
            st.rerun()
        elif action == "restart":
            game.reset()
            st.rerun()

    # Manual fallback controls for accessibility
    st.markdown("### Manual Controls (Fallback)")
    b1, b2, b3 = st.columns([1, 1, 1])
    with b2:
        if st.button("⬆️ UP"):
            game.set_direction("UP")
            game.step()
            st.rerun()
    b4, b5, b6 = st.columns([3, 3, 3])
    with b4:
        if st.button("⬅️ LEFT"):
            game.set_direction("LEFT")
            game.step()
            st.rerun()
    with b5:
        if st.button("🔄 STEP / TICK"):
            game.step()
            st.rerun()
    with b6:
        if st.button("➡️ RIGHT"):
            game.set_direction("RIGHT")
            game.step()
            st.rerun()
    with b2:
        if st.button("⬇️ DOWN"):
            game.set_direction("DOWN")
            game.step()
            st.rerun()

if __name__ == "__main__":
    main()