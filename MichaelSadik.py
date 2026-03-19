from collections import deque

team_name = "APEX"

# ─────────────────────────────────────────────────────────────────────────────
#  APEX v5 — Predictive Hunter
#
#  New in v5:
#   • Enemy move prediction  — for every enemy, compute their greedy-best move
#     (the one that maximises their own flood fill).  This builds a "predicted
#     future board" we reason about instead of the static current board.
#   • 3-turn minimax safety check  — before committing to any move (especially
#     kills), simulate 3 turns of (us, then all enemies playing greedy) and
#     verify we still have ≥ 15 cells of space at the end.  If not, that path
#     is marked dangerous regardless of how tempting the kill looks.
#   • Kill validation  — a "kill shot" only scores the bonus if the 3-turn
#     simulation shows the enemy actually ends up trapped AND we survive.
# ─────────────────────────────────────────────────────────────────────────────

_D4   = [(0,-1),(0,1),(-1,0),(1,0)]
_DMAP = {"UP":(0,-1),"DOWN":(0,1),"LEFT":(-1,0),"RIGHT":(1,0)}


# ── Basic helpers ─────────────────────────────────────────────────────────────

def _inbounds(nx, ny, g):
    return 0 <= nx < g and 0 <= ny < g


def _flood(start, board, g, limit=5000):
    if start in board:
        return 0
    vis = {start}
    q   = deque([start])
    while q and len(vis) < limit:
        cx, cy = q.popleft()
        for dx, dy in _D4:
            nb = (cx+dx, cy+dy)
            if _inbounds(nb[0],nb[1],g) and nb not in board and nb not in vis:
                vis.add(nb)
                q.append(nb)
    return len(vis)


def _true_reachable(pos, board, g):
    """
    Simulate claiming `pos`, then return the size of the LARGEST connected
    component accessible from pos's free neighbours.
    Penalises moves that orphan pockets — bot only scores the chunk it enters.
    """
    tmp = set(board)
    tmp.add(pos)
    cx, cy = pos
    seeds = [(cx+dx, cy+dy) for dx,dy in _D4
             if _inbounds(cx+dx,cy+dy,g) and (cx+dx,cy+dy) not in tmp]
    if not seeds:
        return 0

    seen = {}
    sizes = []
    for seed in seeds:
        if seed in seen:
            continue
        idx = len(sizes)
        size = 0
        vis  = {seed}
        q    = deque([seed])
        seen[seed] = idx
        while q:
            ncx, ncy = q.popleft()
            size += 1
            for dx,dy in _D4:
                nb = (ncx+dx, ncy+dy)
                if _inbounds(nb[0],nb[1],g) and nb not in tmp and nb not in vis:
                    vis.add(nb)
                    seen[nb] = idx
                    q.append(nb)
        sizes.append(size)
    return max(sizes)


def _strict_voronoi(my_next, eheads, board, g):
    """Count cells I reach strictly faster than any enemy (Penguin-style)."""
    dist_me = {my_next: 0}
    q = deque([(my_next, 0)])
    while q:
        pos, d = q.popleft()
        cx, cy = pos
        for dx,dy in _D4:
            nb = (cx+dx, cy+dy)
            if _inbounds(nb[0],nb[1],g) and nb not in board and nb not in dist_me:
                dist_me[nb] = d+1
                q.append((nb, d+1))

    dist_en = {}
    q = deque()
    for eh in eheads:
        if eh not in dist_en:
            dist_en[eh] = 0
            q.append((eh, 0))
    while q:
        pos, d = q.popleft()
        cx, cy = pos
        for dx,dy in _D4:
            nb = (cx+dx, cy+dy)
            if _inbounds(nb[0],nb[1],g) and nb not in board and nb not in dist_en:
                dist_en[nb] = d+1
                q.append((nb, d+1))

    return sum(1 for cell, dm in dist_me.items()
               if dm < dist_en.get(cell, 10**9))


def _enemy_legal_moves(ehead, board, g):
    ex, ey = ehead
    return [(ex+dx,ey+dy) for dx,dy in _D4
            if _inbounds(ex+dx,ey+dy,g) and (ex+dx,ey+dy) not in board]


