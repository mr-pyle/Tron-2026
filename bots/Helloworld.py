# helloworld.py
# Improved version: direction-aware + fast flood-fill + right-hand bias
# Designed to be fast enough for 60×60 visual mode

import random
from collections import deque

team_name = "HelloWorld"

# Persistent state across turns
prev_pos = None
current_dir = "RIGHT"  # initial guess

DIRECTIONS = {
    "UP":    (0, -1),
    "DOWN":  (0, 1),
    "LEFT":  (-1, 0),
    "RIGHT": (1, 0)
}

RIGHT_HAND_RULE = {
    "UP":    ["RIGHT", "UP", "LEFT", "DOWN"],
    "RIGHT": ["DOWN", "RIGHT", "UP", "LEFT"],
    "DOWN":  ["LEFT", "DOWN", "RIGHT", "UP"],
    "LEFT":  ["UP", "LEFT", "DOWN", "RIGHT"]
}

def infer_direction(old, new):
    dx = new[0] - old[0]
    dy = new[1] - old[1]
    for d, (ddx, ddy) in DIRECTIONS.items():
        if (dx, dy) == (ddx, ddy):
            return d
    return current_dir  # fallback

def is_valid(nx, ny, grid_dim, board):
    return (0 <= nx < grid_dim and
            0 <= ny < grid_dim and
            (nx, ny) not in board)

def fast_flood_size(start, board, grid_dim, max_check=350):
    """Fast BFS with early cutoff – good enough approximation"""
    visited = set()
    q = deque([start])
    visited.add(start)
    count = 1

    while q and count < max_check:
        cx, cy = q.popleft()
        for dx, dy in [(0,-1), (0,1), (-1,0), (1,0)]:
            nx, ny = cx + dx, cy + dy
            if is_valid(nx, ny, grid_dim, board) and (nx, ny) not in visited:
                visited.add((nx, ny))
                q.append((nx, ny))
                count += 1
                if count >= max_check:
                    return max_check + 500  # treat as "very large"
    return count

def move(my_pos, board, grid_dim, players):
    global prev_pos, current_dir

    # Update our facing direction from previous move
    if prev_pos is not None:
        current_dir = infer_direction(prev_pos, my_pos)
    prev_pos = my_pos

    # Get preferred moves in right-hand order
    candidates = []
    for d in RIGHT_HAND_RULE[current_dir]:
        dx, dy = DIRECTIONS[d]
        nx, ny = my_pos[0] + dx, my_pos[1] + dy
        if is_valid(nx, ny, grid_dim, board):
            candidates.append((d, (nx, ny)))

    # If no preferred moves, allow any safe direction
    if not candidates:
        for d in ["UP", "DOWN", "LEFT", "RIGHT"]:
            dx, dy = DIRECTIONS[d]
            nx, ny = my_pos[0] + dx, my_pos[1] + dy
            if is_valid(nx, ny, grid_dim, board):
                candidates.append((d, (nx, ny)))
        if not candidates:
            return "UP"  # trapped – die

    # ─── Decision: prefer largest reachable area + direction bias ───
    best_dir = None
    best_score = -1

    for d, next_pos in candidates:
        # Pretend we move there
        temp_board = board.copy()
        temp_board[next_pos] = 999  # dummy player id – just mark occupied

        space = fast_flood_size(next_pos, temp_board, grid_dim)

        score = space

        # Small bias: prefer continuing straight or turning right
        if d == current_dir:
            score += 80
        elif d == RIGHT_HAND_RULE[current_dir][0]:
            score += 120

        if score > best_score:
            best_score = score
            best_dir = d

    return best_dir if best_dir else random.choice([d for d, _ in candidates])