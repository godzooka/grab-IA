import os
import re
import time
import hashlib
import threading
import sqlite3
import requests
import logging
from queue import Queue, Empty
from pathlib import Path
from collections import deque
from typing import Dict, Any, List, Set
from dataclasses import dataclass
import internetarchive as ia
from internetarchive import get_item, configure 
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor

@dataclass
class DownloadTask:
    item_id: str
    file_name: str
    safe_file_name: str
    expected_md5: str
    size: int
    attempts: int = 0

class GrabIAEngine:
    def __init__(self, config: Dict[str, Any]):
        self.lock = threading.Lock()
        self.worker_lock = threading.Lock()
        self.stop_event = threading.Event()
        
        self.config = config
        self.output_dir = Path(config.get('output', 'downloads')).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.num_workers = config.get('workers', 4)
        self.num_scanners = min(10, self.num_workers * 2) 
        self.max_retries = config.get('retries', 3)
        self.start_time = time.time()
        
        self.bps_limit = config.get('limit_bps', 0) 
        self._tokens = self.bps_limit
        self._last_token_update = time.time()
        
        self.include_re = re.compile(config['include']) if config.get('include') else None
        self.exclude_re = re.compile(config['exclude']) if config.get('exclude') else None
        
        formats = config.get('formats', [])
        self.format_re = re.compile(rf".*\.({'|'.join(formats)})$", re.IGNORECASE) if formats else None

        self.log_file = self.output_dir / "grabia_session.log"
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger("GrabIA")
        self.ui_events = deque(maxlen=15)

        self.session = requests.Session()
        self._authenticate(config.get('username'), config.get('password'))

        retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
        adapter = HTTPAdapter(pool_connections=self.num_workers + self.num_scanners + 2, 
                              pool_maxsize=self.num_workers + self.num_scanners + 5, 
                              max_retries=retries)
        self.session.mount('https://', adapter)
        
        self.download_queue = Queue(maxsize=config.get('queue_size', 50000))
        self.db_queue = Queue() 
        self.worker_states = {i: {"file": "Idle", "status": "Waiting", "done": 0, "total": 0} for i in range(self.num_workers)}
        
        self.db_path = self.output_dir / "grabia_state.db"
        self._init_db()
        self.db_thread = threading.Thread(target=self._db_manager, daemon=True)
        self.db_thread.start()
        
        self.total_ids = 0
        self.scanned_ids_count = 0
        self.total_files_found = 0
        self.files_finished = 0
        self.files_failed = 0
        self.total_bytes = 0
        self.downloaded_bytes = 0
        self.current_session_bytes = 0
        self.is_scanning = False

    def _authenticate(self, username, password):
        if username and password:
            try:
                configure(username, password)
                ia_session = ia.get_session()
                self.session.cookies.update(ia_session.cookies)
                self.log_event(f"Logged in as: {username}")
                self.logger.info(f"--- Authenticated Session: {username} ---")
            except Exception as e:
                self.log_event("Login Failed", "error")
                self.logger.error(f"Auth Error: {e}")
        else:
            self.log_event("Guest Mode (Anonymous)")
            self.logger.info("--- Anonymous Session ---")

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        with conn:
            conn.execute("CREATE TABLE IF NOT EXISTS files (id TEXT, filename TEXT, status TEXT, size INTEGER, PRIMARY KEY(id, filename))")
        conn.close()

    def _db_manager(self):
        conn = sqlite3.connect(self.db_path, timeout=60)
        while not self.stop_event.is_set() or not self.db_queue.empty():
            try:
                task = self.db_queue.get(timeout=1)
                with conn:
                    conn.execute("INSERT OR REPLACE INTO files (id, filename, status, size) VALUES (?, ?, 'completed', ?)", task)
                self.db_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Database Error: {e}")
        conn.close()

    def _throttle(self, amount: int):
        if self.bps_limit <= 0: return
        while amount > 0:
            with self.lock:
                now = time.time()
                elapsed = now - self._last_token_update
                self._tokens = min(self.bps_limit, self._tokens + (elapsed * self.bps_limit))
                self._last_token_update = now
                can_send = min(amount, int(self._tokens))
                if can_send > 0:
                    self._tokens -= can_send
                    amount -= can_send
            if amount > 0:
                time.sleep(0.05)

    def log_event(self, msg: str, level: str = "info"):
        timestamp = time.strftime('%H:%M:%S')
        with self.lock:
            self.ui_events.append(f"[{timestamp}] {msg}")
        if level == "error":
            self.logger.error(msg)
        else:
            self.logger.info(msg)

    def _get_completed_files(self, item_id: str) -> Set[str]:
        conn = sqlite3.connect(self.db_path)
        res = conn.execute("SELECT filename FROM files WHERE id=? AND status='completed'", (item_id,)).fetchall()
        conn.close()
        return {row[0] for row in res}

    def _scan_single_item(self, item_id: str):
        if self.stop_event.is_set(): return
        clean_id = item_id.strip()
        if not clean_id: return
        try:
            item = get_item(clean_id)
            if not item.exists:
                return self.log_event(f"ID not found: {clean_id}", "error")
            
            completed_set = self._get_completed_files(clean_id)
            valid_files = [f for f in item.get_files() if not f.name.endswith(('_meta.xml', '_files.xml', 'archive.torrent'))]
            
            for f in valid_files:
                if self.stop_event.is_set(): return
                if self.format_re and not self.format_re.match(f.name): continue
                if self.include_re and not self.include_re.search(f.name): continue
                if self.exclude_re and self.exclude_re.search(f.name): continue
                
                with self.lock: self.total_files_found += 1
                name_parts = f.name.split('/')
                safe_parts = [re.sub(r'[\\*?:"<>|]', "_", p) for p in name_parts]
                sub_dir = self.output_dir / clean_id / Path(*safe_parts[:-1])
                sub_dir.mkdir(parents=True, exist_ok=True)
                dest = sub_dir / safe_parts[-1]
                size = int(f.size or 0)
                
                if f.name in completed_set and dest.exists():
                    with self.lock:
                        self.files_finished += 1
                        self.total_bytes += size
                        self.downloaded_bytes += size
                else:
                    self.download_queue.put(DownloadTask(clean_id, f.name, str(dest), f.md5, size))
                    with self.lock: self.total_bytes += size
        except Exception as e:
            self.log_event(f"Scan Error {item_id}: {str(e)[:50]}", "error")
        finally:
            with self.lock: self.scanned_ids_count += 1

    def _worker_consumer(self, wid: int):
        while not self.stop_event.is_set():
            try:
                task = self.download_queue.get(timeout=1)
                self._download_file(wid, task)
                self.download_queue.task_done()
            except Empty:
                if not self.is_scanning and self.download_queue.empty():
                    break

    def _download_file(self, worker_id: int, task: DownloadTask):
        dest = Path(task.safe_file_name)
        temp_dest = dest.with_suffix(".part")
        url = f"https://archive.org/download/{task.item_id}/{task.file_name}"
        initial_pos = temp_dest.stat().st_size if temp_dest.exists() else 0
        if initial_pos >= task.size: initial_pos = 0
        mode = "ab" if initial_pos > 0 else "wb"
        headers = {'Range': f"bytes={initial_pos}-"} if initial_pos > 0 else {}
        if initial_pos > 0:
            with self.lock: self.downloaded_bytes += initial_pos
        try:
            with self.worker_lock:
                self.worker_states[worker_id] = {"file": task.file_name, "status": "Downloading", "done": initial_pos, "total": task.size}
            resp = self.session.get(url, headers=headers, stream=True, timeout=(10, 60))
            if initial_pos > 0 and resp.status_code == 416: 
                initial_pos, mode, resp = 0, "wb", self.session.get(url, stream=True, timeout=(10, 60))
            resp.raise_for_status()
            with open(temp_dest, mode) as f:
                for chunk in resp.iter_content(chunk_size=64*1024): 
                    if self.stop_event.is_set(): return
                    self._throttle(len(chunk))
                    f.write(chunk)
                    with self.lock: 
                        self.downloaded_bytes += len(chunk)
                        self.current_session_bytes += len(chunk)
                    with self.worker_lock: 
                        self.worker_states[worker_id]["done"] += len(chunk)
            if task.expected_md5 and not self._verify_md5(temp_dest, task.expected_md5):
                raise ValueError(f"MD5 Mismatch for {task.file_name}")
            temp_dest.replace(dest)
            self.db_queue.put((task.item_id, task.file_name, task.size))
            self.log_event(f"Completed: {task.file_name}") 
            with self.lock: self.files_finished += 1
        except Exception as e:
            self._handle_error(worker_id, task, temp_dest, str(e), initial_pos)
        finally:
            with self.worker_lock:
                self.worker_states[worker_id] = {"file": "Idle", "status": "Waiting", "done": 0, "total": 0}

    def _verify_md5(self, file_path, expected):
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest() == expected

    def _handle_error(self, worker_id, task, temp_path, error_msg, bytes_at_start):
        if "MD5 Mismatch" in error_msg and temp_path.exists():
            try: temp_path.unlink()
            except: pass
        current_size = temp_path.stat().st_size if temp_path.exists() else 0
        downloaded_this_attempt = current_size - bytes_at_start
        with self.lock: self.downloaded_bytes -= (bytes_at_start + downloaded_this_attempt)
        if task.attempts < self.max_retries and not self.stop_event.is_set():
            task.attempts += 1
            self.log_event(f"Retry {task.attempts}/{self.max_retries}: {task.file_name}")
            self.download_queue.put(task)
        else:
            with self.lock: self.files_failed += 1
            self.log_event(f"Fail: {task.file_name} ({error_msg[:30]})", "error")

    def start(self, item_ids: List[str]):
        self.total_ids = len(item_ids)
        scanner_t = threading.Thread(target=self._run_scanner, args=(item_ids,), daemon=True)
        scanner_t.start()
        workers = [threading.Thread(target=self._worker_consumer, args=(i,), daemon=True) for i in range(self.num_workers)]
        for w in workers: w.start()
        return workers, scanner_t

    def _run_scanner(self, ids):
        self.is_scanning = True
        self.log_event(f"Starting Multi-Threaded Scan ({self.num_scanners} threads)...")
        with ThreadPoolExecutor(max_workers=self.num_scanners) as executor:
            executor.map(self._scan_single_item, ids)
        self.is_scanning = False
        self.log_event("Discovery Complete.")

    def get_stats(self):
        with self.lock:
            return {
                "total_ids": self.total_ids, "scanned_ids": self.scanned_ids_count, 
                "total_bytes": self.total_bytes, "down_bytes": self.downloaded_bytes, 
                "session_bytes": self.current_session_bytes, "is_scanning": self.is_scanning, 
                "events": list(self.ui_events), "files_done": self.files_finished, 
                "total_files": self.total_files_found, "files_failed": self.files_failed,
                "start_time": self.start_time
            }

    def get_worker_states(self):
        with self.worker_lock: return self.worker_states.copy()
