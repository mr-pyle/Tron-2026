import collections

team_name = "SmartHugger_v1"

def get_flood_fill_score(start_pos, board, grid_dim):
    """Counts how many empty tiles are reachable from a position."""
    queue = collections.deque([start_pos])
    visited = {start_pos}
    count = 0
    
    while queue:
        curr_x, curr_y = queue.popleft()
        count += 1
        # Limit search to 200 tiles to keep the bot fast for your GUI engine
        if count > 200: 
            break
            
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = curr_x + dx, curr_y + dy
            if (0 <= nx < grid_dim and 0 <= ny < grid_dim and 
                (nx, ny) not in board and (nx, ny) not in visited):
                visited.add((nx, ny))
                queue.append((nx, ny))
    return count

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    directions = {"UP": (x, y-1), "DOWN": (x, y+1), "LEFT": (x-1, y), "RIGHT": (x+1, y)}
    
    scored_moves = []

    for move_name, (nx, ny) in directions.items():
        # 1. Basic Collision Check
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
            
            # 2. Wall Hugging Score (How many obstacles are next to this new tile?)
            wall_score = 0
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nnx, nny = nx + dx, ny + dy
                if not (0 <= nnx < grid_dim and 0 <= nny < grid_dim) or (nnx, nny) in board:
                    wall_score += 1
            
            # 3. Flood Fill (How much total space is actually in this direction?)
            space_score = get_flood_fill_score((nx, ny), board, grid_dim)
            
            # STRATEGY: High space is mandatory, High wall_score is the tie-breaker
            # We use a large multiplier for space so we never pick a "wall" that leads to a trap
            total_score = (space_score * 10) + wall_score
            scored_moves.append((total_score, move_name))

    if not scored_moves:
        return "UP"

    # Pick the move with the best combined score
    scored_moves.sort(key=lambda x: x[0], reverse=True)
    return scored_moves[0][1]
