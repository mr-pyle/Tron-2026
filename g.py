import random
from collections import deque

team_name = "goober bot"

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
                
            # THE FIX: If it's a wall, check if it's an enemy head first!
            if (nx, ny) in board:
                if (nx, ny) in enemy_heads:
                    visited.add((nx, ny)) # Add them to our region so we detect them!
                continue # Still stop expanding past the wall

            visited.add((nx, ny))
            queue.append(((nx, ny), depth + 1))

    return count, visited

def enemies_in_region(region, players, my_pos):
    enemies = []
    for p in players:
        if not p['alive']:
            continue
        if p['pos'] == my_pos:
            continue
        if p['pos'] in region:
            enemies.append(p['pos'])
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
    x, y = my_pos
    my_data = next(p for p in players if p['pos'] == my_pos)

    # Grab all alive enemy heads to pass to the new flood_fill
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

    # ---------------------------------------------------------
    # REQUIREMENT 1: Detect opponent heads in territory
    # ---------------------------------------------------------
    current_region_size, current_region = flood_fill(my_pos, board, grid_dim, enemy_heads)
    enemies = enemies_in_region(current_region, players, my_pos)

    # --- DEBUG PRINTS ---
    if enemies:
        mode = "FIGHT"
        closest = min(enemies, key=lambda e: distance(my_pos, e))
        print(f"[goober] FIGHT MODE! Nearest enemy at {closest}. Distance: {distance(my_pos, closest)}")
    else:
        mode = "BOX"
        print(f"[goober] BOX MODE. No enemies in my region.")

    best_move = safe_moves[0][0]
    best_score = -9999999

    for direction, new_pos in safe_moves:
        temp_board = board.copy()
        temp_board[new_pos] = -1
        score = 0

        # Corridor penalty to prevent trapping itself
        if open_neighbors(new_pos, temp_board, grid_dim) <= 1:
            score -= 500

        if mode == "FIGHT":
            # ---------------------------------------------------------
            # REQUIREMENT 2 (Part A): Target the NEAREST opponent.
            # ---------------------------------------------------------
            closest_enemy_pos = min(enemies, key=lambda e: distance(new_pos, e))
            dist_to_enemy = distance(new_pos, closest_enemy_pos)

            # Check the state of the board IF we make this move
            new_territory, new_region = flood_fill(new_pos, temp_board, grid_dim, enemy_heads)
            enemies_after_move = enemies_in_region(new_region, players, my_pos)

            # ---------------------------------------------------------
            # REQUIREMENT 4: The Ultimate Cutoff
            # ---------------------------------------------------------
            if not enemies_after_move:
                score += 1000000      # The absolute highest priority
                score += new_territory # Tie-breaker: pick the cutoff that gives us the biggest box
                
            else:
                # ---------------------------------------------------------
                # REQUIREMENT 2 (Part B): Approach Mode (Distance > 10)
                # ---------------------------------------------------------
                if dist_to_enemy > 10:
                    score -= dist_to_enemy * 10000 # Massive penalty for not walking toward them
                    
                    # Hug walls mildly to preserve space on the way there
                    walls_around = 4 - open_neighbors(new_pos, temp_board, grid_dim)
                    score += walls_around * 1000
                    
                # ---------------------------------------------------------
                # REQUIREMENT 3: Cut-Off Mode (Distance <= 10)
                # ---------------------------------------------------------
                else:
                    # Look ahead spatially using a depth of 15
                    enemy_territory, _ = flood_fill(closest_enemy_pos, temp_board, grid_dim, enemy_heads, max_depth=15)
                    
                    # If this move makes our territory bigger than theirs, reward heavily
                    if new_territory > enemy_territory:
                        score += 50000
                        
                    # Actively minimize their space (crush their flood fill)
                    score -= enemy_territory * 5000
                    
                    # Abandon wall hugging and draw a straight line to cut them off
                    if direction == current_dir:
                        score += 2000

        else:
            # --- BOX MODE ---
            walls_around = 4 - open_neighbors(new_pos, temp_board, grid_dim)
            score += walls_around * 800 
            
            next_safe_moves = get_safe_moves(new_pos, temp_board, grid_dim)
            best_future_territory = 0
            
            if next_safe_moves:
                for next_dir, next_pos in next_safe_moves:
                    temp_board2 = temp_board.copy()
                    temp_board2[next_pos] = -1
                    future_territory, _ = flood_fill(next_pos, temp_board2, grid_dim, enemy_heads)
                    if future_territory > best_future_territory:
                        best_future_territory = future_territory

            if best_future_territory < current_region_size - 5: 
                score -= 10000 

            score += best_future_territory 

            if direction == current_dir:
                score += 200

        if score > best_score:
            best_score = score
            best_move = direction

    return best_move