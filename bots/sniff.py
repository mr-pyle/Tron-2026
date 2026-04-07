import collections
import random

team_name = "sniff"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    
    directions = {
        "UP": (x, y - 1),
        "DOWN": (x, y + 1),
        "LEFT": (x - 1, y),
        "RIGHT": (x + 1, y)
    }
    
    enemies = [p['pos'] for p in players if p['alive'] and p['pos'] != my_pos]
    
    # 1. ENEMY PATHFINDING
    # Calculate exactly how many steps it takes for any enemy to reach any open square.
    enemy_distances = {}
    queue = collections.deque()
    for ex, ey in enemies:
        queue.append(((ex, ey), 0))
        enemy_distances[(ex, ey)] = 0
        
    while queue:
        (cx, cy), dist = queue.popleft()
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
                if (nx, ny) not in enemy_distances:
                    enemy_distances[(nx, ny)] = dist + 1
                    queue.append(((nx, ny), dist + 1))

    # 2. SPACE EVALUATION
    def evaluate(start_pos):
        q = collections.deque([(start_pos, 1)])
        visited = {start_pos: 1}
        
        voronoi = 0
        raw_space = 0
        enemies_in_chamber = False
        
        # Deep search to perfectly map late-game arenas
        max_depth = 1000 
        
        while q and raw_space < max_depth:
            (cx, cy), my_dist = q.popleft()
            raw_space += 1
            
            # Check if enemies have access to this square
            e_dist = enemy_distances.get((cx, cy), float('inf'))
            if e_dist != float('inf'):
                enemies_in_chamber = True
            
            # Voronoi logic: Who gets here first?
            if my_dist < e_dist:
                voronoi += 1
            elif my_dist == e_dist:
                voronoi += 0.5
                
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
                    if (nx, ny) not in visited:
                        visited[(nx, ny)] = my_dist + 1
                        q.append(((nx, ny), my_dist + 1))
                        
        return voronoi, raw_space, enemies_in_chamber

    best_moves = []
    best_score = (-1, -1)
    move_stats = {}
    
    # 3. SCORE ALL MOVES
    for move_dir, (nx, ny) in directions.items():
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
            v, r, shared = evaluate((nx, ny))
            move_stats[move_dir] = (v, r, shared)
            
            score = (v, r)
            if score > best_score:
                best_score = score
                best_moves = [move_dir]
            elif score == best_score:
                best_moves.append(move_dir)
                
    if not best_moves:
        return "UP" # Trapped, die with dignity
        
    # 4. PHASE-SHIFTING TIE-BREAKER (The Magic Sauce)
    final_move = best_moves[0]
    
    if len(best_moves) > 1:
        # Check the state of the chamber we are about to step into
        _, _, is_shared_chamber = move_stats[best_moves[0]]
        
        if is_shared_chamber:
            # PHASE 1: AGGRESSOR
            # Push towards the center of the board to bully opponents into the walls
            center = grid_dim / 2.0
            best_center_dist = float('inf')
            for m in best_moves:
                mx, my = directions[m]
                dist_to_center = abs(mx - center) + abs(my - center)
                if dist_to_center < best_center_dist:
                    best_center_dist = dist_to_center
                    final_move = m
        else:
            # PHASE 2: ARCHITECT
            # We are isolated! Hug the walls to perfectly coil inward and maximize survival time.
            best_wall_score = -1
            for m in best_moves:
                mx, my = directions[m]
                wall_count = 0
                for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                    adj_x, adj_y = mx + dx, my + dy
                    if not (0 <= adj_x < grid_dim and 0 <= adj_y < grid_dim) or (adj_x, adj_y) in board:
                        wall_count += 1
                
                if wall_count > best_wall_score:
                    best_wall_score = wall_count
                    final_move = m
                    
    return final_move