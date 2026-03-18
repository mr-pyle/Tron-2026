from collections import deque
import random

team_name = "APEX"

# ─────────────────────────────────────────────────────────────────────────────
#  APEX BOT — Aggressive + Cautious Hybrid
#
#  Philosophy:
#    1. Never die to a trap  (flood-fill safety gate)
#    2. Hunt & choke enemies (Voronoi + kill-shot detection)
#    3. Seal off territory and pack it perfectly (isolation mode)
#    4. Avoid head-on collisions UNLESS we're the one winning the trade
# ─────────────────────────────────────────────────────────────────────────────

_DELTAS = [(0, -1), (0, 1), (-1, 0), (1, 0)]
_DNAMES = ["UP",    "DOWN", "LEFT",  "RIGHT"]
_DELTA_MAP = {n: d for n, d in zip(_DNAMES, _DELTAS)}

# ── Flood fill ────────────────────────────────────────────────────────────────
def _flood(start, board, grid_dim, extra=None, limit=3000):
    if start in board or (extra and start in extra):
        return 0
    blocked = board if extra is None else board
    visited = {start}
    q = deque([start])
    while q and len(visited) < limit:
        cx, cy = q.popleft()
        for dx, dy in _DELTAS:
            nb = (cx + dx, cy + dy)
            if (0 <= nb[0] < grid_dim and 0 <= nb[1] < grid_dim
                    and nb not in blocked
                    and (extra is None or nb not in extra)
                    and nb not in visited):
                visited.add(nb)
                q.append(nb)
    return len(visited)


# ── Multi-source Voronoi: returns my territory count ─────────────────────────
def _voronoi(my_next, enemy_heads, board, grid_dim):
    visited = {}
    q = deque()
    visited[my_next] = 'me'
    q.append((my_next, 'me'))
    for eh in enemy_heads:
        if eh not in visited:
            visited[eh] = 'enemy'
            q.append((eh, 'enemy'))
    mine = 0
    while q:
        pos, owner = q.popleft()
        if owner == 'me':
            mine += 1
        cx, cy = pos
        for dx, dy in _DELTAS:
            nb = (cx + dx, cy + dy)
            if (0 <= nb[0] < grid_dim and 0 <= nb[1] < grid_dim
                    and nb not in board and nb not in visited):
                visited[nb] = owner
                q.append((nb, owner))
    return mine


# ── Check if a region containing `pos` is completely isolated from enemies ────
def _get_region(start, board, grid_dim):
    """BFS flood, return the set of reachable cells."""
    if start in board:
        return set()
    visited = {start}
    q = deque([start])
    while q:
        cx, cy = q.popleft()
        for dx, dy in _DELTAS:
            nb = (cx + dx, cy + dy)
            if (0 <= nb[0] < grid_dim and 0 <= nb[1] < grid_dim
                    and nb not in board and nb not in visited):
                visited.add(nb)
                q.append(nb)
    return visited


# ── Count free neighbours ─────────────────────────────────────────────────────
def _free_neighbors(pos, board, grid_dim):
    cx, cy = pos
    return sum(
        1 for dx, dy in _DELTAS
        if 0 <= cx + dx < grid_dim and 0 <= cy + dy < grid_dim
        and (cx + dx, cy + dy) not in board
    )


# ── Wall-adjacency score (higher = better for packing) ───────────────────────
def _wall_adj(pos, board, grid_dim):
    cx, cy = pos
    return sum(
        1 for dx, dy in _DELTAS
        if not (0 <= cx + dx < grid_dim and 0 <= cy + dy < grid_dim)
        or (cx + dx, cy + dy) in board
    )


# ── 2-step lookahead: after moving to `pos`, how good are our futures? ────────
def _lookahead_score(pos, enemy_heads, board, grid_dim):
    """
    Simulate moving to `pos` (claim it), then evaluate each of our
    next-step options.  Returns the best Voronoi score we can achieve
    from pos, or -1 if pos immediately dead-ends.
    """
    temp = dict(board)
    temp[pos] = 1

    best = -1
    cx, cy = pos
    for dx, dy in _DELTAS:
        nb = (cx + dx, cy + dy)
        if (0 <= nb[0] < grid_dim and 0 <= nb[1] < grid_dim
                and nb not in temp):
            v = _voronoi(nb, enemy_heads, temp, grid_dim)
            if v > best:
                best = v
    return best  # -1 means dead end after this move