def _wall_adj(pos, board, g):
    cx, cy = pos
    return sum(1 for dx,dy in _D4
               if not _inbounds(cx+dx,cy+dy,g) or (cx+dx,cy+dy) in board)


# ─────────────────────────────────────────────────────────────────────────────
#  ENEMY PREDICTION ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _predict_enemy_move(ehead, board, g):
    """
    Greedy 1-step prediction: the enemy picks the move that maximises
    their own flood fill (same heuristic most bots use).
    Returns the predicted next position, or None if enemy is trapped.
    """
    options = _enemy_legal_moves(ehead, board, g)
    if not options:
        return None
    # Pick the option with the most space
    best_pos  = None
    best_space = -1
    for nb in options:
        s = _flood(nb, board, g, limit=800)
        if s > best_space:
            best_space = s
            best_pos   = nb
    return best_pos


def _simulate_future_board(my_pos, my_move, eheads, board, g, depth=3):
    """
    Run `depth` turns of simulation:
      Turn k:  1. We move (greedy flood-fill best among our neighbours)
               2. Each enemy moves (greedy flood-fill best)
    Starting state: we've already decided turn-0 = my_move.

    Returns (our_final_pos, simulated_board, our_space_at_end, all_enemy_final_pos).

    `board` must be a plain dict/set — we work on a copy.
    """
    sim_board = set(board)
    our_pos   = my_move
    sim_board.add(our_pos)   # claim our first move

    # Predict and claim all enemies' first moves simultaneously
    curr_eheads = list(eheads)
    new_eheads  = []
    for eh in curr_eheads:
        nxt = _predict_enemy_move(eh, sim_board, g)
        if nxt:
            sim_board.add(nxt)
            new_eheads.append(nxt)
        else:
            new_eheads.append(eh)  # enemy trapped, stays (effectively dead)
    curr_eheads = new_eheads

    # Simulate remaining depth-1 turns
    for _ in range(depth - 1):
        # Our greedy move from our current pos
        our_options = [
            (cx+dx, cy+dy)
            for cx, cy in [our_pos]
            for dx, dy in _D4
            if _inbounds(our_pos[0]+dx, our_pos[1]+dy, g)
            and (our_pos[0]+dx, our_pos[1]+dy) not in sim_board
        ]
        if our_options:
            our_pos = max(our_options,
                          key=lambda nb: _flood(nb, sim_board, g, limit=400))
            sim_board.add(our_pos)

        # All enemies move simultaneously
        new_eheads = []
        for eh in curr_eheads:
            nxt = _predict_enemy_move(eh, sim_board, g)
            if nxt:
                sim_board.add(nxt)
                new_eheads.append(nxt)
            else:
                new_eheads.append(eh)
        curr_eheads = new_eheads

    our_space = _true_reachable(our_pos, sim_board, g)
    return our_pos, sim_board, our_space, curr_eheads


