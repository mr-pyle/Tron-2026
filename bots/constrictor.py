import random

team_name = "Constrictor"

DIRECTIONS = {
    "UP": (0, -1),
    "DOWN": (0, 1),
    "LEFT": (-1, 0),
    "RIGHT": (1, 0),
}

def move(my_pos, board, grid_dim, players):
    x, y = my_pos

    # 1. Safe moves
    safe_moves = {}
    for name, (dx, dy) in DIRECTIONS.items():
        nx, ny = x + dx, y + dy
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
            safe_moves[name] = (nx, ny)

    if not safe_moves:
        return "UP"

    # 2. Opponent positions
    opps = [p['pos'] for p in players if p['pos'] != my_pos and p.get('alive', True)]

    best_score = None
    best_moves = []

    for d_name, (nx, ny) in safe_moves.items():
        # My reachable space
        my_space = flood_fill_area((nx, ny), board, grid_dim)

        # Opponent reachable space (average)
        if opps:
            opp_space = 0
            for ox, oy in opps:
                opp_space += flood_fill_area((ox, oy), board, grid_dim)
            opp_space /= len(opps)
        else:
            opp_space = 0

        # Voronoi territory
        if opps:
            territory = voronoi_territory((nx, ny), opps, board, grid_dim)
        else:
            territory = my_space

        # SPECIAL: enclosure pressure
        # Reward moves that REDUCE opponent space relative to ours
        enclosure_pressure = max(0, my_space - opp_space)

        # Distance to opponents (closer = more pressure)
        if opps:
            avg_dist = sum(abs(nx - ox) + abs(ny - oy) for ox, oy in opps) / len(opps)
            closeness = max(0, (grid_dim * 2) - avg_dist)
        else:
            closeness = 0

        # Final score: heavy emphasis on enclosure
        score = (
            2.0 * territory +
            1.0 * my_space +
            2.5 * enclosure_pressure +
            0.8 * closeness
        )

        if best_score is None or score > best_score:
            best_score = score
            best_moves = [d_name]
        elif score == best_score:
            best_moves.append(d_name)

    return random.choice(best_moves)


def flood_fill_area(start_pos, board, grid_dim):
    if start_pos in board:
        return 0

    visited = set([start_pos])
    stack = [start_pos]

    while stack:
        x, y = stack.pop()
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

    return len(visited)


def voronoi_territory(my_next_pos, opp_positions, board, grid_dim):
    mx, my = my_next_pos
    if not opp_positions:
        return flood_fill_area(my_next_pos, board, grid_dim)

    territory = 0
    for x in range(grid_dim):
        for y in range(grid_dim):
            pos = (x, y)
            if pos in board:
                continue
            d_me = abs(x - mx) + abs(y - my)
            d_opp = min(abs(x - ox) + abs(y - oy) for ox, oy in opp_positions)
            if d_me < d_opp:
                territory += 1
    return territory