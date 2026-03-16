import collections

team_name ="PittyBot"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    directions = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
    
    # 1. Track all living threats
    enemies = [p['pos'] for p in players if p['alive'] and p['pos'] != my_pos]

    def get_score(start_node):
        if not (0 <= start_node[0] < grid_dim and 0 <= start_node[1] < grid_dim) or start_node in board:
            return -9999999

        # 2. Advanced Voronoi: Multi-agent reachability
        # We simulate the expansion of all players simultaneously
        q = collections.deque()
        reach_map = {}
        
        # Seed the map with enemies (they move simultaneously with us)
        for en in enemies:
            q.append((en, 0, "enemy"))
            reach_map[en] = 0
            
        # Seed with our potential move
        q.append((start_node, 0, "me"))
        reach_map[start_node] = 0

        my_territory = 0
        enemy_territory = 0
        
        # Standard BFS doesn't account for simultaneous moves well; 
        # this version tracks 'ownership' per tick
        while q:
            curr, dist, owner = q.popleft()
            
            for dx, dy in directions.values():
                nxt = (curr[0] + dx, curr[1] + dy)
                if 0 <= nxt[0] < grid_dim and 0 <= nxt[1] < grid_dim and nxt not in board and nxt not in reach_map:
                    reach_map[nxt] = dist + 1
                    if owner == "me":
                        my_territory += 1
                        q.append((nxt, dist + 1, "me"))
                    else:
                        enemy_territory += 1
                        q.append((nxt, dist + 1, "enemy"))

        # 3. Connectivity & Wall-Hugging Heuristics
        # We check how many 'neighbors' this square has to ensure we pack tightly
        neighbors = 0
        for dx, dy in directions.values():
            adj = (start_node[0] + dx, start_node[1] + dy)
            if not (0 <= adj[0] < grid_dim and 0 <= adj[1] < grid_dim) or adj in board:
                neighbors += 1

        # 4. Final Scoring:
        # Priority A: Maximize our territory (Life)
        # Priority B: Minimize enemy territory (The 'Kill' factor)
        # Priority C: Wall density (Efficiency)
        return (my_territory * 1000) - (enemy_territory * 5) + (neighbors * 20)

    # Decision logic
    best_move = "UP"
    max_score = -float('inf')
    
    # We evaluate all directions and pick the one with the highest strategic value
    for move_name, (dx, dy) in directions.items():
        score = get_score((x + dx, y + dy))
        if score > max_score:
            max_score = score
            best_move = move_name
            
    return best_move