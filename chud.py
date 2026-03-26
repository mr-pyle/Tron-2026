import random

team_name = "Analiese Bot"

def get_neighbors(pos):
    x, y = pos
    return {"UP": (x, y - 1), "DOWN": (x, y + 1), "LEFT": (x - 1, y), "RIGHT": (x + 1, y)}

def is_valid(pos, board, grid_dim):
    x, y = pos
    return 0 <= x < grid_dim and 0 <= y < grid_dim and pos not in board

def get_chamber_info(start_pos, board, grid_dim, enemies, limit=500):
    """
    Returns (reachable_count, is_isolated).
    If no enemies are reachable within the chamber, is_isolated is True.
    """
    if not is_valid(start_pos, board, grid_dim):
        return 0, False
    
    queue = [(start_pos, 0)]
    visited = {start_pos}
    enemies_found = False
    
    while queue and len(visited) < limit:
        curr, dist = queue.pop(0)
        
        # Check if an enemy head is in this reachable chamber
        if curr in enemies:
            enemies_found = True
            
        for _, n in get_neighbors(curr).items():
            if is_valid(n, board, grid_dim) and n not in visited:
                visited.add(n)
                queue.append((n, dist + 1))
                
    return len(visited), not enemies_found

def move(my_pos, board, grid_dim, players):
    neighbors = get_neighbors(my_pos)
    best_moves = []
    max_score = -float('inf')

    # Positions of all living enemies
    enemies = [p['pos'] for p in players if p['alive'] and p['pos'] != my_pos]

    for direction, next_pos in neighbors.items():
        if not is_valid(next_pos, board, grid_dim):
            continue

        # 1. Analyze the chamber we are moving into
        space_count, isolated = get_chamber_info(next_pos, board, grid_dim, enemies)
        
        # 2. Wall Hugging Logic (Crucial for space-filling)
        blocked_count = sum(1 for _, n in get_neighbors(next_pos).items() if not is_valid(n, board, grid_dim))
        
        # 3. Collision and Territory Logic
        danger_penalty = 0
        if not isolated:
            for ex, ey in enemies:
                d = abs(next_pos[0] - ex) + abs(next_pos[1] - ey)
                if d <= 2: danger_penalty = 300 # Extremely high to prevent ties
                elif d <= 3: danger_penalty = 100
        
        # 4. SCORING STRATEGY
        if isolated:
            # PANIC MODE: We are alone. Ignore enemies, just hug walls as tight as possible.
            # We prioritize wall-hugging (blocked_count) to 'spiral' into the space.
            total_score = (space_count * 100) + (blocked_count * 50)
        else:
            # COMBAT MODE: Space is king, but stay away from others.
            # We add a small center-bias early on to avoid getting cornered by bots.
            center_dist = abs(next_pos[0] - grid_dim/2) + abs(next_pos[1] - grid_dim/2)
            total_score = (space_count * 100) - danger_penalty + (blocked_count * 5) - (center_dist * 0.1)

        if total_score > max_score:
            max_score = total_score
            best_moves = [direction]
        elif total_score == max_score:
            best_moves.append(direction)

    return random.choice(best_moves) if best_moves else "UP"