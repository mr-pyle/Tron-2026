import random
from collections import deque

team_name = "MichaelSadik"

def get_safe_neighbors(pos, board_set, grid_dim):
    """Returns immediately safe adjacent tiles."""
    x, y = pos
    candidates = [(x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y)]
    return [(nx, ny) for nx, ny in candidates 
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board_set]

def flood_fill(start_pos, board_set, grid_dim):
    """Calculates the absolute total contiguous space we can reach."""
    queue = deque([start_pos])
    visited = {start_pos}
    while queue:
        cx, cy = queue.popleft()
        for nx, ny in [(cx, cy - 1), (cx, cy + 1), (cx - 1, cy), (cx + 1, cy)]:
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board_set and (nx, ny) not in visited:
                visited.add((nx, ny))
                queue.append((nx, ny))
    return len(visited)

def get_metrics(my_pos, enemies, board_set, grid_dim):
    """
    Simulates a simultaneous board flood to find:
    1. Our exclusive territory
    2. Enemy exclusive territory
    3. Are we in the same room as them?
    """
    queue = deque()
    visited = set(board_set)
    owner_map = {}
    
    # Enqueue enemies
    for ex, ey in enemies:
        if (ex, ey) not in visited:
            queue.append(((ex, ey), 'enemy'))
            visited.add((ex, ey))
            owner_map[(ex, ey)] = 'enemy'
            
    # Enqueue us
    if my_pos not in visited:
        queue.append((my_pos, 'me'))
        visited.add(my_pos)
        owner_map[my_pos] = 'me'
        
    my_v = 0
    enemy_v = 0
    touches_enemy = False
    
    while queue:
        (cx, cy), owner = queue.popleft()
        if owner == 'me':
            my_v += 1
        else:
            enemy_v += 1
            
        for nx, ny in [(cx, cy - 1), (cx, cy + 1), (cx - 1, cy), (cx + 1, cy)]:
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim:
                if (nx, ny) not in visited:
                    visited.add((nx, ny))
                    owner_map[(nx, ny)] = owner
                    queue.append(((nx, ny), owner))
                elif owner_map.get((nx, ny)) != owner:
                    # Our expansion crashed into an enemy expansion
                    touches_enemy = True
                    
    return my_v, enemy_v, touches_enemy

def move(my_pos, board, grid_dim, players):
    
    board_set = set(board.keys()) if isinstance(board, dict) else set(board)
    
    safe_moves = get_safe_neighbors(my_pos, board_set, grid_dim)
    if not safe_moves:
        return "UP" # Completely trapped
        
    enemies = [p['pos'] for p in players if p['pos'] != my_pos and p['alive']]
    
    # --- DODGE HEAD-ON COLLISIONS ---
    threats = set()
    for ex, ey in enemies:
        for nx, ny in [(ex, ey - 1), (ex, ey + 1), (ex - 1, ey), (ex + 1, ey)]:
            threats.add((nx, ny))
            
    non_threatened = [m for m in safe_moves if m not in threats]
    candidate_moves = non_threatened if non_threatened else safe_moves
    
    x, y = my_pos
    dir_map = {
        "UP": (x, y - 1), "DOWN": (x, y + 1), 
        "LEFT": (x - 1, y), "RIGHT": (x + 1, y)
    }
    
    valid_dirs = {d: pos for d, pos in dir_map.items() if pos in candidate_moves}
    
    best_dir = None
    best_score = -float('inf')
    
    # Our current pos turns into a wall behind us
    sim_board = board_set | {my_pos}
    
    for d, pos in valid_dirs.items():
        reachable = flood_fill(pos, sim_board, grid_dim)
        my_v, enemy_v, touches_enemy = get_metrics(pos, enemies, sim_board, grid_dim)
        
        # Wall hugging math (4 means in a tight corner, 0 means open field)
        open_after_move = len(get_safe_neighbors(pos, sim_board, grid_dim))
        wall_touches = 4 - open_after_move
        
        is_isolated = not touches_enemy
        
        if is_isolated or not enemies:
            # --- PHASE 2: PACKING MODE ---
            # The enemy is locked out. We won the territory! 
            # Maximize reachable space, and perfectly snake around the walls to waste zero tiles.
            score = 1000000 + (reachable * 100) + wall_touches
        else:
            # --- PHASE 1: HUNTER-KILLER COMBAT MODE ---
            # We share a room with an enemy. We MUST fight.
            min_enemy_dist = min([abs(pos[0] - e[0]) + abs(pos[1] - e[1]) for e in enemies])
            
            # Don't accidentally dive into a tiny 1-tile dead end just to try and block the enemy
            suicide_penalty = -999999 if reachable < 20 else 0
            
            # Mathematical Aggression:
            # 1. Penalizing `enemy_v` heavily forces the bot to steal choke points.
            # 2. Subtracting `min_enemy_dist` forces the bot to physically charge at the enemy's head.
            score = suicide_penalty + (my_v * 100) - (enemy_v * 250) - (min_enemy_dist * 10) + wall_touches
        
        if score > best_score:
            best_score = score
            best_dir = d
            
    return best_dir if best_dir else random.choice(list(valid_dirs.keys()))