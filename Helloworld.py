# helloworld.py
# WallEater – designed to counter APEX v5 by wall-hugging + tight corridor filling
# Exploits APEX's articulation-guard conservatism and prediction failures

import random
from collections import deque

team_name = "HelloWorld"

prev_pos = None
current_dir = "RIGHT"

DIRECTIONS = {
    "UP":    (0, -1),
    "DOWN":  (0, 1),
    "LEFT":  (-1, 0),
    "RIGHT": (1, 0)
}

OPPOSITE = {"UP":"DOWN", "DOWN":"UP", "LEFT":"RIGHT", "RIGHT":"LEFT"}

# Prefer staying close to walls when possible
WALL_HUG_RULE = {
    "UP":    ["LEFT", "RIGHT", "UP", "DOWN"],     # prefer left/right along wall
    "RIGHT": ["UP", "DOWN", "RIGHT", "LEFT"],
    "DOWN":  ["RIGHT", "LEFT", "DOWN", "UP"],
    "LEFT":  ["DOWN", "UP", "LEFT", "RIGHT"]
}

def infer_direction(old, new):
    dx = new[0] - old[0]
    dy = new[1] - old[1]
    for d, (ddx, ddy) in DIRECTIONS.items():
        if (dx, dy) == (ddx, ddy):
            return d
    return current_dir

def is_safe(nx, ny, grid_dim, board):
    return 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board

def fast_flood(start, board, grid_dim, max_check=500):
    visited = set([start])
    q = deque([start])
    count = 1
    while q and count < max_check:
        cx, cy = q.popleft()
        for dx, dy in [(0,-1),(0,1),(-1,0),(1,0)]:
            nx, ny = cx + dx, cy + dy
            if is_safe(nx, ny, grid_dim, board) and (nx, ny) not in visited:
                visited.add((nx, ny))
                q.append((nx, ny))
                count += 1
                if count >= max_check:
                    return max_check + 2500
    return count

def distance_to_wall(pos, grid_dim):
    x, y = pos
    return min(x, y, grid_dim-1-x, grid_dim-1-y)

def move(my_pos, board, grid_dim, players):
    global prev_pos, current_dir

    if prev_pos is not None:
        current_dir = infer_direction(prev_pos, my_pos)
    prev_pos = my_pos

    candidates = []
    for d in WALL_HUG_RULE[current_dir]:
        dx, dy = DIRECTIONS[d]
        nx, ny = my_pos[0] + dx, my_pos[1] + dy
        if is_safe(nx, ny, grid_dim, board):
            candidates.append((d, (nx, ny)))

    if not candidates:
        for d in ["UP", "DOWN", "LEFT", "RIGHT"]:
            dx, dy = DIRECTIONS[d]
            nx, ny = my_pos[0] + dx, my_pos[1] + dy
            if is_safe(nx, ny, grid_dim, board):
                candidates.append((d, (nx, ny)))
        if not candidates:
            return "UP"

    best_dir = None
    best_score = -999999

    for d, next_pos in candidates:
        temp_board = board.copy()
        temp_board[next_pos] = 999

        space = fast_flood(next_pos, temp_board, grid_dim)

        score = space * 10000

        # Very strong wall-hugging bias – stay near borders
        wall_dist = distance_to_wall(next_pos, grid_dim)
        score += (5 - wall_dist) * 800   # reward being close to any wall

        # Momentum – but secondary to wall-hugging
        if d == current_dir:
            score += 350
        elif d == WALL_HUG_RULE[current_dir][0]:
            score += 220

        # Avoid articulation-like moves (mimic APEX weakness)
        free_n = sum(1 for dx, dy in DIRECTIONS.values()
                     if is_safe(next_pos[0] + dx, next_pos[1] + dy, grid_dim, temp_board))
        if space > 700 and free_n <= 2:
            score -= 4000           # heavy penalty – exploits APEX's own articulation guard

        # Avoid reverse
        if d == OPPOSITE.get(current_dir, None):
            score -= 3000

        if score > best_score:
            best_score = score
            best_dir = d

    return best_dir if best_dir else random.choice([d for d, _ in candidates])