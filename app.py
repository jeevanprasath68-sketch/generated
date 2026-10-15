import time
import random
from typing import Dict, List, Any, Optional
import streamlit as st

class KangorooGameEngine:
    """Core physics, state machine, and collision engine for the Kangoroo Game."""
    def __init__(self, gravity: float = 0.6, jump_velocity: float = -11.0, game_speed: float = 6.0):
        self.gravity = gravity
        self.jump_velocity = jump_velocity
        self.base_game_speed = game_speed
        self.reset()

    """Game reset method"""
    def reset(self):
        self.kangaroo_y = 0.0
        self.kangaroo_vy = 0.0
        self.is_jumping = False
        self.obstacles: List[Dict[str, float]] = []
        self.score = 0
        self.high_score = getattr(self, 'high_score', 0)
        self.game_over = False
        self.game_time = 0.0
        self.spawn_timer = 0.0

    def jump(self):
        """Initiate a jump if the kangaroo is on the ground."""
        if not self.is_jumping and not self.game_over:
            self.kangaroo_vy = self.jump_velocity
            self.is_jumping = True

    def update(self, dt: float = 1.0):
        """Update game physics and positions by one tick."""
        if self.game_over:
            return

        self.game_time += dt
        self.score += int(dt * 10)
        if self.score > self.high_score:
            self.high_score = self.score

        # Apply gravity
        self.kangaroo_vy += self.gravity
        self.kangaroo_y += self.kangaroo_vy

        # Ground collision
        if self.kangaroo_y >= 0.0:
            self.kangaroo_y = 0.0
            self.kangaroo_vy = 0.0
            self.is_jumping = False

        # Spawn obstacles
        self.spawn_timer += dt
        current_speed = self.base_game_speed + (self.score / 200.0)
        
        if self.spawn_timer >= random.uniform(25.0, 45.0) / current_speed:
            obstacle_type = random.choice(['bush', 'rock', 'baobab'])
            width = 25.0 if obstacle_type == 'bush' else (35.0 if obstacle_type == 'baobab' else 20.0)
            height = 30.0 if obstacle_type == 'baobab' else 20.0
            self.obstacles.append({
                'x': 400.0,
                'y': 0.0,
                'width': width,
                'height': height,
                'type': obstacle_type
            })
            self.spawn_timer = 0.0

        # Move obstacles
        remaining_obstacles = []
        for obs in self.obstacles:
            obs['x'] -= current_speed
            if obs['x'] > -50:
                remaining_obstacles.append(obs)

            # Check collision (Kangaroo box: x=50 to 80, y=kangaroo_y to kangaroo_y-40)
            # Obstacle box: x=obs['x'] to obs['x']+obs['width'], y=0 to -obs['height']
            k_left = 50.0
            k_right = 75.0
            k_bottom = self.kangaroo_y
            k_top = self.kangaroo_y - 40.0

            o_left = obs['x']
            o_right = obs['x'] + obs['width']
            o_bottom = 0.0
            o_top = -obs['height']

            if not (k_right < o_left or k_left > o_right or k_bottom < o_top or k_top > o_bottom):
                self.game_over = True

        self.obstacles = remaining_obstacles

    def get_render_state(self) -> Dict[str, Any]:
        """Returns serializable state for rendering."""
        return {
            'kangaroo_y': self.kangaroo_y,
            'is_jumping': self.is_jumping,
            'obstacles': self.obstacles,
            'score': self.score,
            'high_score': self.high_score,
            'game_over': self.game_over
        }


