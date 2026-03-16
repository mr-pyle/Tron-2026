
import collections

class ApexEvolver:
    def __init__(self):
        self.generation = 0

    def move(self, my_pos, board, dim, players):
        self.generation += 1
        x, y = my_pos
        
        # 1. DYNAMIC INFLUENCE FIELD (Heatmap)
        # We calculate the 'Temperature' of the board. 
        # High heat = Contested/Dangerous. Low heat = Safety.
        def get_influence_field(my_p, enemies, current_board):
            # Multi-Source BFS to determine 'Ownership'
            q = collections.deque([(my_p, 0, True)])
            for en in enemies:
                q.append((en, 0, False))
            
            influence = {} # (x,y) -> (dist, is_me)
            counts = {True: 0, False: 0}
            
            while q:
                curr, d, is_me = q.popleft()
                for dx, dy in ((0,1),(0,-1),(1,0),(-1,0)):
                    n = (curr[0]+dx, curr[1]+dy)
                    if 0 <= n[0] < dim and 0 <= n[1] < dim and n not in current_board:
                        if n not in influence:
                            influence[n] = (d + 1, is_me)
                            counts[is_me] += 1
                            q.append((n, d + 1, is_me))
            return counts

        # 2. TARGET SELECTION (Evolutionary Hunting)
        opps = [p['pos'] for p in players if p['alive'] and p['pos'] != my_pos]
        if not opps: return "UP"

        # 3. THE RECURSIVE SELECTION
        directions = {"UP": (0,-1), "DOWN": (0,1), "LEFT": (-1,0), "RIGHT": (1,0)}
        scored_moves = []

        for d, (dx, dy) in directions.items():
            nx, ny = x + dx, y + dy
            if not (0 <= nx < dim and 0 <= ny < dim) or (nx, ny) in board:
                continue

            # STEP-BY-STEP EVOLUTION:
            # We simulate the board one step into the future
            future_counts = get_influence_field((nx, ny), opps, board)
            
            # THE APEX FORMULA:
            # Survival (My Area) vs. Suppression (Their Area)
            # As the game progresses (generation increases), we become MORE aggressive.
            aggression_factor = 1.0 + (self.generation / (dim * 2))
            
            # Calculate the 'Dominance Ratio'
            score = (future_counts[True] * 10) - (future_counts[False] * aggression_factor)

            # SPACE RECYCLING:
            # If we are near a wall or our own trail, we get a 'Efficiency' bonus.
            # This forces the bot to 'knit' its trail tightly together.
            for adx, ady in ((0,1),(0,-1),(1,0),(-1,0)):
                if not (0 <= nx+adx < dim and 0 <= ny+ady < dim) or (nx+adx, ny+ady) in board:
                    score += 2 # Bonus for saving space

            scored_moves.append((d, score))

        if not scored_moves:
            return "UP"

        # Sort by the most mathematically dominant outcome
        scored_moves.sort(key=lambda m: m[1], reverse=True)
        return scored_moves[0][0]

# Evolutionary Instance
bot = ApexEvolver()
def move(my_pos, board, dim, players):
    return bot.move(my_pos, board, dim, players)