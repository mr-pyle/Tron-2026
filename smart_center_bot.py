team_name = "SmartCenter"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    center = grid_dim // 2
    
    directions = {
        "UP": (x, y - 1),
        "DOWN": (x, y + 1),
        "LEFT": (x - 1, y),
        "RIGHT": (x + 1, y)
    }

    # 1. Rank moves by how much they decrease distance to center (x=center, y=center)
    def get_dist_to_center(pos):
        return abs(pos[0] - center) + abs(pos[1] - center)

    # Sort moves: closest to center first
    ranked_moves = sorted(directions.keys(), 
                          key=lambda d: get_dist_to_center(directions[d]))

    # 2. Pick the highest ranked move that is SAFE
    for move_dir in ranked_moves:
        nx, ny = directions[move_dir]
        # Check walls AND the board (which contains all trails)
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
            return move_dir

    # 3. If no moves are safe, just try to go UP (death is imminent)
    return "UP"