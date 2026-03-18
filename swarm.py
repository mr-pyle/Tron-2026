import socket
import threading
import json
import struct
import traceback
import os
import math
import concurrent.futures
from tournament import headless_worker

# --- NETWORK PROTOCOL ---
def send_msg(sock, msg_dict):
    """Safely packs and sends JSON data with a 4-byte length prefix."""
    try:
        data = json.dumps(msg_dict).encode('utf-8')
        sock.sendall(struct.pack('>I', len(data)) + data)
    except Exception as e:
        pass

def recvall(sock, n):
    """Helper to ensure we read exactly 'n' bytes."""
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

def recv_msg(sock):
    """Safely receives the length prefix, then the exact JSON payload."""
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    data = recvall(sock, msglen)
    if not data:
        return None
    return json.loads(data.decode('utf-8'))

# --- SWARM SERVER ---
class SwarmServer:
    def __init__(self, update_ui_callback, match_complete_callback, tournament_complete_callback):
        self.port = 5050
        self.server_socket = None
        self.clients = {} # {client_id: {"sock": socket, "cores": int, "pending": int}}
        self.running = False
        self.lock = threading.Lock() # Thread safety for math operations
        
        # Tournament State
        self.target_runs = 0
        self.completed_runs = 0
        self.pending_runs = 0
        self.results = []
        self.tourney_finished = False
        
        # Callbacks
        self.update_ui = update_ui_callback
        self.match_complete = match_complete_callback
        self.tourney_complete = tournament_complete_callback

    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind(('0.0.0.0', self.port))
        self.server_socket.listen(10)
        self.running = True
        
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        self.update_ui(f"Server Host IP: {local_ip}")
        
        threading.Thread(target=self._accept_clients, daemon=True).start()

    def _accept_clients(self):
        while self.running:
            try:
                client_sock, addr = self.server_socket.accept()
                client_id = f"{addr[0]}:{addr[1]}"
                
                with self.lock:
                    # Initialize with 1 core until handshake is received
                    self.clients[client_id] = {"sock": client_sock, "cores": 1, "pending": 0}
                
                self.update_ui(f"Connected: {client_id}")
                threading.Thread(target=self._handle_client, args=(client_sock, client_id), daemon=True).start()
            except Exception:
                if self.running: self.update_ui("Error accepting client.")

    def _handle_client(self, client_sock, client_id):
        while self.running:
            try:
                msg = recv_msg(client_sock)
                if not msg: break
                
                # 1. The Core Handshake
                if msg.get("type") == "handshake":
                    with self.lock:
                        if client_id in self.clients:
                            self.clients[client_id]["cores"] = msg.get("cores", 1)
                            
                # 2. Receiving a Batch of Results
                elif msg.get("type") == "batch_result":
                    batch_data = msg["data"]
                    batch_size = len(batch_data)
                    
                    with self.lock:
                        self.completed_runs += batch_size
                        self.pending_runs -= batch_size
                        self.clients[client_id]["pending"] -= batch_size
                        self.results.extend(batch_data) # Flatten the batch into the main list
                        
                        self.match_complete(self.completed_runs, self.target_runs)
                        self._assign_work(client_id) # Ask them to do more!
                        
            except Exception as e:
                break
                
        # Cleanup disconnect (Resilience: Reassign lost runs if a laptop closes!)
        with self.lock:
            if client_id in self.clients:
                lost_runs = self.clients[client_id]["pending"]
                self.pending_runs -= lost_runs
                del self.clients[client_id]
                self.update_ui(f"Disconnected: {client_id}")
                
                # If they dropped matches, give them to someone else
                if lost_runs > 0 and not self.tourney_finished:
                    for cid in list(self.clients.keys()):
                        self._assign_work(cid)
                        
        client_sock.close()

    def _assign_work(self, client_id):
        """Calculates a fair chunk of matches and sends them to the client."""
        if self.tourney_finished or client_id not in self.clients: return
        
        remaining = self.target_runs - (self.completed_runs + self.pending_runs)
        
        # Check if tournament is completely finished
        if remaining <= 0:
            if self.completed_runs >= self.target_runs and not self.tourney_finished:
                self.tourney_finished = True
                self.tourney_complete(self.results)
            return
            
        # DYNAMIC BATCH MATH
        active_clients = len(self.clients)
        fair_chunk = math.ceil(remaining / active_clients)
        client_cores = self.clients[client_id]["cores"]
        
        # Never exceed remaining matches, the client's core count, or the fair share
        chunk = min(remaining, client_cores, fair_chunk)
        if chunk <= 0: return
        
        self.pending_runs += chunk
        self.clients[client_id]["pending"] += chunk
        send_msg(self.clients[client_id]["sock"], {"type": "run_batch", "count": chunk})

    def start_tournament(self, grid_dim, selected_bots, code_snapshots, num_runs):
        if not self.clients:
            self.update_ui("Error: No clients connected!")
            return
            
        with self.lock:
            self.target_runs = num_runs
            self.completed_runs = 0
            self.pending_runs = 0
            self.results = []
            self.tourney_finished = False
            for cid in self.clients:
                self.clients[cid]["pending"] = 0
        
        # 1. Distribute the bot code to everyone
        init_payload = {
            "type": "init",
            "grid_dim": grid_dim,
            "selected_bots": selected_bots,
            "code_snapshots": code_snapshots
        }
        with self.lock:
            for client_info in self.clients.values():
                send_msg(client_info["sock"], init_payload)
            
        # 2. Tell everyone to start running their fair batch
        with self.lock:
            for client_id in list(self.clients.keys()):
                self._assign_work(client_id)

    def stop(self):
        self.running = False
        if self.server_socket: self.server_socket.close()


