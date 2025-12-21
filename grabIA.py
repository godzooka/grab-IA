import argparse
import sys
import time
import re
import shutil
import os
from pathlib import Path
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.progress import ProgressBar
from rich.console import Console
from grabia_core import GrabIAEngine

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

console = Console()

def initialize_deployment():
    readme_md = Path("readme.md")
    if not readme_md.exists():
        content = """# 🏛️ grab-IA: Internet Archive Mass Downloader

**grab-IA** is a high-performance, multi-threaded archival tool designed to mirror Internet Archive (IA) items with precision. 
It features a real-time terminal dashboard, bandwidth throttling, and persistent resume capabilities. 

### 🚀 Key Features

 **Smart Resuming:** Uses a local SQLite database (`grabia_state.db`) to track every byte. 
 **Threaded Architecture:** Separate pools for metadata scanning and file downloading ensure maximum throughput. 
 **Precision Filtering:** Support for both simple extension filtering (e.g., `mp3,pdf`) and complex Regex patterns. 
 **Bandwidth Management:** Built-in "token-bucket" throttling to respect your network's limits. 
 **Container Ready:** Includes deployment logic to maintain a `deploy/` folder for easy environment isolation. 

 🔄 Smart Resuming & Data Integrity

**grab-IA** is built for reliability over long-running archival sessions. 
It uses a local SQLite database to ensure no bandwidth is wasted on redundant data. 

**How it Works:**
* **State Tracking:** Every successfully downloaded file is logged in the database with its item ID, filename, and size. 
* **Pre-Download Verification:** Before a worker starts a download, the engine verifies if the file is already complete in the database. 
* **Interruption Recovery:** If you stop the script (Ctrl+C), all progress is saved. 
* **Restarting:** Will skip completed files and resume partial `.part` downloads. 

### 🛠️ Installation & Setup

It is highly recommended to run this tool in a Python Virtual Environment (venv). 

1. **Clone or Save the Files:** Ensure `grabIA.py` and `grabia_core.py` are in the same directory. 
2. **Create the Virtual Environment:** ```bash
   python3 -m venv venv
   ```
3. **Activate and Install Dependencies:** *Requires Python 3.8+* * On macOS/Linux: `source venv/bin/activate` 
   * On Windows: `venv\\Scripts\\activate` 
   * `pip install internetarchive rich requests python-dotenv` 

### ⚙️ Command Line Arguments

| Argument | Description | Default |
| :--- | :--- | :--- |
| `input` | **(Required)** Path to a text file containing IA Item IDs (one per line). | N/A | 
| `-o`, `--output` | The directory where files will be saved. | `downloads` | 
| `-w`, `--workers` | Number of simultaneous download threads. | `4` | 
| `-f`, `--format` | Comma-separated list of file extensions (e.g., `mp3,pdf`). | All | 
| `-l`, `--limit` | Global speed limit (e.g., `500k`, `2m` for 2MB/s). | Unlimited | 
| `--include` | Regex pattern: only download files matching this name. | None | 
| `--exclude` | Regex pattern: skip files matching this name. | None | 
| `--username` | Your Internet Archive email/username. | None | 
| `--password` | Your Internet Archive password. | None | 

**Example Usage:**
`python3 grabIA.py my_items.txt -w 8 -f mp4 --limit 5m` 

### 📦 Understanding Self-Packaging Logic

Unlike traditional scripts that require manual file management, **grab-IA** includes a built-in deployment initializer. 

**How the `deploy/` Folder Works:** Every time you run the script, it checks for and maintains a `deploy/` directory: 
* **Environment Isolation:** It generates a standalone `requirements.txt` containing only the necessary libraries. 
* **Code Portability:** It creates exact copies of the core logic (`grabIA.py` and `grabia_core.py`) inside the folder. 
* **Configuration Readiness:** It ensures a basic `README.md` is present. 

| Component | Purpose |
| :--- | :--- |
| `deploy/grabIA.py` | The main entry point for the tool. | 
| `deploy/grabia_core.py` | The underlying engine handling threads and SQLite. | 
| `deploy/requirements.txt` | Used to install dependencies via `pip install -r`. | 

### 🐳 Running with Docker

**grab-IA** is fully containerized. 
1. **Build the Image:** `docker build -t grab-ia .` 
2. **Run the Container:** `docker run -v $(pwd)/downloads:/app/downloads grab-ia <path_to_ids.txt>` 

---
❤️ **Support the Internet Archive**
#Support their mission at [archive.org/donate](https://archive.org/donate). 
"""
        readme_md.write_text(content, encoding="utf-8")
    
    deploy_dir = Path("deploy")
    deploy_dir.mkdir(exist_ok=True)
    
    req_file = deploy_dir / "requirements.txt"
    if not req_file.exists():
        req_file.write_text("internetarchive\nrich\nrequests\npython-dotenv\n")
    
    for f_name in ["grabIA.py", "grabia_core.py"]:
        src = Path(f_name)
        if src.exists():
            shutil.copy2(src, deploy_dir / f_name)

def format_size(b: float) -> str:
    if b <= 0: return "0 B"
    for u in ['B','KB','MB','GB','TB']:
        if b < 1024: return f"{b:.2f} {u}"
        b /= 1024
    return f"{b:.2f} PB"

def parse_limit(limit_str: str) -> int:
    if not limit_str: return 0
    match = re.match(r"(\d+)\s*([kKmMgG]?)", limit_str)
    if not match: return 0
    val, unit = int(match.group(1)), match.group(2).lower()
    if unit == 'k': return val * 1024
    if unit == 'm': return val * 1024 * 1024
    if unit == 'g': return val * 1024 * 1024 * 1024
    return val

