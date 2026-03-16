import random

def move(my_pos, board, dim, players):
    x, y = my_pos

    def get_space(start_pos, current_board, limit=60):
        queue, visited, count = [start_pos], {start_pos}, 0
        while queue and count < limit:
            cx, cy = queue.pop(0)
            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < dim and 0 <= ny < dim and (nx, ny) not in current_board and (nx, ny) not in visited:
                    visited.add((nx, ny)); queue.append((nx, ny)); count += 1
        return count

    # 1. EVALUATE MOVES
    directions = {"UP": (x, y-1), "DOWN": (x, y+1), "LEFT": (x-1, y), "RIGHT": (x+1, y)}
    move_options = []
    
    # Identify nearby threats
    threats = []
    for p in players:
        if p['alive'] and p['pos'] != my_pos:
            tx, ty = p['pos']
            dist = abs(x - tx) + abs(y - ty)
            if dist < 8: # Only care about bots within 8 squares
                threats.append(p['pos'])

    for d, (nx, ny) in directions.items():
        if 0 <= nx < dim and 0 <= ny < dim and (nx, ny) not in board:
            space = get_space((nx, ny), board)
            
            # Distance to the average position of nearby threats
            threat_dist = 0
            if threats:
                avg_tx = sum(t[0] for t in threats) / len(threats)
                avg_ty = sum(t[1] for t in threats) / len(threats)
                threat_dist = abs(nx - avg_tx) + abs(ny - avg_ty)
            
            move_options.append({'dir': d, 'space': space, 'threat_dist': threat_dist})

    if not move_options:
        return "UP"

    # 2. THE SPLATTER LOGIC
    # Check if we are "trapped" (less than 10 squares of life left)
    move_options.sort(key=lambda m: m['space'], reverse=True)
    if move_options[0]['space'] < 12:
        # TRIGGER EXPLOSION: Prioritize moving TOWARD the center of the enemy cluster
        # while taking the move that turns the most (to create a jagged trail).
        # This turns your final trail into a 'shrapnel' wall.
        move_options.sort(key=lambda m: m['threat_dist'])
        return move_options[0]['dir']
    
    # 3. NORMAL HUNTING MODE
    # If we have space, be aggressive but stay in the roomiest areas.
    move_options.sort(key=lambda m: (m['space'] > 20, -m['threat_dist']), reverse=True)
    return move_options[0]['dir']