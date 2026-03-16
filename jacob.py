def move(pos, board, dim, safe_players):
    x, y = pos

    # 1. THE TIME-WARP ENGINE (Massive Speed Optimization)
    # The tournament likely passes the board as a standard List. Searching a list takes O(N) time.
    # By converting it to a Python Set right here, we drop lookup times to O(1). 
    # This makes the bot roughly 100x faster, unlocking the ability to see into the future.
    fast_board = set(board)

    # 2. Extract Enemy Heads
    enemy_heads = []
    for p in safe_players:
        if p.get("alive") and p.get("pos") != pos:
            # We enforce tuples so they can be hashed easily
            enemy_heads.append(tuple(p.get("pos"))) 

    # 3. Phase Shifting
    match_progress = len(fast_board) / (dim * dim)
    is_hunting_phase = match_progress < 0.40

    # Valid Immediate Moves
    possible_moves = [
        (x, y - 1, "UP"), (x, y + 1, "DOWN"), 
        (x - 1, y, "LEFT"), (x + 1, y, "RIGHT")
    ]
    
    valid_moves = []
    for nx, ny, direction in possible_moves:
        if 0 <= nx < dim and 0 <= ny < dim and (nx, ny) not in fast_board:
            valid_moves.append((nx, ny, direction))

    if not valid_moves:
        return "UP" # Trapped, accept fate

    best_move = valid_moves[0][2]
    best_score = -float('inf')

    for nx, ny, direction in valid_moves:
        # --- FUTURE-CASTING (Depth-2 Lookahead) ---
        # We temporarily claim this square as our own to see what happens NEXT.
        fast_board.add((nx, ny))
        
        future_moves = [
            (nx, ny - 1), (nx, ny + 1), 
            (nx - 1, ny), (nx + 1, ny)
        ]
        
        valid_futures = 0
        max_future_score = -float('inf')
        
        for nnx, nny in future_moves:
            if 0 <= nnx < dim and 0 <= nny < dim and (nnx, nny) not in fast_board:
                valid_futures += 1
                
                # Run the Neural Graph on our FUTURE position
                # Limit slightly reduced to 400 to guarantee we stay under the 0.1s timeout
                stats = analyze_map((nnx, nny), enemy_heads, fast_board, dim, limit=400)
                
                # THE GOD FORMULA
                score = (stats["my_area"] * 100) - (stats["opp_area"] * 150)
                
                # --- ISOLATION ENDGAME CHECK ---
                # If opp_area is 0, we have completely sealed off our own private room.
                if stats["opp_area"] == 0 and stats["neutral"] == 0:
                    # The war is over. Pivot entirely to Perfect Space-Packing.
                    # We multiply by 10,000 so it ignores all other logic and focuses purely on survival.
                    score = stats["my_area"] * 10000 
                else:
                    # Immediate Danger & Aggression Checks
                    min_enemy_dist = 999
                    for ex, ey in enemy_heads:
                        dist = abs(nnx - ex) + abs(nny - ey)
                        if dist < min_enemy_dist:
                            min_enemy_dist = dist
                            
                    if min_enemy_dist <= 1:
                        score -= 100000 
                    elif min_enemy_dist == 2:
                        score -= 5000   
                        
                    if is_hunting_phase and min_enemy_dist > 2:
                        score -= (min_enemy_dist * 20) 
                    elif not is_hunting_phase:
                        score += (min_enemy_dist * 10)
                        
                    # Choke Point Bias
                    if stats["opp_area"] < 10 and stats["my_area"] > 20:
                        score += 50000 

                # Future Wall Hugging
                neighbors = [(nnx, nny-1), (nnx, nny+1), (nnx-1, nny), (nnx+1, nny)]
                walls = sum(1 for vx, vy in neighbors if vx < 0 or vx >= dim or vy < 0 or vy >= dim or (vx, vy) in fast_board)
                wall_weight = 30 if is_hunting_phase else 120 
                score += walls * wall_weight 

                # Tie-breaker: Depth
                score += stats["max_depth"]

                if score > max_future_score:
                    max_future_score = score
                    
        # Clean up our simulation so it doesn't mess up the next loop iteration
        fast_board.remove((nx, ny)) 
        
        # If moving here leaves us trapped with 0 moves on the NEXT turn, it's a death trap!
        if valid_futures == 0:
            current_move_score = -1000000 
        else:
            # We judge this immediate move by its BEST possible future
            current_move_score = max_future_score
            
        # Tie-breaker logic for the immediate step
        immediate_neighbors = [(nx, ny-1), (nx, ny+1), (nx-1, ny), (nx+1, ny)]
        imm_walls = sum(1 for vx, vy in immediate_neighbors if vx < 0 or vx >= dim or vy < 0 or vy >= dim or (vx, vy) in fast_board)
        current_move_score += imm_walls * 5 # Slight bump so we don't float aimlessly if futures tie
            
        if current_move_score > best_score:
            best_score = current_move_score
            best_move = direction

    return best_move


def analyze_map(start_p, opp_ps, fast_board, dim, limit=400):
    """
    The Neural Graph - Now optimized to use the O(1) fast_board.
    """
    queue = [(start_p, 0, True)]
    for op in opp_ps:
        queue.append((op, 0, False))
        
    visited = {start_p: (0, True)}
    for op in opp_ps:
        visited[op] = (0, False)
        
    stats = {"my_area": 0, "opp_area": 0, "neutral": 0, "max_depth": 0}
    
    read_idx = 0
    while read_idx < len(queue) and read_idx < limit:
        curr, dist, is_me = queue[read_idx]
        read_idx += 1 
        
        if is_me and dist > stats["max_depth"]:
            stats["max_depth"] = dist

        cx, cy = curr
        for dx, dy in ((0,1), (0,-1), (1,0), (-1,0)):
            nx, ny = cx + dx, cy + dy
            
            # Now using fast_board (O(1)) instead of board (O(N))
            if 0 <= nx < dim and 0 <= ny < dim and (nx, ny) not in fast_board:
                if (nx, ny) not in visited:
                    visited[(nx, ny)] = (dist + 1, is_me)
                    
                    if is_me: 
                        stats["my_area"] += 1
                    else: 
                        stats["opp_area"] += 1
                        
                    queue.append(((nx, ny), dist + 1, is_me))
                else:
                    v_dist, v_me = visited[(nx, ny)]
                    if v_dist == dist + 1 and v_me != is_me:
                        stats["neutral"] += 1
                        
    return stats

#help