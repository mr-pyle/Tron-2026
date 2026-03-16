# helloworld.py
# Improved defensive HelloWorld bot – direction-aware + fast flood-fill + strong right-hand bias
# Designed to be fast and reliable on 60×60 grids

import random
from collections import deque

team_name = "HelloWorld"

# Persistent state across turns
prev_pos = None
current_dir = "RIGHT"           # initial guess

DIRECTIONS = {
    "UP":    (0, -1),
    "DOWN":  (0, 1),
    "LEFT":  (-1, 0),
    "RIGHT": (1, 0)
}

OPPOSITE = {
    "UP": "DOWN",
    "DOWN": "UP",
    "LEFT": "RIGHT",
    "RIGHT": "LEFT"
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

def is_safe(nx, ny, grid_dim, board):
    return (0 <= nx < grid_dim and
            0 <= ny < grid_dim and
            (nx, ny) not in board)

def fast_flood_size(start, board, grid_dim, max_check=450):
    """Fast BFS with early cutoff – returns large value when area is huge"""
    visited = set([start])
    q = deque([start])
    count = 1

    while q and count < max_check:
        cx, cy = q.popleft()
        for dx, dy in [(0,-1), (0,1), (-1,0), (1,0)]:
            nx, ny = cx + dx, cy + dy
            if is_safe(nx, ny, grid_dim, board) and (nx, ny) not in visited:
                visited.add((nx, ny))
                q.append((nx, ny))
                count += 1
                if count >= max_check:
                    return max_check + 2000  # treat as very large

    return count

def move(my_pos, board, grid_dim, players):
    global prev_pos, current_dir

    # Update facing direction
    if prev_pos is not None:
        current_dir = infer_direction(prev_pos, my_pos)
    prev_pos = my_pos

    # Get candidate moves — prefer right-hand rule order
    candidates = []
    for d in RIGHT_HAND_RULE[current_dir]:
        dx, dy = DIRECTIONS[d]
        nx, ny = my_pos[0] + dx, my_pos[1] + dy
        if is_safe(nx, ny, grid_dim, board):
            candidates.append((d, (nx, ny)))

    # If none, allow any safe direction (still avoid reverse if possible)
    if not candidates:
        for d in ["UP", "DOWN", "LEFT", "RIGHT"]:
            dx, dy = DIRECTIONS[d]
            nx, ny = my_pos[0] + dx, my_pos[1] + dy
            if is_safe(nx, ny, grid_dim, board):
                candidates.append((d, (nx, ny)))
        if not candidates:
            return "UP"  # trapped – die

    # ─── Evaluate moves ───
    best_dir = None
    best_score = -1
    best_pos = None

    for d, next_pos in candidates:
        # Simulate move
        temp_board = board.copy()
        temp_board[next_pos] = 999  # mark as occupied

        space = fast_flood_size(next_pos, temp_board, grid_dim)

        score = space

        # Strong preference for continuing straight
        if d == current_dir:
            score += 250
        # Then right turn
        elif d == RIGHT_HAND_RULE[current_dir][0]:
            score += 180
        # Small bonus for left turn over reverse
        elif d != OPPOSITE.get(current_dir, None):
            score += 40

        # Small penalty for moving into low-mobility cell early
        free_neighbors = sum(1 for dx, dy in DIRECTIONS.values()
                             if is_safe(next_pos[0] + dx, next_pos[1] + dy, grid_dim, temp_board))
        if space > 600 and free_neighbors <= 2:
            score -= 300

        # Avoid 180° unless desperate
        if d == OPPOSITE.get(current_dir, None):
            score -= 800

        if score > best_score:
            best_score = score
            best_dir = d
            best_pos = next_pos

    # If no clear winner or tie → prefer continuing current direction
    if best_dir is None or best_score <= 0:
        # Check if current direction is still possible
        dx, dy = DIRECTIONS.get(current_dir, (0,0))
        nx, ny = my_pos[0] + dx, my_pos[1] + dy
        if is_safe(nx, ny, grid_dim, board):
            return current_dir

    return best_dir if best_dir else random.choice([d for d, _ in candidates])