def move(pos, board, dim, safe_players):
    # --- 1. THE BARE METAL INDEXER ---
    # We completely abandon X,Y coordinates. Everything is a single integer index.
    my_idx = pos[1] * dim + pos[0]
    
    flat_board = [False] * (dim * dim)
    for bx, by in board:
        flat_board[by * dim + bx] = True

    enemy_indices = []
    for p in safe_players:
        if p.get("alive") and p.get("pos") != pos:
            ex, ey = p.get("pos")
            enemy_indices.append(ey * dim + ex)

    match_progress = len(board) / (dim * dim)
    is_hunting_phase = match_progress < 0.40

    # 1D Directional Offsets: UP, DOWN, LEFT, RIGHT
    offsets = [(-dim, "UP"), (dim, "DOWN"), (-1, "LEFT"), (1, "RIGHT")]
    
    valid_moves = []
    for offset, direction in offsets:
        n_idx = my_idx + offset
        # Boundary math using modulo to ensure we didn't wrap around the edges
        if 0 <= n_idx < (dim * dim) and not flat_board[n_idx]:
            # Extra check to prevent LEFT/RIGHT from wrapping around the map horizontally
            if offset == 1 and n_idx % dim == 0: continue
            if offset == -1 and my_idx % dim == 0: continue
            valid_moves.append((n_idx, direction, offset))

    if not valid_moves:
        return "UP"

    best_move = valid_moves[0][1]
    best_score = -9999999

    for n_idx, direction, move_offset in valid_moves:
        flat_board[n_idx] = True
        
        valid_futures = 0
        max_future_score = -9999999
        
        for f_offset, _ in offsets:
            nn_idx = n_idx + f_offset
            if 0 <= nn_idx < (dim * dim) and not flat_board[nn_idx]:
                if f_offset == 1 and nn_idx % dim == 0: continue
                if f_offset == -1 and n_idx % dim == 0: continue
                
                valid_futures += 1
                
                # --- PROJECTED ENEMIES (Pure Integer Math) ---
                projected_enemies = []
                for e_idx in enemy_indices:
                    moved = False
                    for e_off, _ in offsets:
                        pe_idx = e_idx + e_off
                        if 0 <= pe_idx < (dim * dim) and not flat_board[pe_idx]:
                            if e_off == 1 and pe_idx % dim == 0: continue
                            if e_off == -1 and e_idx % dim == 0: continue
                            projected_enemies.append(pe_idx)
                            moved = True
                    if not moved:
                        projected_enemies.append(e_idx)
                
                # Run the hyper-optimized 1D Neural Graph
                stats = analyze_map(nn_idx, projected_enemies, flat_board, dim, offsets, limit=350)
                
                score = (stats["my_area"] * 100) - (stats["opp_area"] * 150)
                
                if stats["opp_area"] == 0 and stats["neutral"] == 0:
                    score = stats["my_area"] * 10000 
                else:
                    # Manhattan distance without X/Y tuples (using integer division and modulo)
                    min_enemy_dist = 999
                    my_nx, my_ny = nn_idx % dim, nn_idx // dim
                    for ex, ey in [ (e % dim, e // dim) for e in enemy_indices ]:
                        dist = abs(my_nx - ex) + abs(my_ny - ey)
                        if dist < min_enemy_dist:
                            min_enemy_dist = dist
                            
                    if min_enemy_dist <= 1: score -= 100000 
                    elif min_enemy_dist == 2: score -= 5000   
                        
                    if is_hunting_phase and min_enemy_dist > 2: score -= (min_enemy_dist * 20) 
                    elif not is_hunting_phase: score += (min_enemy_dist * 10)
                        
                    if stats["opp_area"] < 10 and stats["my_area"] > 20: score += 50000 

                # Wall count via integer offsets
                walls = 0
                for w_off, _ in offsets:
                    w_idx = nn_idx + w_off
                    if w_idx < 0 or w_idx >= (dim * dim) or flat_board[w_idx]:
                        walls += 1
                    elif w_off == 1 and w_idx % dim == 0: walls += 1
                    elif w_off == -1 and nn_idx % dim == 0: walls += 1
                        
                wall_weight = 30 if is_hunting_phase else 120 
                score += walls * wall_weight 
                score += stats["max_depth"]

                if score > max_future_score: max_future_score = score
                    
        flat_board[n_idx] = False 
        
        current_move_score = max_future_score if valid_futures > 0 else -1000000
        
        # Tie-breaker immediate walls
        imm_walls = 0
        for w_off, _ in offsets:
            w_idx = my_idx + w_off
            if w_idx < 0 or w_idx >= (dim * dim) or flat_board[w_idx]: imm_walls += 1
            elif w_off == 1 and w_idx % dim == 0: imm_walls += 1
            elif w_off == -1 and my_idx % dim == 0: imm_walls += 1
                
        current_move_score += imm_walls * 5 
            
        if current_move_score > best_score:
            best_score = current_move_score
            best_move = direction

    return best_move


def analyze_map(start_idx, opp_indices, flat_board, dim, offsets, limit=350):
    """
    The Bare Metal Graph.
    No tuples. No standard loops. Local variable caching.
    """
    # Initialize with [index, distance, is_me]
    # We use a flat list and groups of 3 to avoid tuple creation entirely
    queue = [start_idx, 0, True]
    for op_idx in opp_indices:
        queue.extend([op_idx, 0, False])
        
    visited = {start_idx: (0, True)}
    for op_idx in opp_indices:
        visited[op_idx] = (0, False)
        
    my_area = 0
    opp_area = 0
    neutral = 0
    max_depth = 0
    
    # --- LOCAL CACHING ---
    # Assigning methods to local variables skips Python's global dictionary lookup.
    # This makes the inner loop run significantly faster.
    q_extend = queue.extend
    
    read_idx = 0
    q_len = len(queue)
    total_cells = dim * dim
    
    # Unroll the offsets for extreme speed
    off_up, off_down, off_left, off_right = -dim, dim, -1, 1
    
    while read_idx < q_len and read_idx < limit * 3:
        c_idx = queue[read_idx]
        dist = queue[read_idx + 1]
        is_me = queue[read_idx + 2]
        read_idx += 3 
        
        if is_me and dist > max_depth:
            max_depth = dist

        new_dist = dist + 1
        
        # --- LOOP UNROLLING ---
        # Instead of `for offset in offsets`, we explicitly write out the 4 checks.
        # This completely bypasses the overhead of creating Python iterator objects.
        
        # UP
        n_idx = c_idx + off_up
        if n_idx >= 0 and not flat_board[n_idx]:
            if n_idx not in visited:
                visited[n_idx] = (new_dist, is_me)
                if is_me: my_area += 1
                else: opp_area += 1
                q_extend([n_idx, new_dist, is_me])
                q_len += 3
            elif visited[n_idx][0] == new_dist and visited[n_idx][1] != is_me:
                neutral += 1

        # DOWN
        n_idx = c_idx + off_down
        if n_idx < total_cells and not flat_board[n_idx]:
            if n_idx not in visited:
                visited[n_idx] = (new_dist, is_me)
                if is_me: my_area += 1
                else: opp_area += 1
                q_extend([n_idx, new_dist, is_me])
                q_len += 3
            elif visited[n_idx][0] == new_dist and visited[n_idx][1] != is_me:
                neutral += 1

        # LEFT
        n_idx = c_idx + off_left
        if n_idx >= 0 and c_idx % dim != 0 and not flat_board[n_idx]:
            if n_idx not in visited:
                visited[n_idx] = (new_dist, is_me)
                if is_me: my_area += 1
                else: opp_area += 1
                q_extend([n_idx, new_dist, is_me])
                q_len += 3
            elif visited[n_idx][0] == new_dist and visited[n_idx][1] != is_me:
                neutral += 1

        # RIGHT
        n_idx = c_idx + off_right
        if n_idx < total_cells and n_idx % dim != 0 and not flat_board[n_idx]:
            if n_idx not in visited:
                visited[n_idx] = (new_dist, is_me)
                if is_me: my_area += 1
                else: opp_area += 1
                q_extend([n_idx, new_dist, is_me])
                q_len += 3
            elif visited[n_idx][0] == new_dist and visited[n_idx][1] != is_me:
                neutral += 1
                        
    return {"my_area": my_area, "opp_area": opp_area, "neutral": neutral, "max_depth": max_depth}