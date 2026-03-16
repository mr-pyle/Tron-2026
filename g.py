import random
from collections import deque

team_name = "goober bot"

bot_state = {
    "mode": "BOX",
    "target_id": None
}

def distance(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def flood_fill(start, board, grid_dim, enemy_heads, max_depth=1000):
    queue = deque([(start, 0)]) 
    visited = set([start])
    count = 0

    while queue:
        (x, y), depth = queue.popleft()
        count += 1
        
        if depth >= max_depth:
            continue

        neighbors = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]

        for nx, ny in neighbors:
            if (nx, ny) in visited:
                continue
            if not (0 <= nx < grid_dim and 0 <= ny < grid_dim):
                continue
                
            if (nx, ny) in board:
                if (nx, ny) in enemy_heads:
                    visited.add((nx, ny)) 
                continue 

            visited.add((nx, ny))
            queue.append(((nx, ny), depth + 1))

    return count, visited

def enemies_in_region(region, players, my_pos):
    enemies = []
    for p in players:
        if not p['alive'] or p['pos'] == my_pos:
            continue
        if p['pos'] in region:
            enemies.append(p)
    return enemies

def open_neighbors(pos, board, grid_dim):
    x, y = pos
    neighbors = [(x+1, y), (x-1, y), (x, y+1), (x, y-1)]
    count = 0
    for nx, ny in neighbors:
        if not (0 <= nx < grid_dim and 0 <= ny < grid_dim):
            continue
        if (nx, ny) not in board:
            count += 1
    return count

def get_safe_moves(pos, board, grid_dim):
    x, y = pos
    directions = {
        "UP": (x, y-1),
        "DOWN": (x, y+1),
        "LEFT": (x-1, y),
        "RIGHT": (x+1, y)
    }
    safe = []
    for d, (nx, ny) in directions.items():
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
            safe.append((d, (nx, ny)))
    return safe

