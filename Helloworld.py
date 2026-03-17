# helloworld.py – Hamilton-style corridor maximizer (strong counter to Penguin 0)

import random
from collections import deque

team_name = "HelloWorld"

prev_pos = None
current_dir = "RIGHT"

DIRECTIONS = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}
OPPOSITE = {"UP":"DOWN", "DOWN":"UP", "LEFT":"RIGHT", "RIGHT":"LEFT"}

RIGHT_HAND_RULE = {
    "UP":    ["RIGHT", "UP", "LEFT", "DOWN"],
    "RIGHT": ["DOWN", "RIGHT", "UP", "LEFT"],
    "DOWN":  ["LEFT", "DOWN", "RIGHT", "UP"],
    "LEFT":  ["UP", "LEFT", "DOWN", "RIGHT"]
}

# ── prefer this order when space is large ──
LONG_CORRIDOR_RULE = {
    "UP":    ["UP", "RIGHT", "LEFT", "DOWN"],     # straight first
    "RIGHT": ["RIGHT", "DOWN", "UP", "LEFT"],
    "DOWN":  ["DOWN", "LEFT", "RIGHT", "UP"],
    "LEFT":  ["LEFT", "UP", "DOWN", "RIGHT"]
}

def infer_direction(old, new):
    dx, dy = new[0] - old[0], new[1] - old[1]
    for d, (ddx, ddy) in DIRECTIONS.items():
        if (dx, dy) == (ddx, ddy): return d
    return current_dir

def is_safe(nx, ny, grid_dim, board):
    return 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx, ny) not in board

def fast_flood(start, board, grid_dim, max_check=550):
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
                    return max_check + 3000
    return count

def move(my_pos, board, grid_dim, players):
    global prev_pos, current_dir

    if prev_pos is not None:
        current_dir = infer_direction(prev_pos, my_pos)
    prev_pos = my_pos

    # Choose rule based on board openness
    rule = LONG_CORRIDOR_RULE if len(board) < grid_dim*grid_dim//3 else RIGHT_HAND_RULE
    candidates = []

    for d in rule[current_dir]:
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

        # Very strong corridor bias
        if d == current_dir:
            score += 600
        elif d == rule[current_dir][0]:
            score += 400

        # Avoid 180° very strongly
        if d == OPPOSITE.get(current_dir, None):
            score -= 2500

        # Avoid closing into dead-ends early
        free_n = sum(1 for dx, dy in DIRECTIONS.values()
                     if is_safe(next_pos[0] + dx, next_pos[1] + dy,
                                grid_dim, temp_board))
        if space > 800 and free_n <= 2:
            score -= 1800

        if score > best_score:
            best_score = score
            best_dir = d

    return best_dir if best_dir else random.choice([d for d,_ in candidates])
