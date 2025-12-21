import customtkinter as ctk
import threading
import time
import os
import sys                 
from pathlib import Path    
from tkinter import filedialog, messagebox
from grabia_core import GrabIAEngine
from collections import deque

UBUNTU_ORANGE = "#E95420"
WIN_BLUE = "#0078D4"

class GrabIAGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("grab-IA: Internet Archive Mass Downloader")
        self.geometry("1100x850")
        
        self.engine = None
        self.workers = []      
        self.scanner = None    
        self.monitor_running = False
        self.last_bytes = 0
        self.last_time = time.time()
        self.worker_widgets = {}
        
        self.protocol("WM_DELETE_WINDOW", self._exit_app)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self._setup_sidebar()
        self._setup_main_view()
        ctk.set_appearance_mode("dark")
        self._update_accent_color()

    def _setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="grab-IA", font=ctk.CTkFont(size=26, weight="bold")).pack(pady=(20, 10))
        self.theme_switch = ctk.CTkSwitch(self.sidebar, text="Dark Mode", command=self._update_accent_color)
        self.theme_switch.select()
        self.theme_switch.pack(pady=10)
        
        base_dir = Path.cwd()
        default_dl = str(base_dir / "downloads")
        
        # All Configurable Arguments on Left
        self.input_path = self._create_entry(self.sidebar, "Input File (IDs/Queries)", "items.txt", browse="file")
        self.output_path = self._create_entry(self.sidebar, "Download Directory", default_dl, browse="dir")
        self.ia_user = self._create_entry(self.sidebar, "IA Email", "")
        self.ia_pass = self._create_entry(self.sidebar, "IA Password", "", show="*")
        self.formats = self._create_entry(self.sidebar, "Formats (e.g. mp3,pdf)", "")
        self.include_rex = self._create_entry(self.sidebar, "Include Regex", "")
        self.exclude_rex = self._create_entry(self.sidebar, "Exclude Regex", "")
        self.worker_count = self._create_entry(self.sidebar, "Worker Threads", "4")
        self.limit = self._create_entry(self.sidebar, "Speed Limit (e.g. 5m)", "0")
        
        self.start_btn = ctk.CTkButton(self.sidebar, text="START JOB", command=self.start_download)
        self.start_btn.pack(pady=(25, 10), padx=20, fill="x")
        self.stop_btn = ctk.CTkButton(self.sidebar, text="CANCEL JOB", state="disabled", command=self.stop_download)
        self.stop_btn.pack(pady=5, padx=20, fill="x")

    def _setup_main_view(self):
        self.main_view = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_view.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        self.progress_label = ctk.CTkLabel(self.main_view, text="SYSTEM IDLE", font=ctk.CTkFont(size=18, weight="bold"))
        self.progress_label.pack(pady=(5, 5))
        
        self.main_progress = ctk.CTkProgressBar(self.main_view, height=12)
        self.main_progress.pack(fill="x", pady=(0, 20))
        self.main_progress.set(0)
        
        stats_grid = ctk.CTkFrame(self.main_view, fg_color="transparent")
        stats_grid.pack(fill="x", pady=(0, 20))
        self.stat_speed = self._create_stat_card(stats_grid, "SPEED", "0 KB/s", 0)
        self.stat_scanned = self._create_stat_card(stats_grid, "ITEMS SCANNED", "0/0", 1)
        self.stat_files = self._create_stat_card(stats_grid, "FILES SAVED", "0/0", 2)
        self.stat_failed = self._create_stat_card(stats_grid, "FAILED", "0", 3)

        ctk.CTkLabel(self.main_view, text="ACTIVE WORKERS", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self.worker_frame = ctk.CTkScrollableFrame(self.main_view, height=180, border_width=1)
        self.worker_frame.pack(fill="x", pady=(5, 15))
        
        ctk.CTkLabel(self.main_view, text="SESSION CONSOLE", font=ctk.CTkFont(size=11, weight="bold")).pack(anchor="w")
        self.log_box = ctk.CTkTextbox(self.main_view, state="disabled", border_width=1)
        self.log_box.pack(fill="both", expand=True, pady=(5, 0))

    def start_download(self):
        try:
            config = {
                "output": self.output_path.get(),
                "workers": int(self.worker_count.get()),
                "formats": [f.strip() for f in self.formats.get().split(',')] if self.formats.get() else [],
                "include": self.include_rex.get() or None,
                "exclude": self.exclude_rex.get() or None,
                "limit_bps": self._parse_limit(self.limit.get()),
                "username": self.ia_user.get() or None,
                "password": self.ia_pass.get() or None
            }
            
            with open(self.input_path.get(), "r") as f:
                ids = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]
            
            if not ids:
                messagebox.showwarning("Warning", "No valid IDs found in the input file.")
                return

            self.engine = GrabIAEngine(config)
            self.workers, self.scanner = self.engine.start(ids)
            
            self.progress_label.configure(text="SCANNING ARCHIVE...", text_color=self.accent)
            self._init_worker_ui(config["workers"])
            self.monitor_running = True
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.update_loop()
        except Exception as e: 
            messagebox.showerror("Error", str(e))

    def update_loop(self):
        if not self.monitor_running or not self.engine: return
        stats = self.engine.get_stats()
        
        if self.scanner and self.scanner.is_alive():
            self.progress_label.configure(text="SCANNING ARCHIVE...")
        elif any(w.is_alive() for w in self.workers):
            self.progress_label.configure(text="DOWNLOADING...", text_color=self.accent)
        else:
            if stats['total_files'] >= 0:
                self.progress_label.configure(text="FINISHED", text_color="#2ECC71")
                self.stop_download(natural_finish=True)
                return

        now = time.time()
        delta = now - self.last_time
        if delta >= 1.0:
            speed = (stats['session_bytes'] - self.last_bytes) / delta
            self.last_bytes, self.last_time = stats['session_bytes'], now
            self.stat_speed.configure(text=f"{speed/1048576:.2f} MB/s" if speed > 1048576 else f"{speed/1024:.1f} KB/s")

        self.stat_scanned.configure(text=f"{stats['scanned_ids']} / {stats['total_ids']}")
        self.stat_files.configure(text=f"{stats['files_done']} / {stats['total_files']}")
        self.stat_failed.configure(text=str(stats['files_failed']))
        self.main_progress.set(stats['files_done'] / max(1, stats['total_files']))
        
        states = self.engine.get_worker_states()
        for i, s in states.items():
            if i in self.worker_widgets:
                self.worker_widgets[i]["pb"].set(s['done']/s['total'] if s['total'] > 0 else 0)
                fname = (s['file'][:50] + '...') if len(s['file']) > 53 else s['file']
                self.worker_widgets[i]["txt"].configure(text=f"[{s['status']}] {fname}")

        # Console logging update
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.insert("end", "\n".join(stats['events'][-100:]))
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

        self.after(500, self.update_loop)

    def _init_worker_ui(self, count):
        for widget in self.worker_frame.winfo_children(): widget.destroy()
        self.worker_widgets = {}
        for i in range(count):
            f = ctk.CTkFrame(self.worker_frame, fg_color="transparent")
            f.pack(fill="x", pady=2)
            lbl = ctk.CTkLabel(f, text=f"W#{i}", width=40, font=("Courier", 12))
            lbl.pack(side="left")
            pb = ctk.CTkProgressBar(f, width=150)
            pb.set(0)
            pb.pack(side="left", padx=10)
            txt = ctk.CTkLabel(f, text="Idle", font=("Courier", 11), anchor="w")
            txt.pack(side="left", fill="x", expand=True)
            self.worker_widgets[i] = {"pb": pb, "txt": txt}

    def stop_download(self, natural_finish=False):
        if not natural_finish and self.monitor_running:
            self.progress_label.configure(text="JOB CANCELLED", text_color="#E74C3C")
        if self.engine: self.engine.stop_event.set()
        self.monitor_running = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def _exit_app(self):
        self.stop_download()
        self.destroy()

    def _update_accent_color(self):
        is_dark = self.theme_switch.get()
        ctk.set_appearance_mode("dark" if is_dark else "light")
        self.accent = UBUNTU_ORANGE if is_dark else WIN_BLUE
        self.start_btn.configure(fg_color=self.accent)
        self.main_progress.configure(progress_color=self.accent)

    def _parse_limit(self, s):
        import re
        if not s or s == "0": return 0
        m = re.match(r"(\d+)\s*([kKmMgG]?)", str(s))
        if not m: return 0
        mult = {'k': 1024, 'm': 1024**2, 'g': 1024**3}.get(m.group(2).lower(), 1)
        return int(m.group(1)) * mult

    def _create_entry(self, parent, label, default, browse=None, show=None):
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(8, 0), padx=20, anchor="w")
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=20)
        e = ctk.CTkEntry(f, height=28, show=show)
        e.insert(0, default)
        e.pack(side="left", fill="x", expand=True)
        if browse: ctk.CTkButton(f, text="...", width=30, command=lambda: self._browse(e, browse)).pack(side="right", padx=(5,0))
        return e

    def _browse(self, entry, mode):
        p = filedialog.askopenfilename() if mode == "file" else filedialog.askdirectory()
        if p: entry.delete(0, "end"); entry.insert(0, p)

    def _create_stat_card(self, parent, label, val, col):
        card = ctk.CTkFrame(parent, corner_radius=8)
        card.grid(row=0, column=col, padx=5, sticky="nsew")
        parent.grid_columnconfigure(col, weight=1)
        ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=10, weight="bold")).pack(pady=(8,0))
        v = ctk.CTkLabel(card, text=val, font=ctk.CTkFont(size=16, weight="bold"))
        v.pack(pady=(0,8))
        return v

if __name__ == "__main__":
    app = GrabIAGUI()
    app.mainloop()
