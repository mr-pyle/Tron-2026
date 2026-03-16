import random
from collections import deque

team_name = "Voronoi Hunter"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    
    # 1. Define directions
    directions = {
        "UP": (x, y - 1),
        "DOWN": (x, y + 1),
        "LEFT": (x - 1, y),
        "RIGHT": (x + 1, y)
    }

    # 2. Identify alive enemies
    enemies = [p['pos'] for p in players if p['pos'] != my_pos and p['alive']]
    
    # 3. Find immediate safe moves
    valid_moves = {}
    for d_name, (nx, ny) in directions.items():
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
            valid_moves[d_name] = (nx, ny)

    if not valid_moves:
        return "UP" # Die with dignity

    best_move = None
    max_territory = -1
    min_enemy_dist = float('inf')

    # 4. Evaluate each valid move using Voronoi Territory + Aggression
    for d_name, new_pos in valid_moves.items():
        # Simulate the board with our new move added
        sim_board = set(board.keys()) 
        sim_board.add(new_pos)
        
        # Calculate how much territory we own if we make this move
        my_territory = calculate_voronoi(new_pos, enemies, sim_board, grid_dim)
        
        # Calculate Manhattan distance to the nearest enemy for aggression
        if enemies:
            enemy_dist = min([abs(new_pos[0]-ex) + abs(new_pos[1]-ey) for ex, ey in enemies])
        else:
            enemy_dist = float('inf')

        # Evaluate the results
        if my_territory > max_territory:
            max_territory = my_territory
            min_enemy_dist = enemy_dist
            best_move = d_name
        elif my_territory == max_territory:
            # AGGRESSIVE CUT-OFF: If territory is tied, move closer to the enemy to crowd them out!
            if enemy_dist < min_enemy_dist:
                min_enemy_dist = enemy_dist
                best_move = d_name

    return best_move if best_move else random.choice(list(valid_moves.keys()))

def calculate_voronoi(my_pos, enemies, board, grid_dim):
    """
    Multi-source Breadth-First Search to calculate Voronoi territory.
    Returns the number of empty cells 'my_pos' can reach before any enemy.
    """
    queue = deque()
    visited = {} # Format: { position: (distance, owner_id) }
    
    # owner_id: 0 means me, 1 means an enemy
    queue.append((my_pos, 0, 0))
    visited[my_pos] = (0, 0)
    
    for e_pos in enemies:
        queue.append((e_pos, 0, 1))
        visited[e_pos] = (0, 1)

    my_cell_count = 0

    while queue:
        curr_pos, dist, owner = queue.popleft()
        
        if owner == 0:
            my_cell_count += 1

        cx, cy = curr_pos
        neighbors = [
            (cx, cy - 1), (cx, cy + 1), 
            (cx - 1, cy), (cx + 1, cy)
        ]

        for nx, ny in neighbors:
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
                if (nx, ny) not in visited:
                    visited[(nx, ny)] = (dist + 1, owner)
                    queue.append(((nx, ny), dist + 1, owner))
                    
    return my_cell_count