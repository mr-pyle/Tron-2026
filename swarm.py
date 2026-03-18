import socket
import threading
import json
import struct
import traceback
from tournament import headless_worker

# --- NETWORK PROTOCOL ---
def send_msg(sock, msg_dict):
    """Safely packs and sends JSON data with a 4-byte length prefix."""
    try:
        data = json.dumps(msg_dict).encode('utf-8')
        # '>I' means Big-Endian Unsigned Integer (4 bytes)
        sock.sendall(struct.pack('>I', len(data)) + data)
    except Exception as e:
        print(f"Send error: {e}")

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
        self.clients = {} # {client_addr: socket}
        self.running = False
        
        # Tournament State
        self.target_runs = 0
        self.completed_runs = 0
        self.pending_runs = 0
        self.results = []
        
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
                self.clients[client_id] = client_sock
                self.update_ui(f"Connected: {client_id}")
                threading.Thread(target=self._handle_client, args=(client_sock, client_id), daemon=True).start()
            except Exception:
                if self.running: self.update_ui("Error accepting client.")

    def _handle_client(self, client_sock, client_id):
        while self.running:
            try:
                msg = recv_msg(client_sock)
                if not msg: break
                
                if msg.get("type") == "result":
                    self.completed_runs += 1
                    self.pending_runs -= 1  # <--- THE MISSING FIX!
                    self.results.append(msg["data"])
                    self.match_complete(self.completed_runs, self.target_runs)
                    
                    # Give them another run if we still need more
                    if self.completed_runs + self.pending_runs < self.target_runs:
                        self.pending_runs += 1
                        send_msg(client_sock, {"type": "run_match"})
                    elif self.completed_runs == self.target_runs: # Changed to exactly equal to prevent double-firing
                        self.tourney_complete(self.results)
                        
            except Exception as e:
                print(f"Client error {client_id}: {e}")
                break
                
        # Cleanup disconnect
        if client_id in self.clients:
            del self.clients[client_id]
            self.update_ui(f"Disconnected: {client_id}")
        client_sock.close()

    def start_tournament(self, grid_dim, selected_bots, code_snapshots, num_runs):
        if not self.clients:
            self.update_ui("Error: No clients connected!")
            return
            
        self.target_runs = num_runs
        self.completed_runs = 0
        self.pending_runs = 0
        self.results = []
        
        # 1. Distribute the heavy bot code to everyone
        init_payload = {
            "type": "init",
            "grid_dim": grid_dim,
            "selected_bots": selected_bots,
            "code_snapshots": code_snapshots
        }
        for sock in self.clients.values():
            send_msg(sock, init_payload)
            
        # 2. Tell everyone to start running a match
        for sock in self.clients.values():
            if self.pending_runs < self.target_runs:
                self.pending_runs += 1
                send_msg(sock, {"type": "run_match"})

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
            self.update_ui("✅ Connected to Server!")
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
                    
                elif msg.get("type") == "run_match":
                    self.update_ui(f"Running Match (Total completed: {self.runs_completed})...")
                    # Run the match locally!
                    results = headless_worker(self.grid_dim, self.selected_bots, self.code_snapshots)
                    self.runs_completed += 1
                    # Send results back
                    send_msg(self.client_socket, {"type": "result", "data": results})
                    self.update_ui(f"Match submitted! (Total completed: {self.runs_completed})")
                    
            except Exception as e:
                self.update_ui(f"Server disconnected or error: {e}")
                traceback.print_exc()
                break
                
        self.client_socket.close()
        self.running = False

    def disconnect(self):
        self.running = False
        if self.client_socket: self.client_socket.close()