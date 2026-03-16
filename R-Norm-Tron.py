import random

def move(my_pos, board, dim, players):
    x, y = my_pos
    directions = {
        "UP": (x, y - 1),
        "DOWN": (x, y + 1),
        "LEFT": (x - 1, y),
        "RIGHT": (x + 1, y)
    }

    def get_space_count(start_pos, current_board):
        """Simple BFS to count reachable squares."""
        queue = [start_pos]
        visited = set()
        visited.add(start_pos)
        count = 0
        
        # We limit the search depth to 100 to keep the bot within the 0.1s time limit
        max_search = 100 
        
        while queue and count < max_search:
            curr = queue.pop(0)
            cx, cy = curr
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = cx + dx, cy + dy
                if (0 <= nx < dim and 0 <= ny < dim and 
                    (nx, ny) not in current_board and 
                    (nx, ny) not in visited):
                    visited.add((nx, ny))
                    queue.append((nx, ny))
                    count += 1
        return count

    best_move = "UP"
    max_space = -1
    
    # Analyze all possible moves
    possible_moves = []
    for move_dir, (nx, ny) in directions.items():
        if 0 <= nx < dim and 0 <= ny < dim and (nx, ny) not in board:
            # The "Gamble": Calculate space available if we take this move
            space = get_space_count((nx, ny), board)
            possible_moves.append((move_dir, space, (nx, ny)))

    if not possible_moves:
        return "UP"

    # Sort moves by space available
    possible_moves.sort(key=lambda x: x[1], reverse=True)
    
    # 1. Primary Goal: Survival (Max Space)
    best_move = possible_moves[0][0]
    best_space = possible_moves[0][1]

    # 2. The Winning Edge: If multiple moves offer similar space,
    # pick the one that moves toward the opponent (to cut them off).
    if len(possible_moves) > 1 and possible_moves[0][1] == possible_moves[1][1]:
        closest_dist = float('inf')
        for p in players:
            if p['alive'] and p['pos'] != my_pos:
                ox, oy = p['pos']
                for move_dir, space, (nx, ny) in possible_moves:
                    if space == best_space:
                        dist = abs(nx - ox) + abs(ny - oy)
                        if dist < closest_dist:
                            closest_dist = dist
                            best_move = move_dir

    return best_move