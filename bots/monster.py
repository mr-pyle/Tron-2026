import random

team_name = "Overlord_v4"

def move(my_pos, board, grid_dim, players):
    x, y = my_pos
    directions = {"UP": (x, y - 1), "DOWN": (x, y + 1), "LEFT": (x - 1, y), "RIGHT": (x + 1, y)}
    enemies = [p['pos'] for p in players if p['alive'] and p['pos'] != my_pos]

    def get_advanced_score(start_pos, current_board, enemy_positions):
        """
        Combines Voronoi territory with a 'bottleneck' check.
        It penalizes moves that lead into areas with narrow exits.
        """
        mine = {start_pos}
        # Multi-agent BFS to find contested territory
        queue = [(start_pos, 0, True)]
        for e_pos in enemy_positions:
            queue.append((e_pos, 0, False))
        
        visited = {start_pos} | set(enemy_positions)
        my_territory = []
        
        while queue:
            (curr_x, curr_y), dist, is_me = queue.pop(0)
            if dist > 25: continue # Increased depth for long-range planning

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = curr_x + dx, curr_y + dy
                if (0 <= nx < grid_dim and 0 <= ny < grid_dim and 
                    (nx, ny) not in current_board and (nx, ny) not in visited):
                    visited.add((nx, ny))
                    queue.append(((nx, ny), dist + 1, is_me))
                    if is_me: my_territory.append((nx, ny))

        if not my_territory: return 0

        # BOTTLENECK CHECK: How many 'exit' options do we have in our territory?
        exit_count = 0
        for tx, ty in my_territory[:10]: # Check immediate future tiles
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                if (tx+dx, ty+dy) not in current_board and (tx+dx, ty+dy) not in my_territory:
                    exit_count += 1
        
        return len(my_territory) + (exit_count * 2)

    scored_moves = []
    for move_dir, (nx, ny) in directions.items():
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board:
            score = get_advanced_score((nx, ny), board, enemies)
            
            # Wall-hug only when space is abundant (early game)
            # If space is tight, ignore walls and fight for territory
            wall_dist = min(nx, ny, grid_dim - nx, grid_dim - ny)
            wall_bonus = 2.0 / (wall_dist + 1) if score > 50 else 0
            
            scored_moves.append({'dir': move_dir, 'score': score + wall_bonus})

    if not scored_moves: return "UP"

    scored_moves.sort(key=lambda m: m['score'], reverse=True)
    return scored_moves[0]['dir']