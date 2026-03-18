import collections

team_name = "TengenToppa_Kizuna"

# =========================================================================
# INTRA-MATCH MEMORY
# This dictionary lives exactly as long as the match does. 
# It resets to 0 when the engine kills the subprocess, which is perfect!
# =========================================================================
STATE = {
    "turn": 0,
    "opp_profiles": {} # Tracks enemy aggression and distance
}

def move(my_pos, raw_board, grid_dim, players):
    DIRS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
    STATE["turn"] += 1
    
    # 1. RECONSTRUCT REALITY (The Shadow Board)
    true_board = set()
    alive_opps = []
    
    for p in players:
        for t_pos in p['trail']:
            true_board.add(t_pos)
        if p['alive'] and p['pos'] != my_pos:
            alive_opps.append(p)

    def is_safe(p):
        return 0 <= p[0] < grid_dim and 0 <= p[1] < grid_dim and p not in true_board

    # =========================================================================
    # 2. INTRA-MATCH PSYCHOLOGICAL PROFILING
    # =========================================================================
    x, y = my_pos
    closest_enemy_dist = 999
    closest_enemy_aggro = 0
    
    for opp in alive_opps:
        oid = opp['id']
        ox, oy = opp['pos']
        dist = abs(x - ox) + abs(y - oy)
        
        # Track if this specific opponent is hunting us or running away
        if oid not in STATE["opp_profiles"]:
            STATE["opp_profiles"][oid] = {"aggro": 0, "last_dist": dist}
        else:
            prof = STATE["opp_profiles"][oid]
            if dist < prof["last_dist"]:
                prof["aggro"] += 1 # They stepped towards us!
            elif dist > prof["last_dist"]:
                prof["aggro"] = max(0, prof["aggro"] - 1) # They stepped away
            prof["last_dist"] = dist
            
        # Find the most immediate threat
        if dist < closest_enemy_dist:
            closest_enemy_dist = dist
            closest_enemy_aggro = STATE["opp_profiles"][oid]["aggro"]

    # =========================================================================
    # 3. HIGH-SPEED VORONOI WITH CHOKE-POINT DETECTION
    # =========================================================================
    def evaluate_target(target_pos):
        q = collections.deque([(target_pos, 0, 0)]) # pos, owner, distance
        owners = {target_pos: 0}
        
        for i, op in enumerate(alive_opps):
            owners[op['pos']] = i + 1
            q.append((op['pos'], i + 1, 0))
            
        my_area = 0
        wall_touches = 0
        choke_points = 0
        
        while q:
            curr, owner, dist = q.popleft()
            if owner == 0:
                my_area += 1
            
            # Optimization: We don't need to look past 30 squares to know who is winning a fight
            if dist > 30: continue 
                
            for dx, dy in DIRS.values():
                nxt = (curr[0]+dx, curr[1]+dy)
                if is_safe(nxt):
                    if nxt not in owners:
                        owners[nxt] = owner
                        q.append((nxt, owner, dist + 1))
                    # If we touch a square the enemy is about to take, it's a battle-line (choke)
                    elif owner == 0 and owners[nxt] != 0 and dist > 0:
                        choke_points += 1
                elif owner == 0:
                    wall_touches += 1
                    
        return my_area, wall_touches, choke_points

    # =========================================================================
    # 4. ADAPTIVE PERSONALITY EXECUTION
    # =========================================================================
    scored_moves = []
    
    for d_name, (dx, dy) in DIRS.items():
        target = (x+dx, y+dy)
        if not is_safe(target): continue
            
        true_board.add(target)
        area, walls, chokes = evaluate_target(target)
        true_board.remove(target)
        
        dist_center = abs(target[0] - grid_dim//2) + abs(target[1] - grid_dim//2)
        
        # --- THE ADAPTATION MATRIX ---
        if closest_enemy_dist < 6:
            # COMBAT PHASE: An enemy is in our personal space.
            if closest_enemy_aggro > 3:
                # ADAPTATION -> "THE TURTLE": The enemy is aggressively hunting us.
                # Trying to cut them off is too dangerous. We switch entirely to wall-hugging.
                # We tightly coil into a gapless spiral, letting them crash into us or run out of air.
                score = (area * 10) + (walls * 150) + (chokes * 10)
            else:
                # ADAPTATION -> "THE GUILLOTINE": The enemy is close, but they aren't actively hunting us.
                # They might be trying to run past us. We aggressively slam into their Choke Points to cut them off.
                score = (area * 20) + (walls * 20) + (chokes * 300)
        
        elif STATE["turn"] < (grid_dim // 2):
            # EARLY GAME PHASE: Everyone is far apart.
            # ADAPTATION -> "THE SPRINTER": Ignore walls. Rush the absolute center of the board.
            score = (area * 100) - (dist_center * 15)
            
        else:
            # MID/LATE GAME PHASE: We have territory, now we secure it.
            # ADAPTATION -> "THE LANDLORD": Value raw area, but start hugging walls lightly so we don't waste space.
            score = (area * 80) + (walls * 10) - (dist_center * 2) + (chokes * 40)
            
        scored_moves.append((score, d_name))

    # =========================================================================
    # 5. EMERGENCY FAIL-SAFE
    # =========================================================================
    if not scored_moves:
        for d, (dx, dy) in DIRS.items():
            if is_safe((x+dx, y+dy)): return d
        return "UP"
        
    return max(scored_moves, key=lambda i: i[0])[1]