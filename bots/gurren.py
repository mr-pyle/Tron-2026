from collections import deque

team_name = "TENGEN_TOPPA"

# Persistent memory for a single match
MEMORY = {
    "turn": 0,
    "profiles": {},  # Tracks enemy aggression
    "initialized": False
}

def move(my_pos, raw_board, grid_dim, players):
    x, y = my_pos
    dirs = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
    blocked = set(raw_board.keys())

    me = next(p for p in players if p['pos'] == my_pos)
    
    # Reset memory on new match
    if not MEMORY["initialized"] or len(me['trail']) <= 1:
        MEMORY["turn"] = 0
        MEMORY["profiles"] = {p['id']: {"last_dist": 999, "aggro": 0} for p in players if p['id'] != me['id']}
        MEMORY["initialized"] = True

    MEMORY["turn"] += 1
    enemies = [p for p in players if p['pos'] != my_pos and p.get('alive', True)]
    
    # --- 1. DYNAMIC PROFILING ---
    highest_threat_aggro = 0
    closest_enemy_dist = 999
    
    for e in enemies:
        eid = e['id']
        dist = abs(x - e['pos'][0]) + abs(y - e['pos'][1])
        closest_enemy_dist = min(closest_enemy_dist, dist)
        
        prof = MEMORY["profiles"].get(eid, {"last_dist": dist, "aggro": 0})
        
        # If they moved closer to us, increase their aggression score
        if dist < prof["last_dist"]:
            prof["aggro"] = min(10, prof["aggro"] + 2)
        elif dist > prof["last_dist"]:
            prof["aggro"] = max(0, prof["aggro"] - 1)
            
        prof["last_dist"] = dist
        MEMORY["profiles"][eid] = prof
        
        if dist < 15:
            highest_threat_aggro = max(highest_threat_aggro, prof["aggro"])

    # --- 2. ADAPTIVE WEIGHTS ---
    if not enemies or closest_enemy_dist > 25:
        # STANCE: ISOLATED (End-Game Packing)
        # We are alone. Maximize space, ignore voronoi, strictly hug walls.
        w_space, w_voronoi, w_openness, w_packing = 20.0, 0.0, 0.0, 15.0
    elif highest_threat_aggro >= 6:
        # STANCE: MATADOR (Evasion)
        # Running from an aggressive bot. Prioritize wide open spaces to escape.
        w_space, w_voronoi, w_openness, w_packing = 8.0, 2.0, 15.0, -5.0 
    else:
        # STANCE: ANACONDA (Aggressive Area Denial)
        # Fighting a passive bot (like corbin might be). Steal their space.
        w_space, w_voronoi, w_openness, w_packing = 5.0, 15.0, 3.0, 2.0

    # --- 3. SHADOW VORONOI ---
    def is_safe(nx, ny, extra_blocked=None):
        if not (0 <= nx < grid_dim and 0 <= ny < grid_dim): return False
        if (nx, ny) in blocked: return False
        if extra_blocked and (nx, ny) in extra_blocked: return False
        return True

    enemy_reach = {}
    if enemies:
        q = deque([(e['pos'][0], e['pos'][1], 0) for e in enemies])
        while q:
            cx, cy, d = q.popleft()
            if d > 12: continue # Fast local mapping
            for dx, dy in dirs.values():
                nx, ny = cx + dx, cy + dy
                if is_safe(nx, ny) and (nx, ny) not in enemy_reach:
                    enemy_reach[(nx, ny)] = d + 1
                    q.append((nx, ny, d + 1))

    # --- 4. SPACE EVALUATION ---
    def evaluate(start_node):
        q = deque([(start_node[0], start_node[1], 1)])
        visited = {start_node}
        parity = {0: 0, 1: 0}
        openness = 0
        voronoi_count = 0

        while q:
            cx, cy, d = q.popleft()
            if d > 300: break # Keep under the timeout limit
            
            parity[(cx + cy) % 2] += 1
            
            # Openness: How many safe exits does this tile have?
            safe_exits = sum(1 for dx, dy in dirs.values() if is_safe(cx+dx, cy+dy, {start_node}))
            if safe_exits >= 3: openness += 1

            for dx, dy in dirs.values():
                nx, ny = cx + dx, cy + dy
                if is_safe(nx, ny, {start_node}) and (nx, ny) not in visited:
                    # Can I get here before the enemy?
                    if d + 1 < enemy_reach.get((nx, ny), 999):
                        voronoi_count += 1
                        visited.add((nx, ny))
                        q.append((nx, ny, d + 1))

        # True space calculates checkerboard parity to prevent dead-ends
        true_space = min(parity[0], parity[1]) * 2
        return true_space, openness, voronoi_count

    # --- 5. DECISION ENGINE ---
    scored_moves = []
    for d_name, (dx, dy) in dirs.items():
        target = (x + dx, y + dy)
        if is_safe(target[0], target[1]):
            
            # The "Sudden Death" shield: Never step where an enemy can step next turn
            enemy_arrival = enemy_reach.get(target, 999)
            collision_risk = -1000 if enemy_arrival <= 1 else 0

            space, open_val, vor_val = evaluate(target)

            score = (space * w_space) + (vor_val * w_voronoi) + (open_val * w_openness) + collision_risk

            # Packing bonus: Hugs walls based on our dynamic stance
            obstacles = sum(1 for dx2, dy2 in dirs.values() if not is_safe(target[0]+dx2, target[1]+dy2))
            score += (obstacles * w_packing)

            scored_moves.append((score, d_name))

    if not scored_moves: 
        return "UP" # Better to try a move than crash out
        
    return max(scored_moves, key=lambda x: x[0])[1]