import collections

def move(my_pos, board, dim, players):
    # --- 1. THE ENGINE ROOM (BFS) ---
    def get_territory(start_p, current_board):
        queue = collections.deque([start_p])
        visited = {start_p}
        while queue:
            cx, cy = queue.popleft()
            for dx, dy in ((0,1), (0,-1), (1,0), (-1,0)):
                n = (cx+dx, cy+dy)
                if 0 <= n[0] < dim and 0 <= n[1] < dim and n not in current_board and n not in visited:
                    visited.add(n)
                    queue.append(n)
        return visited

    # --- 2. SITUATIONAL AWARENESS ---
    opponents = [p for p in players if p['alive'] and p['pos'] != my_pos]
    if not opponents: return "UP"
    opp_pos = opponents[0]['pos']

    my_room = get_territory(my_pos, board)
    
    # Check if we can even reach the opponent
    is_separated = opp_pos not in my_room

    # --- 3. THE DECISION LOGIC ---
    directions = {"UP": (0,-1), "DOWN": (0,1), "LEFT": (-1,0), "RIGHT": (1,0)}
    best_move = "UP"
    best_score = -float('inf')

    for d_name, (dx, dy) in directions.items():
        nx, ny = my_pos[0]+dx, my_pos[1]+dy
        if not (0 <= nx < dim and 0 <= ny < dim) or (nx, ny) in board:
            continue

        if is_separated:
            # --- ENDGAME MODE: Longest Path Heuristic ---
            # Fill the space as efficiently as possible.
            # We prioritize moving toward squares with fewer neighbors 
            # (hugging walls) to avoid cutting our own space in half.
            neighbors = 0
            for adx, ady in ((0,1), (0,-1), (1,0), (-1,0)):
                if (nx+adx, ny+ady) in board: neighbors += 1
            
            # Survival space is king, neighbors are the tie-breaker
            score = len(get_territory((nx, ny), board)) * 10 + neighbors
        else:
            # --- COMBAT MODE: Voronoi / Space Theft ---
            # Standard high-efficiency aggression
            my_next_room = get_territory((nx, ny), board)
            # We want to maximize our room while minimizing the opponent's
            score = len(my_next_room) - (abs(nx - opp_pos[0]) + abs(ny - opp_pos[1]))

        if score > best_score:
            best_score = score
            best_move = d_name

    return best_move