import collections

class SingularityBot:
    def __init__(self):
        self.depth_limit = 3  # How many turns to look ahead
        self.directions = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}

    def get_valid_moves(self, pos, board_set, dim):
        moves = []
        for d, (dx, dy) in self.directions.items():
            nx, ny = pos[0] + dx, pos[1] + dy
            if 0 <= nx < dim and 0 <= ny < dim and (nx, ny) not in board_set:
                moves.append((d, (nx, ny)))
        return moves

    def heuristic(self, my_pos, opp_pos, board_set, dim):
        """
        Enhanced Voronoi: Predicts territorial control.
        Squares reachable by me sooner than the opponent are 'mine'.
        """
        q = collections.deque([(my_pos, 0, True), (opp_pos, 0, False)])
        visited = {my_pos: True, opp_pos: False}
        my_territory = 0
        
        while q:
            curr, dist, is_me = q.popleft()
            for dx, dy in self.directions.values():
                nx, ny = curr[0] + dx, curr[1] + dy
                if 0 <= nx < dim and 0 <= ny < dim and (nx, ny) not in board_set and (nx, ny) not in visited:
                    visited[(nx, ny)] = is_me
                    if is_me: my_territory += 1
                    q.append(((nx, ny), dist + 1, is_me))
        
        # Add a tiny 'center bias' to avoid getting hugged into a wall early
        center = dim / 2
        dist_to_center = abs(my_pos[0] - center) + abs(my_pos[1] - center)
        
        return my_territory - (dist_to_center * 0.1)

    def minimax(self, my_pos, opp_pos, board_set, depth, alpha, beta, is_maximizing, dim):
        # Base case: end of search or someone is trapped
        my_moves = self.get_valid_moves(my_pos, board_set, dim)
        opp_moves = self.get_valid_moves(opp_pos, board_set, dim)
        
        if not my_moves: return -1000000 + (self.depth_limit - depth)
        if not opp_moves: return 1000000 - (self.depth_limit - depth)
        if depth == 0: return self.heuristic(my_pos, opp_pos, board_set, dim)

        if is_maximizing:
            max_eval = -float('inf')
            # Move Ordering: Evaluate moves with more immediate space first
            my_moves.sort(key=lambda m: len(self.get_valid_moves(m[1], board_set, dim)), reverse=True)
            
            for _, next_pos in my_moves:
                board_set.add(next_pos)
                eval = self.minimax(next_pos, opp_pos, board_set, depth - 1, alpha, beta, False, dim)
                board_set.remove(next_pos)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha: break
            return max_eval
        else:
            min_eval = float('inf')
            opp_moves.sort(key=lambda m: len(self.get_valid_moves(m[1], board_set, dim)), reverse=True)
            
            for _, next_pos in opp_moves:
                board_set.add(next_pos)
                eval = self.minimax(my_pos, next_pos, board_set, depth - 1, alpha, beta, True, dim)
                board_set.remove(next_pos)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha: break
            return min_eval

    def move(self, my_pos, board, dim, players):
        my_pos = tuple(my_pos)
        board_set = {tuple(p) for p in board}
        
        # Identify the closest active threat
        opps = [p for p in players if p['alive'] and tuple(p['pos']) != my_pos]
        if not opps: return "UP"
        
        # Sort opponents by proximity
        opps.sort(key=lambda o: abs(my_pos[0]-o['pos'][0]) + abs(my_pos[1]-o['pos'][1]))
        target_opp = tuple(opps[0]['pos'])

        best_move = "UP"
        best_score = -float('inf')
        
        valid_moves = self.get_valid_moves(my_pos, board_set, dim)
        if not valid_moves: return "UP"

        for d, next_pos in valid_moves:
            board_set.add(next_pos)
            score = self.minimax(next_pos, target_opp, board_set, self.depth_limit, -float('inf'), float('inf'), False, dim)
            board_set.remove(next_pos)
            
            if score > best_score:
                best_score = score
                best_move = d
                
        return best_move

# Engine interface
bot_instance = SingularityBot()
def move(my_pos, board, dim, players):
    return bot_instance.move(my_pos, board, dim, players)