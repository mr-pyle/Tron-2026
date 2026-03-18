import sys
import os
import json
import ast
import subprocess
import concurrent.futures

# --- THE GHOST RUNNER ---
# This code lives only in RAM. It never touches the hard drive.
RUNNER_CODE = """
import sys
import os
import json
import importlib

sys.path.insert(0, os.path.abspath('bots'))

# Redirect student print() statements to the void
student_stdout = sys.stdout
sys.stdout = open(os.devnull, 'w')

def main():
    if len(sys.argv) < 2:
        return
        
    bot_name = sys.argv[1]
    
    try:
        bot_module = importlib.import_module(bot_name)
    except Exception:
        return

    # THE FIX: Persistent local memory so we don't have to send the whole board every tick
    local_board = {}
    local_players = {}

    while True:
        line = sys.stdin.readline()
        if not line:
            break
            
        try:
            state = json.loads(line)
            
            # --- LIGHTNING FAST DELTA RECONSTRUCTION ---
            for coord in state["new_board"]:
                local_board[tuple(coord)] = 1
                
            safe_players_list = []
            for p in state["players"]:
                pid = p["id"]
                if p["is_new"]:
                    local_players[pid] = {
                        "id": pid, 
                        "name": p["name"], 
                        "pos": tuple(p["pos"]), 
                        "alive": p["alive"], 
                        "trail": [tuple(t) for t in p["new_trail"]]
                    }
                else:
                    local_players[pid]["pos"] = tuple(p["pos"])
                    local_players[pid]["alive"] = p["alive"]
                    for t in p["new_trail"]:
                        local_players[pid]["trail"].append(tuple(t))
                
                safe_players_list.append(local_players[pid].copy())
            
            my_pos = tuple(state["pos"])
            
            move = bot_module.move(
                my_pos, 
                local_board.copy(), 
                state["dim"], 
                safe_players_list
            )
            
            student_stdout.write(str(move) + chr(10))
            student_stdout.flush()
            
        except Exception as e:
            student_stdout.write("UP" + chr(10))
            student_stdout.flush()

if __name__ == "__main__":
    main()
"""

# --- SECURITY SCANNER ---
def is_bot_safe(filepath):
    """Scans a python file for syntax errors, blatant illegal concepts, and network calls."""
    banned_modules = [
        'os', 'sys', 'subprocess', 'inspect', 'threading', 'multiprocessing', 
        'builtins', 'shutil', 'importlib', 'ctypes', 'pathlib', 'io', 
        'fileinput', 'codecs', 'tempfile', 'socket', 'urllib', 'http', 
        'requests', 'xmlrpc', 'ftplib', 'telnetlib', 'asyncio', 'pickle', 'marshal'
    ]
    banned_functions = [
        'exec', 'eval', 'compile', 'open', 'globals', 'locals', 
        'getattr', 'setattr', 'delattr', '__import__', 'dir', 'vars', 'type'
    ]
    banned_attributes = [
        '__traceback__', 'tb_frame', 'f_back', 'f_locals', 'f_globals', 
        '__dict__', '__class__', '__subclasses__', '__builtins__', '__code__',
        'write_text', 'write_bytes', 'write', '__getattribute__'
    ]
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] in banned_modules:
                        return False, f"Banned Import: '{alias.name}' is restricted."
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] in banned_modules:
                        return False, f"Banned Import: '{node.module}' is restricted."
            elif isinstance(node, ast.Name):
                if node.id in banned_functions:
                    return False, f"Banned Identifier: '{node.id}' usage is restricted."
                if node.id in banned_attributes:
                    return False, f"Banned Identifier: '{node.id}' usage is restricted."
            elif isinstance(node, ast.Attribute):
                if node.attr in banned_attributes:
                    return False, f"Banned Attribute: '.{node.attr}' access is restricted."
        return True, "Safe"
    except Exception as e:
        return False, f"Syntax Error: {e}"

class SecureBotProcess:
    def __init__(self, bot_filename, bot_id, name, snapshots=None):
        self.bot_id = bot_id
        self.name = name
        self.alive = True
        
        # Persistent Thread & State Tracking
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.last_board_len = 0
        self.last_trail_lens = {}
        
        # Self-Healing Protocol
        if snapshots and name in snapshots:
            filepath = os.path.join("bots", f"{name}.py")
            pristine_code = snapshots[name]
            needs_healing = False
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    if f.read() != pristine_code:
                        needs_healing = True
            except FileNotFoundError:
                needs_healing = True
                
            if needs_healing:
                print(f"[SECURITY] Tampering detected in {filepath}! Healing file.")
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(pristine_code)
                    
        self.process = subprocess.Popen(
            [sys.executable, "-c", RUNNER_CODE, bot_filename],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1 
        )

    def get_move(self, pos, board, dim, safe_players, timeout=2.0):
        if not self.alive:
            return "DEAD"

        current_board_coords = list(board.keys())
        new_board = current_board_coords[self.last_board_len:]
        self.last_board_len = len(current_board_coords)
        
        player_deltas = []
        for p in safe_players:
            pid = p["id"]
            last_len = self.last_trail_lens.get(pid, 0)
            new_trail = p["trail"][last_len:]
            self.last_trail_lens[pid] = len(p["trail"])
            
            player_deltas.append({
                "id": pid,
                "name": p["name"],
                "pos": p["pos"],
                "alive": p["alive"],
                "new_trail": new_trail,
                "is_new": last_len == 0
            })

        state = {"pos": pos, "new_board": new_board, "players": player_deltas, "dim": dim}
        
        try:
            self.process.stdin.write(json.dumps(state) + "\n")
            self.process.stdin.flush()
        except Exception:
            self.stop()
            return "DEAD"

        def read_pipe():
            try:
                raw_output = self.process.stdout.readline(100) 
                return raw_output.strip()
            except Exception:
                return "ERROR"

        try:
            future = self.executor.submit(read_pipe)
            move = future.result(timeout=timeout) 
            return move
        except concurrent.futures.TimeoutError:
            print(f"[{self.name}] TIMED OUT! Terminating process.")
            self.stop()
            return "DEAD"
        except Exception:
            self.stop()
            return "DEAD"

    def stop(self):
        self.alive = False
        try:
            self.process.kill()
            self.executor.shutdown(wait=False)
        except Exception:
            pass