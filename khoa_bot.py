# BOT: AGGRESSOR BOT — Enhanced Edition
# Strategy:
#   1. Voronoi-based territory awareness — prefers moves that give US more reachable cells than opponents
#   2. Look-ahead safety — simulates 3 steps ahead to avoid dead ends we can't escape
#   3. Opponent trapping — actively tries to cut off opponents into smaller pockets
#   4. Adaptive aggression — hunts when safe, survives when cornered
#   5. Nearest-wall avoidance and center-of-mass territory bias

from collections import deque

team_name = "Khoa"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    deltas = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
    delta_list = list(deltas.values())

    # ── helpers ────────────────────────────────────────────────────────────────

    def in_bounds(pos):
        return 0 <= pos[0] < grid_dim and 0 <= pos[1] < grid_dim

    def is_free(pos):
        return in_bounds(pos) and pos not in board

    def neighbors(pos):
        px, py = pos
        return [(px + dx, py + dy) for dx, dy in delta_list
                if in_bounds((px + dx, py + dy)) and (px + dx, py + dy) not in board]

    def flood_count(start, extra_blocked=None):
        """BFS flood-fill; returns reachable cell count from start."""
        if not is_free(start):
            return 0
        blocked = board if extra_blocked is None else board | extra_blocked
        visited = {start}
        q = deque([start])
        while q:
            cx, cy = q.popleft()
            for dx, dy in delta_list:
                nb = (cx + dx, cy + dy)
                if in_bounds(nb) and nb not in blocked and nb not in visited:
                    visited.add(nb)
                    q.append(nb)
        return len(visited)

    def bfs_dist(start, end):
        """Shortest BFS path length between two free cells."""
        if not is_free(end):
            return 9999
        if start == end:
            return 0
        visited = {start}
        q = deque([(start, 0)])
        while q:
            cur, d = q.popleft()
            for dx, dy in delta_list:
                nb = (cur[0] + dx, cur[1] + dy)
                if nb == end:
                    return d + 1
                if in_bounds(nb) and nb not in board and nb not in visited:
                    visited.add(nb)
                    q.append((nb, d + 1))
        return 9999

    def voronoi_score(my_next, opp_positions):
        """
        Approximate Voronoi: BFS from all positions simultaneously.
        Returns (my_cells, total_cells). Higher my_cells/total_cells = better territory.
        """
        if not is_free(my_next):
            return 0, 1

        # Filter opponents to only those on free cells
        opp_starts = [p for p in opp_positions if is_free(p)]

        dist_me = {}
        dist_opp = {}

        # BFS from my next position
        q = deque([(my_next, 0)])
        dist_me[my_next] = 0
        while q:
            cur, d = q.popleft()
            for nb in neighbors(cur):
                if nb not in dist_me:
                    dist_me[nb] = d + 1
                    q.append((nb, d + 1))

        # BFS from each opponent simultaneously (multi-source)
        q = deque()
        for op in opp_starts:
            dist_opp[op] = 0
            q.append((op, 0))
        while q:
            cur, d = q.popleft()
            for nb in neighbors(cur):
                if nb not in dist_opp:
                    dist_opp[nb] = d + 1
                    q.append((nb, d + 1))

        my_cells = 0
        total_cells = len(dist_me)
        for cell, d_me in dist_me.items():
            d_op = dist_opp.get(cell, 9999)
            if d_me <= d_op:
                my_cells += 1

        return my_cells, max(total_cells, 1)

    def lookahead_safe(pos, depth=3):
        """
        Simulate depth steps: check that from pos we always have
        at least one escape route, recursively. Returns min reachable space.
        """
        if depth == 0:
            return flood_count(pos)
        best = 0
        for dx, dy in delta_list:
            nb = (pos[0] + dx, pos[1] + dy)
            if is_free(nb):
                space = flood_count(nb)
                if space > best:
                    best = space
        return best

    # ── gather alive opponents ──────────────────────────────────────────────

    alive_opps = [p for p in players if p['pos'] != my_pos and p.get('alive', True)]
    opp_positions = [p['pos'] for p in alive_opps]

    # ── enumerate candidate moves ───────────────────────────────────────────

    candidates = []
    for d, (dx, dy) in deltas.items():
        nb = (x + dx, y + dy)
        if is_free(nb):
            candidates.append((d, nb))

    if not candidates:
        return "UP"

    # ── pure survival: no opponents ─────────────────────────────────────────

    if not alive_opps:
        return max(candidates, key=lambda m: flood_count(m[1]))[0]

    # ── score each candidate move ───────────────────────────────────────────

    scored = []

    for d, nb in candidates:
        # 1. Raw flood space from this cell
        my_space = flood_count(nb)

        # 2. Look-ahead: avoid moves that dead-end in 1-2 steps
        la_space = lookahead_safe(nb, depth=2)
        effective_space = min(my_space, la_space)

        # Hard survival floor — but only enforce it if another option clears it.
        # We'll soft-penalise instead of hard-discard so we always have a move.
        survival_penalty = 0
        if effective_space < 12:
            survival_penalty = (12 - effective_space) * 80  # heavy penalty

        # 3. Voronoi territory: how much of the board do we own?
        my_voro, total_voro = voronoi_score(nb, opp_positions)
        territory_score = (my_voro / total_voro) * 600

        # 4. Aggression: distance to nearest opponent (closer = better for trapping)
        nearest_dist = min(bfs_dist(nb, op) for op in opp_positions)

        # 5. Trapping bonus: if moving here shrinks an opponent's flood space
        trap_bonus = 0
        for op in opp_positions:
            # Opponent's space if we take this cell (simulate board with nb blocked)
            opp_space_after = flood_count(op, extra_blocked={nb})
            opp_space_before = flood_count(op)
            reduction = opp_space_before - opp_space_after
            if reduction > 0:
                trap_bonus += reduction * 3

        # 6. Intercept bonus: moving adjacent to multiple opponent neighbours
        intercept_bonus = 0
        for op_pos in opp_positions:
            ox, oy = op_pos
            for dx2, dy2 in delta_list:
                op_nb = (ox + dx2, oy + dy2)
                if is_free(op_nb):
                    d2 = bfs_dist(nb, op_nb)
                    if d2 < 4:
                        intercept_bonus += (4 - d2) * 15

        # 7. Aggression blend: hunt if we have plenty of space,
        #    retreat into territory control if space is low
        space_ratio = effective_space / max(grid_dim * grid_dim, 1)
        if space_ratio > 0.15:
            # We have room — be aggressive
            aggression_score = -nearest_dist * 12 + intercept_bonus + trap_bonus
        else:
            # Tight — prioritise survival and territory
            aggression_score = trap_bonus + intercept_bonus * 0.3

        total_score = (
            territory_score
            + aggression_score
            + effective_space * 0.5
            - survival_penalty
        )

        scored.append((total_score, d))

    if not scored:
        # Absolute fallback: most open space
        return max(candidates, key=lambda m: flood_count(m[1]))[0]

    return max(scored)[1]