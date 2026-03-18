team_name = "Tea"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    
    directions = {
        "UP": (x, y - 1),
        "DOWN": (x, y + 1),
        "LEFT": (x - 1, y),
        "RIGHT": (x + 1, y)
    }
    
    # --- HELPER 1: FLOOD FILL ---
    # Nested exactly like smart_center to avoid namespace crashes
    def get_flood_fill_size(start_pos):
        visited = set()
        visited.add(start_pos)
        queue = [start_pos]
        head = 0
        
        while head < len(queue):
            cx, cy = queue[head]
            head += 1
            
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                nxt = (nx, ny)
                if 0 <= nx < grid_dim and 0 <= ny < grid_dim:
                    if nxt not in board and nxt not in visited:
                        visited.add(nxt)
                        queue.append(nxt)
                        # Optimization cap to keep the bot lightning fast
                        if len(visited) > 200:
                            return 200
        return len(visited)

    # --- HELPER 2: VORONOI ---
    def get_voronoi_score(target_pos):
        # Identify enemies
        enemy_heads = [p['pos'] for p in players if p['alive'] and p['pos'] != my_pos]
        
        queue = []
        visited = {}
        
        # We start from our potential next move
        queue.append((target_pos, "ME"))
        visited[target_pos] = "ME"
        
        # Enemies start from where they currently are
        for eh in enemy_heads:
            queue.append((eh, "ENEMY"))
            visited[eh] = "ENEMY"
            
        my_territory = 0
        head = 0
        
        while head < len(queue):
            curr_pos, owner = queue[head]
            head += 1
            cx, cy = curr_pos
            
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                nxt = (nx, ny)
                if 0 <= nx < grid_dim and 0 <= ny < grid_dim:
                    if nxt not in board and nxt not in visited:
                        visited[nxt] = owner
                        queue.append((nxt, owner))
                        if owner == "ME":
                            my_territory += 1
                            
        return my_territory

    # 1. Identify valid safe moves
    safe_moves = []
    for d, nxt in directions.items():
        if 0 <= nxt[0] < grid_dim and 0 <= nxt[1] < grid_dim and nxt not in board:
            safe_moves.append(d)
            
    # If completely trapped, crash gracefully by moving UP
    if not safe_moves:
        return "UP"  

    # 2. Evaluate each safe move
    move_scores = {}
    for d in safe_moves:
        nxt = directions[d]
        
        # Calculate flood fill (survival space)
        ff_size = get_flood_fill_size(nxt)
        
        # Calculate Wall Contact (higher is better for packing space)
        wall_contact = 0
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            adj = (nxt[0] + dx, nxt[1] + dy)
            if not (0 <= adj[0] < grid_dim and 0 <= adj[1] < grid_dim) or adj in board:
                wall_contact += 1
                
        # Calculate Voronoi (territory control)
        voronoi = get_voronoi_score(nxt)
        
        move_scores[d] = {
            'ff_size': ff_size,
            'wall_contact': wall_contact,
            'voronoi': voronoi
        }

    # 3. Filter out moves that lead to dead ends (must be within 90% of max available space)
    max_ff = max(scores['ff_size'] for scores in move_scores.values())
    viable_moves = [d for d in safe_moves if move_scores[d]['ff_size'] >= max_ff * 0.9]

    # 4. Rank viable moves: Voronoi first, then wall-hugging
    def get_final_score(d):
        return (move_scores[d]['voronoi'], move_scores[d]['wall_contact'])
        
    viable_moves.sort(key=get_final_score, reverse=True)
    
    return viable_moves[0]