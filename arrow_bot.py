import collections
import time

team_name = "APOLLYON"

class TopologyCore:
    def __init__(self, grid_dim):
        self.grid_dim = grid_dim
        self.dirs = {"UP": (0, -1), "DOWN": (0, 1), "LEFT": (-1, 0), "RIGHT": (1, 0)}

    def is_valid(self, pos, board):
        return 0 <= pos[0] < self.grid_dim and 0 <= pos[1] < self.grid_dim and pos not in board

    def get_neighbors(self, pos, board):
        return [(d, (pos[0]+dx, pos[1]+dy)) for d, (dx, dy) in self.dirs.items() if self.is_valid((pos[0]+dx, pos[1]+dy), board)]

    def analyze_chambers(self, my_pos, opponents, board):
        """
        Runs a simultaneous BFS to find:
        1. My total space.
        2. Are there enemies in my space? (If yes, we are hunting)
        3. Who owns what? (Voronoi)
        """
        queue = collections.deque()
        visited = {}
        
        queue.append((my_pos, 'ME'))
        visited[my_pos] = 'ME'
        
        active_targets = []
        for opp in opponents:
            queue.append((opp['pos'], f"OPP_{opp['pos']}"))
            visited[opp['pos']] = f"OPP_{opp['pos']}"
            active_targets.append(opp['pos'])

        my_space = 0
        enemy_spaces = {f"OPP_{t}": 0 for t in active_targets}
        shared_chamber = False

        while queue:
            curr, owner = queue.popleft()
            
            if owner == 'ME': my_space += 1
            elif owner.startswith('OPP_'): enemy_spaces[owner] += 1

            for _, n_pos in self.get_neighbors(curr, board):
                if n_pos not in visited:
                    visited[n_pos] = owner
                    queue.append((n_pos, owner))
                elif visited[n_pos] != owner:
                    # Borders touched! We are in the same chamber as an enemy.
                    shared_chamber = True

        return my_space, enemy_spaces, shared_chamber

    def get_wall_hug_score(self, pos, board):
        """Calculates how tightly we are packing ourselves (Hamiltonian pathing)."""
        blocked = 0
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            n = (pos[0]+dx, pos[1]+dy)
            if not self.is_valid(n, board): 
                blocked += 1
        return blocked

class ApollyonAI:
    def __init__(self, core):
        self.core = core
        self.time_limit = 0.04
        self.start_time = 0

    def evaluate_move(self, my_pos, target_pos, board, opponents, is_combat):
        """The mathematical brain prioritizing HUNTING and MAXIMIZING."""
        my_reach, enemy_reaches, still_combat = self.core.analyze_chambers(target_pos, opponents, board)
        
        if my_reach < 3: return -999999 # Avoid suicide

        score = my_reach * 100 # Base desire: MAXIMIZE SPACE
        
        # Calculate how tightly we are packing
        hug_score = self.core.get_wall_hug_score(target_pos, board)

        if is_combat and opponents:
            # --- THE HUNTER (Seek Out & Destroy) ---
            # 1. Target the weakest enemy (least space) or closest
            closest_opp = min(opponents, key=lambda o: abs(o['pos'][0]-target_pos[0]) + abs(o['pos'][1]-target_pos[1]))
            dist_to_prey = abs(closest_opp['pos'][0]-target_pos[0]) + abs(closest_opp['pos'][1]-target_pos[1])
            
            # Predatory Gravity: Massive reward for moving closer to the enemy
            score += ((self.core.grid_dim * 2) - dist_to_prey) * 500
            
            # 2. Suffocation: Punish the enemy's available space
            # We want moves that drastically reduce the enemy's flood-fill count
            opp_key = f"OPP_{closest_opp['pos']}"
            opp_space = enemy_reaches.get(opp_key, 0)
            score += (1000 - opp_space) * 200

            # 3. Interception: Look at their trail and step in front of them
            if len(closest_opp['trail']) > 1:
                last_pos = closest_opp['trail'][-2]
                dx, dy = closest_opp['pos'][0] - last_pos[0], closest_opp['pos'][1] - last_pos[1]
                # Project 1, 2, and 3 steps ahead
                for step in range(1, 4):
                    proj = (closest_opp['pos'][0] + (dx*step), closest_opp['pos'][1] + (dy*step))
                    if target_pos == proj:
                        score += 25000 # Lunge directly into their path!

            # 4. Agility: While hunting, DO NOT hug walls. Stay in the center to branch out.
            score -= (hug_score * 300) 
            
            # 5. The Kill Shot: If we are adjacent, trap them
            if dist_to_prey == 1:
                score += 100000

        else:
            # --- THE MAXIMIZER (Coil & Survive) ---
            # We are alone in our chamber. The enemy is walled off or dead.
            # 1. Ignore the enemy distance entirely.
            # 2. Maximize space perfectly by hugging walls/trails.
            score += (my_reach * 1000)
            
            # The more blocked neighbors we have, the less "open space" we waste.
            # 3 blocked neighbors means we are driving into a perfect cul-de-sac.
            score += (hug_score * 5000)

        return score

    def get_best_move(self, my_pos, board, opponents):
        self.start_time = time.time()
        
        # Fast board for simulation
        sim_board = set(board.keys() if isinstance(board, dict) else board)
        
        legal_moves = self.core.get_neighbors(my_pos, sim_board)
        if not legal_moves: return "UP"

        # Global Chamber Check
        _, _, is_combat = self.core.analyze_chambers(my_pos, opponents, sim_board)

        best_score = -float('inf')
        best_dir = legal_moves[0][0]

        for move_dir, target_pos in legal_moves:
            sim_board.add(target_pos)
            
            # Primary Heuristic Evaluation
            score = self.evaluate_move(my_pos, target_pos, sim_board, opponents, is_combat)
            
            # 1-Ply Enemy Lookahead (Trap Prevention)
            if is_combat and opponents:
                closest_opp = min(opponents, key=lambda o: abs(o['pos'][0]-target_pos[0]) + abs(o['pos'][1]-target_pos[1]))
                enemy_moves = self.core.get_neighbors(closest_opp['pos'], sim_board)
                
                worst_case_for_me = float('inf')
                for _, e_pos in enemy_moves:
                    sim_board.add(e_pos)
                    my_future_reach, _, _ = self.core.analyze_chambers(target_pos, [], sim_board)
                    sim_board.remove(e_pos)
                    
                    if my_future_reach < worst_case_for_me:
                        worst_case_for_me = my_future_reach
                        
                # If an enemy move leaves us with almost no space, abort this path!
                if worst_case_for_me < 5:
                    score -= 5000000

            sim_board.remove(target_pos)

            if score > best_score:
                best_score = score
                best_dir = move_dir
                
            # Time safety
            if time.time() - self.start_time > self.time_limit:
                break

        return best_dir

def move(my_pos, board, grid_dim, players):
    core = TopologyCore(grid_dim)
    ai = ApollyonAI(core)
    
    opponents = [p for p in players if p['alive'] and p['pos'] != my_pos]
    return ai.get_best_move(my_pos, board, opponents)

