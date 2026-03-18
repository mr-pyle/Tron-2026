import random
import concurrent.futures
from bot_runner import SecureBotProcess
from engine import calculate_new_pos, resolve_collisions

def headless_worker(grid_dim, selected_bots, code_snapshots): 
    _engine_board = {}
    _engine_players = []
    _dead_player_ids = set() 
    
    random.seed() 
    start_positions = [(random.randint(5, grid_dim-6), random.randint(5, grid_dim-6)) for _ in selected_bots]
    
    for i, bot_name in enumerate(selected_bots):
        # Pass the snapshots down to the subprocess
        bot_process = SecureBotProcess(bot_name, i + 1, bot_name, code_snapshots)
        pos = start_positions[i]
        _engine_players.append({
            'id': i + 1,
            'name': bot_name,
            'wrapper': bot_process,
            'move_func': bot_process.get_move, 
            'pos': pos,
            'trail': [pos],
            'alive': True,
            'survival': 0,
            'rank': 0
        })
        _engine_board[pos] = i + 1

    max_ticks = grid_dim * grid_dim
    tick = 0
    
    while tick < max_ticks:
        tick += 1
        
        for p in _engine_players:
            if p['id'] in _dead_player_ids:
                p['alive'] = False
                
        alive = [p for p in _engine_players if p['id'] not in _dead_player_ids]
        current_rank_score = len(alive)
        
        if len(alive) <= 1:
            if alive: alive[0]['rank'] = 1
            break

        safe_players = []
        for other_p in _engine_players:
            safe_players.append({
                "id": other_p['id'], "name": other_p['name'],
                "pos": other_p['pos'], "alive": other_p['alive'],
                "trail": list(other_p['trail'])
            })

        # --- PHASE 1: GATHER INTENTIONS (CONCURRENTLY!) ---
        intended_moves = {}
        
        # Helper function to run in a background I/O thread
        def fetch_move_headless(p):
            import time
            start_time = time.perf_counter()
            try:
                move = p['move_func'](p['pos'], _engine_board.copy(), grid_dim, safe_players)
                think_time = time.perf_counter() - start_time
                if move not in ["UP", "DOWN", "LEFT", "RIGHT"]:
                    raise ValueError(f"Illegal Move Command: {move}")
                
                x, y = p['pos']
                # Replace the 4 if/elif statements with this:
                new_coord = calculate_new_pos(p['pos'], move)
                return p['id'], new_coord, None, think_time
                
                return p['id'], (x, y), None, think_time
            except Exception as e:
                think_time = time.perf_counter() - start_time
                return p['id'], "ERROR", e, think_time

        # Ask ALL bots for their move at the exact same time
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(alive)) as executor:
            futures = [executor.submit(fetch_move_headless, p) for p in alive]
            
            for future in concurrent.futures.as_completed(futures):
                pid, result, error, think_time = future.result()
                
                # Find the matching player in the main thread
                p = next(player for player in alive if player['id'] == pid)
                p['survival'] += 1
                
                # --- NEW: Track total computation time ---
                p['total_time'] = p.get('total_time', 0.0) + think_time
                p['move_count'] = p.get('move_count', 0) + 1
                # -----------------------------------------
                
                if result == "ERROR":
                    intended_moves[p['id']] = "ERROR" 
                    p['alive'] = False
                    _dead_player_ids.add(p['id']) 
                    p['rank'] = current_rank_score
                else:
                    intended_moves[p['id']] = result

        # --- PHASE 2: COUNT CLAIMS ON EACH SQUARE ---
        square_claims = {}
        for pos in intended_moves.values():
            if pos != "ERROR":
                square_claims[pos] = square_claims.get(pos, 0) + 1

        # --- PHASE 3: RESOLVE COLLISIONS AND UPDATE BOARD ---
        # --- RESOLVE COLLISIONS AND UPDATE BOARD ---
        resolve_collisions(grid_dim, alive, intended_moves, _engine_board, _dead_player_ids, current_rank_score)

    # Cleanup subprocesses
    for p in _engine_players:
        p['wrapper'].stop()

    _engine_secure_results_v9 = {}
    for p in _engine_players:
        _engine_secure_results_v9[p['name']] = {
            'rank': p['rank'], 
            'survival': p['survival'],
            'total_time': p.get('total_time', 0.0),
            'move_count': p.get('move_count', 0)
        }
        
    return _engine_secure_results_v9