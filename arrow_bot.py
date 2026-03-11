import random

team_name = "StraightArrow"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    # Check current direction (logic to determine what direction we were facing)
    # For simplicity, let's just find ANY open neighbor
    options = {
        "UP": (x, y-1),
        "DOWN": (x, y+1),
        "LEFT": (x-1, y),
        "RIGHT": (x+1, y)
    }
    
    valid_moves = []
    for move, (nx, ny) in options.items():
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
            valid_moves.append(move)
            
    if not valid_moves:
        return "UP" # Die with dignity
    return random.choice(valid_moves)