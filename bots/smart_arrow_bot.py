import random

team_name = "SmartArrow"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    
    # Define all possible directions and their coordinate changes
    directions = {
        "UP": (x, y - 1),
        "DOWN": (x, y + 1),
        "LEFT": (x - 1, y),
        "RIGHT": (x + 1, y)
    }

    # 1. Figure out current direction by looking at the trail
    # Find our own player data in the players list
    my_data = next(p for p in players if p['pos'] == my_pos)
    current_dir = None
    if len(my_data['trail']) > 1:
        last_pos = my_data['trail'][-2]
        if x > last_pos[0]: current_dir = "RIGHT"
        elif x < last_pos[0]: current_dir = "LEFT"
        elif y > last_pos[1]: current_dir = "DOWN"
        elif y < last_pos[1]: current_dir = "UP"

    # 2. Check if staying the course is safe
    if current_dir:
        nx, ny = directions[current_dir]
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
            return current_dir

    # 3. If not safe (or first move), find ANY safe move
    safe_moves = []
    for move_dir, (nx, ny) in directions.items():
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
            safe_moves.append(move_dir)

    if safe_moves:
        return random.choice(safe_moves)
    
    return "UP" # Nowhere to go