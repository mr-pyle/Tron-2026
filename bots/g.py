import random

team_name = "Guillotine"

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
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
            safe[name] = (nx, ny)

    if not safe:
        return "UP"

    # 2. Opponents
    opps = [p['pos'] for p in players if p['pos'] != my_pos and p.get('alive', True)]

    best_score = None
    best_moves = []

    for d_name, (nx, ny) in safe.items():

        # --- My reachable space (weighted flood fill) ---
        my_space = weighted_flood_fill((nx, ny), board, grid_dim)

        # --- Opponent reachable space ---
        if opps:
            opp_space = 0
            for ox, oy in opps:
                opp_space += weighted_flood_fill((ox, oy), board, grid_dim)
            opp_space /= len(opps)
        else:
            opp_space = 0

        # --- Territory control (Voronoi) ---
        if opps:
            territory = voronoi((nx, ny), opps, board, grid_dim)
        else:
            territory = my_space

        # --- Closeness to opponents (for pressure) ---
        if opps:
            avg_dist = sum(abs(nx - ox) + abs(ny - oy) for ox, oy in opps) / len(opps)
            closeness = max(0, (grid_dim * 2) - avg_dist)
        else:
            closeness = 0

        # --- Enclosure pressure: how much more space I have than they do ---
        enclosure = max(0, my_space - opp_space)

        # --- Wall buffer (avoid trapping myself early) ---
        wall_buffer = min(nx, grid_dim - 1 - nx, ny, grid_dim - 1 - ny)

        # FINAL SCORE — heavily weighted toward trapping
        score = (
            2.8 * enclosure +     # main trapping metric
            2.0 * territory +     # steal territory
            1.2 * closeness +     # apply pressure
            1.0 * my_space +      # ensure I don't trap myself
            0.3 * wall_buffer     # avoid early wall death
        )

        # Slight unpredictability
        score += random.uniform(-0.03, 0.03) * score

        if best_score is None or score > best_score:
            best_score = score
            best_moves = [d_name]
        elif score == best_score:
            best_moves.append(d_name)

    return random.choice(best_moves)


# ---------------------------------------------------------
# Weighted flood fill (penalizes tunnels)
# ---------------------------------------------------------
def weighted_flood_fill(start_pos, board, grid_dim):
    if start_pos in board:
        return 0

    visited = {start_pos}
    stack = [start_pos]
    score = 0

    while stack:
        x, y = stack.pop()

        exits = 0
        for dx, dy in DIRECTIONS.values():
            nx, ny = x + dx, y + dy
            if (
                0 <= nx < grid_dim and 0 <= ny < grid_dim and
                (nx, ny) not in board
            ):
                exits += 1

        # Reward open areas, penalize tunnels
        if exits >= 3:
            score += 3
        elif exits == 2:
            score += 2
        else:
            score += 1

        for dx, dy in DIRECTIONS.values():
            nx, ny = x + dx, y + dy
            np = (nx, ny)
            if (
                0 <= nx < grid_dim and 0 <= ny < grid_dim and
                np not in board and
                np not in visited
            ):
                visited.add(np)
                stack.append(np)

    return score


# ---------------------------------------------------------
# Voronoi territory
# ---------------------------------------------------------
def voronoi(my_next_pos, opp_positions, board, grid_dim):
    mx, my = my_next_pos
    territory = 0

    for x in range(grid_dim):
        for y in range(grid_dim):
            if (x, y) in board:
                continue

            d_me = abs(x - mx) + abs(y - my)
            d_opp = min(abs(x - ox) + abs(y - oy) for ox, oy in opp_positions)

            if d_me < d_opp:
                territory += 1

    return territory
