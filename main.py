import tkinter as tk
from tkinter import ttk, messagebox
import os
import random
import time
import math
import colorsys
import concurrent.futures
import threading
import sys
import ast
import subprocess
import json

# --- CONSTANTS ---
DARK_BG = "#0d1117"
SIDEBAR_BG = "#161b22"
ACCENT = "#58a6ff"
TEXT_COLOR = "#c9d1d9"

# --- CONSTANTS ---
DARK_BG = "#0d1117"
SIDEBAR_BG = "#161b22"
ACCENT = "#58a6ff"
TEXT_COLOR = "#c9d1d9"

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        # Calculate tooltip position based on mouse coordinates
        x = event.x_root + 15
        y = event.y_root + 10
        
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True) # Removes window borders
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        # Match your engine's aesthetic
        label = tk.Label(self.tooltip_window, text=self.text, justify='left',
                         background="#161b22", relief='solid', borderwidth=1,
                         highlightbackground="#58a6ff", highlightcolor="#58a6ff", highlightthickness=1,
                         font=("Courier", 10), fg="#c9d1d9", padx=10, pady=5)
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

# --- THE GHOST RUNNER ---
# This code lives only in RAM. It never touches the hard drive.
RUNNER_CODE = """
import sys
import os
import json
import importlib

# Redirect student print() statements to the void
student_stdout = sys.stdout
sys.stdout = open(os.devnull, 'w')

def main():
    if len(sys.argv) < 2:
        return
        
    bot_name = sys.argv[1]
    
    try:
        bot_module = importlib.import_module(bot_name)
    except Exception:
        return

    # THE FIX: Persistent local memory so we don't have to send the whole board every tick
    local_board = {}
    local_players = {}

    while True:
        line = sys.stdin.readline()
        if not line:
            break
            
        try:
            state = json.loads(line)
            
            # --- LIGHTNING FAST DELTA RECONSTRUCTION ---
            # 1. Apply only the new walls to our local board
            for coord in state["new_board"]:
                local_board[tuple(coord)] = 1
                
            # 2. Apply only the new trail steps to our local players
            safe_players_list = []
            for p in state["players"]:
                pid = p["id"]
                if p["is_new"]:
                    local_players[pid] = {
                        "id": pid, 
                        "name": p["name"], 
                        "pos": tuple(p["pos"]), 
                        "alive": p["alive"], 
                        "trail": [tuple(t) for t in p["new_trail"]]
                    }
                else:
                    local_players[pid]["pos"] = tuple(p["pos"])
                    local_players[pid]["alive"] = p["alive"]
                    for t in p["new_trail"]:
                        local_players[pid]["trail"].append(tuple(t))
                
                # Copy the dictionary so student bots can't corrupt the runner's memory
                safe_players_list.append(local_players[pid].copy())
            
            my_pos = tuple(state["pos"])
            
            move = bot_module.move(
                my_pos, 
                local_board.copy(), 
                state["dim"], 
                safe_players_list
            )
            
            student_stdout.write(str(move) + chr(10))
            student_stdout.flush()
            
        except Exception as e:
            student_stdout.write("UP" + chr(10))
            student_stdout.flush()

if __name__ == "__main__":
    main()
"""

# --- SECURITY SCANNER ---
def is_bot_safe(filepath):
    """Scans a python file for syntax errors, blatant illegal concepts, and network calls."""
    
    banned_modules = [
        'os', 'sys', 'subprocess', 'inspect', 'threading', 'multiprocessing', 
        'builtins', 'shutil', 'importlib', 'ctypes', 'pathlib', 'io', 
        'fileinput', 'codecs', 'tempfile', 'socket', 'urllib', 'http', 
        'requests', 'xmlrpc', 'ftplib', 'telnetlib', 'asyncio', 'pickle', 'marshal'
    ]
    
    banned_functions = [
        'exec', 'eval', 'compile', 'open', 'globals', 'locals', 
        'getattr', 'setattr', 'delattr', '__import__', 'dir', 'vars', 'type'
    ]
    
    banned_attributes = [
        '__traceback__', 'tb_frame', 'f_back', 'f_locals', 'f_globals', 
        '__dict__', '__class__', '__subclasses__', '__builtins__', '__code__',
        'write_text', 'write_bytes', 'write', '__getattribute__'
    ]
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
            
        for node in ast.walk(tree):
            # Block Standard Imports (import os)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] in banned_modules:
                        return False, f"Banned Import: '{alias.name}' is restricted."
                        
            # Block From Imports (from os import path)
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] in banned_modules:
                        return False, f"Banned Import: '{node.module}' is restricted."
                        
            # --- THE FIX: Check AST Names instead of AST Calls ---
            elif isinstance(node, ast.Name):
                # Blocks assignments like `get_module = __import__` 
                # and standalone references like `print(open)`
                if node.id in banned_functions:
                    return False, f"Banned Identifier: '{node.id}' usage is restricted."
                
                # Also blocks users from accessing __builtins__ directly as a name 
                # instead of just as an attribute
                if node.id in banned_attributes:
                    return False, f"Banned Identifier: '{node.id}' usage is restricted."
                    
            # Block Banned Attributes (obj.__dict__, obj.__class__)
            elif isinstance(node, ast.Attribute):
                if node.attr in banned_attributes:
                    return False, f"Banned Attribute: '.{node.attr}' access is restricted."
                    
        return True, "Safe"
    except Exception as e:
        return False, f"Syntax Error: {e}"