# --- SWARM CLIENT ---
class SwarmClient:
    def __init__(self, update_ui_callback):
        self.client_socket = None
        self.running = False
        self.update_ui = update_ui_callback
        
        # Tournament Memory
        self.grid_dim = None
        self.selected_bots = None
        self.code_snapshots = None
        self.runs_completed = 0

    def connect(self, server_ip):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((server_ip, 5050))
            self.running = True
            
            # --- THE HANDSHAKE ---
            cores = os.cpu_count() or 1
            send_msg(self.client_socket, {"type": "handshake", "cores": cores})
            
            self.update_ui(f"✅ Connected! (Reported {cores} Cores)")
            threading.Thread(target=self._listen_to_server, daemon=True).start()
        except Exception as e:
            self.update_ui(f"❌ Connection failed: {e}")

    def _listen_to_server(self):
        while self.running:
            try:
                msg = recv_msg(self.client_socket)
                if not msg: break
                
                if msg.get("type") == "init":
                    self.grid_dim = msg["grid_dim"]
                    self.selected_bots = msg["selected_bots"]
                    self.code_snapshots = msg["code_snapshots"]
                    self.runs_completed = 0
                    self.update_ui("Received Tournament Data. Waiting for start...")
                    
                elif msg.get("type") == "run_batch":
                    count = msg["count"]
                    self.update_ui(f"Processing Batch of {count} Matches...")
                    
                    batch_results = []
                    
                    # --- THE MULTI-CORE THREAD POOL ---
                    with concurrent.futures.ThreadPoolExecutor(max_workers=count) as executor:
                        # Queue up the matches
                        futures = [executor.submit(headless_worker, self.grid_dim, self.selected_bots, self.code_snapshots) for _ in range(count)]
                        
                        # Gather results as they finish concurrently
                        for future in concurrent.futures.as_completed(futures):
                            batch_results.append(future.result())
                            self.runs_completed += 1
                            self.update_ui(f"Processing Batch... (Total completed: {self.runs_completed})")
                    
                    # Send the entire batch back at once
                    send_msg(self.client_socket, {"type": "batch_result", "data": batch_results})
                    self.update_ui(f"Batch submitted! (Total completed: {self.runs_completed})")
                    
            except Exception as e:
                self.update_ui(f"Server disconnected or error: {e}")
                traceback.print_exc()
                break
                
        self.client_socket.close()
        self.running = False

    def disconnect(self):
        self.running = False
        if self.client_socket: self.client_socket.close()