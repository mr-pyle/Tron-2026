import random

team_name = "GhostPlus4"

DIRECTIONS = {
    "UP": (0, -1),
    "DOWN": (0, 1),
    "LEFT": (-1, 0),
    "RIGHT": (1, 0),
}

def move(my_pos, board, grid_dim, players):
    x, y = my_pos

    # 1. Safe moves
    safe = {}
    for name, (dx, dy) in DIRECTIONS.items():
        nx, ny = x + dx, y + dy
        if (
            0 <= nx < grid_dim and 0 <= ny < grid_dim and
            (nx, ny) not in board
        ):
            safe[name] = (nx, ny)

    if not safe:
        return "UP"

    # 2. Opponents
    opps = [p["pos"] for p in players if p["pos"] != my_pos and p.get("alive", True)]

    # 3. Compute reachable areas
    my_area = flood_fill_area(my_pos, board, grid_dim)

    if opps:
        opp_area = 0
        for ox, oy in opps:
            opp_area += flood_fill_area((ox, oy), board, grid_dim)
        opp_area /= len(opps)
    else:
        opp_area = 0

    # 4. Detect POCKET MODE
    pocket_mode = (opp_area == 0)

    # 5. Determine normal mode
    if opps:
        avg_dist = sum(abs(x - ox) + abs(y - oy) for ox, oy in opps) / len(opps)
    else:
        avg_dist = grid_dim * 2

    if pocket_mode:
        mode = "POCKET"
    elif avg_dist < grid_dim // 3:
        mode = "AVOID"
    else:
        mode = "SPACE"

    # 6. Compute open-space target
    target = find_open_space_target(board, grid_dim)

    best_score = None
    best_moves = []

    for d_name, (nx, ny) in safe.items():

        # Flood fill for safety
        space_score = flood_fill_area((nx, ny), board, grid_dim)

        # Distance from opponents
        if opps:
            dist_score = sum(abs(nx - ox) + abs(ny - oy) for ox, oy in opps) / len(opps)
        else:
            dist_score = grid_dim * 2

        # Danger map
        danger = opponent_influence((nx, ny), opps)

        # Row sweeping pattern
        if ny % 2 == 0:
            preferred = "RIGHT"
        else:
            preferred = "LEFT"

        sweep_score = 6 if d_name == preferred else 1  # boosted sweep priority

        # Wall buffer
        wall_buffer = min(nx, grid_dim - 1 - nx, ny, grid_dim - 1 - ny)

        # Attraction to open space
        if target:
            tx, ty = target
            open_space_pull = -(abs(nx - tx) + abs(ny - ty))
        else:
            open_space_pull = 0

        # MODE LOGIC
        if mode == "AVOID":
            score = (
                2.8 * dist_score +
                2.0 * space_score +
                0.4 * sweep_score +   # NEW: sweep slightly even in avoid mode
                0.6 * wall_buffer -
                2.5 * danger
            )

        elif mode == "SPACE":
            score = (
                2.0 * space_score +
                2.5 * sweep_score +   # STRONG sweep priority
                1.5 * open_space_pull +
                0.5 * wall_buffer -
                1.0 * danger
            )

        else:  # POCKET MODE — pure survival sweeping
            score = (
                4.0 * sweep_score +   # MAX sweep priority
                2.5 * space_score +
                0.3 * wall_buffer
            )

        # Very low randomness
        score += random.uniform(-0.015, 0.015) * score

        if best_score is None or score > best_score:
            best_score = score
            best_moves = [d_name]
        elif score == best_score:
            best_moves.append(d_name)

    return random.choice(best_moves)


# ---------------------------------------------------------
# FLOOD FILL — reachable space
# ---------------------------------------------------------
def flood_fill_area(start_pos, board, grid_dim):
    if start_pos in board:
        return 0

    visited = {start_pos}
    stack = [start_pos]

    while stack:
        x, y = stack.pop()

        for dx, dy in DIRECTIONS.values():
            nx, ny = x + dx, y + dy
            if (
                0 <= nx < grid_dim and 0 <= ny < grid_dim and
                (nx, ny) not in board and
                (nx, ny) not in visited
            ):
                visited.add((nx, ny))
                stack.append((nx, ny))

    return len(visited)


# ---------------------------------------------------------
# FIND LARGEST OPEN REGION CENTER
# ---------------------------------------------------------
def find_open_space_target(board, grid_dim):
    visited = set()
    best_region = []
    
    for x in range(grid_dim):
        for y in range(grid_dim):
            if (x, y) in board or (x, y) in visited:
                continue

            region = []
            stack = [(x, y)]
            visited.add((x, y))

            while stack:
                cx, cy = stack.pop()
                region.append((cx, cy))

                for dx, dy in DIRECTIONS.values():
                    nx, ny = cx + dx, cy + dy
                    if (
                        0 <= nx < grid_dim and 0 <= ny < grid_dim and
                        (nx, ny) not in board and
                        (nx, ny) not in visited
                    ):
                        visited.add((nx, ny))
                        stack.append((nx, ny))

            if len(region) > len(best_region):
                best_region = region

    if not best_region:
        return None

    sx = sum(p[0] for p in best_region)
    sy = sum(p[1] for p in best_region)
    return (sx // len(best_region), sy // len(best_region))


# ---------------------------------------------------------
# OPPONENT INFLUENCE MAP
# ---------------------------------------------------------
def opponent_influence(pos, opp_positions):
    if not opp_positions:
        return 0

    x, y = pos
    influence = 0

    for ox, oy in opp_positions:
        dist = abs(x - ox) + abs(y - oy)
        if dist == 0:
            influence += 10
        else:
            influence += 1 / dist

    return influence
