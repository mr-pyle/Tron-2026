import random

def move(my_pos, board, dim, players):
    x, y = my_pos
    
    # --- 1. SENSE THE DANGER (Flood Fill) ---
    def get_reach(start_pos, current_board, limit=150):
        """Calculates exactly how many squares are reachable from a position."""
        queue = [start_pos]
        visited = {start_pos}
        count = 0
        while queue and count < limit:
            cx, cy = queue.pop(0)
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if (0 <= nx < dim and 0 <= ny < dim and 
                    (nx, ny) not in current_board and (nx, ny) not in visited):
                    visited.add((nx, ny))
                    queue.append((nx, ny))
                    count += 1
        return count

    # --- 2. DEFINE THE IDEAL SPIRAL ---
    # Determine current direction to maintain clockwise momentum
    my_trail = next((p['trail'] for p in players if p['pos'] == my_pos), [])
    current_dir = "UP"
    if len(my_trail) >= 2:
        lx, ly = my_trail[-2]
        if x > lx: current_dir = "RIGHT"
        elif x < lx: current_dir = "LEFT"
        elif y > ly: current_dir = "DOWN"
        elif y < ly: current_dir = "UP"

    directions = ["UP", "RIGHT", "DOWN", "LEFT"]
    idx = directions.index(current_dir)
    # Clockwise Priority: Turn Right, then Straight, then Left
    spiral_priority = [directions[(idx + 1) % 4], directions[idx], directions[(idx - 1) % 4]]

    # --- 3. EVALUATE ALL MOVES ---
    move_evals = []
    for d in ["UP", "DOWN", "LEFT", "RIGHT"]:
        nx, ny = x, y
        if d == "UP": ny -= 1
        elif d == "DOWN": ny += 1
        elif d == "LEFT": nx -= 1
        elif d == "RIGHT": nx += 1
        
        if 0 <= nx < dim and 0 <= ny < dim and (nx, ny) not in board:
            # Score this move based on reachable space
            space = get_reach((nx, ny), board)
            
            # Bonus points if the move follows the spiral pattern
            spiral_bonus = 0
            if d == spiral_priority[0]: spiral_bonus = 15 # Turning right is best
            elif d == spiral_priority[1]: spiral_bonus = 10 # Going straight is okay
            
            move_evals.append({
                'dir': d,
                'space': space,
                'score': space + spiral_bonus
            })

    # --- 4. EXECUTE THE SURVIVAL CHOICE ---
    if not move_evals:
        return "UP" # GG

    # Sort primarily by space (survival) and secondarily by spiral score
    # This ensures we NEVER take a spiral turn if it leads to a smaller pocket
    move_evals.sort(key=lambda m: (m['space'], m['score']), reverse=True)
    
    # If the best space option is significantly better than the spiral option,
    # abandon the spiral immediately to avoid being boxed in.
    return move_evals[0]['dir']