def move(my_pos, board, grid_dim, players):
    global bot_state
    x, y = my_pos
    my_data = next(p for p in players if p['pos'] == my_pos)

    # Reset state on new match
    if my_data['survival'] <= 1:
        bot_state = {"mode": "BOX", "target_id": None}

    enemy_heads = [p['pos'] for p in players if p['alive'] and p['pos'] != my_pos]

    current_dir = None
    if len(my_data['trail']) > 1:
        last = my_data['trail'][-2]
        if x > last[0]: current_dir = "RIGHT"
        elif x < last[0]: current_dir = "LEFT"
        elif y > last[1]: current_dir = "DOWN"
        elif y < last[1]: current_dir = "UP"

    safe_moves = get_safe_moves(my_pos, board, grid_dim)
    if not safe_moves:
        return "UP" 

    current_region_size, current_region = flood_fill(my_pos, board, grid_dim, enemy_heads)
    enemies = enemies_in_region(current_region, players, my_pos)

    # --- STATE MACHINE ---
    if enemies:
        nearest_enemy = min(enemies, key=lambda e: distance(my_pos, e['pos']))
        dist_to_nearest = distance(my_pos, nearest_enemy['pos'])
        
        if bot_state["mode"] == "FIGHT" and bot_state["target_id"] is not None:
            enemy_ids = [e['id'] for e in enemies]
            if bot_state["target_id"] not in enemy_ids:
                bot_state["mode"] = "BOX"
                bot_state["target_id"] = None
                print(f"[goober] CUTOFF SECURED. Entering Box Mode.")

        if len(enemies) <= 2 or dist_to_nearest <= 20:
            if bot_state["mode"] != "FIGHT":
                print(f"[goober] HUNTING TARGET: {nearest_enemy['pos']}.")
            bot_state["mode"] = "FIGHT"
            bot_state["target_id"] = nearest_enemy['id']
        else:
            bot_state["mode"] = "BOX"
            bot_state["target_id"] = None
    else:
        if bot_state["mode"] == "FIGHT":
            print(f"[goober] ROOM CLEARED. Locking Box Mode.")
        bot_state["mode"] = "BOX"
        bot_state["target_id"] = None

    target_obj = None
    if bot_state["mode"] == "FIGHT":
        target_obj = next((e for e in enemies if e['id'] == bot_state["target_id"]), None)
        if not target_obj and enemies:
            target_obj = nearest_enemy

    # --- MOVE EVALUATION ---
    best_move = safe_moves[0][0]
    best_score = -9999999

    for direction, new_pos in safe_moves:
        temp_board = board.copy()
        temp_board[new_pos] = -1
        score = 0

        # Lookahead 1 step for dead ends
        next_safe_moves = get_safe_moves(new_pos, temp_board, grid_dim)
        max_future_territory = 0
        
        if not next_safe_moves:
            score -= 2000000 
        else:
            for next_dir, next_pos in next_safe_moves:
                temp_board2 = temp_board.copy()
                temp_board2[next_pos] = -1
                future_territory, _ = flood_fill(next_pos, temp_board2, grid_dim, enemy_heads)
                if future_territory > max_future_territory:
                    max_future_territory = future_territory

        if open_neighbors(new_pos, temp_board, grid_dim) <= 1:
            score -= 500

        if bot_state["mode"] == "FIGHT" and target_obj:
            closest_enemy_pos = target_obj['pos']
            dist_to_enemy = distance(new_pos, closest_enemy_pos)

            if max_future_territory < 30:
                score -= 500000 # Absolute survival floor

            # Base Hunting Score: PRIORITY 1 is closing the distance
            score -= dist_to_enemy * 1000 
            # Secondary: Hug walls while closing distance
            walls_around = 4 - open_neighbors(new_pos, temp_board, grid_dim)
            score += walls_around * 200    
            score += max_future_territory * 10
            
            if direction == current_dir:
                score += 300 # Anti-wiggle

            # --- OMNIDIRECTIONAL RADAR ---
            # Check all 4 directions from this potential new step
            best_ray_score = 0
            
            for ray_dir in ["UP", "DOWN", "LEFT", "RIGHT"]:
                ray_board = temp_board.copy()
                ray_pos = new_pos
                ray_steps = 1
                
                while True:
                    nx, ny = ray_pos
                    if ray_dir == "UP": ny -= 1
                    elif ray_dir == "DOWN": ny += 1
                    elif ray_dir == "LEFT": nx -= 1
                    elif ray_dir == "RIGHT": nx += 1
                    
                    if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in ray_board and (nx, ny) not in enemy_heads:
                        ray_pos = (nx, ny)
                        ray_board[ray_pos] = -1
                        ray_steps += 1
                    else:
                        break 

                if ray_steps > 1:
                    enemy_steps_to_impact = distance(closest_enemy_pos, ray_pos)

                    if ray_steps < enemy_steps_to_impact:
                        # WE WIN THE RACE to the wall. Evaluate cutoff.
                        ray_my_territory, ray_my_region = flood_fill(new_pos, ray_board, grid_dim, enemy_heads)
                        ray_enemies = enemies_in_region(ray_my_region, players, my_pos)
                        target_in_ray = any(e['id'] == target_obj['id'] for e in ray_enemies)

                        if not target_in_ray:
                            ray_enemy_territory, _ = flood_fill(closest_enemy_pos, ray_board, grid_dim, enemy_heads)
                            
                            if ray_my_territory > ray_enemy_territory and ray_my_territory >= 30:
                                if ray_my_territory > (current_region_size * 0.40):
                                    # LETHAL CUTOFF FOUND
                                    ray_score = 2000000 + (ray_my_territory * 100)
                                    if ray_dir == direction:
                                        ray_score += 50000 # Massive bonus to actually take the shot
                                    best_ray_score = max(best_ray_score, ray_score)
                                else:
                                    # Weak cutoff, don't overcommit
                                    best_ray_score = max(best_ray_score, ray_my_territory * 10)
                            else:
                                # Suicidal cutoff (traps us in smaller space)
                                if ray_dir == direction:
                                    score -= 5000000
                    else:
                        # THEY WIN THE RACE.
                        if ray_dir == direction:
                            score -= 1000000 # Do NOT move straight into an interception

            score += best_ray_score

        else:
            # --- PERMANENT BOX MODE ---
            walls_around = 4 - open_neighbors(new_pos, temp_board, grid_dim)
            score += walls_around * 800 

            if max_future_territory < current_region_size - 5: 
                score -= 10000 

            score += max_future_territory 

            if direction == current_dir:
                score += 500 

        if score > best_score:
            best_score = score
            best_move = direction

    return best_move