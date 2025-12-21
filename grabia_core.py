import os
import re
import time
import sqlite3
import requests
import logging
import threading
import hashlib
from logging.handlers import RotatingFileHandler
from queue import Empty, PriorityQueue # Improved: PriorityQueue instead of Queue
from pathlib import Path
from collections import deque
from typing import Dict, Any, List
from dataclasses import dataclass, field
import internetarchive as ia
from internetarchive import get_item, configure, search_items
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor

@dataclass(order=True)
class DownloadTask:
    # Priority field added for ordering; all other fields match original exactly
    priority: int 
    item_id: str = field(compare=False)
    file_name: str = field(compare=False)
    safe_file_name: str = field(compare=False)
    expected_md5: str = field(compare=False)
    size: int = field(compare=False)
    attempts: int = field(default=0, compare=False)
    error_reason: str = field(default="", compare=False)

class GrabIAEngine:
    def __init__(self, config: Dict[str, Any]):
        self.lock = threading.Lock()
        self.worker_lock = threading.Lock()
        self.db_lock = threading.Lock() 
        self.scan_lock = threading.Lock() 
        self.stop_event = threading.Event()
        self.config = config
        
        # IMPROVEMENT: Bounded PriorityQueue prevents memory spikes on huge scans
        self.download_queue = PriorityQueue(maxsize=10000)
        
        custom_path = config.get('output')
        self.output_dir = Path(custom_path).resolve() if custom_path else (Path.cwd() / "downloads").resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.output_dir / "grabia_state.db"
        self._init_db()
        
        # FIXED: Corrected RotatingFileHandler argument to maxBytes
        self.log_file = (Path.cwd() / "grabia_debug.log").resolve()
        self.logger = logging.getLogger("GrabIA")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = RotatingFileHandler(self.log_file, maxBytes=5*1024*1024, backupCount=3)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

        self.num_workers = config.get('workers', 4)
        self.num_scanners = 10 
        self.max_retries = config.get('retries', 3)
        self.start_time = time.time()
        
        # Original Throttling Variables
        self.bps_limit = config.get('limit_bps', 0) 
        self._tokens = self.bps_limit
        self._last_token_update = time.time()
        
        self.ui_events = deque(maxlen=100)
        self.failed_items_report = {}
        self.session = requests.Session()
        
        # Original Auth Logic
        self._authenticate(config.get('username'), config.get('password'))

        retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
        adapter = HTTPAdapter(pool_connections=self.num_workers + 10, pool_maxsize=self.num_workers + 20, max_retries=retries)
        self.session.mount('https://', adapter)
        
        # RECONCILED: UI Statistics Variables
        self.total_ids = 0
        self.scanned_ids = 0 # FIXED: Restored original variable name
        self.total_files_found = 0
        self.files_finished = 0
        self.total_bytes = 0
        self.downloaded_bytes = 0
        self.current_session_bytes = 0
        self.is_scanning = False
        self.report_generated = False
        
        self.worker_states = {i: {"file": "Idle", "status": "Waiting", "done": 0, "total": 0} for i in range(self.num_workers)}
        
        # IMPROVEMENT: Toggle for metadata preservation (defaults to original behavior)
        self.save_metadata = config.get('save_metadata', False)

    def _init_db(self):
        with self.db_lock:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("CREATE TABLE IF NOT EXISTS files (id TEXT, filename TEXT, status TEXT, size INTEGER, PRIMARY KEY(id, filename))")

    def _authenticate(self, u, p):
        if u and p:
            try:
                configure(u, p)
                self.log_event(f"Authenticated as {u}")
            except Exception: self.log_event("Auth failed - Guest mode")
        else: self.log_event("Guest Mode")

    def log_event(self, msg: str):
        ts = time.strftime('%H:%M:%S')
        evt = f"[{ts}] {msg}"
        with self.lock: self.ui_events.append(evt)
        self.logger.info(msg)

    def get_stats(self):
        """
        RECONCILED: Matches the exact keys required by grabia_gui.py and grabIA.py.
        """
        with self.lock:
            report = [f"{k} -> {v}" for k, v in self.failed_items_report.items() if "Final Fail" in v]
            return {
                "total_ids": self.total_ids,
                "scanned_ids": self.scanned_ids, # FIXED: key 'scanned_ids' verified
                "total_bytes": self.total_bytes,
                "down_bytes": self.downloaded_bytes,
                "session_bytes": self.current_session_bytes,
                "is_scanning": self.is_scanning,
                "events": list(self.ui_events),
                "files_done": self.files_finished,
                "total_files": self.total_files_found,
                "files_failed": len(report),
                "failed_report": report,
                "start_time": self.start_time
            }

    def start(self, input_lines: List[str]):
        self.report_generated = False
        ids = []
        for line in input_lines:
            line = line.strip()
            if not line or line.startswith('#'): continue
            if ":" in line and not line.startswith("http"):
                try:
                    res = search_items(line)
                    for item in res: ids.append(item['identifier'])
                except Exception as e: self.log_event(f"Search Error: {str(e)}")
            else: ids.append(line)
        
        self.total_ids = len(ids)
        scan_thread = threading.Thread(target=self._run_scanner, args=(ids,), daemon=True)
        scan_thread.start()
        
        workers = []
        for i in range(self.num_workers):
            t = threading.Thread(target=self._worker_loop, args=(i,), daemon=True)
            t.start()
            workers.append(t)
        return workers, scan_thread

    def _run_scanner(self, ids):
        self.is_scanning = True
        with ThreadPoolExecutor(max_workers=self.num_scanners) as exe:
            exe.map(self._scan_item, ids)
        self.is_scanning = False
        self.log_event("Scanning complete.")

    def _scan_item(self, item_id: str):
        if self.stop_event.is_set(): return
        with self.scan_lock: time.sleep(0.1) # Rate-limiting protection
        try:
            item = get_item(item_id)
            if not item.exists: return
            
            meta_names = ["_meta.xml", "_files.xml"] if self.save_metadata else []
            fmts = self.config.get('formats', [])
            inc = self.config.get('include')
            exc = self.config.get('exclude')

            for f in item.get_files():
                fname = f.name
                is_meta = fname in meta_names
                
                if not is_meta:
                    if fname.endswith(('_meta.xml', '_files.xml', 'archive.torrent')): continue
                    if fmts and not any(fname.lower().endswith(fmt.lower()) for fmt in fmts): continue
                    if inc and not re.search(inc, fname): continue
                    if exc and re.search(exc, fname): continue
                
                safe = "".join([c if c.isalnum() or c in "._- " else "_" for c in fname])
                sz = int(f.size or 0)
                
                with self.db_lock:
                    with sqlite3.connect(self.db_path, timeout=30) as conn:
                        if conn.execute("SELECT 1 FROM files WHERE id=? AND filename=? AND status='completed'", (item_id, fname)).fetchone():
                            with self.lock: self.files_finished += 1
                            continue

                with self.lock:
                    self.total_files_found += 1
                    self.total_bytes += sz
                
                # Bounded queue: Put will block if queue is full (Lazy-loading effect)
                self.download_queue.put(DownloadTask(
                    priority=1 if is_meta else 2,
                    item_id=item_id, file_name=fname, safe_file_name=safe, 
                    expected_md5=f.md5 or "", size=sz
                ))
        except Exception as e: self.log_event(f"Scan Fail {item_id}: {str(e)[:40]}")
        finally:
            with self.lock: self.scanned_ids += 1

    def _worker_loop(self, wid: int):
        while not self.stop_event.is_set():
            try:
                task = self.download_queue.get(timeout=1)
                self._download_logic(wid, task)
                self.download_queue.task_done()
            except Empty:
                if not self.is_scanning and self.download_queue.empty(): break

    def _download_logic(self, wid, task):
        item_dir = self.output_dir / task.item_id
        item_dir.mkdir(parents=True, exist_ok=True)
        dest = item_dir / task.safe_file_name
        part = dest.with_suffix(dest.suffix + ".part")
        
        try:
            with self.worker_lock:
                self.worker_states[wid] = {"file": task.file_name, "status": "Connecting", "done": 0, "total": task.size}

            url = f"https://archive.org/download/{task.item_id}/{task.file_name}"
            headers = {}
            start_pos = part.stat().st_size if part.exists() else 0
            if start_pos < task.size: headers['Range'] = f"bytes={start_pos}-"
            
            resp = self.session.get(url, headers=headers, stream=True, timeout=30)
            resp.raise_for_status()
            
            with self.worker_lock: self.worker_states[wid]['status'] = "Downloading"
            
            mode = 'ab' if 'Content-Range' in resp.headers else 'wb'
            with open(part, mode) as f:
                for chunk in resp.iter_content(chunk_size=1024*1024):
                    if self.stop_event.is_set(): return
                    
                    # Token-Bucket Throttling
                    if self.bps_limit > 0:
                        while self._tokens < len(chunk):
                            now = time.time()
                            self._tokens = min(self.bps_limit, self._tokens + self.bps_limit * (now - self._last_token_update))
                            self._last_token_update = now
                            if self._tokens < len(chunk): time.sleep(0.1)
                        self._tokens -= len(chunk)

                    f.write(chunk)
                    with self.lock: 
                        self.downloaded_bytes += len(chunk)
                        self.current_session_bytes += len(chunk)
                    with self.worker_lock: self.worker_states[wid]['done'] += len(chunk)

            # Verification: Post-download Integrity
            if part.stat().st_size >= task.size:
                md5 = hashlib.md5()
                with open(part, "rb") as vf:
                    for chunk in iter(lambda: vf.read(1024*1024), b""):
                        md5.update(chunk)
                
                if not task.expected_md5 or md5.hexdigest() == task.expected_md5:
                    part.replace(dest) # Atomic Swap
                    with self.db_lock:
                        with sqlite3.connect(self.db_path, timeout=30) as conn:
                            conn.execute("INSERT OR REPLACE INTO files VALUES (?, ?, 'completed', ?)", (task.item_id, task.file_name, task.size))
                    with self.lock: self.files_finished += 1
                else:
                    if part.exists(): part.unlink()
                    raise Exception("MD5 Integrity Failed")
            else: raise Exception("Size mismatch")

        except Exception as e: self._handle_error(task, str(e))
        finally:
            with self.worker_lock:
                self.worker_states[wid] = {"file": "Idle", "status": "Waiting", "done": 0, "total": 0}

    def _handle_error(self, task, msg):
        if task.attempts < self.max_retries and not self.stop_event.is_set():
            task.attempts += 1
            self.download_queue.put(task)
        else:
            with self.lock: self.failed_items_report[task.file_name] = f"Final Fail: {msg[:40]}"

    def get_worker_states(self):
        with self.worker_lock: return self.worker_states.copy()

    def stop(self): self.stop_event.set()