# ═════════════════════════════════════════════════════════════════════════════
#  MAIN MOVE FUNCTION
# ═════════════════════════════════════════════════════════════════════════════
def move(my_pos, board, grid_dim, players):
    x, y = my_pos

    # ── Enemies ──────────────────────────────────────────────────────────────
    enemies    = [p for p in players if p['pos'] != my_pos and p.get('alive', True)]
    eheads     = [p['pos'] for p in enemies]

    # ── Safe immediate moves ─────────────────────────────────────────────────
    safe = {}
    for dname, (dx, dy) in _DELTA_MAP.items():
        nb = (x + dx, y + dy)
        if (0 <= nb[0] < grid_dim and 0 <= nb[1] < grid_dim
                and nb not in board):
            safe[dname] = nb

    if not safe:
        return "UP"
    if len(safe) == 1:
        return next(iter(safe))

    # ── Head-on kill-zone map ────────────────────────────────────────────────
    # Tiles that an enemy *could* move to next turn (danger if we step there)
    enemy_kill_zone = set()
    for ex, ey in eheads:
        for dx, dy in _DELTAS:
            nb = (ex + dx, ey + dy)
            if 0 <= nb[0] < grid_dim and 0 <= nb[1] < grid_dim:
                enemy_kill_zone.add(nb)

    # ── Flood fills for EVERY candidate ─────────────────────────────────────
    floods = {d: _flood(pos, board, grid_dim) for d, pos in safe.items()}
    max_flood = max(floods.values())

    # Hard filter: discard moves into tiny traps
    # (must reach at least 70% of the best available space)
    viable = {d: pos for d, pos in safe.items()
              if floods[d] >= max(max_flood * 0.70, 4)}
    if not viable:
        # Everything looks bad — pick safest
        viable = dict(safe)

    # ── Exclude danger zone moves UNLESS they produce a kill shot ───────────
    # A "kill shot" is stepping next to an enemy whose flood fill drops to ≤8
    def is_kill_shot(pos):
        cx, cy = pos
        for eh in eheads:
            if abs(cx - eh[0]) + abs(cy - eh[1]) == 1:
                # Simulate blocking: add our new head to board
                temp = dict(board)
                temp[pos] = 1
                enemy_space = _flood(eh, temp, grid_dim)
                if enemy_space <= 8:
                    return True
        return False

    safe_viable   = {d: p for d, p in viable.items() if p not in enemy_kill_zone}
    # Fall back to all viable if avoiding kill zone leaves nothing
    candidates = safe_viable if safe_viable else viable

    # ── Isolation check ──────────────────────────────────────────────────────
    # Are we already sealed away from all enemies?
    my_region = _get_region(my_pos, board, grid_dim)
    isolated  = not any(eh in my_region for eh in eheads)

    # ── Momentum ─────────────────────────────────────────────────────────────
    current_heading = None
    my_data = next((p for p in players if p['pos'] == my_pos), None)
    if my_data and len(my_data.get('trail', [])) >= 2:
        lx, ly = my_data['trail'][-2]
        if   x > lx: current_heading = "RIGHT"
        elif x < lx: current_heading = "LEFT"
        elif y > ly: current_heading = "DOWN"
        elif y < ly: current_heading = "UP"

    # ── Game-phase detection ─────────────────────────────────────────────────
    fill_ratio   = len(board) / (grid_dim * grid_dim)
    late_game    = fill_ratio > 0.55 or len(enemies) <= 1

    # ── SCORE EACH CANDIDATE ─────────────────────────────────────────────────
    scores = {}

    for dname, pos in candidates.items():
        flood = floods[dname]

        # ── ISOLATED (pocket) mode: perfect space packing ──────────────────
        if isolated:
            wa = _wall_adj(pos, board, grid_dim)
            fn = _free_neighbors(pos, board, grid_dim)
            # Maximise flood, hug walls, avoid dead-ends
            score = flood * 8000 + wa * 400 - (fn == 0) * 9999999
            scores[dname] = score
            continue

        # ── COMBAT mode ────────────────────────────────────────────────────

        # 1. Voronoi territory
        vor = _voronoi(pos, eheads, board, grid_dim)

        # 2. Two-step lookahead Voronoi (quality of futures)
        la  = _lookahead_score(pos, eheads, board, grid_dim)
        if la == -1:
            # Moving here dead-ends us on the very next step — punish hard
            scores[dname] = -9_000_000
            continue

        # 3. Kill-shot bonus
        ks_bonus = 60_000 if is_kill_shot(pos) else 0

        # 4. Danger penalty (stepping into kill zone)
        kz_penalty = 4_000 if pos in enemy_kill_zone and ks_bonus == 0 else 0

        # 5. Proximity: distance to nearest enemy
        if eheads:
            min_dist = min(abs(pos[0]-ex) + abs(pos[1]-ey) for ex, ey in eheads)
        else:
            min_dist = grid_dim * 2

        # Aggression weight: chase when we're larger, be cautious when smaller
        opp_avg_flood = (sum(_flood(eh, board, grid_dim, limit=500)
                             for eh in eheads) / len(eheads)) if eheads else 0
        we_are_bigger = flood > opp_avg_flood * 1.1

        chase_score = (grid_dim * 2 - min_dist) * (350 if we_are_bigger else 80)

        # 6. Wall adjacency (mild bonus — don't be obsessed)
        wa = _wall_adj(pos, board, grid_dim)
        wa_bonus = wa * (150 if late_game else 60)

        # 7. Momentum (straight lines fill space more efficiently)
        momentum = 250 if dname == current_heading else 0

        # ── Final formula ───────────────────────────────────────────────────
        score = (
            vor    * 4_000      # territory control is paramount
          + la     * 1_200      # quality of our future positions
          + flood  *   700      # raw survival space
          + ks_bonus            # kill shot
          + chase_score         # aggression
          + wa_bonus            # wall efficiency
          + momentum            # straight-line preference
          - kz_penalty          # avoid stepping into head-on danger
        )

        scores[dname] = score

    if not scores:
        return random.choice(list(candidates.keys()))

    # ── Pick best move; tie-break with momentum, then deterministic order ───
    max_score = max(scores.values())
    best      = [d for d, s in scores.items() if s == max_score]

    if current_heading in best:
        return current_heading

    for d in ["UP", "RIGHT", "DOWN", "LEFT"]:
        if d in best:
            return d

    return best[0]

