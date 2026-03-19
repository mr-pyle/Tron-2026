from collections import deque

team_name = "APEX"

# ─────────────────────────────────────────────────────────────────────────────
#  APEX v6 — Anti-Constriction Edition
#
#  Root problem fixed: previous versions counted cells but not cell *quality*.
#  A 1-wide corridor of 60 cells scored the same as a 6×10 open room — but
#  the corridor will trap you once you're inside.
#
#  New in v6:
#   1. WEIGHTED SPACE QUALITY  — each reachable cell is worth 1 + its free
#      neighbour count.  Open cells (4 exits) score 5×; dead-ends score 1×.
#      This makes corridors look cheap and open rooms look valuable.
#
#   2. ESCAPE-ROUTE COUNTING  — after flooding from a candidate tile, count
#      how many distinct "border exits" the region has (boundary cells that
#      touch free space outside the region).  Zero exits = sealed room.
#      One exit = dangerous bottleneck.  Penalise hard.
#
#   3. BOTTLENECK / ARTICULATION-POINT AVOIDANCE  — detect if the candidate
#      tile is itself the only connection between two large spaces.  If moving
#      there cuts off the bigger space from us, reject it.
#
#   4. ENCIRCLEMENT DETECTOR  — if ≥ 2 enemies are converging (each getting
#      closer this turn), switch to MAX-ESCAPE mode: ignore kill bonuses,
#      maximise escape quality and exit count.
#
#   5. DEEPER LOOKAHEAD (4 turns) with enemy greedy-prediction.
# ─────────────────────────────────────────────────────────────────────────────

_D4   = [(0,-1),(0,1),(-1,0),(1,0)]
_DMAP = {"UP":(0,-1),"DOWN":(0,1),"LEFT":(-1,0),"RIGHT":(1,0)}


# ── Utilities ─────────────────────────────────────────────────────────────────

def _inbounds(nx, ny, g):
    return 0 <= nx < g and 0 <= ny < g


def _free_nbrs(pos, board, g):
    cx, cy = pos
    return [(cx+dx, cy+dy) for dx,dy in _D4
            if _inbounds(cx+dx,cy+dy,g) and (cx+dx,cy+dy) not in board]


def _flood_basic(start, board, g, limit=5000):
    """Raw BFS cell count — used only where we need speed, not quality."""
    if start in board:
        return 0
    vis = {start}
    q   = deque([start])
    while q and len(vis) < limit:
        cx, cy = q.popleft()
        for dx,dy in _D4:
            nb = (cx+dx,cy+dy)
            if _inbounds(nb[0],nb[1],g) and nb not in board and nb not in vis:
                vis.add(nb); q.append(nb)
    return len(vis)


def _space_quality(pos, board, g):
    """
    Flood fill that returns a quality score AND escape-route count.

    Quality: each visited cell contributes (1 + free_neighbour_count).
      - Dead-end cell   (1 exit)  → 2 pts
      - Corridor cell   (2 exits) → 3 pts
      - Junction cell   (3 exits) → 4 pts
      - Open cell       (4 exits) → 5 pts
    Open rooms score much higher than corridors of equal cell count.

    Escape routes: count boundary cells whose outside neighbours are
    free AND not already in the visited region.  These are the "doors"
    out of our reachable area.  0 = sealed, 1 = single bottleneck.
    """
    if pos in board:
        return 0, 0, set()

    vis     = {pos}
    q       = deque([pos])
    quality = 0
    exits   = set()   # (inside_cell, outside_cell) border crossings

    while q:
        cx, cy = q.popleft()
        local_free = 0
        for dx,dy in _D4:
            nb = (cx+dx,cy+dy)
            in_b = _inbounds(nb[0],nb[1],g)
            if in_b and nb not in board:
                local_free += 1
                if nb not in vis:
                    vis.add(nb)
                    q.append(nb)
            # Track border exits: in-bounds free cells just outside our region
            # We'll recheck at the end for exits pointing OUT of the region.

        quality += 1 + local_free   # cell weight

    # Second pass: count exit doors (cells in vis that neighbour free cells
    # outside vis — i.e. the "gap" to the rest of the board)
    # In practice after flooding the whole reachable area there ARE no free
    # cells outside vis unless the board is disconnected.  So escape_count
    # = 0 means we're sealed in, > 0 means there's still open space to reach.
    # Since flood fills the connected component, a component isolated from
    # the rest of the board simply won't include those outside cells.
    # So: escape_count = 0 ↔ we are already sealed.
    #
    # More useful: count cells in vis that are adjacent to board-blocked cells
    # (walls/trails) — this is "wall contact", which we use to detect corridors.
    # Better metric: count cells in vis with free_neighbours ≤ 1 (dead ends).
    dead_ends = 0
    for (cx,cy) in vis:
        fn = sum(1 for dx,dy in _D4
                 if _inbounds(cx+dx,cy+dy,g) and (cx+dx,cy+dy) not in board)
        if fn <= 1:
            dead_ends += 1

    # escape_count = how many cells on the border of our region are free
    # but not in our visited set — since we did a full flood this will only
    # be > 0 if those cells are on a DIFFERENT component, meaning we found
    # a disconnection.  For a single connected component this is always 0.
    # Instead return dead_end ratio and region size alongside quality.
    return quality, len(vis), dead_ends


