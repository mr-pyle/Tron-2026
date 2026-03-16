import collections

team_name = "TengenToppa_Zenith_V2"

def move(my_pos, raw_board, grid_dim, players):
    DIRS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
    x, y = my_pos
    
    # 1. RECONSTRUCT REALITY (Ignore engine-side board tampering)
    true_board = set()
    opp_positions = []
    for p in players:
        for t_pos in p['trail']:
            true_board.add(t_pos)
        if p['alive'] and p['pos'] != my_pos:
            opp_positions.append(p['pos'])

    def is_safe(p):
        return 0 <= p[0] < grid_dim and 0 <= p[1] < grid_dim and p not in true_board

    # 2. VORONOI TERRITORY (Who owns what?)
    def evaluate_territory(start_node):
        q = collections.deque([(start_node, 0)])
        # Occupied tracks distance: (owner_id, distance)
        # 0 = Us, 1 = Opponents
        occupied = {start_node: (0, 0)}
        for opp in opp_positions:
            occupied[opp] = (1, 0)
            q.append((opp, 1))
            
        my_area = 0
        wall_contact = 0
        
        while q:
            curr, owner = q.popleft()
            if owner == 0:
                my_area += 1
            
            for dx, dy in DIRS.values():
                nxt = (curr[0]+dx, curr[1]+dy)
                if is_safe(nxt):
                    if nxt not in occupied:
                        occupied[nxt] = (owner, 0)
                        q.append((nxt, owner))
                elif owner == 0:
                    wall_contact += 1
        return my_area, wall_contact

    # 3. STRATEGIC ANALYSIS
    scored_moves = []
    for d_name, (dx, dy) in DIRS.items():
        target = (x + dx, y + dy)
        if is_safe(target):
            # Simulate the move
            true_board.add(target)
            area, walls = evaluate_territory(target)
            true_board.remove(target)
            
            # FIXED: Correct unpacking of opponent tuples
            enemy_dist = min([abs(target[0]-ox) + abs(target[1]-oy) for ox, oy in opp_positions]) if opp_positions else 99
            
            dist_center = abs(target[0] - grid_dim//2) + abs(target[1] - grid_dim//2)
            
            # --- THE IQ UPGRADE ---
            # If we are in a tight spot, wall-hugging (walls) is vital.
            # In the open, raw territory (area) and center control are better.
            if enemy_dist < 5:
                # Combat: Efficiency is key. 
                # We want the most area with the most "compactness" (walls)
                score = (area * 20) + (walls * 15)
            else:
                # Early/Mid Game: Territory grab
                score = (area * 100) - (dist_center * 5)
                
            scored_moves.append((score, d_name))

    # Fallback if every direction is a death trap
    if not scored_moves:
        for d_name, (dx, dy) in DIRS.items():
            if 0 <= x+dx < grid_dim and 0 <= y+dy < grid_dim:
                return d_name
        return "UP"
        
    return max(scored_moves, key=lambda m: m[0])[1]