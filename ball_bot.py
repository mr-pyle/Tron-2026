team_name = "Ball"

from collections import deque

DIRECTIONS = {
    "UP": (0, -1),
    "DOWN": (0, 1),
    "LEFT": (-1, 0),
    "RIGHT": (1, 0),
}


def move(my_pos, board, grid_dim, players):
    my_player = None
    for p in players:
        if p.get("alive", True) and p["pos"] == my_pos:
            my_player = p
            break

    current_dir = get_current_direction(my_player)

    safe_moves = []
    for direction, (dx, dy) in DIRECTIONS.items():
        nx, ny = my_pos[0] + dx, my_pos[1] + dy
        if is_safe((nx, ny), board, grid_dim):
            safe_moves.append(direction)

    if not safe_moves:
        return "UP"

    # Emergency rule: if only one safe move, take it.
    if len(safe_moves) == 1:
        return safe_moves[0]

    opponent_heads = [
        p["pos"]
        for p in players
        if p.get("alive", True) and p["pos"] != my_pos
    ]

    center = (grid_dim // 2, grid_dim // 2)

    best_move = None
    best_score = float("-inf")

    for direction in safe_moves:
        dx, dy = DIRECTIONS[direction]
        next_pos = (my_pos[0] + dx, my_pos[1] + dy)

        score = 0.0

        # 1. Main feature: Voronoi reachability (replaces basic flood fill)
        reachable = voronoi_space(next_pos, opponent_heads, board, grid_dim, limit=600)
        score += reachable * 12.0

        # 2. Prefer positions with more immediate exits
        exits = count_safe_neighbors(next_pos, board, grid_dim)
        score += exits * 25.0

        # 3. Slightly prefer continuing straight for stability
        if current_dir and direction == current_dir:
            score += 8.0

        # 4. Avoid hugging the exact wall too hard unless it gives space
        wall_dist = distance_to_nearest_wall(next_pos, grid_dim)
        score += min(wall_dist, 4) * 3.0

        # 5. Early/mid-game: mild center preference
        center_dist = manhattan(next_pos, center)
        score -= center_dist * 0.8

        # 6. Avoid moving too close to opponents if space is tight
        if opponent_heads:
            nearest_enemy = min(manhattan(next_pos, e) for e in opponent_heads)
            score += min(nearest_enemy, 6) * 4.0

        # 7. Penalize "corridor" cells that are likely trap entrances
        if exits <= 1:
            score -= 80.0
        elif exits == 2:
            score -= 10.0

        # 8. LOOKAHEAD: Simulate making the move to see next turn's options
        my_id = my_player.get("id", 999) if my_player else 999
        board[next_pos] = my_id  # Temporarily add our hypothetical move to the board
        
        future_safe_moves = 0
        for fx, fy in DIRECTIONS.values():
            future_pos = (next_pos[0] + fx, next_pos[1] + fy)
            if is_safe(future_pos, board, grid_dim):
                future_safe_moves += 1
                
        # Heavy penalties for moves that lead to dead-ends next turn
        if future_safe_moves == 0:
            score -= 1000.0  # Immediate death next turn!
        elif future_safe_moves == 1:
            score -= 50.0    # Forced into a corner
        else:
            score += future_safe_moves * 5.0 # Keep options open
            
        del board[next_pos] # Clean up our simulation so it doesn't break other directions

        # 9. Tiny tie-breaker for deterministic preference
        score += direction_tiebreak(direction)

        if score > best_score:
            best_score = score
            best_move = direction

    return best_move if best_move else safe_moves[0]


def get_current_direction(my_player):
    if not my_player:
        return None

    trail = my_player.get("trail", [])
    if len(trail) < 2:
        return None

    x1, y1 = trail[-2]
    x2, y2 = trail[-1]

    if x2 > x1:
        return "RIGHT"
    if x2 < x1:
        return "LEFT"
    if y2 > y1:
        return "DOWN"
    if y2 < y1:
        return "UP"
    return None


def is_safe(pos, board, grid_dim):
    x, y = pos
    return 0 <= x < grid_dim and 0 <= y < grid_dim and pos not in board


def count_safe_neighbors(pos, board, grid_dim):
    count = 0
    x, y = pos
    for dx, dy in DIRECTIONS.values():
        nxt = (x + dx, y + dy)
        if is_safe(nxt, board, grid_dim):
            count += 1
    return count


def voronoi_space(start_pos, opponent_heads, board, grid_dim, limit=600):
    """
    Simultaneous BFS. Calculates how many cells 'start_pos' can reach 
    STRICTLY BEFORE any opponent can reach them.
    """
    if not is_safe(start_pos, board, grid_dim):
        return 0
        
    q = deque()
    seen = {}
    
    # Add my start position (owner 0)
    q.append((start_pos, 0))
    seen[start_pos] = 0
    
    # Add enemy positions (owner 1)
    for enemy in opponent_heads:
        if is_safe(enemy, board, grid_dim):
            q.append((enemy, 1))
            seen[enemy] = 1
            
    my_territory = 0
    total_processed = 0
    
    while q and total_processed < limit:
        curr_pos, owner = q.popleft()
        total_processed += 1
        
        # If this cell belongs to us, count it
        if owner == 0:
            my_territory += 1
            
        x, y = curr_pos
        for dx, dy in DIRECTIONS.values():
            nxt = (x + dx, y + dy)
            if is_safe(nxt, board, grid_dim) and nxt not in seen:
                # Claim the square for whoever reached it first
                seen[nxt] = owner
                q.append((nxt, owner))
                
    return my_territory


def distance_to_nearest_wall(pos, grid_dim):
    x, y = pos
    return min(x, y, grid_dim - 1 - x, grid_dim - 1 - y)


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def direction_tiebreak(direction):
    order = {
        "UP": 0.03,
        "LEFT": 0.02,
        "RIGHT": 0.01,
        "DOWN": 0.00,
    }
    return order.get(direction, 0.0)