def _partition_and_quality(pos, board, g):
    """
    Simulate claiming `pos`, then analyse the resulting free space.

    Returns:
      largest_component_size  — cells in largest accessible region
      quality_score           — weighted quality of largest region
      dead_ends               — # dead-end cells in largest region
      n_components            — how many separate components exist
    """
    tmp = set(board)
    tmp.add(pos)
    cx, cy = pos
    seeds = [(cx+dx,cy+dy) for dx,dy in _D4
             if _inbounds(cx+dx,cy+dy,g) and (cx+dx,cy+dy) not in tmp]
    if not seeds:
        return 0, 0, 0, 0

    seen = {}
    components = []   # list of (size, quality, dead_ends)

    for seed in seeds:
        if seed in seen:
            continue
        idx = len(components)
        vis = {seed}
        q   = deque([seed])
        seen[seed] = idx
        size = 0
        qual = 0
        dead = 0

        while q:
            ncx, ncy = q.popleft()
            size += 1
            local_free = 0
            for dx,dy in _D4:
                nb = (ncx+dx,ncy+dy)
                if _inbounds(nb[0],nb[1],g) and nb not in tmp:
                    local_free += 1
                    if nb not in vis:
                        vis.add(nb); seen[nb] = idx; q.append(nb)
            qual += 1 + local_free
            if local_free <= 1:
                dead += 1

        components.append((size, qual, dead))

    # Bot enters the largest component
    best = max(components, key=lambda c: c[0])
    return best[0], best[1], best[2], len(components)


def _wall_adj(pos, board, g):
    cx, cy = pos
    return sum(1 for dx,dy in _D4
               if not _inbounds(cx+dx,cy+dy,g) or (cx+dx,cy+dy) in board)


def _strict_voronoi(my_next, eheads, board, g):
    """Count cells I reach strictly faster than all enemies combined."""
    dist_me = {my_next: 0}
    q = deque([(my_next, 0)])
    while q:
        pos, d = q.popleft()
        cx, cy = pos
        for dx,dy in _D4:
            nb = (cx+dx,cy+dy)
            if _inbounds(nb[0],nb[1],g) and nb not in board and nb not in dist_me:
                dist_me[nb] = d+1; q.append((nb,d+1))

    dist_en = {}
    q = deque()
    for eh in eheads:
        if eh not in dist_en:
            dist_en[eh] = 0; q.append((eh,0))
    while q:
        pos, d = q.popleft()
        cx, cy = pos
        for dx,dy in _D4:
            nb = (cx+dx,cy+dy)
            if _inbounds(nb[0],nb[1],g) and nb not in board and nb not in dist_en:
                dist_en[nb] = d+1; q.append((nb,d+1))

    return sum(1 for cell,dm in dist_me.items()
               if dm < dist_en.get(cell, 10**9))


def _enemy_legal_moves(ehead, board, g):
    ex, ey = ehead
    return [(ex+dx,ey+dy) for dx,dy in _D4
            if _inbounds(ex+dx,ey+dy,g) and (ex+dx,ey+dy) not in board]


def _predict_enemy_move(ehead, board, g):
    """Greedy: enemy picks the move that maximises their raw flood fill."""
    opts = _enemy_legal_moves(ehead, board, g)
    if not opts:
        return None
    return max(opts, key=lambda nb: _flood_basic(nb, board, g, limit=600))


