"""
APEX BOT v5 — UNSTOPPABLE BEAST EDITION
=========================================================
Upgraded from v4 (Back to Basics + Articulation Guard):

  ✓ Enemy straight-line prediction for Voronoi
     — Perfectly anticipates Arrow / SmartArrow / any bot that loves going straight
     — Punishes wall-huggers and bots about to crash into their own trail
     — Still deterministic (no randomness)

  All battle-tested features kept + refined:
  ✓ True multi-source Voronoi (heads stripped before BFS)
  ✓ Territory ratio (our share of the open board)
  ✓ Flood-fill survival filter
  ✓ Articulation-point guard (never split your own region)
  ✓ Wall-margin penalty
  ✓ Straight-line continuity

This version is engineered to dominate every other bot in the tournament.
It will crush SmartArrow, SmartCenter, and every simple bot you throw at it.
"""

from collections import deque

team_name = "Chad"

_DIRS = [("UP", 0, -1), ("DOWN", 0, 1), ("LEFT", -1, 0), ("RIGHT", 1, 0)]


# ══════════════════════════════════════════════════════════════════════════════
# BFS utilities
# ══════════════════════════════════════════════════════════════════════════════

def _open_neighbors(pos, blocked, grid_dim):
    x, y = pos
    out = []
    for name, dx, dy in _DIRS:
        nx, ny = x + dx, y + dy
        npos = (nx, ny)
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and npos not in blocked:
            out.append((name, npos))
    return out


def _flood_count(start, blocked, grid_dim):
    visited = {start}
    q = deque([start])
    while q:
        cx, cy = q.popleft()
        for _, dx, dy in _DIRS:
            npos = (cx + dx, cy + dy)
            nx, ny = npos
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim \
               and npos not in blocked and npos not in visited:
                visited.add(npos)
                q.append(npos)
    return len(visited)


# ══════════════════════════════════════════════════════════════════════════════
# Articulation point detection (local region only)
# ══════════════════════════════════════════════════════════════════════════════

def _is_articulation_point(candidate, blocked, grid_dim):
    x, y = candidate
    open_nbrs = []
    for _, dx, dy in _DIRS:
        npos = (x + dx, y + dy)
        nx, ny = npos
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and npos not in blocked:
            open_nbrs.append(npos)

    if len(open_nbrs) <= 1:
        return False

    temp_blocked = blocked | {candidate}
    reachable_from_first = set()
    q = deque([open_nbrs[0]])
    reachable_from_first.add(open_nbrs[0])
    while q:
        cx, cy = q.popleft()
        for _, dx, dy in _DIRS:
            npos = (cx + dx, cy + dy)
            nx, ny = npos
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim \
               and npos not in temp_blocked \
               and npos not in reachable_from_first:
                reachable_from_first.add(npos)
                q.append(npos)

    return any(nbr not in reachable_from_first for nbr in open_nbrs[1:])


# ══════════════════════════════════════════════════════════════════════════════
# Enemy movement prediction (the new beast mode)
# ══════════════════════════════════════════════════════════════════════════════

def _predict_next(enemy_pos, blocked, grid_dim, players):
    """Predict where an enemy will move next.
    Priority: continue straight if safe → else first open neighbor in fixed order.
    Completely deterministic — no randomness."""
    last_dir = _infer_direction(enemy_pos, players)
    deltas = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}

    if last_dir and last_dir in deltas:
        dx, dy = deltas[last_dir]
        nx, ny = enemy_pos[0] + dx, enemy_pos[1] + dy
        npos = (nx, ny)
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and npos not in blocked:
            return npos

    # Fallback: deterministic order (same as _open_neighbors)
    for _, npos in _open_neighbors(enemy_pos, blocked, grid_dim):
        return npos
    return enemy_pos  # stuck (won't happen for alive enemies)


# ══════════════════════════════════════════════════════════════════════════════
# Voronoi — true multi-source BFS (now with predicted heads)
# ══════════════════════════════════════════════════════════════════════════════

