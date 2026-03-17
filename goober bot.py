import random
from collections import deque

team_name = "goober bot"

bot_state = {
    "target_id": None,
    "tick": 0
}

def neighbors(pos):
    x, y = pos
    return [(x+1,y), (x-1,y), (x,y+1), (x,y-1)]

def get_safe_moves(pos, board, grid_dim):
    dirs = {
        "UP": (0,-1),
        "DOWN": (0,1),
        "LEFT": (-1,0),
        "RIGHT": (1,0)
    }
    moves = []
    for d, (dx,dy) in dirs.items():
        nx, ny = pos[0]+dx, pos[1]+dy
        if 0 <= nx < grid_dim and 0 <= ny < grid_dim and (nx,ny) not in board:
            moves.append((d,(nx,ny)))
    return moves

def flood(start, board, grid_dim):
    q = deque([start])
    seen = {start}
    count = 0

    while q:
        p = q.popleft()
        count += 1
        for n in neighbors(p):
            if n in seen:
                continue
            if not (0 <= n[0] < grid_dim and 0 <= n[1] < grid_dim):
                continue
            if n in board:
                continue
            seen.add(n)
            q.append(n)

    return count

def dist(a, b, board, grid_dim):
    q = deque([(a,0)])
    seen = {a}

    while q:
        p, d = q.popleft()
        if p == b:
            return d

        for n in neighbors(p):
            if n in seen:
                continue
            if not (0 <= n[0] < grid_dim and 0 <= n[1] < grid_dim):
                continue
            if n in board and n != b:
                continue
            seen.add(n)
            q.append((n,d+1))

    return float('inf')

def lookahead_space(pos, board, grid_dim):
    best = 0
    first = get_safe_moves(pos, board, grid_dim)
    if not first:
        return 0

    for _, p1 in first:
        b1 = board.copy()
        b1[p1] = -1

        second = get_safe_moves(p1, b1, grid_dim)
        if not second:
            continue

        for _, p2 in second:
            b2 = b1.copy()
            b2[p2] = -1
            best = max(best, flood(p2, b2, grid_dim))

    return best

def project_ray(start, direction, board, grid_dim):
    dx, dy = direction
    x, y = start
    ray_board = board.copy()

    while True:
        x += dx
        y += dy
        if not (0 <= x < grid_dim and 0 <= y < grid_dim):
            break
        if (x, y) in ray_board:
            break
        ray_board[(x, y)] = -1

    return ray_board, (x, y)

def dist_to_wall(pos, grid_dim):
    x, y = pos
    return min(x, y, grid_dim-1-x, grid_dim-1-y)

