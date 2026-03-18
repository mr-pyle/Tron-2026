# engine.py

def calculate_new_pos(pos, move):
    """Calculates the next (x, y) coordinate based on a direction string."""
    x, y = pos
    if move == "UP": y -= 1
    elif move == "DOWN": y += 1
    elif move == "LEFT": x -= 1
    elif move == "RIGHT": x += 1
    return (x, y)

def resolve_collisions(grid_dim, alive_players, intended_moves, board, dead_player_ids, current_rank_score):
    """
    Takes the intended moves and resolves all physics and collisions.
    Updates the board, player positions, trails, and deaths in-place.
    Returns a list of player IDs that died this specific turn.
    """
    # --- PHASE 1: COUNT CLAIMS ON EACH SQUARE ---
    square_claims = {}
    for pos in intended_moves.values():
        if pos != "ERROR":
            square_claims[pos] = square_claims.get(pos, 0) + 1

    died_this_turn = []

    # --- PHASE 2: RESOLVE COLLISIONS ---
    for p in alive_players:
        if p['id'] in dead_player_ids: 
            continue
            
        new_pos = intended_moves.get(p['id'])
        old_pos = p['pos']
        
        # 1. Error / Timeout
        if new_pos == "ERROR":
            died_this_turn.append(p['id'])
            continue
            
        # 2. Head-to-head collision
        if square_claims[new_pos] > 1:
            died_this_turn.append(p['id'])
            continue
            
        # 3. Ghost pass-through collision (swapping spots)
        ghost_swap = False
        for other_p in alive_players:
            if other_p['id'] != p['id'] and other_p['id'] not in dead_player_ids:
                if intended_moves.get(other_p['id']) == old_pos and other_p['pos'] == new_pos:
                    ghost_swap = True
                    break
                    
        if ghost_swap:
            died_this_turn.append(p['id'])
            continue

        # 4. Walls and Trails
        if not (0 <= new_pos[0] < grid_dim and 0 <= new_pos[1] < grid_dim) or new_pos in board:
            died_this_turn.append(p['id'])
        else:
            # Move is completely safe! Update the player and the board.
            p['pos'] = new_pos
            p['trail'].append(new_pos)
            board[new_pos] = p['id']

    # --- PHASE 3: APPLY DEATHS ---
    for pid in died_this_turn:
        dead_player_ids.add(pid)
        # Find the player object and update its stats
        for p in alive_players:
            if p['id'] == pid:
                p['alive'] = False
                p['rank'] = current_rank_score
                break
                
    return died_this_turn