# ═════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═════════════════════════════════════════════════════════════════════════════
def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    g    = grid_dim
    cx_b = g // 2
    cy_b = g // 2

    enemies = [p for p in players if p['pos'] != my_pos and p.get('alive', True)]
    eheads  = [p['pos'] for p in enemies]

    # ── Raw safe moves ────────────────────────────────────────────────────────
    raw_safe = {}
    for dname, (dx,dy) in _DMAP.items():
        nb = (x+dx, y+dy)
        if _inbounds(nb[0],nb[1],g) and nb not in board:
            raw_safe[dname] = nb

    if not raw_safe:
        return "UP"
    if len(raw_safe) == 1:
        return next(iter(raw_safe))

    # ─────────────────────────────────────────────────────────────────────────
    #  FILTER 0 — HEAD-ON COLLISION BLOCK
    # ─────────────────────────────────────────────────────────────────────────
    enemy_reachable = set()
    certain_kill    = set()
    for eh in eheads:
        opts = _enemy_legal_moves(eh, board, g)
        for nb in opts:
            enemy_reachable.add(nb)
        if len(opts) == 1:
            certain_kill.add(opts[0])

    headon_free = {d:p for d,p in raw_safe.items() if p not in enemy_reachable}
    if headon_free:
        working = headon_free
    else:
        not_certain = {d:p for d,p in raw_safe.items() if p not in certain_kill}
        working = not_certain if not_certain else raw_safe

    # ─────────────────────────────────────────────────────────────────────────
    #  FILTER 1 — PARTITION-AWARE SPACE GATE  (85% of current space, min 10)
    # ─────────────────────────────────────────────────────────────────────────
    current_space = _flood(my_pos, board, g)
    true_reach    = {d: _true_reachable(pos, board, g) for d,pos in working.items()}
    threshold     = max(current_space * 0.85, 10)

    viable = {d:p for d,p in working.items() if true_reach[d] >= threshold}
    if not viable:
        viable = {d:p for d,p in working.items()
                  if true_reach[d] >= max(current_space*0.60, 4)}
    if not viable:
        viable = dict(working)

    # ─────────────────────────────────────────────────────────────────────────
    #  FILTER 2 — 3-TURN MINIMAX SAFETY  (new in v5)
    #
    #  For each candidate move, simulate 3 turns of (us greedy, enemies greedy).
    #  If our projected space at the end of those 3 turns drops below 15 cells,
    #  the move is "future-dangerous" — flag it so scoring can avoid it unless
    #  there's literally no alternative.
    # ─────────────────────────────────────────────────────────────────────────
    future_safe   = {}   # dname → (our_end_space, enemy_end_spaces)
    FUTURE_DEPTH  = 3
    MIN_FUTURE_SPACE = 15

    for dname, pos in viable.items():
        _, sim_board, our_end_space, final_eheads = \
            _simulate_future_board(my_pos, pos, eheads, board, g, FUTURE_DEPTH)
        enemy_end_spaces = [_flood(eh, sim_board, g, limit=300)
                            for eh in final_eheads]
        future_safe[dname] = (our_end_space, enemy_end_spaces)

    future_ok   = {d:p for d,p in viable.items()
                   if future_safe[d][0] >= MIN_FUTURE_SPACE}
    # Only use future-safe moves if at least one exists
    candidates  = future_ok if future_ok else viable

    # ─────────────────────────────────────────────────────────────────────────
    #  SITUATION ASSESSMENT
    # ─────────────────────────────────────────────────────────────────────────
    if eheads:
        min_dist = min(abs(x-ex)+abs(y-ey) for ex,ey in eheads)
    else:
        min_dist = g * 2

    # Isolation
    my_reg = set()
    vis2 = {my_pos}; q2 = deque([my_pos])
    while q2:
        ncx,ncy = q2.popleft(); my_reg.add((ncx,ncy))
        for dx,dy in _D4:
            nb = (ncx+dx,ncy+dy)
            if _inbounds(nb[0],nb[1],g) and nb not in board and nb not in vis2:
                vis2.add(nb); q2.append(nb)
    isolated = not any(eh in my_reg for eh in eheads)

    if eheads:
        opp_floods = [_flood(eh, board, g, limit=1000) for eh in eheads]
        opp_avg    = sum(opp_floods) / len(opp_floods)
    else:
        opp_avg = 0

    under_threat = min_dist <= 3
    we_dominate  = current_space > opp_avg * 1.35
    fill_ratio   = len(board) / (g * g)
    early_game   = fill_ratio < 0.30
    late_game    = fill_ratio > 0.55 or len(enemies) <= 1

    # Momentum
    current_heading = None
    my_data = next((p for p in players if p['pos'] == my_pos), None)
    if my_data and len(my_data.get('trail', [])) >= 2:
        lx, ly = my_data['trail'][-2]
        if   x > lx: current_heading = "RIGHT"
        elif x < lx: current_heading = "LEFT"
        elif y > ly: current_heading = "DOWN"
        elif y < ly: current_heading = "UP"

    # ─────────────────────────────────────────────────────────────────────────
    #  SCORE
    # ─────────────────────────────────────────────────────────────────────────
    scores = {}

    for dname, pos in candidates.items():
        space = true_reach[dname]

        # ══ ISOLATION / POCKET MODE ═══════════════════════════════════════════
        if isolated:
            wa = _wall_adj(pos, board, g)
            fn = sum(1 for dx2,dy2 in _D4
                     if _inbounds(pos[0]+dx2,pos[1]+dy2,g)
                     and (pos[0]+dx2,pos[1]+dy2) not in board)
            scores[dname] = (space * 10_000 + wa * 500
                             - (99_999_999 if fn == 0 else 0))
            continue

        # ══ COMBAT MODE ═══════════════════════════════════════════════════════

        vor_me = _strict_voronoi(pos, eheads, board, g)

        # ── Validated kill bonus (v5 upgrade) ────────────────────────────────
        # A kill only scores if:
        #   1. The enemy's projected space after 3 turns is ≤ 8 (truly trapped)
        #   2. OUR projected space after 3 turns is ≥ MIN_FUTURE_SPACE (we survive)
        # This stops APEX from chasing kills that it doesn't survive.
        kill_bonus = 0
        our_future_space, enemy_future_spaces = future_safe.get(dname, (0, []))
        px, py = pos
        if our_future_space >= MIN_FUTURE_SPACE:
            for i, eh in enumerate(eheads):
                if abs(px-eh[0])+abs(py-eh[1]) <= 3:
                    # Check both immediate space AND predicted future space
                    tmp = set(board); tmp.add(pos)
                    e_now = _flood(eh, tmp, g, limit=200)
                    e_future = (enemy_future_spaces[i]
                                if i < len(enemy_future_spaces) else e_now)
                    if e_now <= 12 or e_future <= 6:
                        # Enemy is either immediately boxed OR will be in 3 turns
                        tightness = min(e_now, e_future)
                        kill_bonus = max(kill_bonus, 80_000 - tightness * 1_500)
        # If our own future space is poor, zero out the kill bonus entirely
        # (don't sacrifice ourselves for a kill we might not get)
        if our_future_space < MIN_FUTURE_SPACE:
            kill_bonus = 0

        # ── Future-danger penalty ─────────────────────────────────────────────
        # Soft penalty if this move leads to a tight future even if not fatal.
        # Scales from 0 (plenty of space) up to -50_000 (near-death).
        future_penalty = 0
        if our_future_space < MIN_FUTURE_SPACE * 2:   # < 30 cells in 3 turns
            future_penalty = (MIN_FUTURE_SPACE * 2 - our_future_space) * 1_200

        dist_from_tile = min((abs(px-ex)+abs(py-ey) for ex,ey in eheads),
                             default=g*2)
        dist_center    = abs(pos[0]-cx_b) + abs(pos[1]-cy_b)
        center_pull    = g * 2 - dist_center
        wa             = _wall_adj(pos, board, g)
        wa_bonus       = wa * (200 if late_game else 0)
        mom            = 250 if dname == current_heading else 0

        # ── DEFENSIVE ────────────────────────────────────────────────────────
        if under_threat and not we_dominate:
            score = (
                space         * 6_000
              + our_future_space * 3_000   # weight future survival
              + vor_me        *   600
              + center_pull   * (300 if early_game else 50)
              + wa_bonus + mom + kill_bonus
              - future_penalty
            )

        # ── EARLY RACE ───────────────────────────────────────────────────────
        elif early_game and not under_threat:
            score = (
                vor_me            * 4_000
              + center_pull       * 2_500
              + space             * 1_200
              + our_future_space  *   800
              + kill_bonus + mom
              - future_penalty
            )

        # ── HUNTER ───────────────────────────────────────────────────────────
        elif we_dominate and not under_threat:
            chase = (g*2 - dist_from_tile) * 150
            score = (
                vor_me            * 3_500
              + space             * 1_200
              + our_future_space  * 1_000
              + center_pull       *   500
              + kill_bonus + chase + wa_bonus + mom
              - future_penalty
            )

        # ── BALANCED ─────────────────────────────────────────────────────────
        else:
            score = (
                vor_me            * 3_000
              + space             * 2_200
              + our_future_space  * 1_500
              + center_pull       *   400
              + kill_bonus + wa_bonus + mom
              - future_penalty
            )

        scores[dname] = score

    # ── Fallback ──────────────────────────────────────────────────────────────
    if not scores:
        return max(true_reach, key=lambda d: true_reach[d])

    # ── Pick best ─────────────────────────────────────────────────────────────
    max_score = max(scores.values())
    best_dirs = [d for d,s in scores.items() if s == max_score]

    if current_heading in best_dirs:
        return current_heading
    for d in ["UP","RIGHT","DOWN","LEFT"]:
        if d in best_dirs:
            return d
    return best_dirs[0]