import random

team_name = "BEZE"

def get_flood_fill_count(start_pos, board, grid_dim, max_depth=60):
    """Deep scan to find the move that provides the most total future territory."""
    nodes = [start_pos]
    visited = {start_pos}
    count = 0
    while nodes and count < max_depth:
        curr = nodes.pop(0)
        count += 1
        x, y = curr
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = x + dx, y + dy
            if (0 <= nx < grid_dim and 0 <= ny < grid_dim and 
                (nx, ny) not in board and (nx, ny) not in visited):
                visited.add((nx, ny))
                nodes.append((nx, ny))
    return count

def get_line_length(pos, direction, board, grid_dim):
    """Calculates how far BEZE can sweep in one direction before hitting something."""
    dx, dy = direction
    x, y = pos
    length = 0
    while True:
        x += dx
        y += dy
        if 0 <= x < grid_dim and 0 <= y < grid_dim and (x, y) not in board:
            length += 1
        else:
            break
    return length

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    dirs = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
    
    legal_moves = {name: (x+dx, y+dy) for name, (dx, dy) in dirs.items() 
                   if 0 <= x+dx < grid_dim and 0 <= y+dy < grid_dim and (x+dx, y+dy) not in board}

    if not legal_moves:
        return "UP"

    scored_moves = []
    for move_name, npos in legal_moves.items():
        score = 0
        
        # 1. MIN-MAX SPACE (Deep Flood Fill)
        # We look much further ahead (60 spots) to see which move secures the biggest 'room'
        space_available = get_flood_fill_count(npos, board, grid_dim)
        if space_available < 15:
            score -= 20000 # Hard avoid for small pockets
        else:
            score += space_available * 100

        # 2. LONG SWEEP LOGIC
        # Reward moves that maintain a straight 'sweep' for as long as possible
        sweep_dist = get_line_length(my_pos, dirs[move_name], board, grid_dim)
        score += sweep_dist * 50

        # 3. HYPER-AGGRESSION (Lead Pursuit)
        for p in players:
            if p['alive'] and p['pos'] != my_pos:
                ex, ey = p['pos']
                # Predict where they are going
                dist_to_enemy = abs(npos[0] - ex) + abs(npos[1] - ey)
                if dist_to_enemy < 8:
                    # If close, prioritize cutting them off over sweeping
                    score += (grid_dim - dist_to_enemy) * 80

        # 4. ZIPPERING (Wall Affinity)
        # To make the sweep 'clean', stay close to an edge or trail
        adj_blocks = sum(1 for dx, dy in dirs.values() 
                         if (npos[0]+dx, npos[1]+dy) in board or 
                         not (0 <= npos[0]+dx < grid_dim and 0 <= npos[1]+dy < grid_dim))
        score += adj_blocks * 40

        scored_moves.append((score, move_name))

    scored_moves.sort(key=lambda x: x[0], reverse=True)
    return scored_moves[0][1]