def render_game_canvas(state: Dict[str, Any]) -> str:
        """Generates an SVG string representing the game state visually."""
        k_y_svg = 150 + state['kangaroo_y']
        
        obstacles_svg = ""
        for obs in state['obstacles']:
            o_x = obs['x']
            o_type = obs['type']
            if o_type == 'bush':
                obstacles_svg += f'<rect x="{o_x}" y="130" width="{obs["width"]}" height="25" rx="8" fill="#2e7d32" />'
            elif o_type == 'baobab':
                obstacles_svg += f'<rect x="{o_x + 10}" y="110" width="15" height="40" fill="#795548" />'
                obstacles_svg += f'<circle cx="{o_x + 17.5}" cy="110" r="18" fill="#388e3c" />'
            else:
                obstacles_svg += f'<polygon points="{o_x},{155} {o_x + 10},{125} {o_x + 20},{155}" fill="#616161" />'

        svg = f'''
        <svg width="100%" height="220" viewBox="0 0 400 220" style="background: linear-gradient(to bottom, #e3f2fd, #bbdefb); border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <!-- Sun -->
            <circle cx="350" cy="40" r="22" fill="#ffeb3b" opacity="0.9" />
            
            <!-- Ground -->
            <line x1="0" y1="155" x2="400" y2="155" stroke="#8d6e63" stroke-width="4" />
            <rect x="0" y="157" width="400" height="63" fill="#d7ccc8" />

            <!-- Obstacles -->
            {obstacles_svg}

            <!-- Kangaroo -->
            <g transform="translate(50, {k_y_svg})">
                <!-- Body -->
                <ellipse cx="15" cy="-20" rx="14" ry="18" fill="#ffb74d" />
                <!-- Head -->
                <circle cx="22" cy="-38" r="10" fill="#ffb74d" />
                <!-- Ear -->
                <ellipse cx="26" cy="-50" rx="3" ry="8" fill="#ffa726" />
                <!-- Snout -->
                <ellipse cx="28" cy="-36" rx="4" ry="3" fill="#ffa726" />
                <!-- Tail -->
                <path d="M 2 -15 Q -10 -25 -6 -35" stroke="#ffb74d" stroke-width="5" fill="none" stroke-linecap="round" />
                <!-- Legs / Pouch -->
                <rect x="8" y="-10" width="12" height="10" rx="4" fill="#ffa726" />
                <circle cx="14" cy="-15" r="4" fill="#ffe0b2" />
            </g>

            <!-- Scoreboard -->
            <text x="20" y="30" font-family="monospace" font-size="18" font-weight="bold" fill="#37474f">HI {state["high_score"]:05d}  {state["score"]:05d}</text>
        </svg>
        '''
        return svg


def main():
    st.set_page_config(page_title="Kangoroo Jump Game", page_icon="🦘", layout="centered")

    st.title("🦘 Kangoroo Jump (Google Dino Clone)")
    st.markdown("Help the Outback Kangaroo dodge native Australian obstacles! Compare this gameplay mechanics with the classic Google Chrome Dino game.")

    # Initialize session state for game engine
    if 'engine' not in st.session_state:
        st.session_state.engine = KangorooGameEngine()
        st.session_state.playing = False

    engine: KangorooGameEngine = st.session_state.engine

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        if st.button("🦘 JUMP! (Space / Click)", use_container_width=True, type="primary"):
            engine.jump()
            if not st.session_state.playing and not engine.game_over:
                st.session_state.playing = True
    with col2:
        if st.button("🔄 Reset Game", use_container_width=True):
            engine.reset()
            st.session_state.playing = False
    with col3:
        difficulty = st.selectbox("Speed Mode", ["Normal", "Fast", "Extreme"], index=0)
        if difficulty == "Normal":
            engine.base_game_speed = 6.0
        elif difficulty == "Fast":
            engine.base_game_speed = 8.5
        else:
            engine.base_game_speed = 11.0

    # Game Container
    canvas_placeholder = st.empty()

    # Render current state
    state = engine.get_render_state()
    canvas_placeholder.markdown(render_game_canvas(state), unsafe_allow_html=True)

    # Metrics & Comparison
    m1, m2, m3 = st.columns(3)
    m1.metric("Current Score", state['score'])
    m2.metric("High Score", state['high_score'])
    m3.metric("Status", "💥 Game Over" if state['game_over'] else ("▶️ Running" if st.session_state.playing else "⏸️ Ready"))

    with st.expander("🔍 Compare with Google Dino Game"):
        st.markdown("""
        ### Google Chrome Dino Game vs. Kangoroo Jump Game
        | Feature | Google Chrome Dino | Kangoroo Jump Arcade |
        | :--- | :--- | :--- |
        | **Protagonist** | T-Rex Dinosaur | Australian Kangaroo 🦘 |
        | **Environment** | Prehistoric desert with cacti & Pterodactyls | Outback desert with bushes, rocks & baobab trees |
        | **Physics Engine** | Gravity, constant acceleration, ducking mechanics | Gravity, parabolic jump arcs, variable velocity |
        | **Speed Progression** | Increments gradually with distance score | Dynamic speed scaling based on score & mode selection |
        | **Tech Stack** | C++ / JS Canvas in Chromium Browser | Python backend + Streamlit Reactive UI & SVG rendering |
        """)

    # Automatic Game Loop if playing
    if st.session_state.playing and not engine.game_over:
        time.sleep(0.04) # ~25 FPS
        engine.update(dt=1.0)
        st.rerun()

if __name__ == '__main__':
    main()