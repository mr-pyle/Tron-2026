import collections

def move(my_pos, board, dim, players):
    # 1. SETUP & TARGETING
    opponents = [p for p in players if p['alive'] and p['pos'] != my_pos]
    if not opponents: return "UP"
    
    # Target the closest threat
    opponents.sort(key=lambda p: abs(my_pos[0]-p['pos'][0]) + abs(my_pos[1]-p['pos'][1]))
    opp_pos = opponents[0]['pos']

    # --- THE BRAIN: EVALUATION FUNCTION ---
    def evaluate_state(my_p, his_p, current_board):
        """
        The Voronoi heuristic: Who owns more of the map from these positions?
        """
        queue = collections.deque([(my_p, 0, True), (his_p, 0, False)])
        visited = {my_p: True, his_p: False}
        score = 0
        limit = 120 # Computational budget
        
        while queue and limit > 0:
            (cx, cy), dist, is_me = queue.popleft()
            limit -= 1
            for dx, dy in ((0,1), (0,-1), (1,0), (-1,0)):
                n = (cx+dx, cy+dy)
                if 0 <= n[0] < dim and 0 <= n[1] < dim:
                    if n not in current_board and n not in visited:
                        visited[n] = is_me
                        score += 1 if is_me else -1
                        queue.append((n, dist+1, is_me))
        return score

    # --- THE LOOKAHEAD (MINIMAX) ---
    best_move = "UP"
    max_eval = -float('inf')
    
    directions = {"UP": (0,-1), "DOWN": (0,1), "LEFT": (-1,0), "RIGHT": (1,0)}
    
    for d_name, (dx, dy) in directions.items():
        nx, ny = my_pos[0]+dx, my_pos[1]+dy
        
        # Prune immediate suicide
        if not (0 <= nx < dim and 0 <= ny < dim) or (nx, ny) in board:
            continue
            
        # Simulate my move
        new_board = board.copy()
        new_board[(nx, ny)] = 1
        
        # Predict Opponent's best response (Minimizing my score)
        min_eval = float('inf')
        for odx, ody in ((0,1), (0,-1), (1,0), (-1,0)):
            onx, ony = opp_pos[0]+odx, opp_pos[1]+ody
            if 0 <= onx < dim and 0 <= ony < dim and (onx, ony) not in new_board:
                # Score the board after both moved
                val = evaluate_state((nx, ny), (onx, ony), new_board)
                if val < min_eval:
                    min_eval = val
        
        # If opponent has no moves, this is a winning path
        if min_eval == float('inf'): min_eval = 999 

        if min_eval > max_eval:
            max_eval = min_eval
            best_move = d_name

    return best_move