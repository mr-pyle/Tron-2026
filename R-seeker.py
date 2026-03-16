import collections

def move(my_pos, board, dim, players):
    x, y = my_pos
    
    # --- ULTRA-FAST SPACE SCANNER ---
    def get_space_fast(start_pos, obstacle_dict, grid_dim, limit=200):
        """Uses a deque and bit-checking logic for max speed."""
        queue = collections.deque([start_pos])
        visited = {start_pos}
        count = 0
        while queue and count < limit:
            cx, cy = queue.popleft()
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < grid_dim and 0 <= ny < grid_dim:
                    pos = (nx, ny)
                    if pos not in obstacle_dict and pos not in visited:
                        visited.add(pos)
                        queue.append(pos)
                        count += 1
        return count

    # 1. FIND NEAREST PREY
    target = None
    min_dist = 9999
    for p in players:
        if p['alive'] and p['pos'] != my_pos:
            tx, ty = p['pos']
            d = abs(x - tx) + abs(y - ty)
            if d < min_dist:
                min_dist = d
                target = (tx, ty)

    # 2. EVALUATE MOVES
    best_move = "UP"
    best_score = -999999
    
    # We iterate in a fixed order to stay consistent
    directions = [
        ("UP", (x, y - 1)), ("DOWN", (x, y + 1)),
        ("LEFT", (x - 1, y)), ("RIGHT", (x + 1, y))
    ]

    for d_name, (nx, ny) in directions:
        # Instant death check
        if not (0 <= nx < dim and 0 <= ny < dim) or (nx, ny) in board:
            continue
            
        # Calculate survival space (The "Brain")
        # Because this is faster, we can set the limit higher (200 squares)
        space = get_space_fast((nx, ny), board, dim, limit=200)
        
        # Calculate aggression
        dist_score = 0
        if target:
            # Lower distance to target = higher score
            dist_score = (dim * 2) - (abs(nx - target[0]) + abs(ny - target[1]))
        
        # Scoring: Space is weighted to prevent suicide, dist_score for hunting
        # If space is dangerously low, ignore the target and just survive
        total_score = (space * 5) + dist_score if space > 15 else (space * 100)
        
        if total_score > best_score:
            best_score = total_score
            best_move = d_name

    return best_move