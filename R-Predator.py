import collections

def move(my_pos, board, dim, players):
    x, y = my_pos
    
    # Identify the primary threat (closest active opponent)
    opponents = [p for p in players if p['alive'] and p['pos'] != my_pos]
    if not opponents:
        return "UP" # Default if solo
    
    # Sort opponents by Manhattan distance to find the immediate target
    opponents.sort(key=lambda p: abs(x - p['pos'][0]) + abs(y - p['pos'][1]))
    target_pos = opponents[0]['pos']

    def get_voronoi_score(my_next_pos, opp_pos, current_board, grid_dim):
        """
        Calculates how much territory is 'ours' vs 'theirs'.
        A square belongs to the person who can reach it in fewer steps.
        """
        # Multi-source BFS
        queue = collections.deque([(my_next_pos, 0, True), (opp_pos, 0, False)])
        visited = {my_next_pos: True, opp_pos: False}
        my_territory_count = 0
        
        # We cap the search to stay under 0.1s; 150 is plenty for efficiency
        limit = 150 
        cells_processed = 0

        while queue and cells_processed < limit:
            (cx, cy), dist, is_me = queue.popleft()
            cells_processed += 1
            
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < grid_dim and 0 <= ny < grid_dim:
                    if (nx, ny) not in current_board and (nx, ny) not in visited:
                        visited[(nx, ny)] = is_me
                        if is_me:
                            my_territory_count += 1
                        queue.append(((nx, ny), dist + 1, is_me))
        
        return my_territory_count

    # --- DECISION ENGINE ---
    directions = [("UP", (x, y-1)), ("DOWN", (x, y+1)), ("LEFT", (x-1, y)), ("RIGHT", (x+1, y))]
    scored_moves = []

    for d_name, (nx, ny) in directions:
        # 1. Collision Check
        if not (0 <= nx < dim and 0 <= ny < dim) or (nx, ny) in board:
            continue
        
        # 2. Territorial Efficiency (Voronoi)
        # We want the move that maximizes our exclusive territory
        score = get_voronoi_score((nx, ny), target_pos, board, dim)
        
        # 3. Aggression (Distance to enemy head)
        # We add a small weight to stay close to the enemy to box them in
        dist_to_opp = abs(nx - target_pos[0]) + abs(ny - target_pos[1])
        final_score = (score * 10) - dist_to_opp 

        scored_moves.append((d_name, final_score))

    if not scored_moves:
        return "UP"

    # Pick the move with the highest territorial score
    scored_moves.sort(key=lambda m: m[1], reverse=True)
    return scored_moves[0][0]