class SecureBotProcess:
    def __init__(self, bot_filename, bot_id, name, snapshots=None):
        self.bot_id = bot_id
        self.name = name
        self.alive = True
        
        # --- THE FIX: Persistent Thread & State Tracking ---
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.last_board_len = 0
        self.last_trail_lens = {}
        
        # --- SELF-HEALING PROTOCOL ---
        if snapshots and name in snapshots:
            filepath = f"{name}.py"
            pristine_code = snapshots[name]
            needs_healing = False
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    if f.read() != pristine_code:
                        needs_healing = True
            except FileNotFoundError:
                needs_healing = True
                
            if needs_healing:
                print(f"[SECURITY] Tampering detected in {filepath}! Healing file.")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(pristine_code)
        # -----------------------------
        
        self.process = subprocess.Popen(
            [sys.executable, "-c", RUNNER_CODE, bot_filename],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1 
        )

    def get_move(self, pos, board, dim, safe_players, timeout=2.0):
        if not self.alive:
            return "DEAD"

        # --- THE FIX: DELTA PACKAGING ---
        # Python 3 guarantees dictionary insertion order.
        # We slice the board to only grab the coordinates added since the last tick!
        current_board_coords = list(board.keys())
        new_board = current_board_coords[self.last_board_len:]
        self.last_board_len = len(current_board_coords)
        
        player_deltas = []
        for p in safe_players:
            pid = p["id"]
            last_len = self.last_trail_lens.get(pid, 0)
            new_trail = p["trail"][last_len:]
            self.last_trail_lens[pid] = len(p["trail"])
            
            player_deltas.append({
                "id": pid,
                "name": p["name"],
                "pos": p["pos"],
                "alive": p["alive"],
                "new_trail": new_trail,
                "is_new": last_len == 0
            })

        state = {
            "pos": pos,
            "new_board": new_board,
            "players": player_deltas,
            "dim": dim
        }
        
        try:
            self.process.stdin.write(json.dumps(state) + "\n")
            self.process.stdin.flush()
        except Exception:
            self.stop()
            return "DEAD"

        def read_pipe():
            try:
                raw_output = self.process.stdout.readline(100) 
                return raw_output.strip()
            except Exception:
                return "ERROR"

        try:
            # Re-use the persistent thread pool instead of spawning a new one
            future = self.executor.submit(read_pipe)
            move = future.result(timeout=timeout) 
            return move
        except concurrent.futures.TimeoutError:
            print(f"[{self.name}] TIMED OUT! Terminating process.")
            self.stop()
            return "DEAD"
        except Exception:
            self.stop()
            return "DEAD"

    def stop(self):
        self.alive = False
        try:
            self.process.kill()
            self.executor.shutdown(wait=False) # Safely release the persistent thread
        except Exception:
            pass

# --- UTILS ---
def generate_vibrant_color(index, total_players):
    h = (index / max(1, total_players)) % 1.0 
    s = 0.95 
    l = 0.55 
    r, g, b = [int(x * 255) for x in colorsys.hls_to_rgb(h, l, s)]
    return f"#{r:02x}{g:02x}{b:02x}"

def get_fade_color(hex_color, step, max_steps=6):
    if step >= max_steps: return hex_color
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    mix = 0.6 * (1.0 - (step / max_steps))
    r = min(255, int(r + (255 - r) * mix))
    g = min(255, int(g + (255 - g) * mix))
    b = min(255, int(b + (255 - b) * mix))
    return f'#{r:02x}{g:02x}{b:02x}'

def get_dead_color(hex_color):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    r, g, b = int(r * 0.2 + 40 * 0.8), int(g * 0.2 + 44 * 0.8), int(b * 0.2 + 52 * 0.8)
    return f'#{r:02x}{g:02x}{b:02x}'

def get_dim_color(hex_color):
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return f'#{int(r*0.15):02x}{int(g*0.15):02x}{int(b*0.15):02x}'

