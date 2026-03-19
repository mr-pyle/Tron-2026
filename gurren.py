from collections import deque

team_name = "TENGEN_TOPPA"

# Persistent memory for a single match
MEMORY = {
    "turn": 0,
    "profiles": {},  # Tracks enemy aggression
    "initialized": False
}

def move(my_pos, raw_board, grid_dim, players):
    x, y = my_pos
    dirs = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
    blocked = set(raw_board.keys())

    me = next(p for p in players if p['pos'] == my_pos)
    
    # Reset memory on new match
    if not MEMORY["initialized"] or len(me['trail']) <= 1:
        MEMORY["turn"] = 0
        MEMORY["profiles"] = {p['id']: {"last_dist": 999, "aggro": 0} for p in players if p['id'] != me['id']}
        MEMORY["initialized"] = True

    MEMORY["turn"] += 1
    enemies = [p for p in players if p['pos'] != my_pos and p.get('alive', True)]
    
    # --- 1. DYNAMIC PROFILING ---
    highest_threat_aggro = 0
    closest_enemy_dist = 999
    
    for e in enemies:
        eid = e['id']
        dist = abs(x - e['pos'][0]) + abs(y - e['pos'][1])
        closest_enemy_dist = min(closest_enemy_dist, dist)
        
        prof = MEMORY["profiles"].get(eid, {"last_dist": dist, "aggro": 0})
import collections

team_name = "TengenToppa"

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
        
        # If they moved closer to us, increase their aggression score
        if dist < prof["last_dist"]:
            prof["aggro"] = min(10, prof["aggro"] + 2)
        elif dist > prof["last_dist"]:
            prof["aggro"] = max(0, prof["aggro"] - 1)
            
        prof["last_dist"] = dist
        MEMORY["profiles"][eid] = prof
        
        if dist < 15:
            highest_threat_aggro = max(highest_threat_aggro, prof["aggro"])

    # --- 2. ADAPTIVE WEIGHTS ---
    if not enemies or closest_enemy_dist > 25:
        # STANCE: ISOLATED (End-Game Packing)
        # We are alone. Maximize space, ignore voronoi, strictly hug walls.
        w_space, w_voronoi, w_openness, w_packing = 20.0, 0.0, 0.0, 15.0
    elif highest_threat_aggro >= 6:
        # STANCE: MATADOR (Evasion)
        # Running from an aggressive bot. Prioritize wide open spaces to escape.
        w_space, w_voronoi, w_openness, w_packing = 8.0, 2.0, 15.0, -5.0 
    else:
        # STANCE: ANACONDA (Aggressive Area Denial)
        # Fighting a passive bot (like corbin might be). Steal their space.
        w_space, w_voronoi, w_openness, w_packing = 5.0, 15.0, 3.0, 2.0

    # --- 3. SHADOW VORONOI ---
    def is_safe(nx, ny, extra_blocked=None):
        if not (0 <= nx < grid_dim and 0 <= ny < grid_dim): return False
        if (nx, ny) in blocked: return False
        if extra_blocked and (nx, ny) in extra_blocked: return False
        return True

    enemy_reach = {}
    if enemies:
        q = deque([(e['pos'][0], e['pos'][1], 0) for e in enemies])
        while q:
            cx, cy, d = q.popleft()
            if d > 12: continue # Fast local mapping
            for dx, dy in dirs.values():
                nx, ny = cx + dx, cy + dy
                if is_safe(nx, ny) and (nx, ny) not in enemy_reach:
                    enemy_reach[(nx, ny)] = d + 1
                    q.append((nx, ny, d + 1))

    # --- 4. SPACE EVALUATION ---
    def evaluate(start_node):
        q = deque([(start_node[0], start_node[1], 1)])
        visited = {start_node}
        parity = {0: 0, 1: 0}
        openness = 0
        voronoi_count = 0

        while q:
            cx, cy, d = q.popleft()
            if d > 300: break # Keep under the timeout limit
            
            parity[(cx + cy) % 2] += 1
            
            # Openness: How many safe exits does this tile have?
            safe_exits = sum(1 for dx, dy in dirs.values() if is_safe(cx+dx, cy+dy, {start_node}))
            if safe_exits >= 3: openness += 1

            for dx, dy in dirs.values():
                nx, ny = cx + dx, cy + dy
                if is_safe(nx, ny, {start_node}) and (nx, ny) not in visited:
                    # Can I get here before the enemy?
                    if d + 1 < enemy_reach.get((nx, ny), 999):
                        voronoi_count += 1
                        visited.add((nx, ny))
                        q.append((nx, ny, d + 1))

        # True space calculates checkerboard parity to prevent dead-ends
        true_space = min(parity[0], parity[1]) * 2
        return true_space, openness, voronoi_count

    # --- 5. DECISION ENGINE ---
    scored_moves = []
    for d_name, (dx, dy) in dirs.items():
        target = (x + dx, y + dy)
        if is_safe(target[0], target[1]):
            
            # The "Sudden Death" shield: Never step where an enemy can step next turn
            enemy_arrival = enemy_reach.get(target, 999)
            collision_risk = -1000 if enemy_arrival <= 1 else 0

            space, open_val, vor_val = evaluate(target)

            score = (space * w_space) + (vor_val * w_voronoi) + (open_val * w_openness) + collision_risk

            # Packing bonus: Hugs walls based on our dynamic stance
            obstacles = sum(1 for dx2, dy2 in dirs.values() if not is_safe(target[0]+dx2, target[1]+dy2))
            score += (obstacles * w_packing)

            scored_moves.append((score, d_name))

    if not scored_moves: 
        return "UP" # Better to try a move than crash out
        
    return max(scored_moves, key=lambda x: x[0])[1]
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
