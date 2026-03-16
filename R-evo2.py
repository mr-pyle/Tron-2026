import collections

class ApexEvolver:
    def __init__(self):
        self.generation = 0

    def move(self, my_pos, board, dim, players):
        self.generation += 1
        x, y = my_pos
        opps = [p['pos'] for p in players if p['alive'] and p['pos'] != my_pos]
        
        if not opps:
            return "UP"

        directions = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
        scored_moves = []

        for d, (dx, dy) in directions.items():
            nx, ny = x + dx, y + dy
            
            # 1. IMMEDIATE FATALITY CHECK
            if not (0 <= nx < dim and 0 <= ny < dim) or (nx, ny) in board:
                continue

            # 2. THE CHOKE-POINT TEST (Flood Fill)
            # We check how much space is ACTUALLY reachable from this move
            reachable_space = self.get_reachable_space((nx, ny), board, dim)
            
            # 3. DYNAMIC INFLUENCE (Voronoi)
            # Factor in opponent proximity to see who "owns" the reachable space
            influence = self.get_influence_field((nx, ny), opps, board, dim)
            
            # 4. THE APEX FORMULA V2
            # We prioritize: Reachable Space > Territory Dominance > Aggression
            aggression = 1.0 + (self.generation / (dim * 2))
            
            # Logic: If reachable space is tiny, score is massive negative (Death Trap)
            if reachable_space < 10: 
                score = -1000 + reachable_space
            else:
                score = (reachable_space * 20) + (influence * aggression)

            # 5. WALL-HUGGING (Efficiency)
            # Bonus for being near walls/trails to keep the board "clean"
            for adx, ady in directions.values():
                ax, ay = nx + adx, ny + ady
                if not (0 <= ax < dim and 0 <= ay < dim) or (ax, ay) in board:
                    score += 5 

            scored_moves.append((d, score))

        if not scored_moves:
            return "UP"

        # Sort by best score
        scored_moves.sort(key=lambda m: m[1], reverse=True)
        return scored_moves[0][0]

    def get_reachable_space(self, start, board, dim):
        """Simple Flood Fill to see how many tiles are in this pocket."""
        q = collections.deque([start])
        visited = {start}
        count = 0
        while q and count < 200: # Cap search for performance
            curr = q.popleft()
            count += 1
            for dx, dy in ((0,1),(0,-1),(1,0),(-1,0)):
                n = (curr[0]+dx, curr[1]+dy)
                if 0 <= n[0] < dim and 0 <= n[1] < dim and n not in board and n not in visited:
                    visited.add(n)
                    q.append(n)
        return count

    def get_influence_field(self, my_p, enemies, board, dim):
        """Calculates territorial advantage (My Area - Opponent Area)."""
        # Multi-source BFS
        q = collections.deque([(my_p, 0, True)])
        for en in enemies:
            q.append((en, 0, False))
        
        visited = {my_p: (0, True)}
        for en in enemies:
            visited[en] = (0, False)
            
        my_cells = 0
        opp_cells = 0
        
        while q:
            curr, d, is_me = q.popleft()
            for dx, dy in ((0,1),(0,-1),(1,0),(-1,0)):
                n = (curr[0]+dx, curr[1]+dy)
                if 0 <= n[0] < dim and 0 <= n[1] < dim and n not in board:
                    if n not in visited:
                        visited[n] = (d + 1, is_me)
                        if is_me: my_cells += 1
                        else: opp_cells += 1
                        q.append((n, d + 1, is_me))
        return my_cells - opp_cells