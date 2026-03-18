import collections
import random

team_name = "TengenToppa_Clean"

def move(my_pos, raw_board, grid_dim, players):
    # Standard Directions
    DIRS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
    x, y = my_pos
    
    # 1. SHADOW BOARD (The "Cheat-Proof" Scan)
    # We ignore 'raw_board' because bots like NahI'dWin modify it.
    # We build our own reality from the players list.
    true_board = set()
    opp_positions = []
    for p in players:
        for t_pos in p['trail']:
            true_board.add(t_pos)
        if p['alive'] and p['pos'] != my_pos:
            opp_positions.append(p['pos'])

    def is_safe(p):
        return 0 <= p[0] < grid_dim and 0 <= p[1] < grid_dim and p not in true_board

    # 2. DYNAMIC RADAR (Adaptation Logic)
    # We adapt by checking how close the threat is.
    min_dist = 999
    for opp in alive_opps:
        dist = abs(x - opp['pos'][0]) + abs(y - opp['pos'][1])
        if dist < min_dist:
            min_dist = dist

    # 3. VORONOI TERRITORY ANALYSIS
    def get_score(target):
        # Flood fill simulation
        q = collections.deque([(target, 0)])
        visited = {target}
        area = 0
        edges = 0
        
        while q:
            curr, dist = q.popleft()
            area += 1
            for dx, dy in DIRS.values():
                nxt = (curr[0]+dx, curr[1]+dy)
                if is_safe(nxt):
                    if nxt not in visited and dist < 15: # Lookahead limit
                        visited.add(nxt)
                        q.append((nxt, dist + 1))
                else:
                    edges += 1 # Walls/Trails touched
        return area, edges

    # 4. EXECUTING THE ADAPTIVE MOVE
    best_move = "UP"
    max_val = -999999

    for d_name, (dx, dy) in DIRS.items():
        target = (x + dx, y + dy)
        if is_safe(target):
            area, edges = get_score(target)
            
            # --- THE ADAPTATION ---
            if min_dist < 5:
                # CLOSE COMBAT: Adapt to "Spiral Packing"
                # Priority: Stay tight against walls (edges) to save space
                score = (area * 10) + (edges * 50)
            else:
                # OPEN FIELD: Adapt to "Center Control"
                # Priority: Take ground and stay near the middle
                dist_to_mid = abs(target[0] - grid_dim//2) + abs(target[1] - grid_dim//2)
                score = (area * 100) - (dist_to_mid * 5)
            
            if score > max_val:
                max_val = score
                best_move = d_name

    return best_move
