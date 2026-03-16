import random
from collections import deque

team_name = "MichaelSadik"

def get_open_neighbors(pos, board, grid_dim):
    """Returns a list of safe, open adjacent coordinates."""
    x, y = pos
    candidates = [(x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y)]
    return [(nx, ny) for nx, ny in candidates 
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board]

def get_threatened_tiles(enemies, board, grid_dim):
    """Calculates all tiles that enemies could potentially step on next tick."""
    threats = set()
    for ex, ey in enemies:
        for nx, ny in [(ex, ey - 1), (ex, ey + 1), (ex - 1, ey), (ex + 1, ey)]:
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
                threats.add((nx, ny))
    return threats

def calculate_voronoi_and_isolation(my_new_pos, enemies, board, grid_dim):
    """Returns (territory_size, is_isolated) to evaluate a move's strength."""
    queue = deque()
    visited = set(board)
    owner_map = {}
    
    # 1. Add enemies to the map
    for ex, ey in enemies:
        if (ex, ey) not in visited:
            queue.append(((ex, ey), 'enemy'))
            visited.add((ex, ey))
            owner_map[(ex, ey)] = 'enemy'
            
    # 2. Add our simulated next position
    if my_new_pos not in visited:
        queue.append((my_new_pos, 'me'))
        visited.add(my_new_pos)
        owner_map[my_new_pos] = 'me'
        
    my_territory = 0
    touches_enemy = False
    
    # 3. Flood the board to see who reaches what first
    while queue:
        (cx, cy), owner = queue.popleft()
        
        if owner == 'me':
            my_territory += 1
            
        for nx, ny in [(cx, cy - 1), (cx, cy + 1), (cx - 1, cy), (cx + 1, cy)]:
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim:
                if (nx, ny) not in visited:
                    visited.add((nx, ny))
                    owner_map[(nx, ny)] = owner
                    queue.append(((nx, ny), owner))
                elif owner_map.get((nx, ny)) != owner:
                    # Our territory clashed with an enemy's territory
                    touches_enemy = True
                    
    return my_territory, not touches_enemy

def move(my_pos, board, grid_dim, players):
    
    # Get all immediately safe tiles
    open_neighbors = get_open_neighbors(my_pos, board, grid_dim)
    
    if not open_neighbors:
        return "UP" # Completely trapped, die with dignity
        
    # Find all living enemies on the board
    enemies = [p['pos'] for p in players if p['pos'] != my_pos and p['alive']]
    
    # --- AVOID DYING (Threat Anticipation) ---
    # Find tiles enemies could step into and filter them out to prevent head-on collisions
    threatened_tiles = get_threatened_tiles(enemies, board, grid_dim)
    safe_neighbors = [pos for pos in open_neighbors if pos not in threatened_tiles]
    
    # If avoiding a head-on collision means hitting a wall, we ignore the threat 
    # and risk the 50/50 collision tie just to survive another tick.
    candidate_neighbors = safe_neighbors if safe_neighbors else open_neighbors
    
    x, y = my_pos
    dir_map = {
        "UP": (x, y - 1),
        "DOWN": (x, y + 1),
        "LEFT": (x - 1, y),
        "RIGHT": (x + 1, y)
    }
    
    valid_moves = {d: pos for d, pos in dir_map.items() if pos in candidate_neighbors}
    
    best_move = None
    max_territory = -1
    all_isolated = True
    move_evaluations = {}

    # --- ATTACK OTHER PLAYERS (Voronoi Territory Control) ---
    for direction, pos in valid_moves.items():
        # Evaluate how much territory this move aggressively cuts off from opponents
        territory, is_isolated = calculate_voronoi_and_isolation(pos, enemies, board, grid_dim)
        move_evaluations[direction] = (territory, is_isolated, pos)
        
        if not is_isolated:
            all_isolated = False
            
        if territory > max_territory:
            max_territory = territory
            best_move = direction

    # --- FILL ALL HOLES (Warnsdorff's Rule) ---
    # If the bot successfully seals an enemy out and has its own private room, 
    # it completely abandons attacking and switches to perfect space packing.
    if all_isolated:
        best_packing_move = None
        min_future_freedoms = 999
        
        for direction, (_, _, pos) in move_evaluations.items():
            # Check how many empty tiles we can step on AFTER making this move
            future_freedoms = len(get_open_neighbors(pos, board, grid_dim))
            
            # Move to the tile with the FEWEST future options. 
            # This forces the bot to hug the walls and fill tight corners first, 
            # naturally packing the space like a fluid without cutting the room in half.
            if future_freedoms < min_future_freedoms:
                min_future_freedoms = future_freedoms
                best_packing_move = direction
                
        return best_packing_move if best_packing_move else random.choice(list(valid_moves.keys()))

    # If we are NOT isolated, aggressively attack the center and cut off enemies
    return best_move if best_move else random.choice(list(valid_moves.keys()))