# --- HEADLESS TOURNAMENT WORKER ---
def headless_worker(grid_dim, selected_bots, code_snapshots): 
    _engine_board = {}
    _engine_players = []
    _dead_player_ids = set() 
    
    random.seed() 
    start_positions = [(random.randint(5, grid_dim-6), random.randint(5, grid_dim-6)) for _ in selected_bots]
    
    for i, bot_name in enumerate(selected_bots):
        # Pass the snapshots down to the subprocess
        bot_process = SecureBotProcess(bot_name, i + 1, bot_name, code_snapshots)
        pos = start_positions[i]
        _engine_players.append({
            'id': i + 1,
            'name': bot_name,
            'wrapper': bot_process,
            'move_func': bot_process.get_move, 
            'pos': pos,
            'trail': [pos],
            'alive': True,
            'survival': 0,
            'rank': 0
        })
        _engine_board[pos] = i + 1

    max_ticks = grid_dim * grid_dim
    tick = 0
    
    while tick < max_ticks:
        tick += 1
        
        for p in _engine_players:
            if p['id'] in _dead_player_ids:
                p['alive'] = False
                
        alive = [p for p in _engine_players if p['id'] not in _dead_player_ids]
        current_rank_score = len(alive)
        
        if len(alive) <= 1:
            if alive: alive[0]['rank'] = 1
            break

        safe_players = []
        for other_p in _engine_players:
            safe_players.append({
                "id": other_p['id'], "name": other_p['name'],
                "pos": other_p['pos'], "alive": other_p['alive'],
                "trail": list(other_p['trail'])
            })

        # --- PHASE 1: GATHER INTENTIONS (CONCURRENTLY!) ---
        intended_moves = {}
        
        # Helper function to run in a background I/O thread
        def fetch_move_headless(p):
            import time
            start_time = time.perf_counter()
            try:
                move = p['move_func'](p['pos'], _engine_board.copy(), grid_dim, safe_players)
                think_time = time.perf_counter() - start_time
                if move not in ["UP", "DOWN", "LEFT", "RIGHT"]:
                    raise ValueError(f"Illegal Move Command: {move}")
                
                x, y = p['pos']
                if move == "UP": y -= 1
                elif move == "DOWN": y += 1
                elif move == "LEFT": x -= 1
                elif move == "RIGHT": x += 1
                
                return p['id'], (x, y), None, think_time
            except Exception as e:
                think_time = time.perf_counter() - start_time
                return p['id'], "ERROR", e, think_time

        # Ask ALL bots for their move at the exact same time
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(alive)) as executor:
            futures = [executor.submit(fetch_move_headless, p) for p in alive]
            
            for future in concurrent.futures.as_completed(futures):
                pid, result, error, think_time = future.result()
                
                # Find the matching player in the main thread
                p = next(player for player in alive if player['id'] == pid)
                p['survival'] += 1
                
                # --- NEW: Track total computation time ---
                p['total_time'] = p.get('total_time', 0.0) + think_time
                p['move_count'] = p.get('move_count', 0) + 1
                # -----------------------------------------
                
                if result == "ERROR":
                    intended_moves[p['id']] = "ERROR" 
                    p['alive'] = False
                    _dead_player_ids.add(p['id']) 
                    p['rank'] = current_rank_score
                else:
                    intended_moves[p['id']] = result

        # --- PHASE 2: COUNT CLAIMS ON EACH SQUARE ---
        square_claims = {}
        for pos in intended_moves.values():
            if pos != "ERROR":
                square_claims[pos] = square_claims.get(pos, 0) + 1

        # --- PHASE 3: RESOLVE COLLISIONS AND UPDATE BOARD ---
        for p in alive:
            if p['id'] in _dead_player_ids: continue
            
            new_pos = intended_moves[p['id']]
            old_pos = p['pos']
            
            # 1. Head-to-head collision
            if square_claims[new_pos] > 1:
                p['alive'] = False
                _dead_player_ids.add(p['id']) 
                p['rank'] = current_rank_score
                continue
                
            # 2. Ghost pass-through collision
            ghost_swap = False
            for other_p in alive:
                if other_p['id'] != p['id'] and other_p['id'] not in _dead_player_ids:
                    if intended_moves.get(other_p['id']) == old_pos and other_p['pos'] == new_pos:
                        ghost_swap = True
                        break
                        
            if ghost_swap:
                p['alive'] = False
                _dead_player_ids.add(p['id']) 
                p['rank'] = current_rank_score
                continue

            # 3. Walls and Trails
            if not (0 <= new_pos[0] < grid_dim and 0 <= new_pos[1] < grid_dim) or new_pos in _engine_board:
                p['alive'] = False
                _dead_player_ids.add(p['id']) 
                p['rank'] = current_rank_score
            else:
                p['pos'] = new_pos
                p['trail'].append(new_pos)
                _engine_board[new_pos] = p['id']

    # Cleanup subprocesses
    for p in _engine_players:
        p['wrapper'].stop()

    _engine_secure_results_v9 = {}
    for p in _engine_players:
        _engine_secure_results_v9[p['name']] = {
            'rank': p['rank'], 
            'survival': p['survival'],
            'total_time': p.get('total_time', 0.0),
            'move_count': p.get('move_count', 0)
        }
        
    return _engine_secure_results_v9

