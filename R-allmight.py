import collections

class SingularityBot:
    def __init__(self):
        self.memo = {}

    def move(self, my_pos, board, dim, players):
        # 1. THE NEURAL GRAPH (BFS + Parity)
        def analyze_map(start_p, opp_ps, current_board):
            # Influence map with distance tracking
            q = collections.deque([(start_p, 0, True)])
            for op in opp_ps:
                q.append((op, 0, False))
            
            visited = {start_p: (0, True)}
            for op in opp_ps:
                visited[op] = (0, False)
                
            stats = {"my_area": 0, "opp_area": 0, "neutral": 0}
            
            while q:
                curr, dist, is_me = q.popleft()
                for dx, dy in ((0,1),(0,-1),(1,0),(-1,0)):
                    nx, ny = curr[0]+dx, curr[1]+dy
                    if 0 <= nx < dim and 0 <= ny < dim and (nx, ny) not in current_board:
                        if (nx, ny) not in visited:
                            visited[(nx, ny)] = (dist + 1, is_me)
                            if is_me: stats["my_area"] += 1
                            else: stats["opp_area"] += 1
                            q.append(((nx, ny), dist + 1, is_me))
                        else:
                            # Conflict square: if we reach it at the same time, it's neutral
                            v_dist, v_me = visited[(nx, ny)]
                            if v_dist == dist + 1 and v_me != is_me:
                                stats["neutral"] += 1
            return stats

        # 2. THE HUNTING PROTOCOL
        opps = [p['pos'] for p in players if p['alive'] and p['pos'] != my_pos]
        if not opps: return "UP"

        best_move = "UP"
        ultimate_score = -float('inf')

        # Directional Priority
        for d, (dx, dy) in {"UP":(0,-1), "DOWN":(0,1), "LEFT":(-1,0), "RIGHT":(1,0)}.items():
            nx, ny = my_pos[0]+dx, my_pos[1]+dy
            
            if not (0 <= nx < dim and 0 <= ny < dim) or (nx, ny) in board:
                continue

            # Calculate the 'Map Fate'
            res = analyze_map((nx, ny), opps, board)
            
            # --- THE GOD FORMULA ---
            # 1. My Area: Total potential squares I own.
            # 2. Opp Area: Total potential squares they own.
            # 3. Aggression: Distance to nearest enemy (to keep them cornered).
            dist_to_enemy = min(abs(nx - op[0]) + abs(ny - op[1]) for op in opps)
            
            # We weigh 'My Area' as infinite survival, 
            # but we weigh 'Opp Area' as a negative multiplier.
            # If Opp Area is 0, we have won the partition.
            score = (res["my_area"] * 100) - (res["opp_area"] * 150) - dist_to_enemy

            # 4. CHOKE POINT BIAS
            # If this move reduces the opponent's area to a fraction of ours, 
            # it's a 'Kill Move'.
            if res["opp_area"] < 10 and res["my_area"] > 20:
                score += 10000 

            if score > ultimate_score:
                ultimate_score = score
                best_move = d

        return best_move

# Global instantiation
singularity = SingularityBot()
def move(my_pos, board, dim, players):
    return singularity.move(my_pos, board, dim, players)