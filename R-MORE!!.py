import collections

class GodBot:
    def __init__(self):
        self.turn_count = 0

    def move(self, my_pos, board, dim, players):
        self.turn_count += 1
        x, y = my_pos
        
        # 1. OPTIMIZED NEIGHBOR SCAN
        def get_neighbors(p):
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                nx, ny = p[0] + dx, p[1] + dy
                if 0 <= nx < dim and 0 <= ny < dim:
                    yield (nx, ny)

        # 2. AREA CONTROL (VORONOI)
        def map_control(p1, p2, obstacle_board):
            # Two-player breadth-first search to find 'Choke Points'
            q = collections.deque([(p1, 0, 1), (p2, 0, 2)])
            visited = {p1: 1, p2: 2}
            counts = {1: 0, 2: 0}
            
            while q:
                curr, dist, owner = q.popleft()
                for n in get_neighbors(curr):
                    if n not in obstacle_board and n not in visited:
                        visited[n] = owner
                        counts[owner] += 1
                        q.append((n, dist + 1, owner))
            return counts[1], counts[2]

        # 3. IDENTIFY TARGET
        opponents = [p for p in players if p['alive'] and p['pos'] != my_pos]
        if not opponents: return "UP"
        # Focus on the opponent with the MOST territory (the biggest threat)
        target_pos = opponents[0]['pos']

        # 4. DECISION MATRIX
        directions = {"UP": (x, y-1), "DOWN": (x, y+1), "LEFT": (x-1, y), "RIGHT": (x+1, y)}
        best_move = "UP"
        max_score = -float('inf')

        for d_name, n_pos in directions.items():
            if not (0 <= n_pos[0] < dim and 0 <= n_pos[1] < dim) or n_pos in board:
                continue

            # Calculate our "Control Delta"
            my_area, opp_area = map_control(n_pos, target_pos, board)
            
            # The "Choke" Score:
            # We want to maximize our area and minimize theirs.
            # We add a 'Safety' multiplier to our area.
            score = (my_area * 1.5) - opp_area
            
            # Wall-Hugging Bias (Efficiency)
            # Only apply in early/mid game to keep the center open
            if self.turn_count < (dim * dim) // 4:
                wall_neighbors = sum(1 for nb in get_neighbors(n_pos) if nb in board)
                score += wall_neighbors * 0.2

            if score > max_score:
                max_score = score
                best_move = d_name

        return best_move

# Singleton instance to persist state (turn count)
bot = GodBot()
def move(my_pos, board, dim, players):
    return bot.move(my_pos, board, dim, players)