# --- MAIN APP ---
class TronApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Tron AI Tournament Engine")
        try: self.root.state('zoomed')
        except tk.TclError: self.root.attributes('-zoomed', True)
        self.root.configure(bg=DARK_BG)
        
        self.grid_dim = 60
        self.cell_size = 10
        self.available_bots = {}
        self.bot_colors = {}
        self.dim_colors = {} 
        
        self._engine_players = []
        self._engine_board = {}
        self._dead_player_ids = set() 
        self.running = False
        self.is_paused = False
        
        self.setup_layout()
        self.refresh_bot_list()

    def select_all_bots(self):
        # Loop through all the checkbox variables and set them to True (checked)
        for var in self.available_bots.values():
            var.set(True)

    def deselect_all_bots(self):
        # Loop through all the checkbox variables and set them to False (unchecked)
        for var in self.available_bots.values():
            var.set(False)

    def setup_layout(self):
        self.sidebar = tk.Frame(self.root, width=280, bg=SIDEBAR_BG)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        # 1. TOP LABEL
        tk.Label(self.sidebar, text="TRON ENGINE", bg=SIDEBAR_BG, fg=ACCENT, font=("Courier", 18, "bold")).pack(pady=15)

        # 2. BOTTOM CONTROLS (Packed in reverse order from bottom up)
        tour_frame = tk.LabelFrame(self.sidebar, text="Tournament (Headless)", bg=SIDEBAR_BG, fg="gray")
        tour_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10) # Packed to BOTTOM
        
        r_frame = tk.Frame(tour_frame, bg=SIDEBAR_BG)
        r_frame.pack(fill=tk.X, padx=10, pady=2)
        tk.Label(r_frame, text="Rounds:", bg=SIDEBAR_BG, fg=TEXT_COLOR).pack(side=tk.LEFT)
        self.rounds_var = tk.StringVar(value="100")
        tk.Spinbox(r_frame, from_=1, to=1000, textvariable=self.rounds_var, width=5, bg=DARK_BG, fg="white").pack(side=tk.RIGHT)
        self.btn_tourney = tk.Button(tour_frame, text="RUN TOURNAMENT", command=self.start_tournament, bg="#a371f7", fg="white")
        self.btn_tourney.pack(fill=tk.X, padx=10, pady=5)

        vis_frame = tk.LabelFrame(self.sidebar, text="Visual Match", bg=SIDEBAR_BG, fg="gray")
        vis_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5) # Packed to BOTTOM
        
        tk.Button(vis_frame, text="START VISUAL", command=self.start_visual_match, bg="#238636", fg="white").pack(fill=tk.X, padx=10, pady=2)
        self.btn_pause = tk.Button(vis_frame, text="PAUSE", command=self.toggle_pause, bg="#21262d", fg=TEXT_COLOR)
        self.btn_pause.pack(fill=tk.X, padx=10, pady=2)
        self.btn_step = tk.Button(vis_frame, text="STEP FORWARD", command=self.step_forward, bg="#444c56", fg="white", state=tk.DISABLED)
        self.btn_step.pack(fill=tk.X, padx=10, pady=2)
                        
        self.show_names_var = tk.BooleanVar(value=False)
        tk.Checkbutton(vis_frame, text="Show Display Names", variable=self.show_names_var, bg=SIDEBAR_BG, fg=TEXT_COLOR, selectcolor=DARK_BG, activeforeground="white", highlightthickness=0, bd=0).pack(fill=tk.X, padx=10, pady=2)

        self.speed_var = tk.DoubleVar(value=1.0)
        tk.Scale(vis_frame, from_=0.25, to=25.0, resolution=0.25, variable=self.speed_var, orient=tk.HORIZONTAL, bg=SIDEBAR_BG, fg=TEXT_COLOR, label="Speed").pack(fill=tk.X, padx=10)

        tk.Button(self.sidebar, text="REFRESH & SCAN", command=self.refresh_bot_list, bg="#21262d", fg=TEXT_COLOR).pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5) # Packed to BOTTOM

        # 3. MIDDLE SCROLLABLE AREA (Takes up remaining space)
        tk.Label(self.sidebar, text="Available Bots", bg=SIDEBAR_BG, fg="gray").pack(anchor=tk.W, padx=10)
        
        # --- SELECT / DESELECT BUTTONS ---
        selection_btn_frame = tk.Frame(self.sidebar, bg=SIDEBAR_BG)
        selection_btn_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        btn_select_all = tk.Button(selection_btn_frame, text="Select All", bg="#2ea043", fg="white", command=self.select_all_bots, relief=tk.FLAT, font=("Courier", 9, "bold"))
        btn_select_all.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        btn_deselect_all = tk.Button(selection_btn_frame, text="Deselect All", bg="#da3633", fg="white", command=self.deselect_all_bots, relief=tk.FLAT, font=("Courier", 9, "bold"))
        btn_deselect_all.pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5, 0))
        # ---------------------------------

        # --- SCROLLABLE BOT LIST ---
        # 1. Container for the Canvas and Scrollbar
        self.bot_container = tk.Frame(self.sidebar, bg=SIDEBAR_BG)
        self.bot_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 2. The Canvas & Scrollbar
        self.bot_canvas = tk.Canvas(self.bot_container, bg=SIDEBAR_BG, highlightthickness=0)
        self.bot_scrollbar = tk.Scrollbar(self.bot_container, orient="vertical", command=self.bot_canvas.yview)
        
        # 3. The Inner Frame (Where the bots actually go)
        self.bot_scroll_frame = tk.Frame(self.bot_canvas, bg=SIDEBAR_BG)
        
        # 4. Bindings & Packing
        self.bot_scroll_frame.bind(
            "<Configure>",
            lambda e: self.bot_canvas.configure(scrollregion=self.bot_canvas.bbox("all"))
        )
        
        self.canvas_window = self.bot_canvas.create_window((0, 0), window=self.bot_scroll_frame, anchor="nw")
        
        self.bot_canvas.bind(
            '<Configure>', 
            lambda e: self.bot_canvas.itemconfig(self.canvas_window, width=e.width)
        )
        
        self.bot_canvas.configure(yscrollcommand=self.bot_scrollbar.set)
        
        self.bot_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.bot_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- MOUSE WHEEL SCROLLING ---
        def _on_mousewheel(event):
            self.bot_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            
        def _bind_mousewheel(event):
            self.bot_canvas.bind_all("<MouseWheel>", _on_mousewheel)
            self.bot_canvas.bind_all("<Button-4>", lambda e: self.bot_canvas.yview_scroll(-1, "units"))
            self.bot_canvas.bind_all("<Button-5>", lambda e: self.bot_canvas.yview_scroll(1, "units"))

        def _unbind_mousewheel(event):
            self.bot_canvas.unbind_all("<MouseWheel>")
            self.bot_canvas.unbind_all("<Button-4>")
            self.bot_canvas.unbind_all("<Button-5>")

        self.bot_container.bind("<Enter>", _bind_mousewheel)
        self.bot_container.bind("<Leave>", _unbind_mousewheel)

        # --- 4. MAIN GAME CANVAS (Add this back!) ---
        self.canvas_frame = tk.Frame(self.root, bg=DARK_BG)
        self.canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(
            self.canvas_frame, 
            width=self.grid_dim * self.cell_size, 
            height=self.grid_dim * self.cell_size, 
            bg="black", 
            highlightthickness=0
        )
        self.canvas.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def refresh_bot_list(self):
        for widget in self.bot_scroll_frame.winfo_children(): widget.destroy()
        
        current_files = sorted([f[:-3] for f in os.listdir('.') if f.endswith('.py') and f != 'main.py' and f != 'network_test.py'])
        new_vars = {}
        total_bots = len(current_files)
        
        for index, f in enumerate(current_files):
            # The scanner now returns the safety boolean AND the reason
            is_safe, reason = is_bot_safe(f + ".py")

            if f in self.available_bots: new_vars[f] = self.available_bots[f]
            else: new_vars[f] = tk.BooleanVar(master=self.root, value=is_safe)
            
            if f not in self.bot_colors: self.bot_colors[f] = generate_vibrant_color(index, total_bots)
            color = self.bot_colors[f]

            row = tk.Frame(self.bot_scroll_frame, bg=SIDEBAR_BG)
            row.pack(fill=tk.X, pady=1)

            # --- THE TOOLTIP LOGIC IS ADDED HERE ---
            if not is_safe:
                new_vars[f].set(False)
                cb = tk.Checkbutton(row, state=tk.DISABLED, bg=SIDEBAR_BG)
                cb.pack(side=tk.LEFT)
                
                # 1. Save the label to a variable so we can reference it
                banned_label = tk.Label(row, text=f" [BANNED]", bg=SIDEBAR_BG, fg="red", font=("Courier", 8, "bold"))
                banned_label.pack(side=tk.RIGHT)
                
                # 2. Attach the ToolTip to the [BANNED] text!
                ToolTip(banned_label, f"Reason:\n{reason}")
            else:
                cb = tk.Checkbutton(row, variable=new_vars[f], bg=SIDEBAR_BG, activebackground=SIDEBAR_BG, selectcolor=DARK_BG, fg=TEXT_COLOR, activeforeground="white", highlightthickness=0, bd=0)
                cb.pack(side=tk.LEFT)

            swatch = tk.Canvas(row, width=12, height=12, bg=color, highlightthickness=1, highlightbackground="white")
            swatch.pack(side=tk.LEFT, padx=5)

            name_color = "red" if not is_safe else TEXT_COLOR
            
            # 3. Save the name label to a variable as well
            name_label = tk.Label(row, text=f, bg=SIDEBAR_BG, fg=name_color, font=("Courier", 9))
            name_label.pack(side=tk.LEFT)
            
            # 4. Attach the ToolTip to the Bot's Name too, so it's easier to hover over!
            if not is_safe:
                ToolTip(name_label, f"Reason:\n{reason}")
            
        self.available_bots = new_vars

    def refresh_bot_sidebar(self):
        # 1. Clear the existing widgets (Checkboxes) from the scrollable frame
        for widget in self.bot_scroll_frame.winfo_children():
            widget.destroy()

        alive_bots = []
        dead_bots = []

        # 2. Categorize the bots
        for p in self._engine_players:
            if p['alive']:  
                alive_bots.append(p)
            else:
                dead_bots.append(p)

        # 3. Sort the alive bots alphabetically
        alive_bots.sort(key=lambda x: x['name'].lower())
        
        # Dead bots will naturally be in the order they died!

        # 4. Draw the Alive Bots at the top (Restored Original Style)
        for p in alive_bots:
            name = p['name']
            bot_color = p['color']

            # Create a row frame to hold the layout
            row = tk.Frame(self.bot_scroll_frame, bg=SIDEBAR_BG)
            row.pack(fill=tk.X, pady=1)

            # 1. Recreate the Checkbox (tied to the original variable so it stays checked).
            # We set state=tk.DISABLED so users can't uncheck a bot that is actively playing!
            if name in self.available_bots:
                cb = tk.Checkbutton(
                    row, 
                    variable=self.available_bots[name], 
                    state=tk.DISABLED, 
                    bg=SIDEBAR_BG, 
                    activebackground=SIDEBAR_BG, 
                    selectcolor=DARK_BG, 
                    highlightthickness=0, 
                    bd=0
                )
                cb.pack(side=tk.LEFT)

            # 2. Recreate the square color swatch
            swatch = tk.Canvas(row, width=12, height=12, bg=bot_color, highlightthickness=1, highlightbackground="white")
            swatch.pack(side=tk.LEFT, padx=5)

            # 3. Recreate the standard text label
            name_label = tk.Label(row, text=name, bg=SIDEBAR_BG, fg=TEXT_COLOR, font=("Courier", 9))
            name_label.pack(side=tk.LEFT)

        # 5. Draw the Dead Bots at the bottom
        for p in dead_bots:
            name = p['name']
            lbl = tk.Label(self.bot_scroll_frame, text=f"💀 {name}", bg=SIDEBAR_BG, fg="#666666", font=("Courier", 10))
            lbl.pack(anchor=tk.W, pady=2, padx=5)
            
        # 6. Update the canvas scroll region
        self.bot_canvas.configure(scrollregion=self.bot_canvas.bbox("all"))

    def adjust_grid_size(self, num_players):
        area_needed = max(3600, num_players * 900)
        self.grid_dim = int(math.sqrt(area_needed))
        self.cell_size = max(2, 800 // self.grid_dim)

    def cleanup_processes(self):
        """Stop any running bot subprocesses."""
        for p in self._engine_players:
            if 'wrapper' in p:
                p['wrapper'].stop()

    def init_game_state(self, selected_bots):
        self.cleanup_processes() 
        self._engine_board = {}
        self._engine_players = []
        self._dead_player_ids = set() 
        
        start_positions = [(random.randint(5, self.grid_dim-6), random.randint(5, self.grid_dim-6)) for _ in selected_bots]
        
        for i, bot_name in enumerate(selected_bots):
            # PASS THE SNAPSHOT DICTIONARY HERE
            bot_process = SecureBotProcess(bot_name, i + 1, bot_name, self.bot_snapshots)
            
            pos = start_positions[i]
            self._engine_players.append({
                'id': i + 1, 
                'name': bot_name, 
                'wrapper': bot_process,
                'move_func': bot_process.get_move, 
                'pos': pos, 
                'trail': [pos],
                'alive': True, 
                'color': self.bot_colors[bot_name], 
                'survival': 0, 
                'rank': 0
            })
            self._engine_board[pos] = i + 1

    def start_visual_match(self):
        # --- AUTO-SCALE THE BOARD ---
        # 1. Measure the current size of the dark gray frame on the right
        frame_width = self.canvas_frame.winfo_width()
        frame_height = self.canvas_frame.winfo_height()
        
        # 2. Find the shortest side so the board stays a perfect square (leaving a tiny 20px margin)
        available_space = min(frame_width, frame_height) - 20
        
        # 3. Mathematically calculate the new cell size (Tkinter handles decimals perfectly!)
        self.cell_size = available_space / self.grid_dim
        
        # 4. Resize the canvas to perfectly wrap the new grid
        self.canvas.config(width=self.grid_dim * self.cell_size, height=self.grid_dim * self.cell_size)

        selected = [bot for bot, var in self.available_bots.items() if var.get()]
        if len(selected) < 2: return messagebox.showwarning("Error", "Select at least 2 bots!")

        # --- THE SNAPSHOT (SELF-HEALING) ---
        self.bot_snapshots = {}
        for bot in selected:
            with open(f"{bot}.py", 'r', encoding='utf-8') as f:
                self.bot_snapshots[bot] = f.read()

        self.adjust_grid_size(len(selected))
        self.canvas.config(width=self.grid_dim*self.cell_size, height=self.grid_dim*self.cell_size)

        self.running, self.is_paused = False, False 
        self.btn_pause.config(text="PAUSE", state=tk.NORMAL)
        self.btn_step.config(state=tk.DISABLED, bg="#444c56")
        self.btn_tourney.config(state=tk.NORMAL)
        
        self.init_game_state(selected)
        self.canvas.delete("all")
        
        # Transform the checkboxes into the live scoreboard!
        self.refresh_bot_sidebar()

        for i in range(0, self.grid_dim * self.cell_size, self.cell_size):
            self.canvas.create_line(i, 0, i, self.grid_dim*self.cell_size, fill="#111", tags="grid")
            self.canvas.create_line(0, i, self.grid_dim*self.cell_size, i, fill="#111", tags="grid")

        for p in self._engine_players:
            x, y = p['pos']
            bright_head = get_fade_color(p['color'], 0)
            self.canvas.create_rectangle(x*self.cell_size, y*self.cell_size, (x+1)*self.cell_size, (y+1)*self.cell_size, fill=bright_head, outline="", tags=(f"p{p['id']}", f"cell_{x}_{y}"))
            if self.show_names_var.get():
                self.canvas.create_text(x*self.cell_size + self.cell_size + 5, y*self.cell_size, text=p['name'], fill="white", font=("Arial", max(8, self.cell_size)), anchor=tk.W, tags=f"name_{p['id']}")

        self.running = True
        self.game_loop()

    def toggle_pause(self):
        self.is_paused = not self.is_paused
        self.btn_pause.config(text="RESUME" if self.is_paused else "PAUSE")
        if self.is_paused: self.btn_step.config(state=tk.NORMAL, bg="#8b949e")
        else: self.btn_step.config(state=tk.DISABLED, bg="#444c56")
        if not self.is_paused and self.running: self.game_loop()

    def step_forward(self):
        if self.is_paused and self.running: self.process_tick(visual=True)

    def game_loop(self):
        if not self.running or self.is_paused: return
        self.process_tick(visual=True)
        if self.running: self.root.after(int(100 / max(0.1, self.speed_var.get())), self.game_loop)

    def process_tick(self, visual=True):
        dead_count_start = len(self._dead_player_ids)
        for p in self._engine_players:
            if p['id'] in self._dead_player_ids:
                p['alive'] = False
                
        alive = [p for p in self._engine_players if p['id'] not in self._dead_player_ids]
        current_rank_score = len(alive)
        
        if len(alive) <= 1:
            self.running = False
            if alive: alive[0]['rank'] = 1 
            if visual:
                winner = alive[0]['name'] if alive else "DRAW"
                self.canvas.create_text(self.canvas.winfo_width()//2, self.canvas.winfo_height()//2, text=f"WINNER: {winner}", fill="white", font=("Courier", 40, "bold"))
            self.cleanup_processes()
            return

        safe_players = []
        for other_p in self._engine_players:
            safe_players.append({"id": other_p['id'], "name": other_p['name'], "pos": other_p['pos'], "alive": other_p['alive'], "trail": list(other_p['trail'])})

        # --- PHASE 1: GATHER INTENTIONS (CONCURRENTLY!) ---
        intended_moves = {}
        
        # Helper function to run in a background I/O thread
        def fetch_move(p):
            try:
                move = p['move_func'](p['pos'], self._engine_board.copy(), self.grid_dim, safe_players)
                if move not in ["UP", "DOWN", "LEFT", "RIGHT"]: 
                    raise ValueError(f"Illegal Move Command: {move}")
                
                nx, ny = p['pos']
                if move == "UP": ny -= 1
                elif move == "DOWN": ny += 1
                elif move == "LEFT": nx -= 1
                elif move == "RIGHT": nx += 1
                
                return p['id'], (nx, ny), None
            except Exception as e:
                return p['id'], "ERROR", e
                
        # Ask ALL bots for their move at the exact same time
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(alive)) as executor:
            futures = [executor.submit(fetch_move, p) for p in alive]
            
            for future in concurrent.futures.as_completed(futures):
                pid, result, error = future.result()
                
                # Find the matching player in the main thread
                p = next(player for player in alive if player['id'] == pid)
                p['survival'] += 1
                
                if result == "ERROR":
                    print(f"[ENGINE FATAL]: Bot {p['name']} died because: {repr(error)}")
                    intended_moves[p['id']] = "ERROR"
                    p['alive'] = False
                    self._dead_player_ids.add(p['id']) 
                    p['rank'] = current_rank_score
                    if visual:
                        self.canvas.itemconfig(f"p{p['id']}", fill=get_dead_color(p['color']))
                        self.canvas.delete(f"name_{p['id']}")
                else:
                    intended_moves[p['id']] = result

        # --- PHASE 2: COUNT CLAIMS ON EACH SQUARE ---
        square_claims = {}
        for pos in intended_moves.values():
            if pos != "ERROR":
                square_claims[pos] = square_claims.get(pos, 0) + 1

        # --- PHASE 3: RESOLVE COLLISIONS AND UPDATE BOARD ---
        for p in alive:
            if p['id'] in self._dead_player_ids: continue
            
            new_pos = intended_moves[p['id']]
            old_pos = p['pos']
            nx, ny = new_pos
            
            die = False
            
            # Check for multi-bot crash
            if square_claims[new_pos] > 1:
                die = True
            else:
                # Check for ghost pass-through
                ghost_swap = False
                for other_p in alive:
                    if other_p['id'] != p['id'] and other_p['id'] not in self._dead_player_ids:
                        if intended_moves.get(other_p['id']) == old_pos and other_p['pos'] == new_pos:
                            ghost_swap = True
                            break
                if ghost_swap:
                    die = True
                # Check for walls and trails
                elif not (0 <= nx < self.grid_dim and 0 <= ny < self.grid_dim) or new_pos in self._engine_board:
                    die = True
                    
            if die:
                p['alive'] = False
                self._dead_player_ids.add(p['id']) 
                p['rank'] = current_rank_score 
                if visual:
                    self.canvas.itemconfig(f"p{p['id']}", fill=get_dead_color(p['color']))
                    self.canvas.delete(f"name_{p['id']}")
            else:
                p['pos'] = new_pos
                p['trail'].append(new_pos)
                self._engine_board[new_pos] = p['id']
                
                if visual:
                    bright_head = get_fade_color(p['color'], 0)
                    self.canvas.create_rectangle(nx*self.cell_size, ny*self.cell_size, (nx+1)*self.cell_size, (ny+1)*self.cell_size, fill=bright_head, outline="", tags=(f"p{p['id']}", f"cell_{nx}_{ny}"))
                    
                    max_fade = 6
                    trail = p['trail']
                    for i in range(1, max_fade + 1):
                        idx = len(trail) - 1 - i
                        if idx >= 0:
                            tx, ty = trail[idx]
                            fade_col = get_fade_color(p['color'], i, max_fade)
                            self.canvas.itemconfig(f"cell_{tx}_{ty}", fill=fade_col)

                    self.canvas.delete(f"name_{p['id']}")
                    if self.show_names_var.get():
                        self.canvas.create_text(nx*self.cell_size + self.cell_size + 5, ny*self.cell_size, text=p['name'], fill="white", font=("Arial", max(8, self.cell_size)), anchor=tk.W, tags=f"name_{p['id']}")
            
        # UPDATE THE UI IF SOMEONE JUST DIED
        if visual and len(self._dead_player_ids) > dead_count_start:
            self.refresh_bot_sidebar()

    def start_tournament(self):
        selected = [bot for bot, var in self.available_bots.items() if var.get()]
        if len(selected) < 2: return messagebox.showwarning("Error", "Select at least 2 bots!")

        # --- THE SNAPSHOT (SELF-HEALING) ---
        self.bot_snapshots = {}
        for bot in selected:
            with open(f"{bot}.py", 'r', encoding='utf-8') as f:
                self.bot_snapshots[bot] = f.read()
            
        try: rounds = int(self.rounds_var.get())
        except: rounds = 100
            
        self.adjust_grid_size(len(selected))
        self.canvas.config(width=self.grid_dim*self.cell_size, height=self.grid_dim*self.cell_size)

        self.btn_tourney.config(state=tk.DISABLED)
        self.btn_pause.config(state=tk.DISABLED)
        self.canvas.delete("all")
        
        self.init_game_state(selected)
        self.cleanup_processes()
        
        _engine_secure_stats_v9 = {}
        for p in self._engine_players:
            _engine_secure_stats_v9[p['name']] = {'ranks': [0], 'survivals': [0], 'color': p['color']} 
            
        self.running = True
        self.draw_tournament_progress(_engine_secure_stats_v9, 0, rounds)
        self.root.update()

        def pool_manager():
            completed = 0
            for p in self._engine_players:
                _engine_secure_stats_v9[p['name']] = {'ranks': [], 'survivals': [], 'color': p['color']}
                
            # --- SNAPSHOT GENERATOR ---
            # Take a pristine snapshot of the selected bots to pass to the background workers
            code_snapshots = {}
            for bot_name in selected:
                try:
                    with open(f"{bot_name}.py", 'r', encoding='utf-8') as f:
                        code_snapshots[bot_name] = f.read()
                except Exception:
                    pass
                
            # Leave 2 CPU cores free so the OS can handle the pipe routing without lagging
            safe_cores = max(1, os.cpu_count() - 2) 
            
            with concurrent.futures.ProcessPoolExecutor(max_workers=safe_cores) as executor:
                # ADDED `code_snapshots` to the arguments here!
                futures = [executor.submit(headless_worker, self.grid_dim, selected, code_snapshots) for _ in range(rounds)]
                for future in concurrent.futures.as_completed(futures):
                    if not self.running: break 
                    try:
                        result = future.result()
                        completed += 1
                        for name, data in result.items():
                            _engine_secure_stats_v9[name]['ranks'].append(data['rank'])
                            _engine_secure_stats_v9[name]['survivals'].append(data['survival'])
                            # --- NEW: Accumulate time across all rounds ---
                            _engine_secure_stats_v9[name]['total_time'] = _engine_secure_stats_v9[name].get('total_time', 0.0) + data['total_time']
                            _engine_secure_stats_v9[name]['move_count'] = _engine_secure_stats_v9[name].get('move_count', 0) + data['move_count']
                        self.root.after(0, self.draw_tournament_progress, _engine_secure_stats_v9, completed, rounds)
                    except Exception as e:
                        print(f"Match error on a worker thread: {e}")
                        
            self.root.after(0, self.finalize_tournament, _engine_secure_stats_v9, rounds)

        threading.Thread(target=pool_manager, daemon=True).start()

    def draw_tournament_progress(self, _engine_secure_stats_v9, current_round, total_rounds):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        
        self.canvas.create_text(w//2, 40, text=f"TOURNAMENT PROGRESS: ROUND {current_round} OF {total_rounds}", fill="white", font=("Courier", 20, "bold"))
        
        standings = []
        for name, data in _engine_secure_stats_v9.items():
            avg_rank = sum(data['ranks']) / max(1, len(data['ranks']))
            avg_surv = sum(data['survivals']) / max(1, len(data['survivals']))
            standings.append({'name': name, 'avg_rank': avg_rank, 'avg_surv': avg_surv, 'color': data['color']})
            
        standings.sort(key=lambda x: (x['avg_rank'], -x['avg_surv']))
        
        y_offset = 100
        bar_max_width = max(100, w - 500)
        max_surv = max([s['avg_surv'] for s in standings] + [1])
        
        self.canvas.create_text(40, y_offset, text="Pos", fill="gray", font=("Courier", 12, "bold"), anchor=tk.W)
        self.canvas.create_text(100, y_offset, text="Bot Name", fill="gray", font=("Courier", 12, "bold"), anchor=tk.W)
        self.canvas.create_text(300, y_offset, text="Avg Rank", fill="gray", font=("Courier", 12, "bold"), anchor=tk.W)
        self.canvas.create_text(420, y_offset, text="Avg Survival Time", fill="gray", font=("Courier", 12, "bold"), anchor=tk.W)
        y_offset += 30
        
        for i, s in enumerate(standings):
            self.canvas.create_text(40, y_offset, text=f"#{i+1}", fill="white", font=("Courier", 14, "bold"), anchor=tk.W)
            self.canvas.create_rectangle(100, y_offset-8, 115, y_offset+7, fill=s['color'], outline="white")
            self.canvas.create_text(130, y_offset, text=s['name'], fill="white", font=("Courier", 14), anchor=tk.W)
            self.canvas.create_text(300, y_offset, text=f"{s['avg_rank']:.2f}", fill="white", font=("Courier", 14), anchor=tk.W)
            
            bar_width = (s['avg_surv'] / max_surv) * bar_max_width
            self.canvas.create_rectangle(420, y_offset-12, 420+bar_width, y_offset+12, fill=s['color'], outline="")
            self.canvas.create_text(420+bar_width+10, y_offset, text=f"{s['avg_surv']:.1f} ticks", fill="white", font=("Courier", 10), anchor=tk.W)
            y_offset += 40

    def finalize_tournament(self, _engine_secure_stats_v9, rounds):
        self.btn_tourney.config(state=tk.NORMAL) 
        
        _engine_secure_summary_v9 = []
        for name, data in _engine_secure_stats_v9.items():
            ranks, survivals = data['ranks'], data['survivals']
            
            # --- NEW: Calculate Average Time per Move in milliseconds ---
            total_time = data.get('total_time', 0.0)
            move_count = data.get('move_count', 0)
            avg_time_ms = (total_time / max(1, move_count)) * 1000 
            
            _engine_secure_summary_v9.append({
                "name": name, 
                "total_rank": sum(ranks), 
                "avg_rank": sum(ranks) / max(1, len(ranks)), 
                "total_survival": sum(survivals),
                "avg_time_ms": avg_time_ms
            })
            
        _engine_secure_summary_v9.sort(key=lambda x: (x['total_rank'], -x['total_survival']))

        res_win = tk.Toplevel(self.root)
        res_win.title("Tournament Results")
        res_win.geometry("1150x650") 
        res_win.configure(bg=SIDEBAR_BG)
        
        tk.Label(res_win, text=f"TOURNAMENT LEADERBOARD ({rounds} ROUNDS)", bg=SIDEBAR_BG, fg=ACCENT, font=("Courier", 20, "bold")).pack(pady=20)
        
        st_frame = tk.Frame(res_win, bg=SIDEBAR_BG)
        st_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        
        text_widget = tk.Text(st_frame, bg=DARK_BG, fg=TEXT_COLOR, font=("Courier", 12), padx=20, pady=20)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        sb = tk.Scrollbar(st_frame, command=text_widget.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.config(yscrollcommand=sb.set)
        
        # --- NEW: Add the Avg Time/Move column to the header and rows ---
        header = f"{'Pos':<5} | {'Bot Name':<25} | {'Score (Ranks)':<15} | {'Avg Rank':<10} | {'Tie-Breaker':<15} | {'Avg Time/Move':<15}\n"
        text_widget.insert(tk.END, header)
        text_widget.insert(tk.END, "-" * 105 + "\n")
        
        for i, p in enumerate(_engine_secure_summary_v9):
            pos_str = f"#{i+1}"
            avg_rk_str = f"{p['avg_rank']:.2f}"
            time_str = f"{p['avg_time_ms']:.2f} ms"
            line = f"{pos_str:<5} | {p['name']:<25} | {p['total_rank']:<15} | {avg_rk_str:<10} | {p['total_survival']:<15} | {time_str:<15}\n"
            text_widget.insert(tk.END, line)
            
        text_widget.config(state=tk.DISABLED)

if __name__ == "__main__":
    app = TronApp()
    app.root.mainloop()
