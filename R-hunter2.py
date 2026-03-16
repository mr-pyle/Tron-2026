import random

def move(my_pos, board, dim, players):
    x, y = my_pos
    
    def get_space(start_pos, current_board, limit=100):
        queue, visited, count = [start_pos], {start_pos}, 0
        while queue and count < limit:
            cx, cy = queue.pop(0)
            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < dim and 0 <= ny < dim and (nx, ny) not in current_board and (nx, ny) not in visited:
                    visited.add((nx, ny)); queue.append((nx, ny)); count += 1
        return count

    # 1. SCAN FOR TARGETS
    target = None
    closest_dist = float('inf')
    for p in players:
        if p['alive'] and p['pos'] != my_pos:
            tx, ty = p['pos']
            dist = abs(x - tx) + abs(y - ty)
            if dist < closest_dist:
                closest_dist = dist; target = p

    # 2. EVALUATE MOVES
    directions = {"UP": (x, y-1), "DOWN": (x, y+1), "LEFT": (x-1, y), "RIGHT": (x+1, y)}
    move_options = []
    
    for d, (nx, ny) in directions.items():
        if 0 <= nx < dim and 0 <= ny < dim and (nx, ny) not in board:
            space = get_space((nx, ny), board)
            dist_to_enemy = abs(nx - target['pos'][0]) + abs(ny - target['pos'][1]) if target else 0
            move_options.append({'dir': d, 'space': space, 'dist': dist_to_enemy})

    # 3. THE "EXPLOSION" LOGIC
    # If no move has more than 3 squares of space, we are dying. 
    # Switch to "Explode" mode: move as close to the enemy head as possible to block them.
    is_dying = all(m['space'] < 5 for m in move_options) if move_options else True

    if move_options:
        if is_dying and target:
            # KAMIKAZE: Pick the move that is closest to the enemy, regardless of space.
            move_options.sort(key=lambda m: m['dist'])
        else:
            # STANDARD HUNT: Weight space and distance.
            move_options.sort(key=lambda m: (m['space'] > 15, -m['dist']), reverse=True)
        
        return move_options[0]['dir']

    return "UP" # Fatal crash