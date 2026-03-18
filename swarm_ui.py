import tkinter as tk
from tkinter import ttk, messagebox
import os
from swarm import SwarmServer, SwarmClient

# Colors from your main theme
SIDEBAR_BG = "#161b22"
DARK_BG = "#0d1117"
ACCENT = "#58a6ff"
TEXT_COLOR = "#c9d1d9"

class SwarmPanel:
    def __init__(self, parent_frame, main_app):
        self.parent = parent_frame
        self.app = main_app  # Reference to the main GUI app if we need it later
        
        self.server = None
        self.client = None
        
        self.build_ui()

    def build_ui(self):
        tk.Label(self.parent, text="SWARM NETWORK", bg=SIDEBAR_BG, fg=ACCENT, font=("Courier", 14, "bold")).pack(pady=(20, 10))
        
        self.run_mode_var = tk.StringVar(value="Local")
        modes = ["Local", "Host Server", "Join as Client"]
        mode_dropdown = ttk.Combobox(self.parent, textvariable=self.run_mode_var, values=modes, state="readonly")
        mode_dropdown.pack(fill=tk.X, padx=20, pady=5)
        mode_dropdown.bind("<<ComboboxSelected>>", self.on_mode_change)

        # -- HOST PANEL --
        self.host_frame = tk.Frame(self.parent, bg=SIDEBAR_BG)
        
        # ADDED COMMAND HERE
        self.btn_start_server = tk.Button(self.host_frame, text="Start Host Server", bg="#2ea043", fg="white", font=("Courier", 10, "bold"), command=self.start_swarm_server)
        self.btn_start_server.pack(fill=tk.X, pady=10)
        
        tk.Label(self.host_frame, text="Server IP / Status:", bg=SIDEBAR_BG, fg=TEXT_COLOR, font=("Courier", 10)).pack(anchor=tk.W)
        self.server_status_lbl = tk.Label(self.host_frame, text="Offline", bg=SIDEBAR_BG, fg="gray", font=("Courier", 10, "bold"))
        self.server_status_lbl.pack(anchor=tk.W, pady=(0, 10))
        
        tk.Label(self.host_frame, text="Connected Clients:", bg=SIDEBAR_BG, fg=TEXT_COLOR, font=("Courier", 10)).pack(anchor=tk.W)
        self.client_listbox = tk.Listbox(self.host_frame, height=5, bg=DARK_BG, fg=TEXT_COLOR, selectbackground=ACCENT)
        self.client_listbox.pack(fill=tk.X, pady=(0, 10))

        self.swarm_tourney_status = tk.Label(self.host_frame, text="", bg=SIDEBAR_BG, fg="yellow", font=("Courier", 10))
        self.swarm_tourney_status.pack(fill=tk.X)

        # -- CLIENT PANEL --
        self.client_frame = tk.Frame(self.parent, bg=SIDEBAR_BG)
        
        tk.Label(self.client_frame, text="Teacher's IP Address:", bg=SIDEBAR_BG, fg=TEXT_COLOR, font=("Courier", 10)).pack(anchor=tk.W, pady=(10, 0))
        self.ip_entry = tk.Entry(self.client_frame, bg=DARK_BG, fg=TEXT_COLOR, insertbackground="white")
        self.ip_entry.pack(fill=tk.X, pady=5)
        
        # ADDED COMMAND HERE
        self.btn_connect = tk.Button(self.client_frame, text="Connect to Swarm", bg=ACCENT, fg="white", font=("Courier", 10, "bold"), command=self.connect_swarm_client)
        self.btn_connect.pack(fill=tk.X, pady=10)
        
        self.client_status_lbl = tk.Label(self.client_frame, text="Waiting...", bg=SIDEBAR_BG, fg="gray", font=("Courier", 10), wraplength=200)
        self.client_status_lbl.pack(fill=tk.X, pady=10)

        # Set initial visibility
        self.on_mode_change()

    def on_mode_change(self, event=None):
        mode = self.run_mode_var.get()
        self.host_frame.pack_forget()
        self.client_frame.pack_forget()
        
        if mode == "Host Server":
            self.host_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        elif mode == "Join as Client":
            self.client_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

    def get_mode(self):
        """Allows the main app to ask if we are running Local or Swarm"""
        return self.run_mode_var.get()

    # ==========================================
    # --- SWARM SERVER CONTROLLERS ---
    # ==========================================
    def start_swarm_server(self):
        if self.server: return
        self.server = SwarmServer(
            update_ui_callback=self.update_server_ui,
            match_complete_callback=self.update_swarm_progress,
            tournament_complete_callback=self.swarm_tournament_done
        )
        self.server.start_server()
        self.btn_start_server.config(state=tk.DISABLED, text="Server Running")

    def update_server_ui(self, msg):
        # Tkinter thread-safe UI updates
        self.parent.after(0, lambda: self._safe_update_server_ui(msg))
        
    def _safe_update_server_ui(self, msg):
        if msg.startswith("Server Host IP:"):
            self.server_status_lbl.config(text=msg.split(":")[1].strip(), fg="#2ea043")
        elif msg.startswith("Connected:"):
            self.client_listbox.insert(tk.END, msg.split(" ")[1])
        elif msg.startswith("Disconnected:"):
            try:
                ip = msg.split(" ")[1]
                idx = self.client_listbox.get(0, tk.END).index(ip)
                self.client_listbox.delete(idx)
            except ValueError:
                pass

    def update_swarm_progress(self, current, total):
        self.parent.after(0, lambda: self.swarm_tourney_status.config(text=f"Swarm Progress: {current}/{total} Matches"))

    def swarm_tournament_done(self, aggregated_results):
        self.parent.after(0, lambda: self.swarm_tourney_status.config(text="Compiling Final Stats..."))
        # Restructure swarm results to match local results exactly
        compiled_stats = {}
        for res in aggregated_results:
            for bot, stats in res.items():
                if bot not in compiled_stats:
                    # --- NEW: Grab the bot's assigned color from the main GUI! ---
                    bot_color = self.app.bot_colors.get(bot, "#ffffff")
                    compiled_stats[bot] = {
                        'ranks': [], 'survivals': [], 'times': [], 'moves': [], 
                        'color': bot_color  # <--- INJECTED HERE
                    }
                compiled_stats[bot]['ranks'].append(stats['rank'])
                compiled_stats[bot]['survivals'].append(stats['survival'])
                compiled_stats[bot]['times'].append(stats['total_time'])
                compiled_stats[bot]['moves'].append(stats['move_count'])
                
        # Send it over to the main GUI to draw the leaderboard!
        self.parent.after(0, lambda: self.app.draw_tournament_progress(compiled_stats, len(aggregated_results), self.server.target_runs))

    # ==========================================
    # --- SWARM CLIENT CONTROLLERS ---
    # ==========================================
    def connect_swarm_client(self):
        ip = self.ip_entry.get().strip()
        if not ip: return
        
        self.client = SwarmClient(update_ui_callback=self.update_client_ui)
        self.btn_connect.config(state=tk.DISABLED, text="Connecting...")
        self.client.connect(ip)

    def update_client_ui(self, msg):
        self.parent.after(0, lambda: self.client_status_lbl.config(text=msg))