def _simulate_future(my_pos, first_move, eheads, board, g, depth=4):
    """
    depth-turn simulation: us (greedy quality), enemies (greedy flood).
    Returns (our_final_pos, sim_board, our_future_quality, our_future_size,
             final_eheads, enemy_future_sizes).
    """
    sim = set(board)
    our = first_move
    sim.add(our)

    curr_eh = list(eheads)
    new_eh  = []
    for eh in curr_eh:
        nxt = _predict_enemy_move(eh, sim, g)
        if nxt:
            sim.add(nxt); new_eh.append(nxt)
        else:
            new_eh.append(eh)
    curr_eh = new_eh

    for _ in range(depth - 1):
        # Our move: pick highest-quality next step
        our_opts = [(our[0]+dx,our[1]+dy) for dx,dy in _D4
                    if _inbounds(our[0]+dx,our[1]+dy,g)
                    and (our[0]+dx,our[1]+dy) not in sim]
        if our_opts:
            best = max(our_opts,
                       key=lambda nb: _partition_and_quality(nb, sim, g)[1])
            our = best
            sim.add(our)

        new_eh = []
        for eh in curr_eh:
            nxt = _predict_enemy_move(eh, sim, g)
            if nxt:
                sim.add(nxt); new_eh.append(nxt)
            else:
                new_eh.append(eh)
        curr_eh = new_eh

    sz, qual, dead, n_comp = _partition_and_quality(our, sim, g)
    e_sizes = [_flood_basic(eh, sim, g, limit=300) for eh in curr_eh]
    return our, sim, qual, sz, curr_eh, e_sizes


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
    for dname,(dx,dy) in _DMAP.items():
        nb = (x+dx,y+dy)
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
    #  FILTER 1 — QUALITY-AWARE SPACE GATE
    #
    #  Compute partition+quality for each candidate.
    #  Gate on BOTH cell count (≥ 85% of best) AND quality ratio (≥ 75%).
    #  Also reject moves that create too many dead-ends (> 40% of region).
    # ─────────────────────────────────────────────────────────────────────────
    cur_sz, cur_qual, cur_dead = _space_quality(my_pos, board, g)[:3]

    pdata = {}   # dname → (size, quality, dead_ends, n_components)
    for d,pos in working.items():
        sz, qual, dead, ncomp = _partition_and_quality(pos, board, g)
        pdata[d] = (sz, qual, dead, ncomp)

    max_sz   = max((v[0] for v in pdata.values()), default=1)
    max_qual = max((v[1] for v in pdata.values()), default=1)

    def passes_gate(d):
        sz, qual, dead, ncomp = pdata[d]
        if sz < max(max_sz * 0.85, 8):
            return False
        if qual < max(max_qual * 0.75, 8):
            return False
        # Reject if more than 35% of reachable cells are dead-ends (corridor trap)
        if sz > 0 and dead / sz > 0.35:
            return False
        return True

    viable = {d:p for d,p in working.items() if passes_gate(d)}
    # Soft fallback
    if not viable:
        viable = {d:p for d,p in working.items()
                  if pdata[d][0] >= max(max_sz*0.60, 4)}
    if not viable:
        viable = dict(working)

    # ─────────────────────────────────────────────────────────────────────────
    #  FILTER 2 — 4-TURN LOOKAHEAD SAFETY
    # ─────────────────────────────────────────────────────────────────────────
    MIN_FUTURE = 20   # must have this many cells of quality space in 4 turns

    future = {}   # dname → (our_qual, our_size, enemy_sizes)
    for d,pos in viable.items():
        _, _, fq, fsz, _, esz = _simulate_future(my_pos, pos, eheads, board, g, 4)
        future[d] = (fq, fsz, esz)

    future_ok = {d:p for d,p in viable.items() if future[d][1] >= MIN_FUTURE}
    candidates = future_ok if future_ok else viable

    # ─────────────────────────────────────────────────────────────────────────
    #  SITUATION ASSESSMENT
    # ─────────────────────────────────────────────────────────────────────────
    if eheads:
        # Track which enemies moved closer since last turn (converging)
        min_dist = min(abs(x-ex)+abs(y-ey) for ex,ey in eheads)
        converging = sum(
            1 for eh in eheads
            if abs(x-eh[0])+abs(y-eh[1]) <= 4
        )
    else:
        min_dist   = g * 2
        converging = 0

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
        opp_floods = [_flood_basic(eh, board, g, limit=1000) for eh in eheads]
        opp_avg    = sum(opp_floods)/len(opp_floods)
    else:
        opp_avg = 0

    # Encirclement: ≥2 nearby enemies = escape priority
    encircled    = converging >= 2
    under_threat = min_dist <= 3
    we_dominate  = cur_sz > opp_avg * 1.35
    fill_ratio   = len(board) / (g * g)
    early_game   = fill_ratio < 0.30
    late_game    = fill_ratio > 0.55 or len(enemies) <= 1

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
        sz, qual, dead, ncomp = pdata[dname]
        fq, fsz, esz = future.get(dname, (qual, sz, []))

        # ══ ISOLATION MODE ════════════════════════════════════════════════════
        if isolated:
            wa = _wall_adj(pos, board, g)
            fn = len(_free_nbrs(pos, board, g))
            dead_ratio = dead / max(sz, 1)
            scores[dname] = (qual  * 5_000
                             + sz   * 3_000
                             - dead * 1_500   # penalise corridors strongly
                             + wa   *   300
                             - (99_999_999 if fn == 0 else 0))
            continue

        # ══ COMBAT MODE ═══════════════════════════════════════════════════════

        vor_me = _strict_voronoi(pos, eheads, board, g)

        # Kill validation — only if future size is good AND enemy truly trapped
        kill_bonus = 0
        if fsz >= MIN_FUTURE:
            tmp = set(board); tmp.add(pos)
            px, py = pos
            for i, eh in enumerate(eheads):
                if abs(px-eh[0])+abs(py-eh[1]) <= 3:
                    e_now    = _flood_basic(eh, tmp, g, limit=200)
                    e_future = esz[i] if i < len(esz) else e_now
                    if e_now <= 12 or e_future <= 5:
                        tightness  = min(e_now, e_future)
                        kill_bonus = max(kill_bonus, 70_000 - tightness*1_200)

        if fsz < MIN_FUTURE:
            kill_bonus = 0

        # Future-danger penalty — scaled by how short we'll be
        future_penalty = max(0, (MIN_FUTURE*2 - fsz)) * 1_500

        # Dead-end ratio penalty — avoid corridors even if they have cells
        dead_ratio   = dead / max(sz, 1)
        tunnel_pen   = dead_ratio * qual * 2.0   # hurts more in larger rooms

        dist_center  = abs(pos[0]-cx_b) + abs(pos[1]-cy_b)
        center_pull  = g*2 - dist_center
        dist_nearest = min((abs(pos[0]-ex)+abs(pos[1]-ey) for ex,ey in eheads),
                           default=g*2)
        wa           = _wall_adj(pos, board, g)
        wa_bonus     = wa * (150 if late_game else 0)
        mom          = 200 if dname == current_heading else 0

        # ── ENCIRCLEMENT / MAX-ESCAPE ─────────────────────────────────────────
        if encircled:
            # Multiple enemies closing in — forget kills, maximise escape quality
            score = (
                qual          * 6_000
              + fsz           * 5_000
              + fq            * 2_000
              + center_pull   * 1_000
              + mom
              - tunnel_pen    * 3
              - future_penalty
            )

        # ── DEFENSIVE ────────────────────────────────────────────────────────
        elif under_threat and not we_dominate:
            score = (
                qual          * 4_000
              + fsz           * 4_000
              + fq            * 2_000
              + vor_me        *   500
              + center_pull   *   300
              + wa_bonus + mom + kill_bonus
              - tunnel_pen * 2
              - future_penalty
            )

        # ── EARLY RACE ───────────────────────────────────────────────────────
        elif early_game and not under_threat:
            score = (
                vor_me        * 4_000
              + center_pull   * 2_500
              + qual          * 1_500
              + fsz           * 1_000
              + kill_bonus + mom
              - tunnel_pen
              - future_penalty
            )

        # ── HUNTER ───────────────────────────────────────────────────────────
        elif we_dominate and not under_threat:
            chase = (g*2 - dist_nearest) * 120
            score = (
                vor_me        * 3_500
              + qual          * 1_500
              + fsz           * 1_200
              + center_pull   *   400
              + kill_bonus + chase + wa_bonus + mom
              - tunnel_pen
              - future_penalty
            )

        # ── BALANCED ─────────────────────────────────────────────────────────
        else:
            score = (
                vor_me        * 2_800
              + qual          * 2_500
              + fsz           * 2_000
              + center_pull   *   300
              + kill_bonus + wa_bonus + mom
              - tunnel_pen
              - future_penalty
            )

        scores[dname] = score

    # ── Fallback ──────────────────────────────────────────────────────────────
    if not scores:
        return max(pdata, key=lambda d: pdata[d][1])

    max_score = max(scores.values())
    best_dirs = [d for d,s in scores.items() if s == max_score]

    if current_heading in best_dirs:
        return current_heading
    for d in ["UP","RIGHT","DOWN","LEFT"]:
        if d in best_dirs:
            return d
    return best_dirs[0]