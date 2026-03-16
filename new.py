from collections import deque

team_name = "rahmabot"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    directions = {
        "UP": (x, y - 1),
        "DOWN": (x, y + 1),
        "LEFT": (x - 1, y),
        "RIGHT": (x + 1, y)
    }

    enemies = [p['pos'] for p in players if p['pos'] != my_pos and p['alive']]
    
    # 1. FIND ALL IMMEDIATELY VALID MOVES
    valid_moves = {}
    for dir_name, pos in directions.items():
        if 0 <= pos[0] < grid_dim and 0 <= pos[1] < grid_dim and pos not in board:
            valid_moves[dir_name] = pos
            
    if not valid_moves:
        return "UP" # Cornered, game over

    # 2. CHAMBER ISOLATION SCAN
    reachable_space, reachable_enemies = scan_chamber(my_pos, enemies, board, grid_dim)

    # ==========================================
    # PHASE 1: FILL MODE (We are walled off from enemies)
    # ==========================================
    if not reachable_enemies:
        # Abandon wall-hugging. Use Longest Path Approximation.
        fill_stats = {}
        for dir_name, pos in valid_moves.items():
            # Get the total space, AND the physical length of the longest path in that space
            space, max_depth = get_space_and_depth(pos, board, grid_dim)
            fill_stats[dir_name] = (space, max_depth) 

        # Priority 1: Do not slice the room in half (maximize total space)
        # Priority 2: Stretch the path out as long as possible (maximize depth)
        return max(fill_stats.keys(), key=lambda d: fill_stats[d])

    # ==========================================
    # PHASE 2: BATTLE MODE (Enemies are in our chamber)
    # ==========================================
    move_spaces = {}
    for dir_name, pos in valid_moves.items():
        # We just need the raw volume to check for traps during battle mode
        space, _ = get_space_and_depth(pos, board, grid_dim)
        move_spaces[dir_name] = space
        
    max_available_space = max(move_spaces.values())

    # Dynamic Trap Filter: Only allow moves that retain at least 80% of our max possible space
    safe_moves = []
    for dir_name, pos in valid_moves.items():
        if move_spaces[dir_name] >= (max_available_space * 0.8):
            safe_moves.append((dir_name, pos))

    if not safe_moves:
        return max(move_spaces.keys(), key=lambda d: move_spaces[d])

    # Run Voronoi to claim territory and choke the enemy
    best_move = safe_moves[0][0]
    max_territory = -1
    
    for dir_name, pos in safe_moves:
        territory = calculate_territory(pos, enemies, board, grid_dim)
        if territory > max_territory:
            max_territory = territory
            best_move = dir_name
            
    return best_move

# --- HELPER FUNCTIONS ---

def scan_chamber(start_pos, enemies, board, grid_dim):
    """Checks if we share a connected space with any enemies."""
    queue = deque([start_pos])
    visited = {start_pos}
    space = 0
    found_enemies = set()
    enemy_set = set(enemies)
    
    while queue:
        cx, cy = queue.popleft()
        space += 1
        
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim:
                if (nx, ny) in enemy_set:
                    found_enemies.add((nx, ny))
                elif (nx, ny) not in board and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
                    
    return space, len(found_enemies) > 0

def get_space_and_depth(start_pos, board, grid_dim, max_scan=600):
    """
    Flood fills to find BOTH the total volume of the room, 
    and the 'depth' (distance to the furthest reachable tile).
    """
    queue = deque([(start_pos, 1)]) # Store (position, distance_from_start)
    visited = {start_pos}
    space = 0
    max_d = 0
    
    while queue and space < max_scan:
        (cx, cy), dist = queue.popleft()
        space += 1
        
        # Track the deepest we've gone into this chamber
        if dist > max_d:
            max_d = dist
            
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board and (nx, ny) not in visited:
                visited.add((nx, ny))
                queue.append(((nx, ny), dist + 1))
                
    return space, max_d

def calculate_territory(my_future_pos, enemies, board, grid_dim):
    queue = deque()
    visited = {}
    queue.append((my_future_pos, 0, 'ME'))
    visited[my_future_pos] = 'ME'
    
    for e in enemies:
        queue.append((e, 0, 'ENEMY'))
        visited[e] = 'ENEMY'
        
    my_territory = 0
    while queue:
        (cx, cy), dist, owner = queue.popleft()
        if owner == 'ME':
            my_territory += 1
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board and (nx, ny) not in visited:
                visited[(nx, ny)] = owner
                queue.append(((nx, ny), dist + 1, owner))
    return my_territory