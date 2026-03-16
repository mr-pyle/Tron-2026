
import random

def move(my_pos, board, dim, players):
    x, y = my_pos
    
    # --- 1. DEFINE SURVIVAL SCANNER ---
    def get_reach(start_pos, current_board, depth=100):
        queue = [start_pos]
        visited = {start_pos}
        count = 0
        while queue and count < depth:
            cx, cy = queue.pop(0)
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if (0 <= nx < dim and 0 <= ny < dim and 
                    (nx, ny) not in current_board and (nx, ny) not in visited):
                    visited.add((nx, ny))
                    queue.append((nx, ny))
                    count += 1
        return count

    # --- 2. TARGETING LOGIC (The Drill) ---
    # Find the opponent with the most "claimed" territory and target their path
    target_pos = None
    for p in players:
        if p['alive'] and p['pos'] != my_pos:
            # We don't just target the head; we target the empty space 
            # 2 steps in front of their head (predictive drilling)
            tx, ty = p['pos']
            # Determine their momentum to guess where they are "drilling"
            if len(p['trail']) >= 2:
                lx, ly = p['trail'][-2]
                dx, dy = tx - lx, ty - ly
                target_pos = (tx + dx*2, ty + dy*2)
            else:
                target_pos = (tx, ty)
            break

    # --- 3. EVALUATE MOVES ---
    directions = {"UP": (x, y-1), "DOWN": (x, y+1), "LEFT": (x-1, y), "RIGHT": (x+1, y)}
    move_scores = []

    for d, (nx, ny) in directions.items():
        if 0 <= nx < dim and 0 <= ny < dim and (nx, ny) not in board:
            # Base survival: How much room is behind this door?
            space = get_reach((nx, ny), board)
            
            # Hunting component: How close does this move get us to the "Drill Point"?
            dist_to_target = 0
            if target_pos:
                dist_to_target = abs(nx - target_pos[0]) + abs(ny - target_pos[1])
            
            # The Formula: Space is life, but proximity is the kill.
            # We subtract distance so that lower distance = higher score.
            # We weigh space heavily (x2) so we don't kamikaze into a wall.
            score = (space * 2) - dist_to_target
            move_scores.append((d, score, space))

    # --- 4. THE FAIL-SAFE ---
    if not move_scores:
        return "UP"

    # Sort by the calculated score
    move_scores.sort(key=lambda x: x[1], reverse=True)
    
    # "Drilling" Check: If our best move has very little space (e.g., < 10), 
    # abandon the hunt and search for the maximum possible survival space.
    if move_scores[0][2] < 15:
        move_scores.sort(key=lambda x: x[2], reverse=True)

    return move_scores[0][0]