import collections
import random

team_name = "TengenToppa_SuperGalaxy"

# =========================================================================
# THE DNA VAULT (Anti-Cheat Bypass)
# Survives as long as the tournament engine runs. No files needed.
# =========================================================================
_DNA_VAULT = {
    "played": 0, "last_turns": 0, "last_won": False, "best_score": 0,
    "best_dna": {"aggression": 100.0, "wall_hug": 50.0, "center_control": 5.0, "choke_val": 200.0},
    "dna": {"aggression": 100.0, "wall_hug": 50.0, "center_control": 5.0, "choke_val": 200.0}
}
_TURN = 0

def move(my_pos, raw_board, grid_dim, players):
    global _DNA_VAULT, _TURN
    
    DIRS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
    
    # =========================================================================
    # 1. EVOLUTION ENGINE (Triggers on new match)
    # =========================================================================
    me = next(p for p in players if p['pos'] == my_pos)
    if len(me['trail']) <= 1:
        _TURN = 0
        if _DNA_VAULT["played"] > 0:
            # Did we win or beat our high score? Save this DNA!
            if _DNA_VAULT["last_won"] or _DNA_VAULT["last_turns"] > _DNA_VAULT["best_score"]:
                _DNA_VAULT["best_dna"] = _DNA_VAULT["dna"].copy()
                _DNA_VAULT["best_score"] = _DNA_VAULT["last_turns"] if not _DNA_VAULT["last_won"] else 99999
            
            # Dynamic Mutation Engine
            perf = _DNA_VAULT["last_turns"] / max(1, _DNA_VAULT["best_score"]) if _DNA_VAULT["best_score"] != 99999 else 1.0
            mut_rate = 0.05 if _DNA_VAULT["last_won"] else max(0.05, 0.40 * (1.0 - perf)) # Up to 40% mutation if dying early
            
            new_dna = {}
            for k, v in _DNA_VAULT["best_dna"].items():
                new_dna[k] = max(0.1, v * (1 + random.uniform(-mut_rate, mut_rate)))
            _DNA_VAULT["dna"] = new_dna
            
            _DNA_VAULT["last_won"] = False
            _DNA_VAULT["last_turns"] = 0
            
        _DNA_VAULT["played"] += 1

    _TURN += 1
    _DNA_VAULT["last_turns"] = _TURN

    # =========================================================================
    # 2. SHADOW BOARD (Reality Check)
    # =========================================================================
    true_board = set()
    alive_opps = []
    for p in players:
        for t_pos in p['trail']:
            true_board.add(t_pos)
        if p['alive'] and p['pos'] != my_pos:
            alive_opps.append(p)
            
    if not alive_opps:
        _DNA_VAULT["last_won"] = True

    def is_safe(p):
        return 0 <= p[0] < grid_dim and 0 <= p[1] < grid_dim and p not in true_board

    # =========================================================================
    # 3. ADVANCED VORONOI & CHOKE-POINT SCANNER
    # =========================================================================
    def evaluate_move(target_pos):
        # We race the opponents for every square on the board
        q = collections.deque([(target_pos, 0, 0)]) # (position, owner_id, distance)
        owners = {target_pos: 0}
        
        for i, opp in enumerate(alive_opps):
            owners[opp['pos']] = i + 1
            q.append((opp['pos'], i + 1, 0))
            
        my_area = 0
        wall_touches = 0
        frontiers = 0 # The "Battle Line" (Choke points)
        
        while q:
            curr, owner, dist = q.popleft()
            if owner == 0:
                my_area += 1
            
            for dx, dy in DIRS.values():
                nxt = (curr[0]+dx, curr[1]+dy)
                if is_safe(nxt):
                    if nxt not in owners:
                        owners[nxt] = owner
                        q.append((nxt, owner, dist + 1))
                    # If we touch a square the enemy is about to take, it's a frontier/chokepoint
                    elif owner == 0 and owners[nxt] != 0 and dist > 0:
                        frontiers += 1
                elif owner == 0:
                    wall_touches += 1
        
        return my_area, wall_touches, frontiers

    # =========================================================================
    # 4. CHAMBER ISOLATION (Tactical Radar)
    # =========================================================================
    q = collections.deque([my_pos])
    seen = {my_pos}
    enemy_positions = {op['pos'] for op in alive_opps}
    in_combat = False
    dist_to_enemy = 999
    
    while q:
        curr = q.popleft()
        for dx, dy in DIRS.values():
            nxt = (curr[0]+dx, curr[1]+dy)
            if nxt in enemy_positions:
                in_combat = True
                dist_to_enemy = min(dist_to_enemy, abs(my_pos[0]-nxt[0]) + abs(my_pos[1]-nxt[1]))
            elif is_safe(nxt) and nxt not in seen:
                seen.add(nxt)
                q.append(nxt)

    # =========================================================================
    # 5. EXECUTION & DNA MULTIPLIERS
    # =========================================================================
    dna = _DNA_VAULT["dna"]
    scored_moves = []
    x, y = my_pos
    
    for d_name, (dx, dy) in DIRS.items():
        target = (x+dx, y+dy)
        if not is_safe(target): 
            continue
        
        # Simulate our move
        true_board.add(target)
        area, walls, frontiers = evaluate_move(target)
        true_board.remove(target)
        
        dist_center = abs(target[0] - grid_dim//2) + abs(target[1] - grid_dim//2)
        
        if in_combat:
            if dist_to_enemy < 5:
                # KNIFE FIGHT MODE: We are right next to them. 
                # Prioritize taking their space (aggression) and staying tight (wall_hug)
                score = (area * dna["aggression"]) + (walls * dna["wall_hug"] * 5) + (frontiers * dna["choke_val"])
            else:
                # HUNTING MODE: We share a chamber but are far apart.
                # Rush the chokepoints (frontiers) to cut them off, while holding the center.
                score = (area * dna["aggression"]) + (frontiers * dna["choke_val"]) - (dist_center * dna["center_control"])
        else:
            # ISOLATION MODE: The enemy is dead or locked in a different room.
            # Perform a "Hamiltonian Coil". Maximize raw area, but rigorously hug walls so no gaps are left.
            score = (area * 100) + (walls * 50)
            
        scored_moves.append((score, d_name))

    if not scored_moves:
        # Emergency fail-safe
        for d, (dx, dy) in DIRS.items():
            if is_safe((x+dx, y+dy)): return d
        return "UP"
        
    return max(scored_moves, key=lambda x: x[0])[1]