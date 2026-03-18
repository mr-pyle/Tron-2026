import collections
import random

team_name = "SpaceMaximizer"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    
    # Define all possible directions and their coordinate changes
    directions = {
        "UP": (x, y - 1),
        "DOWN": (x, y + 1),
        "LEFT": (x - 1, y),
        "RIGHT": (x + 1, y)
    }
    
    def count_available_space(start_pos):
        """
        Uses a Breadth-First Search (Flood Fill) to count how many 
        contiguous open squares are accessible from the given starting position.
        """
        queue = collections.deque([start_pos])
        visited = set([start_pos])
        space_count = 0
        
        # We limit the search depth so the bot doesn't freeze the game engine
        # 400 is plenty to make a smart decision in a 60x60 grid
        max_search_depth = 400 
        
        while queue and space_count < max_search_depth:
            curr_x, curr_y = queue.popleft()
            space_count += 1
            
            # Check all 4 surrounding squares from our current search position
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nx, ny = curr_x + dx, curr_y + dy
                
                # If the square is on the board, not in a trail, and not checked yet
                if 0 <= nx < grid_dim and 0 <= ny < grid_dim:
                    if (nx, ny) not in board and (nx, ny) not in visited:
                        visited.add((nx, ny))
                        queue.append((nx, ny))
                        
        return space_count

    best_moves = []
    max_space = -1
    
    # Evaluate every immediate safe neighbor
    for move_dir, (nx, ny) in directions.items():
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
            
            # Ask: "If I step here, how much room do I have left?"
            space_available = count_available_space((nx, ny))
            
            if space_available > max_space:
                max_space = space_available
                best_moves = [move_dir]
            elif space_available == max_space:
                best_moves.append(move_dir)
                
    # If we found safe moves, pick one of the best ones
    if best_moves:
        return random.choice(best_moves)
    
    # If no safe moves exist, we are trapped. Die with dignity.
    return "UP"