import random

team_name = "monster"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    directions = {"UP": (x, y - 1), "DOWN": (x, y + 1), "LEFT": (x - 1, y), "RIGHT": (x + 1, y)}
    enemies = [p['pos'] for p in players if p['alive'] and p['pos'] != my_pos]

    def get_valid_neighbors(pos, current_board):
        """Returns adjacent tiles that are inside the grid and not blocked."""
        valid = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = pos[0] + dx, pos[1] + dy
            if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in current_board:
                valid.append((nx, ny))
        return valid

    def get_chamber_size(start_pos, current_board, limit=500):
        """
        Calculates the ABSOLUTE size of the closed-off area this move leads to.
        This prevents the bot from ever walking into a small, dead-end trap.
        """
        queue = [start_pos]
        visited = {start_pos}
        while queue and len(visited) < limit:
            curr = queue.pop(0)
            for n in get_valid_neighbors(curr, current_board):
                if n not in visited:
                    visited.add(n)
                    queue.append(n)
        return len(visited)

    def get_voronoi_territory(start_pos, current_board):
        """
        Calculates how much of the open space we can reach BEFORE the enemy.
        """
        queue = [(start_pos, 0, True)]
        for e in enemies:
            queue.append((e, 0, False))
        
        visited = {start_pos} | set(enemies)
        my_tiles = 0
        
        while queue:
            curr, dist, is_me = queue.pop(0)
            if dist > 30: continue # Cap the search depth for performance
            
            for n in get_valid_neighbors(curr, current_board):
                if n not in visited:
                    visited.add(n)
                    queue.append((n, dist + 1, is_me))
                    if is_me:
                        my_tiles += 1
        return my_tiles

    scored_moves = []
    for move_dir, n_pos in directions.items():
        if 0 <= n_pos[0] < grid_dim and 0 <= n_pos[1] < grid_dim and n_pos not in board:
            
            # 1. Survival: How big is the box we are entering?
            chamber_size = get_chamber_size(n_pos, board)
            
            # 2. Dominance: How much of that box belongs to us?
            territory = get_voronoi_territory(n_pos, board)
            
            # 3. Compactness: How many walls/trails are we touching? 
            # (Higher is better for late-game space-filling)
            adjacent_obstacles = 4 - len(get_valid_neighbors(n_pos, board))
            
            # SCORING HIERARCHY:
            # Chamber size is weighted massively (1000x) so we never choose a smaller trap.
            # Territory decides ties between equally large chambers.
            # Obstacles force the bot to hug walls and coil tightly.
            score = (chamber_size * 1000) + (territory * 10) + adjacent_obstacles
            
            scored_moves.append({'dir': move_dir, 'score': score})

    if not scored_moves:
        return "UP"

    # Execute the mathematically optimal move
    scored_moves.sort(key=lambda m: m['score'], reverse=True)
    return scored_moves[0]['dir']