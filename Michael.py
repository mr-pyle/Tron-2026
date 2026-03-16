team_name = "SpiralStarve"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    
    # Priority 1: Hug the outside by preferring a specific rotation (Right -> Up -> Left -> Down)
    # This order creates a counter-clockwise spiral.
    directions = {
        "RIGHT": (x + 1, y),
        "UP": (x, y - 1),
        "LEFT": (x - 1, y),
        "DOWN": (x, y + 1)
    }

    def is_safe(p):
        px, py = p
        return 0 <= px < grid_dim and 0 <= py < grid_dim and p not in board

    def get_survival_time(start_pos, limit=30):
        """BFS to ensure we aren't spiraling into a 1x1 dead end."""
        nodes = [start_pos]
        visited = {my_pos, start_pos}
        count = 0
        while nodes and count < limit:
            curr = nodes.pop(0)
            count += 1
            cx, cy = curr
            for neighbor in [(cx, cy-1), (cx, cy+1), (cx-1, cy), (cx+1, cy)]:
                if is_safe(neighbor) and neighbor not in visited:
                    visited.add(neighbor)
                    nodes.append(neighbor)
        return count

    # 1. First, filter only moves that don't lead to immediate death
    safe_dirs = []
    for d, pos in directions.items():
        if is_safe(pos):
            space = get_survival_time(pos)
            # Only consider it 'safe' if it has enough room to maneuver
            if space > 2: 
                safe_dirs.append((d, pos, space))

    if not safe_dirs:
        return "UP" # Game over

    # 2. To Spiral: We want to stay as far 'outside' as possible.
    # We rank moves by their proximity to the edges or existing trails.
    def get_edge_closeness(pos):
        px, py = pos
        # Distance to the nearest boundary (wall or existing trail)
        dist_to_wall = min(px, py, grid_dim - 1 - px, grid_dim - 1 - py)
        return dist_to_wall

    # Sort by:
    # 1st: Most space (to avoid traps)
    # 2nd: Edge closeness (lower is better to hug the wall)
    # 3rd: The RIGHT/UP/LEFT/DOWN preference order
    safe_dirs.sort(key=lambda x: (-x[2], get_edge_closeness(x[1])))

    return safe_dirs[0][0]