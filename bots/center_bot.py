team_name = "Centrist"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    center = grid_dim // 2
    
    # Preferred directions to get to center
    preferred = []
    if x < center: preferred.append("RIGHT")
    else: preferred.append("LEFT")
    if y < center: preferred.append("DOWN")
    else: preferred.append("UP")
        
    for p in preferred:
        # Simple check if path is clear
        nx, ny = my_pos # (Logic to check neighbor omitted for brevity)
        # ... logic to check if (nx, ny) in board ...
        return p
    return "UP"