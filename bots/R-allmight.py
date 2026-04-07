class SingularityBot:
    def __init__(self):
        self.DEPTH = 3 
        self.directions = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}

    def get_valid_moves(self, pos, board, dim):
        moves = []
        for d in ["UP", "DOWN", "LEFT", "RIGHT"]:
            dx, dy = self.directions[d]
            nx, ny = pos[0] + dx, pos[1] + dy
            if 0 <= nx < dim and 0 <= ny < dim and (nx, ny) not in board:
                moves.append((d, (nx, ny)))
        return moves

    def voronoi_score(self, my_pos, opp_pos, board, dim):
        """Standard BFS using a list-queue to avoid 'collections' import."""
        q = [(my_pos, 0, True), (opp_pos, 0, False)]
        visited = {my_pos: True, opp_pos: False}
        score = 0
        idx = 0
        
        # Limit search to 300 nodes to guarantee speed
        while idx < len(q) and idx < 300:
            curr, dist, is_me = q[idx]
            idx += 1
            for d in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = curr[0] + d[0], curr[1] + d[1]
                target = (nx, ny)
                if 0 <= nx < dim and 0 <= ny < dim and target not in board and target not in visited:
                    visited[target] = is_me
                    if is_me:
                        score += 1
                    q.append((target, dist + 1, is_me))
        return score

    def minimax(self, my_pos, opp_pos, board, depth, alpha, beta, is_maximizing, dim):
        my_moves = self.get_valid_moves(my_pos, board, dim)
        opp_moves = self.get_valid_moves(opp_pos, board, dim)
        
        if not my_moves: return -100000 + (self.DEPTH - depth)
        if not opp_moves: return 100000 - (self.DEPTH - depth)
        if depth == 0: return self.voronoi_score(my_pos, opp_pos, board, dim)

        if is_maximizing:
            max_eval = -2000000
            for _, next_pos in my_moves:
                board[next_pos] = 1
                ev = self.minimax(next_pos, opp_pos, board, depth - 1, alpha, beta, False, dim)
                del board[next_pos]
                if ev > max_eval: max_eval = ev
                if ev > alpha: alpha = ev
                if beta <= alpha: break
            return max_eval
        else:
            min_eval = 2000000
            for _, next_pos in opp_moves:
                board[next_pos] = 1
                ev = self.minimax(my_pos, next_pos, board, depth - 1, alpha, beta, True, dim)
                del board[next_pos]
                if ev < min_eval: min_eval = ev
                if ev < beta: beta = ev
                if beta <= alpha: break
            return min_eval

    def move(self, my_pos, board, dim, players):
        my_pos = (my_pos[0], my_pos[1])
        
        # Filter opponents
        active_opps = []
        for p in players:
            if p['alive'] and (p['pos'][0], p['pos'][1]) != my_pos:
                active_opps.append(p)
        
        if not active_opps:
            valid = self.get_valid_moves(my_pos, board, dim)
            return valid[0][0] if valid else "UP"
        
        # Target the closest opponent
        target_opp = (active_opps[0]['pos'][0], active_opps[0]['pos'][1])
        min_dist = 9999
        for p in active_opps:
            d = abs(my_pos[0]-p['pos'][0]) + abs(my_pos[1]-p['pos'][1])
            if d < min_dist:
                min_dist = d
                target_opp = (p['pos'][0], p['pos'][1])

        best_move = "UP"
        best_score = -2000000
        
        valid_choices = self.get_valid_moves(my_pos, board, dim)
        if not valid_choices: return "UP"

        for d, next_pos in valid_choices:
            board[next_pos] = 1
            score = self.minimax(next_pos, target_opp, board, self.DEPTH, -2000000, 2000000, False, dim)
            del board[next_pos]
            
            if score > best_score:
                best_score = score
                best_move = d
                
        return best_move

# Instance creation for the runner
bot_instance = SingularityBot()

def move(my_pos, board, dim, players):
    return bot_instance.move(my_pos, board, dim, players)