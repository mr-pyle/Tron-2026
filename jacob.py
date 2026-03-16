def move(pos, board, dim, safe_players):
    x, y = pos

    # 1. Identify valid immediate moves (avoiding walls and trails)
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

    # If trapped, just go UP and accept our fate
    if not valid_moves:
        return "UP"

    # 2. Identify "Danger Zones" 
    # These are squares immediately adjacent to enemy heads. 
    danger_zones = set()
    for p in safe_players:
        if p.get("alive") and p.get("pos") != pos:
            ex, ey = p.get("pos")
            danger_zones.update([
                (ex, ey - 1), (ex, ey + 1), 
                (ex - 1, ey), (ex + 1, ey)
            ])

    # 3. Fast Flood Fill to evaluate open space
    best_move = valid_moves[0][2]
    max_space = -999999 # Using an arbitrary low number instead of float('-inf')

    for nx, ny, direction in valid_moves:
        # Run a fast BFS to see how much territory this path opens up
        space_score = flood_fill(nx, ny, board, dim)

        # Apply a heavy penalty if the move puts us head-to-head with an enemy
        if (nx, ny) in danger_zones:
            space_score -= 10000 

        # Pick the move with the most breathing room
        if space_score > max_space:
            max_space = space_score
            best_move = direction

    return best_move

def flood_fill(start_x, start_y, board, dim, limit=800):
    """
    Vanilla BFS to approximate available space using standard lists.
    Limit reduced slightly to 800 to account for list.pop(0) being slightly slower 
    than a deque, guaranteeing we stay well under the 0.1s timeout.
    """
    queue = [(start_x, start_y)]
    visited = set()
    visited.add((start_x, start_y))
    space = 0

    while queue and space < limit:
        cx, cy = queue.pop(0) # Standard list pop
        space += 1

        # Standard 4-way neighbors
        neighbors = [
            (cx, cy - 1), (cx, cy + 1),
            (cx - 1, cy), (cx + 1, cy)
        ]

        for nx, ny in neighbors:
            if 0 <= nx < dim and 0 <= ny < dim:
                if (nx, ny) not in board and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))

    return space