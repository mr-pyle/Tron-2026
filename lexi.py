team_name = "lexi bot"

DIRECTIONS = {
    "UP":    (0, -1),
    "RIGHT": (1,  0),
    "DOWN":  (0,  1),
    "LEFT":  (-1, 0),
}

DIR_PRIORITY = ["UP", "RIGHT", "DOWN", "LEFT"]  # deterministic tie-breaking


def move(my_pos, board, grid_dim, players):
    x, y = my_pos

    # 1. SAFE MOVES (deterministic order)
    safe_moves = {}
    for d in DIR_PRIORITY:
        dx, dy = DIRECTIONS[d]
        nx, ny = x + dx, y + dy
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
            safe_moves[d] = (nx, ny)

    if not safe_moves:
        return "UP"

    # 2. GLOBAL STATE
    opps = [p["pos"] for p in players if p["pos"] != my_pos and p.get("alive", True)]

    total_cells = grid_dim * grid_dim
    empty_cells = total_cells - len(board)
    empty_ratio = empty_cells / total_cells if total_cells > 0 else 0.0

    my_space_global = flood_fill_area(my_pos, board, grid_dim)

    if opps:
        opp_space_global = sum(
            flood_fill_area(o, board, grid_dim) for o in opps
        ) / len(opps)
        dists = [manhattan(my_pos, o) for o in opps]
        avg_dist_to_opp = sum(dists) / len(dists)
        min_dist_to_opp = min(dists)
    else:
        opp_space_global = 0
        avg_dist_to_opp = grid_dim * 2
        min_dist_to_opp = grid_dim * 2

    isolated = (opp_space_global == 0 or not opps)

    # 3. CRITICAL SITUATION FLAGS
    kill_window = can_kill_window(my_pos, board, grid_dim, opps, my_space_global, opp_space_global)
    cutoff_window = can_cutoff_window(my_pos, board, grid_dim, opps, my_space_global, opp_space_global)
    in_danger = is_in_danger(my_space_global, opp_space_global, min_dist_to_opp, grid_dim)

    # 4. MODE SELECTION (HYBRID: RULES + HIERARCHY)
    if isolated:
        mode = "POCKET"
    elif kill_window:
        mode = "HUNT"
    elif cutoff_window:
        mode = "CUTOFF"
    elif in_danger:
        mode = "AVOID"
    else:
        # Strategic hierarchy between SPACE, LOOP, SWEEP
        open_target = find_largest_region_center(board, grid_dim)
        straight_dir = best_straight_direction(my_pos, board, grid_dim)

        mode_scores = {}

        # SPACE mode score
        space_score = 0.0
        space_score += 2.5 * my_space_global
        space_score += 1.5 * region_centrality(my_pos, grid_dim)
        if open_target:
            space_score += 1.8 * (-manhattan(my_pos, open_target))
        space_score -= 0.8 * opponent_influence(my_pos, opps)
        mode_scores["SPACE"] = space_score

        # LOOP mode score
        loop_score = 0.0
        loop_score += 2.0 * my_space_global
        if straight_dir is not None:
            loop_score += 2.0 * straight_line_potential(my_pos, board, grid_dim, straight_dir)
        loop_score += 1.0 * wall_buffer_score(my_pos, grid_dim)
        loop_score -= 0.7 * opponent_influence(my_pos, opps)
        mode_scores["LOOP"] = loop_score

        # SWEEP mode score
        sweep_score = 0.0
        sweep_score += 2.2 * my_space_global
        sweep_score += 1.5 * sweep_alignment_potential(my_pos, grid_dim)
        sweep_score += 0.8 * wall_buffer_score(my_pos, grid_dim)
        sweep_score -= 0.5 * opponent_influence(my_pos, opps)
        mode_scores["SWEEP"] = sweep_score

        # Choose best strategic mode deterministically
        mode = max(mode_scores.items(), key=lambda kv: kv[1])[0]

    # 5. MOVE EVALUATION (DETERMINISTIC)
    best_score = None
    best_dir = None

    for d in DIR_PRIORITY:
        if d not in safe_moves:
            continue
        nx, ny = safe_moves[d]

        my_space_local = flood_fill_area((nx, ny), board, grid_dim)

        if opps:
            opp_space_local = sum(
                flood_fill_area(o, board, grid_dim) for o in opps
            ) / len(opps)
            avg_dist_local = sum(manhattan((nx, ny), o) for o in opps) / len(opps)
            min_dist_local = min(manhattan((nx, ny), o) for o in opps)
        else:
            opp_space_local = 0
            avg_dist_local = grid_dim * 2
            min_dist_local = grid_dim * 2

        enclosure_adv = max(0, my_space_local - opp_space_local)
        danger_local = opponent_influence((nx, ny), opps)
        branch = branching_score((nx, ny), board, grid_dim)
        wall_buf = wall_buffer_score((nx, ny), grid_dim)

        open_target = find_largest_region_center(board, grid_dim)
        if open_target:
            open_pull = -manhattan((nx, ny), open_target)
        else:
            open_pull = 0

        sweep_pref = "RIGHT" if ny % 2 == 0 else "LEFT"
        sweep_score_local = 6 if d == sweep_pref else 1

        straight_dir = best_straight_direction(my_pos, board, grid_dim)
        loop_score_local = 5 if straight_dir == d else 0

        # MODE-SPECIFIC SCORING
        if mode == "AVOID":
            score = (
                3.0 * avg_dist_local +
                2.2 * my_space_local +
                1.0 * branch +
                0.8 * wall_buf -
                2.8 * danger_local
            )

        elif mode == "HUNT":
            score = (
                3.0 * enclosure_adv +
                2.4 * (grid_dim * 2 - avg_dist_local) +
                1.6 * my_space_local -
                1.2 * danger_local +
                0.8 * branch
            )

        elif mode == "CUTOFF":
            score = (
                2.8 * enclosure_adv +
                2.2 * (grid_dim * 2 - min_dist_local) +
                1.4 * my_space_local +
                1.0 * branch -
                1.0 * danger_local
            )

        elif mode == "SPACE":
            score = (
                2.6 * my_space_local +
                2.2 * open_pull +
                1.2 * branch +
                0.8 * wall_buf -
                0.9 * danger_local
            )

        elif mode == "LOOP":
            score = (
                2.2 * my_space_local +
                2.8 * loop_score_local +
                1.2 * branch -
                0.8 * danger_local
            )

        elif mode == "SWEEP":
            score = (
                3.8 * sweep_score_local +
                2.2 * my_space_local +
                0.6 * wall_buf
            )

        else:  # POCKET
            score = (
                4.0 * sweep_score_local +
                2.6 * my_space_local +
                0.8 * branch
            )

        # Deterministic tie-breaking via DIR_PRIORITY order
        if best_score is None or score > best_score:
            best_score = score
            best_dir = d

    return best_dir


