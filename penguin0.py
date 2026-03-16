
from collections import deque

team_name = "Emperor Penguin v4"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    dirs = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}

    def is_safe(nx, ny):
        return 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board

    enemies = [p for p in players if p['pos'] != my_pos and p.get('alive', True)]
    enemy_positions = [e['pos'] for e in enemies]

    # --- ENCIRCLEMENT TRACKER ---
    # How many enemies are actively collapsing on our position?
    collapsing_enemies = [e for e in enemy_positions if abs(x - e[0]) + abs(y - e[1]) < 18]
    encirclement_threat_level = len(collapsing_enemies)

    # --- DYNAMIC SCALING ---
    alive_count = len(enemies)
    if alive_count > 6:
        threat_depth, voronoi_depth = 150, 200
    elif alive_count > 2:
        threat_depth, voronoi_depth = 300, 400
    else:
        threat_depth, voronoi_depth = 600, 1000

    # --- PHASE 1: THREAT MATRIX ---
    enemy_dists = {}
    if enemy_positions:
        queue = deque([(ex, ey, 0) for ex, ey in enemy_positions])
        for ex, ey in enemy_positions:
            enemy_dists[(ex, ey)] = 0
            
        while queue:
            cx, cy, dist = queue.popleft()
            if dist > threat_depth: continue 
            
            for dx, dy in dirs.values():
                nx, ny = cx + dx, cy + dy
                if is_safe(nx, ny):
                    if (nx, ny) not in enemy_dists or dist + 1 < enemy_dists[(nx, ny)]:
                        enemy_dists[(nx, ny)] = dist + 1
                        queue.append((nx, ny, dist + 1))

    # --- PHASE 2: VORONOI + PARITY + OPENNESS ---
    def evaluate_move(start_pos):
        queue = deque([(start_pos[0], start_pos[1], 1)])
        visited = {start_pos: 1}
        parity = {0: 0, 1: 0}
        touches_enemy = False
        openness_score = 0 # NEW: Tracks how "wide" the space is
        
        while queue:
            cx, cy, dist = queue.popleft()
            parity[(cx + cy) % 2] += 1
            
            # Calculate openness (tiles with 3+ safe neighbors are wide arenas)
            safe_neighbors = sum(1 for dx, dy in dirs.values() if is_safe(cx + dx, cy + dy))
            if safe_neighbors >= 3:
                openness_score += 1
            
            if touches_enemy and dist > voronoi_depth:
                continue
                
            for dx, dy in dirs.values():
                nx, ny = cx + dx, cy + dy
                if is_safe(nx, ny) and (nx, ny) not in visited:
                    e_dist = enemy_dists.get((nx, ny), float('inf'))
                    if dist + 1 < e_dist:
                        visited[(nx, ny)] = dist + 1
                        queue.append((nx, ny, dist + 1))
                    elif dist + 1 <= e_dist + 2:
                        touches_enemy = True 
                        
        true_space = (min(parity[0], parity[1]) * 2) + 1
        return true_space, touches_enemy, openness_score

    def count_obstacles(px, py):
        return sum(1 for dx, dy in dirs.values() if not is_safe(px + dx, py + dy))

    def is_suicide(px, py):
        return sum(1 for dx, dy in dirs.values() if is_safe(px + dx, py + dy)) == 0

    # --- PHASE 3: MOVE EVALUATION ---
    safe_moves = []
    for d_name, (dx, dy) in dirs.items():
        nx, ny = x + dx, y + dy
        if is_safe(nx, ny):
            if enemy_dists.get((nx, ny), float('inf')) <= 1:
                continue 
                
            if is_suicide(nx, ny):
                safe_moves.append({"dir": d_name, "space": -1, "obstacles": 0, "touches": False, "openness": 0, "pos": (nx, ny)})
                continue

            space, touches, openness = evaluate_move((nx, ny))
            safe_moves.append({
                "dir": d_name, "space": space, "obstacles": count_obstacles(nx, ny), 
                "touches": touches, "openness": openness, "pos": (nx, ny)
            })

    if not safe_moves:
        for d_name, (dx, dy) in dirs.items():
            nx, ny = x + dx, y + dy
            if is_safe(nx, ny):
                if is_suicide(nx, ny):
                    safe_moves.append({"dir": d_name, "space": -1, "obstacles": 0, "touches": False, "openness": 0, "pos": (nx, ny)})
                    continue
                space, touches, openness = evaluate_move((nx, ny))
                safe_moves.append({
                    "dir": d_name, "space": space, "obstacles": count_obstacles(nx, ny), 
                    "touches": touches, "openness": openness, "pos": (nx, ny)
                })

    if not safe_moves:
        return "UP" 

    # --- PHASE 4: THE MASTER STATE MACHINE ---
    survivable_moves = [m for m in safe_moves if m["space"] > -1]
    if not survivable_moves:
        return safe_moves[0]["dir"]

    max_space = max(m["space"] for m in survivable_moves)
    viable_moves = [m for m in survivable_moves if m["space"] >= max_space * 0.85]

    is_isolated = all(not m["touches"] for m in viable_moves)

    # STATE 1: PERFECT ISOLATION
    if is_isolated:
        # We are completely safe. Ignore openness, just hug walls to pack the room.
        viable_moves.sort(key=lambda m: m["obstacles"], reverse=True)
        return viable_moves[0]["dir"]

    # STATE 2: HIGH ENCIRCLEMENT THREAT (2+ Enemies Closing In)
    if encirclement_threat_level >= 2:
        # PANIC/ESCAPE MODE: We are getting pinched. 
        # Top priority: Run to the area with the absolute highest Openness Score!
        # Do NOT hug walls, and do NOT enter narrow corridors.
        viable_moves.sort(key=lambda m: m["openness"], reverse=True)
        return viable_moves[0]["dir"]

    # STATE 3: THE BOUNCER (1 Enemy Nearby)
    if encirclement_threat_level == 1:
        # AREA DENIAL: A single enemy is trying to push into our space.
        # We want to push back and block them, but ONLY if the move keeps our Openness high.
        ex, ey = collapsing_enemies[0]
        def bouncer_score(m):
            dist_to_enemy = abs(m["pos"][0] - ex) + abs(m["pos"][1] - ey)
            # We want to be close to the enemy to block them, but maintain high openness
            return (m["openness"] * 2) - dist_to_enemy 
        
        viable_moves.sort(key=bouncer_score, reverse=True)
        return viable_moves[0]["dir"]

    # STATE 4: OPEN WARFARE (No immediate threats, but board is shared)
    viable_moves.sort(key=lambda m: m["openness"] + m["space"], reverse=True)
    return viable_moves[0]["dir"]