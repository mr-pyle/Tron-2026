from collections import deque

team_name = "Better_Coward"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    
    # Define all possible directions and their coordinate changes
    directions = {
        "UP": (x, y - 1),
        "DOWN": (x, y + 1),
        "LEFT": (x - 1, y),
        "RIGHT": (x + 1, y)
    }
    
    best_move = "UP" # Default fallback
    max_space = -1
    
    # Evaluate each possible direction
    for direction, (nx, ny) in directions.items():
        # Check if the immediate next step is safe (within bounds and not a wall/trail)
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
            
            # Run a Flood Fill to see how much space this path leads to
            space_available = get_reachable_space((nx, ny), board, grid_dim)
            
            # If this direction offers more space than our previous best, update it
            if space_available > max_space:
                max_space = space_available
                best_move = direction
                
    return best_move

def get_reachable_space(start_pos, board, grid_dim, max_depth=400):
    """
    Uses Breadth-First Search (BFS) to count how many contiguous empty 
    cells are accessible from the starting position.
    """
    queue = deque([start_pos])
    visited = {start_pos}
    count = 0
    
    # Run the search until we run out of cells or hit our search limit
    while queue and count < max_depth:
        curr_x, curr_y = queue.popleft()
        count += 1
        
        # Check all 4 neighbors of the current cell
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            nx, ny = curr_x + dx, curr_y + dy
            
            # If the neighbor is inside the grid, not on the board, and hasn't been counted yet
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim:
                if (nx, ny) not in board and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
                    
    return count