def format_time(seconds: float) -> str:
    if seconds < 0 or seconds > 10**7: return "---"
    mins, secs = divmod(int(seconds), 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"

def update_display(layout, engine, current_speed):
    stats = engine.get_stats()
    prog_val = min(1.0, stats['files_done'] / max(1, stats['total_files']))
    prog_msg = f"Job Progress: ({format_size(stats['down_bytes'])} / {format_size(max(1, stats['total_bytes']))})"
    rem_bytes = max(0, stats['total_bytes'] - stats['down_bytes'])
    eta_str = f"[bold green]{format_time(rem_bytes / current_speed)}[/]" if current_speed > 50*1024 else "---"
    
    # Updated Header Line
    layout["header"].update(Panel(f"grab-IA Internet Archive Downloader | Status: {'SCANNING' if stats['is_scanning'] else 'DOWNLOADING'}", border_style="blue"))
    
    st = Table.grid(padding=1)
    st.add_column(style="cyan", width=25)
    st.add_row("Scanned Archives:", f"{stats['scanned_ids']} / {stats['total_ids']}")
    st.add_row("Files Found:", f"{stats['total_files']}")
    st.add_row("Current Speed:", f"{format_size(current_speed)}/s")
    st.add_row("Job ETA:", eta_str)
    layout["stats"].update(Panel(st, title="Session Metrics", border_style="green"))
    layout["monitor"].update(Panel("\n".join(stats['events']), title="System Monitor", border_style="yellow"))
    wt = Table(expand=True, box=None)
    wt.add_column("Worker", width=8); wt.add_column("Progress"); wt.add_column("File")
    for wid, s in engine.get_worker_states().items():
        p_val = (s['done'] / s['total']) if s['total'] > 0 else 0
        display_name = (s['file'][:45] + '...') if len(s['file']) > 48 else s['file']
        wt.add_row(f"W#{wid}", ProgressBar(total=1.0, completed=p_val, width=20), display_name)
    layout["workers"].update(Panel(wt, title="Active Threads"))
    layout["footer"].update(Panel(ProgressBar(total=1.0, completed=prog_val), title=prog_msg))

def print_final_summary(engine, interrupted=False):
    stats = engine.get_stats()
    duration = time.time() - stats['start_time']
    summary_table = Table(title="--- Final Session Summary ---", box=None, show_header=False)
    summary_table.add_column("Metric", style="bold cyan")
    summary_table.add_column("Value", style="white")
    summary_table.add_row("Exit Status:", "[bold red]USER STOPPED[/]" if interrupted else "[bold green]COMPLETED[/]")
    summary_table.add_row("Elapsed Time:", format_time(duration))
    summary_table.add_row("Total Files:", f"{stats['total_files']}")
    summary_table.add_row("Successes:", f"[green]{stats['files_done']}[/]")
    summary_table.add_row("Total Downloaded:", format_size(stats['down_bytes']))
    print("\n")
    console.print(Panel(summary_table, border_style="blue", expand=False))

def main():
    initialize_deployment()
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="File with Item IDs")
    parser.add_argument("-o", "--output", default="downloads")
    parser.add_argument("-w", "--workers", type=int, default=4)
    parser.add_argument("-f", "--format", help="Formats (e.g. mp3,pdf)")
    parser.add_argument("-l", "--limit", help="Speed limit (e.g. 500k, 2m)")
    parser.add_argument("--include", help="Regex to include")
    parser.add_argument("--exclude", help="Regex to exclude")
    parser.add_argument("--username", help="IA Username")
    parser.add_argument("--password", help="IA Password")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists(): sys.exit(f"Error: {args.input} not found.")
    with open(input_path, "r") as f:
        ids = [l.strip() for l in f if l.strip()]
    
    engine = GrabIAEngine({
        "output": args.output, "workers": args.workers,
        "include": args.include, "exclude": args.exclude,
        "formats": [f.strip().lstrip('.') for f in args.format.split(',')] if args.format else [], 
        "limit_bps": parse_limit(args.limit),
        "username": args.username or os.getenv("IA_USER"), 
        "password": args.password or os.getenv("IA_PASS")
    })
    
    layout = Layout()
    layout.split_column(Layout(name="header", size=3), Layout(name="body", ratio=1), 
                        Layout(name="workers", size=args.workers + 4), Layout(name="footer", size=3))
    layout["body"].split_row(Layout(name="stats", size=45), Layout(name="monitor", ratio=1))
    
    wkrs, scanner = engine.start(ids)
    last_session_b, last_t, speed_raw, interrupted = 0, time.time(), 0, False

    with Live(layout, refresh_per_second=4, screen=True):
        try:
            while any(w.is_alive() for w in wkrs) or scanner.is_alive():
                now = time.time()
                delta = now - last_t
                if delta >= 1.0:
                    snap = engine.get_stats()
                    speed_raw = (snap['session_bytes'] - last_session_b) / delta
                    last_session_b, last_t = snap['session_bytes'], now
                update_display(layout, engine, speed_raw)
                time.sleep(0.1)
                if not scanner.is_alive() and engine.download_queue.empty() and not any(s['status'] == "Downloading" for s in engine.get_worker_states().values()):
                    break
        except KeyboardInterrupt:
            interrupted = True
            engine.stop_event.set()

    for w in wkrs: w.join(timeout=1)
    print_final_summary(engine, interrupted)

if __name__ == "__main__":
    main()
