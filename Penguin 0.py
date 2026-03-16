from collections import deque
import random

team_name = "Penguin 0"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    dirs = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}

    def is_safe(nx, ny):
        return 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board

    enemies = [p['pos'] for p in players if p['pos'] != my_pos]

    # --- PHASE 1: ENEMY TERRITORY MAPPING (THE THREAT MATRIX) ---
    # We simulate a flood fill from EVERY enemy head simultaneously.
    # This tells us the absolute minimum number of turns it takes ANY enemy to reach any tile.
    enemy_dists = {}
    if enemies:
        queue = deque([(ex, ey, 0) for ex, ey in enemies])
        for ex, ey in enemies:
            enemy_dists[(ex, ey)] = 0
            
        while queue:
            cx, cy, dist = queue.popleft()
            
            # Cap the depth at 300 to keep computation lightning fast
            if dist > 300: continue 
            
            for dx, dy in dirs.values():
                nx, ny = cx + dx, cy + dy
                if is_safe(nx, ny):
                    if (nx, ny) not in enemy_dists or dist + 1 < enemy_dists[(nx, ny)]:
                        enemy_dists[(nx, ny)] = dist + 1
                        queue.append((nx, ny, dist + 1))

    # --- PHASE 2: VORONOI TERRITORY CALCULATION ---
    def calculate_voronoi(start_pos):
        # Calculates how much space WE can reach strictly faster than any enemy
        queue = deque([(start_pos[0], start_pos[1], 1)])
        visited = {start_pos: 1}
        territory_count = 0
        
        while queue:
            cx, cy, dist = queue.popleft()
            territory_count += 1
            
            for dx, dy in dirs.values():
                nx, ny = cx + dx, cy + dy
                if is_safe(nx, ny) and (nx, ny) not in visited:
                    # GAME THEORY: Only claim this tile if we get here before the enemy.
                    # If it's a tie, we don't count it as safe territory.
                    e_dist = enemy_dists.get((nx, ny), float('inf'))
                    if dist + 1 < e_dist:
                        visited[(nx, ny)] = dist + 1
                        queue.append((nx, ny, dist + 1))
        return territory_count

    def count_obstacles(px, py):
        return sum(1 for dx, dy in dirs.values() if not is_safe(px + dx, py + dy))

    # --- PHASE 3: MOVE EVALUATION ---
    safe_moves = []
    for d_name, (dx, dy) in dirs.items():
        nx, ny = x + dx, y + dy
        if is_safe(nx, ny):
            # Calculate the exact Voronoi territory this specific step secures
            territory = calculate_voronoi((nx, ny))
            obstacles = count_obstacles(nx, ny)
            safe_moves.append({
                "dir": d_name, 
                "territory": territory,
                "obstacles": obstacles
            })

    if not safe_moves:
        return "UP" # Cornered, gg.

    # 1. Primary Objective: Maximize our exclusive territory
    max_territory = max(m["territory"] for m in safe_moves)
    best_moves = [m for m in safe_moves if m["territory"] >= max_territory - 1]
    
    # 2. Secondary Objective: "Chambering"
    # If multiple moves give us the same territory (e.g., we are walled off 
    # and completely safe from enemies), we fall back to the Turtle/Coiling strategy 
    # to perfectly pack our trails without trapping ourselves.
    best_moves.sort(key=lambda m: m["obstacles"], reverse=True)
    
    return best_moves[0]["dir"]