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
    # PHASE 1: FILL MODE (Perfect Space Packing)
    # ==========================================
    if not reachable_enemies:
        fill_stats = {}
        for dir_name, pos in valid_moves.items():
            space = get_absolute_space(pos, board, grid_dim)
            onward_liberties = get_liberties(pos, board, grid_dim)
            fill_stats[dir_name] = (space, -onward_liberties) 

        # Priority 1: Maximize space (don't cut the room in half)
        # Priority 2: Minimize onward liberties (clean up edges and corners first)
        return max(fill_stats.keys(), key=lambda d: fill_stats[d])

    # ==========================================
    # PHASE 2: BATTLE MODE (Predictive Lookahead)
    # ==========================================
    move_spaces = {}
    for dir_name, pos in valid_moves.items():
        move_spaces[dir_name] = get_absolute_space(pos, board, grid_dim)
        
    max_available_space = max(move_spaces.values())

    # Dynamic Trap Filter
    safe_moves = []
    for dir_name, pos in valid_moves.items():
        if move_spaces[dir_name] >= (max_available_space * 0.8):
            safe_moves.append((dir_name, pos))

    if not safe_moves:
        return max(move_spaces.keys(), key=lambda d: move_spaces[d])

    # Predictive Voronoi Evaluation
    best_move = safe_moves[0][0]
    max_guaranteed_territory = -1
    
    for dir_name, my_future_pos in safe_moves:
        # Instead of just calculating territory, we predict the enemy's response
        guaranteed_territory = evaluate_move_with_prediction(my_future_pos, enemies, board, grid_dim)
        
        if guaranteed_territory > max_guaranteed_territory:
            max_guaranteed_territory = guaranteed_territory
            best_move = dir_name
            
    return best_move

# --- PREDICTION ENGINE ---

def evaluate_move_with_prediction(my_future_pos, enemies, board, grid_dim):
    """
    Simulates what happens if we move to my_future_pos.
    It looks at the closest enemy, guesses all their possible next moves, 
    and assumes they will pick the one that gives US the least territory.
    """
    if not enemies:
        return calculate_territory(my_future_pos, enemies, board, grid_dim)

    # Find the most immediate threat (closest enemy)
    closest_enemy = min(enemies, key=lambda e: abs(e[0] - my_future_pos[0]) + abs(e[1] - my_future_pos[1]))
    
    # Figure out all valid moves the enemy could make next turn
    ex, ey = closest_enemy
    enemy_options = [(ex, ey - 1), (ex, ey + 1), (ex - 1, ey), (ex + 1, ey)]
    valid_enemy_moves = [ep for ep in enemy_options 
                         if 0 <= ep[0] < grid_dim and 0 <= ep[1] < grid_dim 
                         and ep not in board and ep != my_future_pos]
                         
    if not valid_enemy_moves:
        # The enemy is trapped next turn; moving here is a massive win
        return calculate_territory(my_future_pos, enemies, board, grid_dim) + 1000

    # MINIMAX: Assume the enemy picks the move that minimizes our territory
    worst_case_territory = float('inf')
    
    for enemy_future_pos in valid_enemy_moves:
        # Simulate the board state with the enemy in their new position
        simulated_enemies = [enemy_future_pos if e == closest_enemy else e for e in enemies]
        
        # Calculate how much territory we would get in this simulated scenario
        territory = calculate_territory(my_future_pos, simulated_enemies, board, grid_dim)
        
        if territory < worst_case_territory:
            worst_case_territory = territory
            
    return worst_case_territory

# --- HELPER FUNCTIONS ---

def scan_chamber(start_pos, enemies, board, grid_dim):
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

def get_liberties(pos, board, grid_dim):
    liberties = 0
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        nx, ny = pos[0] + dx, pos[1] + dy
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
            liberties += 1
    return liberties

def get_absolute_space(start_pos, board, grid_dim, max_depth=600):
    queue = deque([start_pos])
    visited = {start_pos}
    space = 0
    while queue and space < max_depth:
        cx, cy = queue.popleft()
        space += 1
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board and (nx, ny) not in visited:
                visited.add((nx, ny))
                queue.append((nx, ny))
    return space

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
