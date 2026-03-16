import collections

class GhostHunter:
    def __init__(self, max_trail=5):
        self.max_trail = max_trail
        self.my_internal_trail = []

    def move(self, my_pos, board, dim, players):
        x, y = my_pos
        
        # Track our own movement
        self.my_internal_trail.append(my_pos)
        if len(self.my_internal_trail) > self.max_trail:
            self.my_internal_trail.pop(0)

        # 1. FIND TARGET
        target = None
        for p in players:
            if p['alive'] and p['pos'] != my_pos:
                target = p['pos']
                break

        # 2. EVALUATE MOVES
        directions = {"UP": (x, y-1), "DOWN": (x, y+1), "LEFT": (x-1, y), "RIGHT": (x+1, y)}
        best_move = "UP"
        best_score = -999
        
        for d, (nx, ny) in directions.items():
            # Check boundaries
            if not (0 <= nx < dim and 0 <= ny < dim):
                continue
            
            # THE GHOST RULE: 
            # If the square is in the board BUT it's our own 'expired' trail, 
            # we consider it "less dangerous" than a wall or enemy trail.
            is_obstacle = (nx, ny) in board
            is_my_old_trail = (nx, ny) in board and (nx, ny) not in self.my_internal_trail

            if is_obstacle and not is_my_old_trail:
                continue

            # Calculate space and aggression
            # We use a very shallow search because a short-trail bot 
            # needs to be twitchy, not a long-term planner.
            space = self.quick_check((nx, ny), board, dim)
            
            dist = 0
            if target:
                dist = abs(nx - target[0]) + abs(ny - target[1])
            
            # Score: High space, Low distance
            score = (space * 2) - dist
            
            # Preference for its own old trail to keep the "small trail" footprint
            if is_my_old_trail:
                score += 5 

            if score > best_score:
                best_score = score
                best_move = d

        return best_move

    def quick_check(self, start, board, dim):
        # Very fast BFS
        q = collections.deque([start])
        v = {start}
        c = 0
        while q and c < 30:
            cx, cy = q.popleft()
            for dx, dy in ((0,1),(0,-1),(1,0),(-1,0)):
                n = (cx+dx, cy+dy)
                if 0<=n[0]<dim and 0<=n[1]<dim and n not in board and n not in v:
                    v.add(n); q.append(n); c += 1
        return c

# Engine interface
hunter_instance = GhostHunter(max_trail=8) # Set trail size here
def move(my_pos, board, dim, players):
    return hunter_instance.move(my_pos, board, dim, players)