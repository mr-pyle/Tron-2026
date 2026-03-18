import random
from collections import deque

team_name = "Kai67"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    directions = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
    
    # --- MOMENTUM TRACKING ---
    current_dir = None
    my_data = next((p for p in players if p['pos'] == my_pos), None)
    if my_data and len(my_data.get('trail', [])) > 1:
        lx, ly = my_data['trail'][-2]
        if x > lx: current_dir = "RIGHT"
        elif x < lx: current_dir = "LEFT"
        elif y > ly: current_dir = "DOWN"
        elif y < ly: current_dir = "UP"

    # --- IMMEDIATE COLLISION FILTRATION ---
    safe_moves = []
    for dname, (dx, dy) in directions.items():
        nx, ny = x + dx, y + dy
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
            safe_moves.append((dname, nx, ny))

    if not safe_moves: return "UP"
    if len(safe_moves) == 1: return safe_moves[0][0]

    # --- DATA AGGREGATION ---
    alive_opponents = [p for p in players if p.get('alive', True) and p['pos'] != my_pos]
    my_id = my_data['id'] if my_data else 999
    occupied_count = len(board)
    total_cells = grid_dim * grid_dim
    late_game = (occupied_count > total_cells * 0.60) or (len(alive_opponents) <= 1)

    # --- ADVANCED SPATIAL HEURISTICS ---
    def get_wall_adj(cx, cy, temp_board):
        w = 0
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0: continue
                tx, ty = cx + dx, cy + dy
                if not (0 <= tx < grid_dim and 0 <= ty < grid_dim) or (tx, ty) in temp_board:
                    w += 1
        return w

    def get_safe_counts(sx, sy, temp_board):
        step1 = 0
        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            t1x, t1y = sx + dx, sy + dy
            if 0 <= t1x < grid_dim and 0 <= t1y < grid_dim and (t1x, t1y) not in temp_board:
                step1 += 1
        return step1

    def compute_voronoi_and_isolation(sx, sy, temp_board):
        q = deque([(sx, sy, my_id, 0)])
        visited = {(sx, sy): (my_id, 0)}
        for opp in alive_opponents:
            ox, oy = opp['pos']
            q.append((ox, oy, opp['id'], 0))
            visited[(ox, oy)] = (opp['id'], 0)
        
        areas = {p['id']: 0 for p in alive_opponents}
        areas[my_id] = 0
        is_isolated = True

        while q:
            cx, cy, owner, dist = q.popleft()
            areas[owner] += 1
            for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in temp_board:
                    if (nx, ny) not in visited:
                        visited[(nx, ny)] = (owner, dist + 1)
                        q.append((nx, ny, owner, dist + 1))
                    elif visited[(nx, ny)][0] != owner:
                        is_isolated = False 
        return areas, is_isolated

    def get_true_flood_area(sx, sy, temp_board):
        # Calculates EXACTLY how much space we have to survive if we go this way
        v = set([(sx, sy)])
        q = deque([(sx, sy)])
        while q:
            cx, cy = q.popleft()
            for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in temp_board and (nx, ny) not in v:
                    v.add((nx, ny))
                    q.append((nx, ny))
        return len(v)

    # --- ENEMY OPTION STEALING (HYPER-AGGRESSION) ---
    # Find every single tile the enemies could legally move to next turn
    enemy_next_options = set()
    for opp in alive_opponents:
        ox, oy = opp['pos']
        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            ex, ey = ox + dx, oy + dy
            if 0 <= ex < grid_dim and 0 <= ey < grid_dim and (ex, ey) not in board:
                enemy_next_options.add((ex, ey))

    # --- SCORE CALCULATION ---
    scores = {}
    for dname, nx, ny in safe_moves:
        t_board = board.copy()
        t_board[(nx, ny)] = my_id
        
        # Core spatial metrics
        v_areas, isolated = compute_voronoi_and_isolation(nx, ny, t_board)
        my_v_area = v_areas[my_id]
        s1 = get_safe_counts(nx, ny, t_board)
        wall_score = get_wall_adj(nx, ny, t_board)
        
        # ULTIMATE DEFENSE: True Area Check
        true_survival_space = get_true_flood_area(nx, ny, t_board)
        
        # Penalties (Look-ahead death prevention)
        death_penalty = 0
        if s1 == 0: death_penalty -= 90000000       # Immediate death
        elif true_survival_space < 5: death_penalty -= 50000000  # Stepping into a tiny trap
        elif true_survival_space < 15: death_penalty -= 20000000 # Uncomfortable choke point
        
        # ULTIMATE AGGRESSION: Omni-Directional Head Hunting
        head_hunt_bonus = 0
        if (nx, ny) in enemy_next_options:
            head_hunt_bonus += 400000 # Massive priority to steal their next immediate step
            
        # Predictive Block Bonus (Straight line momentum break)
        block_bonus = 0
        for opp in alive_opponents:
            if len(opp.get('trail', [])) >= 2:
                ox, oy = opp['pos']
                olx, oly = opp['trail'][-2]
                pred = (ox + (ox - olx), oy + (oy - oly))
                if pred == (nx, ny):
                    block_bonus += 300000 

        if isolated:
            # PHASE: SURVIVAL (Perfect Enclosure Filling)
            score = (true_survival_space * 250000) + (wall_score * 1200) + death_penalty
        else:
            # PHASE: COMBAT (Starvation & Suffocation)
            opp_v_area = sum(v_areas[p['id']] for p in alive_opponents)
            
            min_opp_dist = min([abs(nx-p['pos'][0]) + abs(ny-p['pos'][1]) for p in alive_opponents])
            chase_bonus = (grid_dim * 2 - min_opp_dist) * 250
            
            # Heavy Voronoi Starvation: Taking their space (-4500) matters MORE than gaining ours (+3200)
            score = (my_v_area * 3200) - (opp_v_area * 4500)
            
            # Combine mechanics
            score += head_hunt_bonus + block_bonus + chase_bonus + death_penalty
            
            # Defense during combat: Always prefer moves that leave us with more true space
            score += (true_survival_space * 800)
            
            # Wall handling: Keep off walls during early fights, hug them in late game
            if late_game:
                score += (wall_score * 400)
            else:
                score -= (wall_score * 150)

        scores[dname] = score

    # --- TIE-BREAKING AND SELECTION ---
    if not scores: return random.choice(safe_moves)[0]
    
    max_val = max(scores.values())
    best_dirs = [d for d, s in scores.items() if s == max_val]
    
    # Keep momentum if it's safe and optimal
    if current_dir in best_dirs:
        return current_dir
        
    for d in ["UP", "RIGHT", "DOWN", "LEFT"]:
        if d in best_dirs:
            return d
            
    return best_dirs[0]