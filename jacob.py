def move(pos, board, dim, safe_players):
    x, y = pos

    # 1. Identify valid immediate moves
    possible_moves = [
        (x, y - 1, "UP"),
        (x, y + 1, "DOWN"),
        (x - 1, y, "LEFT"),
        (x + 1, y, "RIGHT")
    ]
    
    valid_moves = []
    for nx, ny, direction in possible_moves:
        if 0 <= nx < dim and 0 <= ny < dim and (nx, ny) not in board:
            valid_moves.append((nx, ny, direction))

    if not valid_moves:
        return "UP" # Trapped, accept fate

    # 2. Extract Enemy Heads for Voronoi math
    enemy_heads = []
    for p in safe_players:
        if p.get("alive") and p.get("pos") != pos:
            enemy_heads.append(p.get("pos"))

    # 3. Phase Shifting
    board_capacity = dim * dim
    filled_space = len(board) 
    match_progress = filled_space / board_capacity
    is_hunting_phase = match_progress < 0.40

    # 4. Evaluate each valid move
    best_move = valid_moves[0][2]
    best_score = -9999999

    for nx, ny, direction in valid_moves:
        # We now pass our NEXT step into the Voronoi Flood Fill
        space, max_depth = flood_fill_voronoi(nx, ny, board, dim, enemy_heads)
        
        score = space * 10 

        # Immediate Danger Checks
        min_enemy_dist = 999
        for ex, ey in enemy_heads:
            dist = abs(nx - ex) + abs(ny - ey)
            if dist < min_enemy_dist:
                min_enemy_dist = dist
                
        if min_enemy_dist == 1:
            score -= 100000 
        elif min_enemy_dist == 2:
            score -= 5000   
            
        # Dynamic Hunting Logic
        if is_hunting_phase and min_enemy_dist > 2:
            score -= (min_enemy_dist * 20) 
        elif not is_hunting_phase:
            score += (min_enemy_dist * 10)

        # 5. WALL HUGGING
        neighbors = [(nx, ny-1), (nx, ny+1), (nx-1, ny), (nx+1, ny)]
        walls_touched = 0
        for nnx, nny in neighbors:
            if nnx < 0 or nnx >= dim or nny < 0 or nny >= dim or (nnx, nny) in board:
                walls_touched += 1
                
        wall_weight = 30 if is_hunting_phase else 100 # Even heavier wall-hugging late game
        score += walls_touched * wall_weight 

        # 6. Tie-breaker: Depth
        score += max_depth

        if score > best_score:
            best_score = score
            best_move = direction

    return best_move

def flood_fill_voronoi(start_x, start_y, board, dim, enemy_heads, limit=500):
    """
    Advanced Voronoi BFS. 
    It compares our distance (depth) to the enemy's Manhattan distance.
    If the enemy can beat us to a tile, we stop expanding and consider it hostile.
    """
    queue = [(start_x, start_y, 0)] 
    visited = set()
    visited.add((start_x, start_y))
    space = 0
    max_depth = 0

    while queue and space < limit:
        cx, cy, depth = queue.pop(0)
        space += 1
        if depth > max_depth:
            max_depth = depth

        neighbors = [
            (cx, cy - 1), (cx, cy + 1),
            (cx - 1, cy), (cx + 1, cy)
        ]

        for nx, ny in neighbors:
            if 0 <= nx < dim and 0 <= ny < dim:
                if (nx, ny) not in board and (nx, ny) not in visited:
                    
                    # --- THE VORONOI SHIFT ---
                    # Check if an enemy can reach this square faster than we can.
                    # We use depth + 1 (our time to arrive) vs enemy Manhattan distance.
                    is_contested = False
                    for ex, ey in enemy_heads:
                        enemy_dist = abs(nx - ex) + abs(ny - ey)
                        # If enemy is closer or tied, they own this territory.
                        if enemy_dist <= (depth + 1):
                            is_contested = True
                            break
                            
                    if not is_contested:
                        visited.add((nx, ny))
                        queue.append((nx, ny, depth + 1))

    return space, max_depth