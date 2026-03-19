import collections
import itertools

team_name = "Leon S. Kennedy"  # Change this to your team name!

def move(my_pos, board, grid_dim, players):
    dirs = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
    
    def is_safe(nx, ny, current_board):
        return 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in current_board

    enemies = [p['pos'] for p in players if p['pos'] != my_pos and p.get('alive', True)]
    
    # --- CHIMERA'S EVALUATION FUNCTION ---
    # (This evaluates a board state and returns a score tuple)
    def evaluate_state(sim_my_pos, sim_board, sim_enemies):
        # 1. Articulation Point Check
        x, y = sim_my_pos
        open_nbrs = [(x+dx, y+dy) for dx, dy in dirs.values() if is_safe(x+dx, y+dy, sim_board)]
        is_ap = False
        if len(open_nbrs) > 1:
            temp_blocked = set(sim_board.keys()) | {sim_my_pos}
            reachable = set([open_nbrs[0]])
            q = collections.deque([open_nbrs[0]])
            while q:
                cx, cy = q.popleft()
                for dx, dy in dirs.values():
                    nx, ny = cx + dx, cy + dy
                    if is_safe(nx, ny, temp_blocked) and (nx, ny) not in reachable:
                        reachable.add((nx, ny))
                        q.append((nx, ny))
            is_ap = any(nbr not in reachable for nbr in open_nbrs[1:])

        # 2. Flood Fill & Voronoi 
        enemy_dists = {}
        eq = collections.deque([(ex, ey, 0) for ex, ey in sim_enemies])
        for ex, ey in sim_enemies: enemy_dists[(ex, ey)] = 0
        while eq:
            cx, cy, dist = eq.popleft()
            if dist > 50: continue # Shallow search for speed
            for dx, dy in dirs.values():
                nx, ny = cx + dx, cy + dy
                if is_safe(nx, ny, sim_board) and (nx, ny) not in enemy_dists:
                    enemy_dists[(nx, ny)] = dist + 1
                    eq.append((nx, ny, dist + 1))

        q = collections.deque([(sim_my_pos[0], sim_my_pos[1], 1)])
        visited = {sim_my_pos}
        exclusive = 0
        reachable = 0
        
        while q:
            cx, cy, dist = q.popleft()
            reachable += 1
            if dist < enemy_dists.get((cx, cy), float('inf')):
                exclusive += 1
            if reachable > 400: break # Speed optimization
                
            for dx, dy in dirs.values():
                nnx, nny = cx + dx, cy + dy
                if is_safe(nnx, nny, sim_board) and (nnx, nny) not in visited:
                    visited.add((nnx, nny))
                    q.append((nnx, nny, dist + 1))
                    
        onward = sum(1 for dx, dy in dirs.values() if is_safe(sim_my_pos[0] + dx, sim_my_pos[1] + dy, sim_board))
        
        # Tuple scoring matches Chimera's priorities
        return (0 if is_ap else 1, exclusive, reachable, -onward)

    # --- PARANOID MINIMAX WITH ALPHA-BETA PRUNING ---
    def minimax(current_my_pos, current_enemies, current_board, depth, alpha, beta, is_maximizing):
        # Base case: we hit our depth limit, or we died.
        if depth == 0 or not is_safe(current_my_pos[0], current_my_pos[1], current_board):
            return evaluate_state(current_my_pos, current_board, current_enemies)

        if is_maximizing:
            max_eval = (-float('inf'), -float('inf'), -float('inf'), -float('inf'))
            for d, (dx, dy) in dirs.items():
                nx, ny = current_my_pos[0] + dx, current_my_pos[1] + dy
                if is_safe(nx, ny, current_board):
                    sim_board = current_board.copy()
                    sim_board[(nx, ny)] = 1
                    
                    eval_score = minimax((nx, ny), current_enemies, sim_board, depth - 1, alpha, beta, False)
                    max_eval = max(max_eval, eval_score)
                    alpha = max(alpha, eval_score)
                    if beta <= alpha:
                        break # Prune
            return max_eval
            
        else:
            # The "Paranoid" Step: Assume enemies move to minimize our score
            min_eval = (float('inf'), float('inf'), float('inf'), float('inf'))
            
            # Generate all possible combinations of enemy moves
            enemy_moves = []
            for ex, ey in current_enemies:
                e_safe = [(ex+dx, ey+dy) for dx, dy in dirs.values() if is_safe(ex+dx, ey+dy, current_board)]
                enemy_moves.append(e_safe if e_safe else [(ex, ey)])
                
            for combined_moves in itertools.product(*enemy_moves):
                sim_board = current_board.copy()
                for pos in combined_moves:
                    sim_board[pos] = 1
                    
                eval_score = minimax(current_my_pos, list(combined_moves), sim_board, depth - 1, alpha, beta, True)
                min_eval = min(min_eval, eval_score)
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break # Prune
            return min_eval

    # --- THE EXECUTION ---
    best_move = "UP"
    best_score = (-float('inf'), -float('inf'), -float('inf'), -float('inf'))
    
    # We set depth to 2. This looks at Our Move -> Their Moves -> Our Response.
    # In a 50ms Python environment, depth 2 is usually the sweet spot before timing out.
    SEARCH_DEPTH = 2 
    
    for d, (dx, dy) in dirs.items():
        nx, ny = my_pos[0] + dx, my_pos[1] + dy
        if is_safe(nx, ny, board):
            sim_board = board.copy()
            sim_board[(nx, ny)] = 1
            
            # Initial Alpha/Beta values
            alpha = (-float('inf'), -float('inf'), -float('inf'), -float('inf'))
            beta = (float('inf'), float('inf'), float('inf'), float('inf'))
            
            score = minimax((nx, ny), enemies, sim_board, SEARCH_DEPTH, alpha, beta, False)
            
            if score > best_score:
                best_score = score
                best_move = d

    return best_move