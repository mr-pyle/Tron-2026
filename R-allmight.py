import collections
import json
import os
import copy

class SingularityBot:
    def __init__(self, brain_file="brain.json"):
        self.brain_file = brain_file
        self.dna = {"depth": 3, "survival_weight": 1000, "aggression_weight": 500}
        self.load_brain()

    def load_brain(self):
        if os.path.exists(self.brain_file):
            try:
                with open(self.brain_file, 'r') as f:
                    self.dna.update(json.load(f))
            except: pass

    def get_valid_moves(self, pos, board_set, dim):
        moves = []
        for d, (dx, dy) in {"UP":(0,-1), "DOWN":(0,1), "LEFT":(-1,0), "RIGHT":(1,0)}.items():
            nx, ny = pos[0]+dx, pos[1]+dy
            if 0 <= nx < dim and 0 <= ny < dim and (nx, ny) not in board_set:
                moves.append((d, (nx, ny)))
        return moves

    def heuristic(self, my_pos, opp_pos, board_set, dim):
        """Evaluates how 'good' a board state is."""
        my_area = self.voronoi_area(my_pos, opp_pos, board_set, dim)
        # Distance penalty to keep the bot from getting 'lazy' in open space
        dist = abs(my_pos[0]-opp_pos[0]) + abs(my_pos[1]-opp_pos[1])
        return (my_area * self.dna["survival_weight"]) + dist

    def voronoi_area(self, p1, p2, board_set, dim):
        """Fast BFS to count squares closer to me than the opponent."""
        q = collections.deque([(p1, 0, True), (p2, 0, False)])
        visited = {p1: True, p2: False}
        score = 0
        while q:
            curr, dist, is_me = q.popleft()
            for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
                nx, ny = curr[0]+dx, curr[1]+dy
                if 0 <= nx < dim and 0 <= ny < dim and (nx, ny) not in board_set and (nx, ny) not in visited:
                    visited[(nx, ny)] = is_me
                    if is_me: score += 1
                    q.append(((nx, ny), dist + 1, is_me))
        return score

    def minimax(self, my_pos, opp_pos, board_set, dim, depth, alpha, beta, is_maximizing):
        if depth == 0:
            return self.heuristic(my_pos, opp_pos, board_set, dim)

        if is_maximizing:
            max_eval = -float('inf')
            moves = self.get_valid_moves(my_pos, board_set, dim)
            if not moves: return -1000000 # Loss state
            for _, next_pos in moves:
                board_set.add(next_pos)
                eval = self.minimax(next_pos, opp_pos, board_set, dim, depth-1, alpha, beta, False)
                board_set.remove(next_pos)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha: break
            return max_eval
        else:
            min_eval = float('inf')
            moves = self.get_valid_moves(opp_pos, board_set, dim)
            if not moves: return 1000000 # Opponent loss state
            for _, next_pos in moves:
                board_set.add(next_pos)
                eval = self.minimax(my_pos, next_pos, board_set, dim, depth-1, alpha, beta, True)
                board_set.remove(next_pos)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha: break
            return min_eval

    def move(self, my_pos, board, dim, players):
        my_pos = tuple(my_pos)
        board_set = {tuple(p) for p in board}
        opps = [p for p in players if p['alive'] and tuple(p['pos']) != my_pos]
        
        if not opps: return "UP"
        opp_pos = tuple(opps[0]['pos']) # Focus on the primary threat

        best_score = -float('inf')
        best_move = "UP"
        
        valid = self.get_valid_moves(my_pos, board_set, dim)
        if not valid: return "UP"

        for d, next_pos in valid:
            board_set.add(next_pos)
            # Depth 3 is usually the 'sweet spot' for Tkinter-based performance
            score = self.minimax(next_pos, opp_pos, board_set, dim, self.dna["depth"], -float('inf'), float('inf'), False)
            board_set.remove(next_pos)
            
            if score > best_score:
                best_score = score
                best_move = d
                
        return best_move

singularity = SingularityBot()
def move(my_pos, board, dim, players):
    return singularity.move(my_pos, board, dim, players)