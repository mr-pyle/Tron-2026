import random
from collections import deque

team_name = "Ali"

DIRS = {
    "UP": (0, -1),
    "DOWN": (0, 1),
    "LEFT": (-1, 0),
    "RIGHT": (1, 0)
}

def in_bounds(x, y, grid_dim):
    return 0 <= x < grid_dim and 0 <= y < grid_dim


def flood_fill(start, board, grid_dim, limit=800):
    q = deque([start])
    visited = {start}
    count = 0

    while q and count < limit:
        x, y = q.popleft()
        count += 1

        for dx, dy in DIRS.values():
            nx, ny = x + dx, y + dy
            pos = (nx, ny)

            if in_bounds(nx, ny, grid_dim) and pos not in board and pos not in visited:
                visited.add(pos)
                q.append(pos)

    return count


def nearest_enemy_distance(pos, players, my_pos):
    px, py = pos
    best = 9999

    for p in players:
        if not p.get("alive", False):
            continue

        if p["pos"] == my_pos:
            continue

        ex, ey = p["pos"]
        d = abs(px - ex) + abs(py - ey)

        best = min(best, d)

    return best


def move(my_pos, board, grid_dim, players):

    x, y = my_pos

    best_move = None
    best_score = -999999

    for direction, (dx, dy) in DIRS.items():

        nx = x + dx
        ny = y + dy
        new_pos = (nx, ny)

        if not in_bounds(nx, ny, grid_dim) or new_pos in board:
            continue

        temp_board = board.copy()
        temp_board[new_pos] = -1

        # Territory control
        space = flood_fill(new_pos, temp_board, grid_dim)

        # Distance from enemies
        enemy_dist = nearest_enemy_distance(new_pos, players, my_pos)

        # Center control
        center = grid_dim // 2
        center_score = 15 - (abs(nx - center) + abs(ny - center))

        score = (
            space * 6 +
            enemy_dist * 4 +
            center_score
        )

        if score > best_score:
            best_score = score
            best_move = direction

    if best_move:
        return best_move

    safe = []

    for d, (dx, dy) in DIRS.items():
        nx = x + dx
        ny = y + dy

        if in_bounds(nx, ny, grid_dim) and (nx, ny) not in board:
            safe.append(d)

    if safe:
        return random.choice(safe)

    return "UP"