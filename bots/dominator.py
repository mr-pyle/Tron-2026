import random
from collections import deque

team_name = "dominator"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    
    # Define possible moves
    directions = {
        "UP": (x, y - 1), "DOWN": (x, y + 1),
        "LEFT": (x - 1, y), "RIGHT": (x + 1, y)
    }
    
    # ==========================================================
    # TIER 0: SURVIVAL & EVASION
    # ==========================================================
    # Filter out immediate wall/body collisions
    safe_moves = {d: pos for d, pos in directions.items() 
                  if 0 <= pos[0] < grid_dim and 0 <= pos[1] < grid_dim and pos not in board}
                  
    if not safe_moves:
        return "UP" # Cornered, game over.
        
    enemies = [p['pos'] for p in players if p['pos'] != my_pos]
    
    # Identify Enemy Kill Zones (Where enemies can move NEXT turn)
    # Stepping here is a 50/50 gamble. We avoid this unless it's our only option.
    enemy_next_moves = set()
    for ex, ey in enemies:
        for nx, ny in [(ex, ey-1), (ex, ey+1), (ex-1, ey), (ex+1, ey)]:
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim:
                enemy_next_moves.add((nx, ny))
                
    # Prioritize moves that don't risk a head-to-head collision
    safer_moves = {d: pos for d, pos in safe_moves.items() if pos not in enemy_next_moves}
    considered_moves = safer_moves if safer_moves else safe_moves

    # ==========================================================
    # TIER 1 & 2: FLOOD FILL & TRUE VORONOI
    # ==========================================================
    def get_space_metrics(simulated_pos, limit=2000):
        # 1. Flood Fill for Absolute Survival Space (Trap Detection)
        f_queue = deque([simulated_pos])
        visited_flood = {simulated_pos}
        
        while f_queue and len(visited_flood) < limit:
            cx, cy = f_queue.popleft()
            for nx, ny in [(cx, cy-1), (cx, cy+1), (cx-1, cy), (cx+1, cy)]:
                if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
                    if (nx, ny) not in visited_flood:
                        visited_flood.add((nx, ny))
                        f_queue.append((nx, ny))
                        
        absolute_space = len(visited_flood)
        
        # 2. True Distance Voronoi for Contested Space Control
        v_queue = deque()
        visited_vor = {}
        
        # Start me at my simulated next move
        v_queue.append((simulated_pos, 'me', 0))
        visited_vor[simulated_pos] = ('me', 0)
        
        # Start enemies at their current positions (they step simultaneously)
        for e_pos in enemies:
            v_queue.append((e_pos, 'enemy', 0))
            visited_vor[e_pos] = ('enemy', 0)
            
        my_territory = 0
        
        while v_queue:
            curr_pos, owner, dist = v_queue.popleft()
            
            if owner == 'me':
                my_territory += 1
                
            cx, cy = curr_pos
            for nx, ny in [(cx, cy-1), (cx, cy+1), (cx-1, cy), (cx+1, cy)]:
                if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
                    if (nx, ny) not in visited_vor:
                        visited_vor[(nx, ny)] = (owner, dist + 1)
                        v_queue.append(((nx, ny), owner, dist + 1))

        return absolute_space, my_territory

    # Calculate metrics for all viable moves
    move_metrics = {d: get_space_metrics(pos) for d, pos in considered_moves.items()}
    
    # Filter 1: Trap Avoidance (Must be within 5% of the largest absolute room)
    max_flood = max(m[0] for m in move_metrics.values())
    viable_moves = {d: pos for d, pos in considered_moves.items() 
                    if move_metrics[d][0] >= max_flood * 0.95}
                    
    # Filter 2: Maximum Aggression (Steal the most territory)
    max_voronoi = max(move_metrics[d][1] for d in viable_moves)
    best_combat_moves = [d for d in viable_moves if move_metrics[d][1] == max_voronoi]
    
    # ==========================================================
    # TIER 3: WALL HUGGING & MOMENTUM (Endgame Efficiency)
    # ==========================================================
    def count_obstacles(pos):
        px, py = pos
        return sum(1 for nx, ny in [(px, py-1), (px, py+1), (px-1, py), (px+1, py)] 
                   if not (0 <= nx < grid_dim and 0 <= ny < grid_dim) or (nx, ny) in board)
                   
    # Tie-breaker 1: Hug walls tightly to maximize lifespan in closed rooms
    if len(best_combat_moves) > 1:
        move_obstacles = {d: count_obstacles(considered_moves[d]) for d in best_combat_moves}
        max_obs = max(move_obstacles.values())
        best_combat_moves = [d for d, obs in move_obstacles.items() if obs == max_obs]

    # Tie-breaker 2: Maintain straight lines to prevent unfillable zig-zags
    my_data = next((p for p in players if p['pos'] == my_pos), None)
    if my_data and 'trail' in my_data and len(my_data['trail']) >= 2:
        last_x, last_y = my_data['trail'][-2]
        current_heading = None
        
        if x > last_x: current_heading = "RIGHT"
        elif x < last_x: current_heading = "LEFT"
        elif y > last_y: current_heading = "DOWN"
        elif y < last_y: current_heading = "UP"
        
        if current_heading in best_combat_moves:
            return current_heading

    # Flawless random choice if all metrics are perfectly equal
    return random.choice(best_combat_moves)