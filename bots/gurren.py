import collections
import json
import os
import random
import threading

team_name = "TengenToppa"

DNA_FILE = "spiral_dna.json"
# Use a thread lock to prevent the Tkinter engine crash!
file_lock = threading.Lock() 

DEFAULT_DNA = {
    "hunted_area": 50.0,
    "hunted_compact": 500.0,
    "safe_area": 100.0,
    "safe_edges": 1.0,
    "safe_mid_penalty": 5.0
}

MEMORY = {"turn": 0, "dna": DEFAULT_DNA.copy()}

def load_and_evolve():
    """Thread-safe hyper-evolution."""
    with file_lock:
        try:
            if not os.path.exists(DNA_FILE):
                return DEFAULT_DNA.copy()
                
            with open(DNA_FILE, "r") as f:
                data = json.load(f)
                
            best_dna = data.get("best_dna", DEFAULT_DNA)
            best_score = data.get("best_score", 0)
            last_dna = data.get("last_dna", DEFAULT_DNA)
            last_won = data.get("last_won", False)
            last_turns = data.get("last_turns", 0)
            
            if last_won or last_turns > best_score:
                best_dna = last_dna
                best_score = last_turns if not last_won else 99999
                
            perf_ratio = last_turns / best_score if best_score not in [0, 99999] else (1.0 if last_won else 0.0)
            mutation_cap = 0.05 if last_won else max(0.05, 0.50 * (1.0 - perf_ratio))

            new_dna = {t: max(0.1, v * (1 + random.uniform(-mutation_cap, mutation_cap))) 
                       for t, v in best_dna.items()}
                
            with open(DNA_FILE, "w") as f:
                json.dump({
                    "best_dna": best_dna, "best_score": best_score,
                    "last_dna": new_dna, "last_won": False, "last_turns": 0
                }, f)
                
            return new_dna
        except:
            return DEFAULT_DNA.copy()

def update_record(turn_count, is_win):
    """Thread-safe silent update."""
    with file_lock:
        try:
            if os.path.exists(DNA_FILE):
                with open(DNA_FILE, "r") as f:
                    data = json.load(f)
                data["last_turns"] = turn_count
                data["last_won"] = is_win
                with open(DNA_FILE, "w") as f:
                    json.dump(data, f)
        except:
            pass

def move(my_pos, raw_board, grid_dim, players):
    DIRS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
    
    # 1. TRIGGER EVOLUTION ON NEW ROUND
    me_data = next(p for p in players if p['pos'] == my_pos)
    if len(me_data['trail']) <= 1:
        MEMORY["turn"] = 0
        MEMORY["dna"] = load_and_evolve() 
        
    MEMORY["turn"] += 1
    
    # 2. THE SHADOW BOARD (Ignores cheating bots)
    true_board = set()
    alive_opps = []
    for p in players:
        for t_pos in p['trail']:
            true_board.add(t_pos)
        if p['alive'] and p['pos'] != my_pos:
            alive_opps.append(p)

    def is_safe(p):
        return 0 <= p[0] < grid_dim and 0 <= p[1] < grid_dim and p not in true_board

    # Log survival safely
    update_record(MEMORY["turn"], len(alive_opps) == 0)

    # 3. FAST VORONOI
    def evaluate_space(target_pos):
        q = collections.deque([(target_pos, 0)])
        owners = {target_pos: 0}
        for i, op in enumerate(alive_opps):
            owners[op['pos']] = i + 1
            q.append((op['pos'], i + 1))
        area, edges = 0, 0
        while q:
            curr, owner = q.popleft()
            if owner == 0: area += 1
            for dx, dy in DIRS.values():
                nxt = (curr[0]+dx, curr[1]+dy)
                if not is_safe(nxt):
                    if owner == 0: edges += 1
                elif nxt not in owners:
                    owners[nxt] = owner
                    q.append((nxt, owner))
        return area, edges

    # 4. APPLY DNA TO THE ULTIMATE MATH
    x, y = my_pos
    closest_enemy_dist = min([abs(x - o['pos'][0]) + abs(y - o['pos'][1]) for o in alive_opps]) if alive_opps else float('inf')
    
    scored_moves = []
    dna = MEMORY["dna"]
    
    for d_name, (dx, dy) in DIRS.items():
        target = (x + dx, y + dy)
        if is_safe(target):
            true_board.add(target)
            area, edges = evaluate_space(target)
            true_board.remove(target)
            
            # Use DNA to weigh the ultimate combat logic!
            if closest_enemy_dist < 6:
                compactness = edges / (area if area > 0 else 1)
                score = (area * dna["hunted_area"]) + (compactness * dna["hunted_compact"])
            else:
                dist_to_mid = abs(target[0] - grid_dim//2) + abs(target[1] - grid_dim//2)
                score = (area * dna["safe_area"]) + (edges * dna["safe_edges"]) - (dist_to_mid * dna["safe_mid_penalty"])
                
            scored_moves.append((score, d_name))

    if not scored_moves:
        return "UP"
        
    return max(scored_moves, key=lambda i: i[0])[1]