# ===================== HELPERS =====================

def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


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


def branching_score(pos, board, grid_dim):
    x, y = pos
    exits = 0
    for dx, dy in DIRECTIONS.values():
        nx, ny = x + dx, y + dy
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
            exits += 1
    return exits


def opponent_influence(pos, opp_positions):
    if not opp_positions:
        return 0.0
    x, y = pos
    influence = 0.0
    for ox, oy in opp_positions:
        d = abs(x - ox) + abs(y - oy)
        influence += 10.0 if d == 0 else 1.0 / d
    return influence


def find_largest_region_center(board, grid_dim):
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


def best_straight_direction(my_pos, board, grid_dim):
    x, y = my_pos
    best_dir = None
    best_len = -1
    for name, (dx, dy) in DIRECTIONS.items():
        length = 0
        cx, cy = x, y
        while True:
            cx += dx
            cy += dy
            if 0 <= cx < grid_dim and 0 <= cy < grid_dim and (cx, cy) not in board:
                length += 1
            else:
                break
        if length > best_len:
            best_len = length
            best_dir = name
    return best_dir


def wall_buffer_score(pos, grid_dim):
    x, y = pos
    return min(x, grid_dim - 1 - x, y, grid_dim - 1 - y)


def region_centrality(pos, grid_dim):
    x, y = pos
    cx, cy = (grid_dim - 1) / 2.0, (grid_dim - 1) / 2.0
    d = abs(x - cx) + abs(y - cy)
    return -d  # closer to center → higher score


def sweep_alignment_potential(pos, grid_dim):
    _, y = pos
    # Encourage being aligned with serpentine rows
    return -(y % 2)


def straight_line_potential(my_pos, board, grid_dim, direction_name):
    dx, dy = DIRECTIONS[direction_name]
    x, y = my_pos
    length = 0
    while True:
        x += dx
        y += dy
        if 0 <= x < grid_dim and 0 <= y < grid_dim and (x, y) not in board:
            length += 1
        else:
            break
    return length


def is_in_danger(my_space, opp_space, min_dist, grid_dim):
    # In danger if space is small relative to board or opponents are very close with similar space
    if my_space < grid_dim * 2 and min_dist <= 3:
        return True
    if opp_space >= my_space * 0.9 and min_dist <= 2:
        return True
    return False


def can_kill_window(my_pos, board, grid_dim, opps, my_space_global, opp_space_global):
    if not opps:
        return False
    # Kill window if we have significantly more space and are very close
    if my_space_global >= opp_space_global * 1.4:
        dists = [manhattan(my_pos, o) for o in opps]
        if min(dists) <= 3:
            return True
    return False


def can_cutoff_window(my_pos, board, grid_dim, opps, my_space_global, opp_space_global):
    if not opps:
        return False
    # Estimate cutoff potential by seeing if moving closer reduces opponent space more than ours
    base_opp_space = opp_space_global
    base_my_space = my_space_global

    for d in DIR_PRIORITY:
        dx, dy = DIRECTIONS[d]
        nx, ny = my_pos[0] + dx, my_pos[1] + dy
        if not (0 <= nx < grid_dim and 0 <= ny < grid_dim) or (nx, ny) in board:
            continue
        my_space_local = flood_fill_area((nx, ny), board, grid_dim)
        opp_space_local = sum(
            flood_fill_area(o, board, grid_dim) for o in opps
        ) / len(opps)
        # Good cutoff if opponent space shrinks more than ours and we still have advantage
        if opp_space_local < base_opp_space * 0.8 and my_space_local >= base_my_space * 0.7:
            if my_space_local >= opp_space_local * 1.1:
                return True
    return False
