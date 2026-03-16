from collections import deque

team_name = "Brayden's_bot"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    dirs = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}

    def is_safe(nx, ny):
        return 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board

    enemies = [p['pos'] for p in players if p['pos'] != my_pos and p.get('alive', True)]

    # --- PHASE 1: THE THREAT MATRIX ---
    enemy_dists = {}
    if enemies:
        queue = deque([(ex, ey, 0) for ex, ey in enemies])
        for ex, ey in enemies:
            enemy_dists[(ex, ey)] = 0
            
        while queue:
            cx, cy, dist = queue.popleft()
            if dist > 350: continue 
            
            for dx, dy in dirs.values():
                nx, ny = cx + dx, cy + dy
                if is_safe(nx, ny):
                    if (nx, ny) not in enemy_dists or dist + 1 < enemy_dists[(nx, ny)]:
                        enemy_dists[(nx, ny)] = dist + 1
                        queue.append((nx, ny, dist + 1))

    # --- PHASE 2: FRONTIER-AWARE VORONOI + PARITY MATH ---
    def evaluate_move(start_pos):
        queue = deque([(start_pos[0], start_pos[1], 1)])
        visited = {start_pos: 1}
        parity = {0: 0, 1: 0} 
        touches_enemy = False 
        
        while queue:
            cx, cy, dist = queue.popleft()
            parity[(cx + cy) % 2] += 1
            
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
        return true_space, touches_enemy

    def count_obstacles(px, py):
        return sum(1 for dx, dy in dirs.values() if not is_safe(px + dx, py + dy))

    def is_suicide(px, py):
        return sum(1 for dx, dy in dirs.values() 
                   if is_safe(px + dx, py + dy) and (px + dx, py + dy) != my_pos) == 0

    # NEW: ACTIVE TRAPPING SIMULATION
    def get_enemy_space(my_next_pos, target_enemy_pos):
        # Flood fill from the enemy's head, pretending we just moved to my_next_pos
        queue = deque([target_enemy_pos])
        visited = {target_enemy_pos, my_next_pos, my_pos} 
        space = 0
        while queue:
            cx, cy = queue.popleft()
            space += 1
            if space > 100: # Cap at 100 so the bot stays lightning fast
                break
            for dx, dy in dirs.values():
                nx, ny = cx + dx, cy + dy
                if is_safe(nx, ny) and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
        return space

    # --- PHASE 3: MOVE EVALUATION ---
    safe_moves = []
    for d_name, (dx, dy) in dirs.items():
        nx, ny = x + dx, y + dy
        if is_safe(nx, ny):
            
            if enemy_dists.get((nx, ny), float('inf')) <= 1:
                continue 
                
            if is_suicide(nx, ny):
                safe_moves.append({"dir": d_name, "pos": (nx, ny), "territory": -1, "obstacles": 0, "touches_enemy": False})
                continue

            territory, touches_enemy = evaluate_move((nx, ny))
            safe_moves.append({
                "dir": d_name, "pos": (nx, ny), "territory": territory,
                "obstacles": count_obstacles(nx, ny), "touches_enemy": touches_enemy
            })

    if not safe_moves:
        for d_name, (dx, dy) in dirs.items():
            nx, ny = x + dx, y + dy
            if is_safe(nx, ny):
                territory, touches_enemy = evaluate_move((nx, ny))
                safe_moves.append({
                    "dir": d_name, "pos": (nx, ny), "territory": territory,
                    "obstacles": count_obstacles(nx, ny), "touches_enemy": touches_enemy
                })

    if not safe_moves:
        return "UP" 

    # --- PHASE 4: THE STATE MACHINE ---
    survivable_moves = [m for m in safe_moves if m["territory"] > -1]
    if not survivable_moves:
        return safe_moves[0]["dir"] 

    max_territory = max(m["territory"] for m in survivable_moves)
    best_moves = [m for m in survivable_moves if m["territory"] >= max_territory - 2]

    is_isolated = all(not m["touches_enemy"] for m in best_moves)

    if is_isolated:
        # STATE: ISOLATED (Endgame Packing)
        best_moves.sort(key=lambda m: m["obstacles"], reverse=True)
    else:
        # STATE: OPEN WARFARE (Active Trapping)
        if enemies:
            # 1. Find the closest enemy
            closest_enemy = min(enemies, key=lambda e: abs(my_pos[0] - e[0]) + abs(my_pos[1] - e[1]))
            
            # 2. Simulate how much space they have if we take each move
            for m in best_moves:
                m["enemy_space"] = get_enemy_space(m["pos"], closest_enemy)
            
            # 3. Sort by lowest enemy space first, then highest territory for us
            best_moves.sort(key=lambda m: (m["enemy_space"], -m["territory"]))
        else:
            best_moves.sort(key=lambda m: -m["territory"])

    return best_moves[0]["dir"]