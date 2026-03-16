def move(my_pos, board, dim, players):
    def get_space(start):
        q, v = [start], {start}
        count = 0
        while q and count < 400: # Cap to keep it fast
            cx, cy = q.pop(0)
            count += 1
            for dx, dy in [(0,1), (0,-1), (1,0), (-1,0)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < dim and 0 <= ny < dim and board.get((nx, ny), 0) == 0 and (nx, ny) not in v:
                    v.add((nx, ny))
                    q.append((nx, ny))
        return count

    choices = []
    for move_name, (dx, dy) in [("UP", (0, -1)), ("DOWN", (0, 1)), ("LEFT", (-1, 0)), ("RIGHT", (1, 0))]:
        nx, ny = my_pos[0] + dx, my_pos[1] + dy
        if 0 <= nx < dim and 0 <= ny < dim and board.get((nx, ny), 0) == 0:
            choices.append((get_space((nx, ny)), move_name))
    
    if not choices: return "UP"
    # Return the move that leads to the MOST space
    return max(choices, key=lambda x: x[0])[1]