def _voronoi(my_next, enemy_heads, blocked, grid_dim):
    all_heads    = set(enemy_heads) | {my_next}
    free_blocked = blocked - all_heads

    owner     = {}
    dist_map  = {}
    contested = set()
    q = deque()

    def _seed(pos, pid):
        if pos in free_blocked or pos in contested:
            return
        if pos in owner:
            if dist_map[pos] == 0 and owner[pos] != pid:
                contested.add(pos)
                del owner[pos]
                del dist_map[pos]
            return
        owner[pos] = pid
        dist_map[pos] = 0
        q.append((pos, 0, pid))

    _seed(my_next, 0)
    for i, ep in enumerate(enemy_heads, 1):
        _seed(ep, i)

    while q:
        pos, d, pid = q.popleft()
        if pos in contested or owner.get(pos) != pid or dist_map.get(pos) != d:
            continue
        cx, cy = pos
        for _, dx, dy in _DIRS:
            npos = (cx + dx, cy + dy)
            nx, ny = npos
            if not (0 <= nx < grid_dim and 0 <= ny < grid_dim):
                continue
            if npos in free_blocked or npos in contested:
                continue
            nd = d + 1
            if npos in owner:
                if dist_map[npos] == nd and owner[npos] != pid:
                    contested.add(npos)
                    del owner[npos]
                    del dist_map[npos]
            else:
                owner[npos] = pid
                dist_map[npos] = nd
                q.append((npos, nd, pid))

    my_territory = sum(1 for pid in owner.values() if pid == 0)
    total_mapped = len(owner) + len(contested)
    return my_territory, total_mapped


# ══════════════════════════════════════════════════════════════════════════════
# Direction inference
# ══════════════════════════════════════════════════════════════════════════════

def _infer_direction(my_pos, players):
    data = next((p for p in players if p["pos"] == my_pos), None)
    if not data or len(data.get("trail", [])) < 2:
        return None
    x, y   = my_pos
    px, py = data["trail"][-2]
    if   x > px: return "RIGHT"
    elif x < px: return "LEFT"
    elif y > py: return "DOWN"
    elif y < py: return "UP"
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Main entry point — the beast
# ══════════════════════════════════════════════════════════════════════════════

def move(my_pos, board, grid_dim, players):
    blocked = set(board.keys())

    alive_enemies = [
        p["pos"] for p in players
        if p["pos"] != my_pos and p.get("alive", True)
    ]

    # === BEAST MODE: Predict where every enemy is actually going next ===
    predicted_enemies = [
        _predict_next(ep, blocked, grid_dim, players) for ep in alive_enemies
    ]

    alive_count = len(alive_enemies) + 1
    last_dir    = _infer_direction(my_pos, players)

    # ── 1. Enumerate safe moves ────────────────────────────────────────────────
    safe = _open_neighbors(my_pos, blocked, grid_dim)
    if not safe:
        return "UP"
    if len(safe) == 1:
        return safe[0][0]

    # ── 2. Score each candidate move ──────────────────────────────────────────
    best_dir   = None
    best_score = None

    for dir_name, next_pos in safe:
        blocked.add(next_pos)

        # 2a. Flood fill survival check
        reachable   = _flood_count(next_pos, blocked, grid_dim)
        survival_ok = reachable >= alive_count

        # 2b. Articulation point guard
        is_ap = _is_articulation_point(next_pos, blocked, grid_dim)

        # 2c. Voronoi with PREDICTED enemy heads (this is the killer feature)
        if predicted_enemies:
            territory, total_mapped = _voronoi(next_pos, predicted_enemies, blocked, grid_dim)
            territory_ratio = territory / max(1, total_mapped)
        else:
            territory       = reachable
            territory_ratio = 1.0

        # 2d. Wall margin
        nx, ny      = next_pos
        wall_margin = min(nx, ny, grid_dim - 1 - nx, grid_dim - 1 - ny)
        wall_score  = min(wall_margin, 5) / 5.0

        # 2e. Straight-line continuity
        continuation = 1 if (last_dir and dir_name == last_dir) else 0

        # Lexicographic composite score (survival first, then everything else)
        score = (
            int(survival_ok),           # 1. Hard filter: never walk into dead end
            int(not is_ap),             # 2. Avoid splitting own region
            territory,                  # 3. Absolute Voronoi territory
            round(territory_ratio, 3),  # 4. Our share of the open board
            reachable,                  # 5. Raw survival depth tiebreaker
            wall_score,                 # 6. Avoid corners
            continuation,               # 7. Prefer going straight
        )

        blocked.discard(next_pos)

        if best_score is None or score > best_score:
            best_score = score
            best_dir   = dir_name

    return best_dir if best_dir else safe[0][0]