def move(my_pos, board, grid_dim, players):
    global bot_state

    bot_state["tick"] += 1

    my_data = next(p for p in players if p['pos'] == my_pos)
    safe_moves = get_safe_moves(my_pos, board, grid_dim)
    if not safe_moves:
        return "UP"

    enemies = [p for p in players if p['alive'] and p['pos'] != my_pos]

    # ================= FIXED ISOLATION CHECK =================
    enemy_heads = {e['pos'] for e in enemies}

    region = set()
    q = deque([my_pos])
    region.add(my_pos)

    while q:
        p = q.popleft()
        for n in neighbors(p):
            if n in region:
                continue
            if not (0 <= n[0] < grid_dim and 0 <= n[1] < grid_dim):
                continue

            # allow enemy heads to be detected
            if n in board and n not in enemy_heads:
                continue

            region.add(n)
            q.append(n)

    enemies_in_region = [e for e in enemies if e['pos'] in region]

    # ================= BOX MODE =================
    if bot_state["tick"] > 25 and not enemies_in_region:
        current_space = flood(my_pos, board, grid_dim)

        best_move = "UP"
        max_score = -float('inf')
        options = []

        directions = {
            "UP": (0,-1),
            "DOWN": (0,1),
            "LEFT": (-1,0),
            "RIGHT": (1,0)
        }

        for d_name, (dx,dy) in directions.items():
            target_pos = (my_pos[0]+dx, my_pos[1]+dy)

            if not (0 <= target_pos[0] < grid_dim and 0 <= target_pos[1] < grid_dim) or target_pos in board:
                continue

            temp1 = board.copy()
            temp1[target_pos] = -1

            next_moves = get_safe_moves(target_pos, temp1, grid_dim)

            if not next_moves:
                score = -1000000
            else:
                best_future = 0
                for _, p2 in next_moves:
                    temp2 = temp1.copy()
                    temp2[p2] = -1
                    space2 = flood(p2, temp2, grid_dim)
                    best_future = max(best_future, space2)

                wall_score = 0
                for n in neighbors(target_pos):
                    if not (0 <= n[0] < grid_dim and 0 <= n[1] < grid_dim) or n in temp1:
                        wall_score += 1

                score = (best_future * 100) + (wall_score * 10)

                if best_future < current_space * 0.7:
                    score -= 1000000

            if score > max_score:
                max_score = score
                options = [d_name]
            elif score == max_score:
                options.append(d_name)

        if options:
            return random.choice(options)

    # ================= NORMAL MODE =================
    current_dir = None
    if len(my_data['trail']) > 1:
        last = my_data['trail'][-2]
        if my_pos[0] > last[0]: current_dir = "RIGHT"
        elif my_pos[0] < last[0]: current_dir = "LEFT"
        elif my_pos[1] > last[1]: current_dir = "DOWN"
        elif my_pos[1] < last[1]: current_dir = "UP"

    nearest = None
    nearest_dist = float('inf')

    for e in enemies:
        d = dist(my_pos, e['pos'], board, grid_dim)
        if d < nearest_dist:
            nearest_dist = d
            nearest = e

    if nearest and nearest_dist <= 20:
        bot_state["target_id"] = nearest['id']
        target = nearest
    else:
        bot_state["target_id"] = None
        target = nearest

    best_move = safe_moves[0][0]
    best_score = -10**18

    current_space = flood(my_pos, board, grid_dim)

    dir_map = {
        "UP": (0,-1),
        "DOWN": (0,1),
        "LEFT": (-1,0),
        "RIGHT": (1,0)
    }

    for d, new_pos in safe_moves:
        temp = board.copy()
        temp[new_pos] = -1

        score = 0

        future = lookahead_space(new_pos, temp, grid_dim)

        # ================= HARD SAFETY FILTER =================
        if future < current_space * 0.35:
            continue  # ❗ NEVER take catastrophic moves

        if future == 0:
            score -= 1000000
        else:
            score += future

        # softer penalty (kept)
        if future < current_space * 0.55:
            enemy_future = flood(target['pos'], temp, grid_dim) if target else future
            if enemy_future >= future * 0.8:
                score -= 200000

        if target:
            enemy_pos = target['pos']

            d_now = dist(my_pos, enemy_pos, board, grid_dim)
            d_next = dist(new_pos, enemy_pos, temp, grid_dim)
            
            # If enemy is unreachable, treat as maximally distant
            if d_now == float('inf'):
                d_now = grid_dim * 2
            if d_next == float('inf'):
                d_next = grid_dim * 2
            
            # AFTER CUTOFF BEHAVIOR:
            # If we are at the wall, prioritize increasing distance
            if dist_to_wall(my_pos, grid_dim) == 0:
                if d_next > d_now:
                    score += 30000
                else:
                    score -= 30000
            else:
                # normal chase logic
                score += (d_now - d_next) * 8000

            if d_next <= 2:
                score -= 20000
            elif 3 <= d_next <= 6:
                score += 3000

            if d_now <= 6 and d_next <= d_now:
                score -= 10000

        dx, dy = dir_map[d]
        ray_board, ray_end = project_ray(new_pos, (dx,dy), temp, grid_dim)

        if target:
            enemy_pos = target['pos']
            d_after = dist(ray_end, enemy_pos, ray_board, grid_dim)
            d_before = dist(my_pos, enemy_pos, board, grid_dim)

            if d_after - d_before >= 5:
                score += 10000

        wall_dist = dist_to_wall(new_pos, grid_dim)
        if wall_dist < 2:
            score -= 4000

        if target:
            if dist_to_wall(new_pos, grid_dim) == 0:
               enemy_pos = target['pos']
               d_next = dist(new_pos, enemy_pos, temp, grid_dim)
        
               # instead of blindly adding d_next*8000 (chasing), pick the move that increases distance
               # TURN AWAY AFTER CUTOFF
               if bot_state["target_id"] == target["id"]:
                   # prefer moves that increase distance
                   if d_next > d_now:
                       score += 30000   # moving away
                   else:
                       score -= 30000   # moving closer
               else:
                   # normal logic if not in cutoff
                   score += d_next * 8000

        if d == current_dir:
            score += 2000

        score += random.random()

        if score > best_score:
            best_score = score
            best_move = d

    return best_move