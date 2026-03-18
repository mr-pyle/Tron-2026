import collections
import random

team_name = "Dio"

def get_valid_neighbors(pos, board, grid_dim):
    """Finds all safe, immediately adjacent moves."""
    x, y = pos
    neighbors = {
        "UP": (x, y - 1),
        "DOWN": (x, y + 1),
        "LEFT": (x - 1, y),
        "RIGHT": (x + 1, y)
    }
    
    valid = {}
    for d, (nx, ny) in neighbors.items():
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
            valid[d] = (nx, ny)
            
    return valid

def get_chamber_size(pos, board, grid_dim, limit=100):
    """Flood-fill to find raw space available."""
    queue = collections.deque([pos])
    visited = {pos}
    size = 0
    
    while queue and size < limit:
        cx, cy = queue.popleft()
        size += 1
        for nx, ny in [(cx, cy-1), (cx, cy+1), (cx-1, cy), (cx+1, cy)]:
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
                if (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
    return size

def calculate_voronoi(my_next_pos, enemy_heads, board, grid_dim, max_depth=100):
    """Simulates a fair race for territory."""
    queue = collections.deque()
    visited = {} 
    
    queue.append((my_next_pos, 1, 'ME'))
    visited[my_next_pos] = 'ME'
    
    for e_pos in enemy_heads:
        queue.append((e_pos, 0, 'ENEMY'))
        visited[e_pos] = 'ENEMY'
            
    my_territory = 0
    
    while queue:
        curr_pos, dist, owner = queue.popleft()
        if dist > max_depth:
            continue
        if owner == 'ME':
            my_territory += 1
            
        cx, cy = curr_pos
        for nx, ny in [(cx, cy-1), (cx, cy+1), (cx-1, cy), (cx+1, cy)]:
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
                if (nx, ny) not in visited:
                    visited[(nx, ny)] = owner
                    queue.append(((nx, ny), dist + 1, owner))
    return my_territory

def get_danger_level(pos, enemy_heads):
    """Checks for instant head-on collision risk."""
    x, y = pos
    for ex, ey in enemy_heads:
        if abs(x - ex) + abs(y - ey) == 1:
            return True
    return False

def count_adjacent_obstacles(pos, board, grid_dim):
    """Counts touching walls/trails to hug the perimeter."""
    x, y = pos
    obstacles = 0
    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx == 0 and dy == 0: 
                continue
            nx, ny = x + dx, y + dy
            if not (0 <= nx < grid_dim and 0 <= ny < grid_dim) or (nx, ny) in board:
                obstacles += 1
    return obstacles

def predict_enemy_targets(enemy_heads, board, grid_dim):
    """Simulates the enemy's thought process to guess their next move."""
    likely_targets = set()
    for ex, ey in enemy_heads:
        enemy_moves = get_valid_neighbors((ex, ey), board, grid_dim)
        best_enemy_score = float('-inf')
        best_enemy_targets = []
        
        for dir_name, target_pos in enemy_moves.items():
            board[target_pos] = -1
            space = get_chamber_size(target_pos, board, grid_dim, limit=50)
            del board[target_pos]
            
            if space > best_enemy_score:
                best_enemy_score = space
                best_enemy_targets = [target_pos]
            elif space == best_enemy_score:
                best_enemy_targets.append(target_pos)
                
        for target in best_enemy_targets:
            likely_targets.add(target)
    return likely_targets

def get_closest_enemy(my_pos, enemy_heads):
    """Finds the immediate threat to target."""
    if not enemy_heads:
        return None
    return min(enemy_heads, key=lambda e: abs(my_pos[0] - e[0]) + abs(my_pos[1] - e[1]))

def evaluate_board(my_pos, enemy_pos, board, grid_dim):
    """Zero-Sum evaluation: Maximizes our space while minimizing the enemy's."""
    if not enemy_pos:
        return get_chamber_size(my_pos, board, grid_dim, limit=50)
        
    my_space = get_chamber_size(my_pos, board, grid_dim, limit=50)
    enemy_space = get_chamber_size(enemy_pos, board, grid_dim, limit=50)
    return my_space - enemy_space 

def minimax(my_pos, enemy_pos, board, grid_dim, depth, is_maximizing):
    """Deep-future simulation focused on trapping the enemy."""
    if depth == 0:
        return evaluate_board(my_pos, enemy_pos, board, grid_dim)
        
    if is_maximizing:
        best_score = float('-inf')
        moves = get_valid_neighbors(my_pos, board, grid_dim)
        
        if not moves:
            return -9999 
            
        for next_pos in moves.values():
            board[next_pos] = -1 
            score = minimax(next_pos, enemy_pos, board, grid_dim, depth - 1, False)
            del board[next_pos]  
            best_score = max(best_score, score)
        return best_score
        
    else:
        worst_score = float('inf')
        if not enemy_pos:
            return 9999 
            
        moves = get_valid_neighbors(enemy_pos, board, grid_dim)
        
        if not moves:
            return 9999 
            
        for next_pos in moves.values():
            board[next_pos] = -1 
            score = minimax(my_pos, next_pos, board, grid_dim, depth - 1, True)
            del board[next_pos]  
            worst_score = min(worst_score, score)
        return worst_score

def move(my_pos, board, grid_dim, players):
    """Dio's Aggressive Hunter Engine."""
    valid_moves = get_valid_neighbors(my_pos, board, grid_dim)
    
    if not valid_moves:
        return "UP" 
        
    enemy_heads = [p['pos'] for p in players if p['pos'] != my_pos]
    predicted_enemy_moves = predict_enemy_targets(enemy_heads, board, grid_dim)
    closest_enemy = get_closest_enemy(my_pos, enemy_heads)
    
    weight_chamber = 1.0
    weight_voronoi = 1.0  
    weight_obstacles = 0.5 
    weight_prediction_penalty = 20.0 
    weight_minimax = 3.0 
    weight_bloodlust = 2.0 
    
    best_moves = []
    best_score = float('-inf')
    
    for dir_name, next_pos in valid_moves.items():
        board[next_pos] = -1 
        
        is_safe = not get_danger_level(next_pos, enemy_heads)
        if not is_safe and len(valid_moves) > 1:
            del board[next_pos]
            continue
            
        chamber_size = get_chamber_size(next_pos, board, grid_dim, limit=100)
        territory = calculate_voronoi(next_pos, enemy_heads, board, grid_dim)
        obstacles = count_adjacent_obstacles(next_pos, board, grid_dim)
        
        prediction_penalty = weight_prediction_penalty if next_pos in predicted_enemy_moves else 0
        
        # Look 3 steps ahead
        future_score = minimax(next_pos, closest_enemy, board, grid_dim, depth=3, is_maximizing=False)
        
        bloodlust_bonus = 0
        if closest_enemy and future_score > 0:
            dist_to_enemy = abs(next_pos[0] - closest_enemy[0]) + abs(next_pos[1] - closest_enemy[1])
            bloodlust_bonus = -dist_to_enemy * weight_bloodlust 
            
        del board[next_pos] 
        
        move_score = (chamber_size * weight_chamber) + \
                     (territory * weight_voronoi) + \
                     (obstacles * weight_obstacles) + \
                     (future_score * weight_minimax) + \
                     bloodlust_bonus - \
                     prediction_penalty
                     
        if move_score > best_score:
            best_score = move_score
            best_moves = [dir_name]
        elif move_score == best_score:
            best_moves.append(dir_name)
                
    return random.choice(best_moves) if best_moves else list(valid_moves.keys())[0]