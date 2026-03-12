import tkinter as tk
from tkinter import ttk, messagebox
import os
import importlib
import random
import time
import csv
from datetime import datetime
import traceback
import math
import colorsys
import concurrent.futures
import threading
import sys
import ast

# --- CONSTANTS ---
DARK_BG = "#0d1117"
SIDEBAR_BG = "#161b22"
ACCENT = "#58a6ff"
TEXT_COLOR = "#c9d1d9"

# --- SECURITY SCANNER ---
def is_bot_safe(filepath):
    """Scans a python file for illegal imports and dangerous functions."""
    banned_modules = ['os', 'sys', 'subprocess', 'inspect', 'threading', 'multiprocessing', 'builtins', 'shutil', 'importlib', 'ctypes']
    banned_functions = ['exec', 'eval', 'compile', 'open', 'globals', 'locals', 'getattr', 'setattr', 'delattr', '__import__']
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] in banned_modules:
                        return False, f"Illegal import: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] in banned_modules:
                    return False, f"Illegal import: {node.module}"
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in banned_functions:
                    return False, f"Illegal function: {node.func.id}"
        return True, "Safe"
    except Exception as e:
        return False, f"Syntax Error: {e}"

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

def headless_worker(grid_dim, selected_bots):
    import sys, os, random
    if os.path.abspath('.') not in sys.path:
        sys.path.insert(0, os.path.abspath('.'))

    _engine_board = {}
    _engine_players = []
    _dead_player_ids = set() # NECROMANCY PATCH: Permanent registry of dead bots
    
    random.seed() 
    start_positions = [(random.randint(5, grid_dim-6), random.randint(5, grid_dim-6)) for _ in selected_bots]
    
    for i, bot_name in enumerate(selected_bots):
        try:
            import importlib
            mod = importlib.import_module(bot_name)
            display_name = getattr(mod, 'team_name', bot_name)
        except Exception:
            continue
            
        pos = start_positions[i]
        _engine_players.append({
            'id': i + 1,
            'name': display_name,
            'module': mod,
            'move_func': mod.move, 
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
        
        # NECROMANCY PATCH: Forcefully re-kill anyone trying to revive
        for p in _engine_players:
            if p['id'] in _dead_player_ids:
                p['alive'] = False
                
        # Rely ONLY on the engine's isolated crypt, not the player's dictionary
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

        for p in alive:
            p['survival'] += 1
            try:
                move = p['move_func'](p['pos'], _engine_board.copy(), grid_dim, safe_players)
                
                if move not in ["UP", "DOWN", "LEFT", "RIGHT"]:
                    raise ValueError("Illegal Move Command")
                
                x, y = p['pos']
                if move == "UP": y -= 1
                elif move == "DOWN": y += 1
                elif move == "LEFT": x -= 1
                elif move == "RIGHT": x += 1
                
                new_pos = (x, y)
                if not (0 <= x < grid_dim and 0 <= y < grid_dim) or new_pos in _engine_board:
                    p['alive'] = False
                    _dead_player_ids.add(p['id']) # Add to Crypt
                    p['rank'] = current_rank_score
                else:
                    p['pos'] = new_pos
                    p['trail'].append(new_pos)
                    _engine_board[new_pos] = p['id']
            except Exception:
                p['alive'] = False
                _dead_player_ids.add(p['id']) # Add to Crypt
                p['rank'] = current_rank_score

    _engine_secure_results_v9 = {}
    for p in _engine_players:
        _engine_secure_results_v9[p['name']] = {'rank': p['rank'], 'survival': p['survival']}
        
    return _engine_secure_results_v9

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
        self._dead_player_ids = set() # NECROMANCY PATCH
        self.running = False
        self.is_paused = False
        
        self.setup_layout()
        self.refresh_bot_list()

    def setup_layout(self):
        self.sidebar = tk.Frame(self.root, width=280, bg=SIDEBAR_BG)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        tk.Label(self.sidebar, text="TRON ENGINE", bg=SIDEBAR_BG, fg=ACCENT, font=("Courier", 18, "bold")).pack(pady=15)

        tk.Label(self.sidebar, text="Available Bots", bg=SIDEBAR_BG, fg="gray").pack(anchor=tk.W, padx=10)
        self.bot_scroll_frame = tk.Frame(self.sidebar, bg=SIDEBAR_BG)
        self.bot_scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        tk.Button(self.sidebar, text="REFRESH & SCAN", command=self.refresh_bot_list, bg="#21262d", fg=TEXT_COLOR).pack(fill=tk.X, padx=10, pady=5)

        vis_frame = tk.LabelFrame(self.sidebar, text="Visual Match", bg=SIDEBAR_BG, fg="gray")
        vis_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Button(vis_frame, text="START VISUAL", command=self.start_visual_match, bg="#238636", fg="white").pack(fill=tk.X, padx=10, pady=2)
        self.btn_pause = tk.Button(vis_frame, text="PAUSE", command=self.toggle_pause, bg="#21262d", fg=TEXT_COLOR)
        self.btn_pause.pack(fill=tk.X, padx=10, pady=2)
        self.btn_step = tk.Button(vis_frame, text="STEP FORWARD", command=self.step_forward, bg="#444c56", fg="white", state=tk.DISABLED)
        self.btn_step.pack(fill=tk.X, padx=10, pady=2)
                       
        self.show_names_var = tk.BooleanVar(value=False)
        tk.Checkbutton(vis_frame, text="Show Display Names", variable=self.show_names_var, bg=SIDEBAR_BG, fg=TEXT_COLOR, selectcolor=DARK_BG, activeforeground="white", highlightthickness=0, bd=0).pack(fill=tk.X, padx=10, pady=2)

        self.show_heatmap_var = tk.BooleanVar(value=False)
        tk.Checkbutton(vis_frame, text="Territory Heatmap", variable=self.show_heatmap_var, bg=SIDEBAR_BG, fg=TEXT_COLOR, selectcolor=DARK_BG, activeforeground="white", highlightthickness=0, bd=0).pack(fill=tk.X, padx=10, pady=2)

        self.speed_var = tk.DoubleVar(value=1.0)
        tk.Scale(vis_frame, from_=0.25, to=25.0, resolution=0.25, variable=self.speed_var, orient=tk.HORIZONTAL, bg=SIDEBAR_BG, fg=TEXT_COLOR, label="Speed").pack(fill=tk.X, padx=10)

        tour_frame = tk.LabelFrame(self.sidebar, text="Tournament (Headless)", bg=SIDEBAR_BG, fg="gray")
        tour_frame.pack(fill=tk.X, padx=10, pady=10)
        
        r_frame = tk.Frame(tour_frame, bg=SIDEBAR_BG)
        r_frame.pack(fill=tk.X, padx=10, pady=2)
        tk.Label(r_frame, text="Rounds:", bg=SIDEBAR_BG, fg=TEXT_COLOR).pack(side=tk.LEFT)
        self.rounds_var = tk.StringVar(value="100")
        tk.Spinbox(r_frame, from_=1, to=1000, textvariable=self.rounds_var, width=5, bg=DARK_BG, fg="white").pack(side=tk.RIGHT)
        self.btn_tourney = tk.Button(tour_frame, text="RUN TOURNAMENT", command=self.start_tournament, bg="#a371f7", fg="white")
        self.btn_tourney.pack(fill=tk.X, padx=10, pady=5)

        self.canvas_frame = tk.Frame(self.root, bg=DARK_BG)
        self.canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(self.canvas_frame, width=self.grid_dim*self.cell_size, height=self.grid_dim*self.cell_size, bg="black", highlightthickness=0)
        self.canvas.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

    def refresh_bot_list(self):
        for widget in self.bot_scroll_frame.winfo_children(): widget.destroy()
        
        current_files = sorted([f[:-3] for f in os.listdir('.') if f.endswith('.py') and f != 'main.py'])
        new_vars = {}
        total_bots = len(current_files)
        
        for index, f in enumerate(current_files):
            is_safe, reason = is_bot_safe(f + ".py")

            if f in self.available_bots: new_vars[f] = self.available_bots[f]
            else: new_vars[f] = tk.BooleanVar(master=self.root, value=is_safe)
            
            if f not in self.bot_colors: self.bot_colors[f] = generate_vibrant_color(index, total_bots)
            color = self.bot_colors[f]

            row = tk.Frame(self.bot_scroll_frame, bg=SIDEBAR_BG)
            row.pack(fill=tk.X, pady=1)

            if not is_safe:
                new_vars[f].set(False)
                cb = tk.Checkbutton(row, state=tk.DISABLED, bg=SIDEBAR_BG)
                cb.pack(side=tk.LEFT)
                tk.Label(row, text=f" [BANNED]", bg=SIDEBAR_BG, fg="red", font=("Courier", 8, "bold")).pack(side=tk.RIGHT)
            else:
                cb = tk.Checkbutton(row, variable=new_vars[f], bg=SIDEBAR_BG, activebackground=SIDEBAR_BG, selectcolor=DARK_BG, fg=TEXT_COLOR, activeforeground="white", highlightthickness=0, bd=0)
                cb.pack(side=tk.LEFT)

            swatch = tk.Canvas(row, width=12, height=12, bg=color, highlightthickness=1, highlightbackground="white")
            swatch.pack(side=tk.LEFT, padx=5)

            name_color = "red" if not is_safe else TEXT_COLOR
            tk.Label(row, text=f, bg=SIDEBAR_BG, fg=name_color, font=("Courier", 9)).pack(side=tk.LEFT)
            
        self.available_bots = new_vars

    def adjust_grid_size(self, num_players):
        area_needed = max(3600, num_players * 900)
        self.grid_dim = int(math.sqrt(area_needed))
        self.cell_size = max(2, 800 // self.grid_dim)

    def init_game_state(self, selected_bots):
        self._engine_board = {}
        self._engine_players = []
        self._dead_player_ids = set() # NECROMANCY PATCH
        
        start_positions = [(random.randint(5, self.grid_dim-6), random.randint(5, self.grid_dim-6)) for _ in selected_bots]
        
        for i, bot_name in enumerate(selected_bots):
            try:
                if bot_name in sys.modules: mod = importlib.reload(sys.modules[bot_name])
                else: mod = importlib.import_module(bot_name)
                display_name = getattr(mod, 'team_name', bot_name)
            except Exception as e:
                print(f"Failed to load {bot_name}: {e}")
                continue
                
            pos = start_positions[i]
            self._engine_players.append({
                'id': i + 1, 'name': display_name, 'module': mod,
                'move_func': mod.move, 'pos': pos, 'trail': [pos],
                'alive': True, 'color': self.bot_colors[bot_name], 'survival': 0, 'rank': 0
            })
            self._engine_board[pos] = i + 1

    def start_visual_match(self):
        selected = [bot for bot, var in self.available_bots.items() if var.get()]
        if len(selected) < 2: return messagebox.showwarning("Error", "Select at least 2 bots!")

        self.adjust_grid_size(len(selected))
        self.canvas.config(width=self.grid_dim*self.cell_size, height=self.grid_dim*self.cell_size)

        self.running, self.is_paused = False, False 
        self.btn_pause.config(text="PAUSE", state=tk.NORMAL)
        self.btn_step.config(state=tk.DISABLED, bg="#444c56")
        self.btn_tourney.config(state=tk.NORMAL)
        
        self.init_game_state(selected)
        self.canvas.delete("all")

        if self.show_heatmap_var.get():
            self.dim_colors = {p['id']: get_dim_color(p['color']) for p in self._engine_players}
            for x in range(self.grid_dim):
                for y in range(self.grid_dim):
                    self.canvas.create_rectangle(x*self.cell_size, y*self.cell_size, (x+1)*self.cell_size, (y+1)*self.cell_size, fill=DARK_BG, outline="", tags=f"bg_cell_{x}_{y}")

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

    def update_heatmap(self):
        alive_players = [p for p in self._engine_players if p['alive']]
        if not alive_players: return

        for x in range(self.grid_dim):
            for y in range(self.grid_dim):
                if (x, y) not in self._engine_board:
                    min_dist = float('inf')
                    owner_id = None
                    for p in alive_players:
                        px, py = p['pos']
                        dist = abs(x - px) + abs(y - py)
                        if dist < min_dist: min_dist, owner_id = dist, p['id']
                    if owner_id: self.canvas.itemconfig(f"bg_cell_{x}_{y}", fill=self.dim_colors[owner_id])

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
        # NECROMANCY PATCH: Overwrite the dictionary with the engine's permanent crypt
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
            return

        safe_players = []
        for other_p in self._engine_players:
            safe_players.append({"id": other_p['id'], "name": other_p['name'], "pos": other_p['pos'], "alive": other_p['alive'], "trail": list(other_p['trail'])})

        for p in alive:
            p['survival'] += 1
            try:
                move = p['move_func'](p['pos'], self._engine_board.copy(), self.grid_dim, safe_players)
                if move not in ["UP", "DOWN", "LEFT", "RIGHT"]: raise ValueError("Illegal Move Command")
                
                old_x, old_y = p['pos']
                nx, ny = old_x, old_y
                if move == "UP": ny -= 1
                elif move == "DOWN": ny += 1
                elif move == "LEFT": nx -= 1
                elif move == "RIGHT": nx += 1
                new_pos = (nx, ny)
                
                if not (0 <= nx < self.grid_dim and 0 <= ny < self.grid_dim) or new_pos in self._engine_board:
                    p['alive'] = False
                    self._dead_player_ids.add(p['id']) # Add to Crypt
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
            
            except Exception as e:
                p['alive'] = False
                self._dead_player_ids.add(p['id']) # Add to Crypt
                p['rank'] = current_rank_score
                if visual:
                    self.canvas.itemconfig(f"p{p['id']}", fill=get_dead_color(p['color']))
                    self.canvas.delete(f"name_{p['id']}")

        if visual and self.show_heatmap_var.get() and self._engine_players[0]['survival'] % 3 == 0:
            self.update_heatmap()

    def start_tournament(self):
        selected = [bot for bot, var in self.available_bots.items() if var.get()]
        if len(selected) < 2: return messagebox.showwarning("Error", "Select at least 2 bots!")
            
        try: rounds = int(self.rounds_var.get())
        except: rounds = 100
            
        self.adjust_grid_size(len(selected))
        self.canvas.config(width=self.grid_dim*self.cell_size, height=self.grid_dim*self.cell_size)

        self.btn_tourney.config(state=tk.DISABLED)
        self.btn_pause.config(state=tk.DISABLED)
        self.canvas.delete("all")
        
        self.init_game_state(selected)
        
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
                
            with concurrent.futures.ProcessPoolExecutor() as executor:
                futures = [executor.submit(headless_worker, self.grid_dim, selected) for _ in range(rounds)]
                for future in concurrent.futures.as_completed(futures):
                    if not self.running: break 
                    try:
                        result = future.result()
                        completed += 1
                        for name, data in result.items():
                            _engine_secure_stats_v9[name]['ranks'].append(data['rank'])
                            _engine_secure_stats_v9[name]['survivals'].append(data['survival'])
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
            _engine_secure_summary_v9.append({"name": name, "total_rank": sum(ranks), "avg_rank": sum(ranks) / max(1, len(ranks)), "total_survival": sum(survivals)})
            
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
        
        header = f"{'Pos':<5} | {'Bot Name':<25} | {'Score (Ranks)':<15} | {'Avg Rank':<10} | {'Tie-Breaker (Survival)':<25}\n"
        text_widget.insert(tk.END, header + "-" * len(header) + "\n")
        
        for i, row in enumerate(_engine_secure_summary_v9, 1):
            text_widget.insert(tk.END, f"{i:<5} | {row['name']:<25} | {row['total_rank']:<15} | {row['avg_rank']:<10.2f} | {row['total_survival']:<25}\n")
            
        text_widget.config(state=tk.DISABLED)

if __name__ == "__main__":
    app = TronApp()
    app.root.mainloop()