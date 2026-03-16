import collections

team_name = "Bot Thing"

def get_safe_moves(pos, board, grid_dim):
    """Returns a list of safe neighboring coordinates."""
    x, y = pos
    safe_moves = []
    directions = [(x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y)]
    
    for nx, ny in directions:
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim:
            if (nx, ny) not in board:
                safe_moves.append((nx, ny))
    return safe_moves

def flood_fill(start_pos, board, grid_dim):
    """Calculates the total number of reachable empty cells from a starting position."""
    visited = set()
    queue = collections.deque([start_pos])
    visited.add(start_pos)
    
    reachable_count = 0
    
    while queue:
        current_pos = queue.popleft()
        reachable_count += 1
        
        # Get neighbors of the current position
        neighbors = get_safe_moves(current_pos, board, grid_dim)
        
        for neighbor in neighbors:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)
                
    return reachable_count

def move(pos, board, grid_dim, players):
    """
    Evaluates all possible immediate moves and chooses the one 
    that leads to the largest contiguous open area.
    """
    x, y = pos
    
    # Define the 4 cardinal directions and their coordinate changes
    directions = {
        "UP": (x, y - 1),
        "DOWN": (x, y + 1),
        "LEFT": (x - 1, y),
        "RIGHT": (x + 1, y)
    }
    
    best_move = "UP" # Default fallback
    max_area = -1
    
    for direction_name, next_pos in directions.items():
        nx, ny = next_pos
        
        # Check if the immediate move is valid
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and next_pos not in board:
            
            # Simulate making this move by temporarily adding it to the board
            simulated_board = board.copy()
            simulated_board[next_pos] = "simulated_me"
            
            # Calculate the open area available from this new position
            area = flood_fill(next_pos, simulated_board, grid_dim)
            
            # If this direction offers more area than our previous best, update it
            if area > max_area:
                max_area = area
                best_move = direction_name
                
    return best_move