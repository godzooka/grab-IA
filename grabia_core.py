import os
import re
import time
import sqlite3
import requests
import logging
import threading
import hashlib
from logging.handlers import RotatingFileHandler
from queue import Queue, Empty
from pathlib import Path
from collections import deque
from typing import Dict, Any, List
from dataclasses import dataclass
import internetarchive as ia
from internetarchive import get_item, configure, search_items
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
    error_reason: str = ""

class GrabIAEngine:
    """
    Core engine for Internet Archive archival. 
    Hardened for thread-safety, resume support, and full MD5 integrity verification.
    """
    def __init__(self, config: Dict[str, Any]):
        self.lock = threading.Lock()
        self.worker_lock = threading.Lock()
        self.db_lock = threading.Lock() 
        self.stop_event = threading.Event()
        self.config = config
        
        self.output_dir = (Path.cwd() / "downloads").resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.log_file = Path.cwd() / "grabia_debug.log"
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
        
        self.bps_limit = config.get('limit_bps', 0) 
        self._tokens = self.bps_limit
        self._last_token_update = time.time()
        
        self.ui_events = deque(maxlen=100)
        self.failed_items_report = {}
        self.session = requests.Session()
        self._authenticate(config.get('username'), config.get('password'))

        retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
        adapter = HTTPAdapter(pool_connections=self.num_workers + 10, 
                              pool_maxsize=self.num_workers + 20, 
                              max_retries=retries)
        self.session.mount('https://', adapter)
        
        self.download_queue = Queue()
        self.worker_states = {i: {"file": "Idle", "status": "Waiting", "done": 0, "total": 0} for i in range(self.num_workers)}
        
        self.db_path = self.output_dir / "grabia_state.db"
        self._init_db()
        
        self.total_ids = 0
        self.scanned_ids_count = 0
        self.total_files_found = 0
        self.files_finished = 0
        self.total_bytes = 0
        self.downloaded_bytes = 0
        self.current_session_bytes = 0
        self.is_scanning = False
        self.report_generated = False

    def _init_db(self):
        with self.db_lock:
            with sqlite3.connect(self.db_path, timeout=30) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS files 
                    (id TEXT, filename TEXT, status TEXT, size INTEGER, PRIMARY KEY(id, filename))
                """)

    def _authenticate(self, username, password):
        if username and password:
            try:
                configure(username, password)
                ia_session = ia.get_session()
                self.session.cookies.update(ia_session.cookies)
                self.log_event(f"Logged in: {username}")
            except Exception:
                self.log_event("Login Failed - Guest Mode")
        else:
            self.log_event("Guest Mode")

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
            if amount > 0: time.sleep(0.01)

    def log_event(self, msg: str):
        timestamp = time.strftime('%H:%M:%S')
        formatted = f"[{timestamp}] {msg}"
        with self.lock:
            self.ui_events.append(formatted)
        self.logger.info(msg)

    def get_stats(self):
        with self.lock:
            if not self.is_scanning and self.download_queue.empty() and not self.report_generated and self.total_files_found > 0:
                with self.worker_lock:
                    all_idle = all(s["status"] == "Waiting" for s in self.worker_states.values())
                if all_idle:
                    self.report_generated = True
                    threading.Thread(target=self._generate_final_report, daemon=True).start()

            report_list = [f"{k} -> {v}" for k, v in self.failed_items_report.items() if "Final Fail" in v]
            return {
                "total_ids": self.total_ids, "scanned_ids": self.scanned_ids_count, 
                "total_bytes": self.total_bytes, "down_bytes": self.downloaded_bytes, 
                "session_bytes": self.current_session_bytes, "is_scanning": self.is_scanning, 
                "events": list(self.ui_events), "files_done": self.files_finished, 
                "total_files": self.total_files_found, "files_failed": len(report_list),
                "failed_report": report_list, "start_time": self.start_time
            }

    def _generate_final_report(self):
        duration = time.time() - self.start_time
        mins, secs = divmod(duration, 60)
        avg_speed = self.current_session_bytes / duration if duration > 0 else 0
        
        summary = [
            "="*45,
            "         ARCHIVAL SESSION SUMMARY",
            "="*45,
            f"Total Duration:   {int(mins)}m {int(secs)}s",
            f"Files Processed:  {self.files_finished} / {self.total_files_found}",
            f"Session Data:     {self.current_session_bytes / (1024**2):.2f} MB",
            f"Avg Throughput:   {avg_speed / 1024:.2f} KB/s",
            f"Total Failures:   {len([v for v in self.failed_items_report.values() if 'Final' in v])}",
            "="*45
        ]
        for line in summary:
            self.log_event(line)

    def start(self, input_lines: List[str]):
        self.report_generated = False
        final_ids = []
        for line in input_lines:
            line = line.strip()
            if not line or line.startswith('#'): continue
            if ":" in line and not line.startswith("http"):
                self.log_event(f"Searching IA: {line}")
                try:
                    results = search_items(line)
                    for item in results:
                        final_ids.append(item['identifier'])
                except Exception as e:
                    self.log_event(f"Search Error: {str(e)}")
            else:
                final_ids.append(line)
        
        self.total_ids = len(final_ids)
        scanner_t = threading.Thread(target=self._run_scanner, args=(final_ids,), daemon=True)
        scanner_t.start()
        workers = [threading.Thread(target=self._worker_consumer, args=(i,), daemon=True) for i in range(self.num_workers)]
        for w in workers: w.start()
        return workers, scanner_t

    def _run_scanner(self, ids):
        self.is_scanning = True
        with ThreadPoolExecutor(max_workers=self.num_scanners) as executor:
            executor.map(self._scan_single_item, ids)
        self.is_scanning = False
        self.log_event("Discovery Complete.")

    def _scan_single_item(self, item_id: str):
        if self.stop_event.is_set(): return
        try:
            item = get_item(item_id)
            if not item.exists: return self.log_event(f"ID not found: {item_id}")
            
            formats = self.config.get('formats', [])
            inc_rex = self.config.get('include')
            exc_rex = self.config.get('exclude')

            for f in item.get_files():
                if self.stop_event.is_set(): return
                fname = f.name
                if fname.endswith(('_meta.xml', '_files.xml', 'archive.torrent')): continue
                if formats and not any(fname.lower().endswith(fmt.lower()) for fmt in formats): continue
                if inc_rex and not re.search(inc_rex, fname): continue
                if exc_rex and re.search(exc_rex, fname): continue
                
                with self.db_lock:
                    with sqlite3.connect(self.db_path, timeout=30) as conn:
                        res = conn.execute("SELECT status FROM files WHERE id=? AND filename=?", (item_id, fname)).fetchone()
                        if res and res[0] == 'completed':
                            with self.lock: self.files_finished += 1
                            continue

                safe_name = "".join([c if c.isalnum() or c in "._- " else "_" for c in fname])
                size = int(f.size or 0)
                with self.lock:
                    self.total_files_found += 1
                    self.total_bytes += size
                # Pass MD5 from IA metadata into the task
                self.download_queue.put(DownloadTask(item_id, fname, safe_name, f.md5 or "", size))
        except Exception as e:
            self.log_event(f"Scan Error {item_id}: {str(e)[:50]}")
        finally:
            with self.lock: self.scanned_ids_count += 1

    def _worker_consumer(self, wid: int):
        while not self.stop_event.is_set():
            try:
                task = self.download_queue.get(timeout=1)
                self._download_file(wid, task)
                self.download_queue.task_done()
            except Empty:
                if not self.is_scanning and self.download_queue.empty(): break

    def _verify_file_integrity(self, file_path: Path, expected_md5: str) -> bool:
        """Performs a chunked MD5 hash check to ensure data integrity."""
        if not expected_md5:
            return True # Assume OK if IA provides no hash
        
        md5_hash = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                # Read in 1MB chunks to be memory efficient
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    if self.stop_event.is_set(): return False
                    md5_hash.update(chunk)
            return md5_hash.hexdigest() == expected_md5
        except Exception:
            return False

    def _download_file(self, worker_id: int, task: DownloadTask):
        item_dir = self.output_dir / task.item_id
        item_dir.mkdir(parents=True, exist_ok=True)
        dest = item_dir / task.safe_file_name
        part_dest = dest.with_suffix(dest.suffix + ".part")
        
        # Check if file exists but is not in DB (verify it before skipping)
        if dest.exists() and dest.stat().st_size == task.size:
            with self.worker_lock:
                self.worker_states[worker_id] = {"file": task.file_name, "status": "Verifying", "done": task.size, "total": task.size}
            if self._verify_file_integrity(dest, task.expected_md5):
                with self.lock: self.files_finished += 1
                return
            else:
                self.log_event(f"Existing file corrupt: {task.file_name}. Deleting.")
                dest.unlink()

        resume_header = {}
        bytes_on_disk = 0
        if part_dest.exists():
            bytes_on_disk = part_dest.stat().st_size
            if bytes_on_disk < task.size:
                resume_header = {'Range': f'bytes={bytes_on_disk}-'}
            elif bytes_on_disk > task.size:
                part_dest.unlink()
                bytes_on_disk = 0

        try:
            if bytes_on_disk < task.size:
                url = f"https://archive.org/download/{task.item_id}/{task.file_name}"
                resp = self.session.get(url, headers=resume_header, stream=True, timeout=(10, 60))
                
                if resp.status_code == 416: 
                    if part_dest.exists(): part_dest.unlink()
                    bytes_on_disk = 0
                    resp = self.session.get(url, stream=True, timeout=(10, 60))
                
                resp.raise_for_status()
                
                with self.worker_lock:
                    self.worker_states[worker_id] = {"file": task.file_name, "status": "Downloading", "done": bytes_on_disk, "total": task.size}
                
                mode = "ab" if bytes_on_disk > 0 else "wb"
                with open(part_dest, mode) as f:
                    for chunk in resp.iter_content(chunk_size=128*1024):
                        if self.stop_event.is_set(): return
                        self._throttle(len(chunk))
                        f.write(chunk)
                        with self.lock:
                            self.downloaded_bytes += len(chunk)
                            self.current_session_bytes += len(chunk)
                        with self.worker_lock:
                            self.worker_states[worker_id]["done"] += len(chunk)

            # Final size check and MD5 Verification
            if part_dest.exists() and part_dest.stat().st_size == task.size:
                with self.worker_lock:
                    self.worker_states[worker_id]["status"] = "Verifying"
                
                if self._verify_file_integrity(part_dest, task.expected_md5):
                    part_dest.rename(dest) 
                    with self.lock:
                        self.files_finished += 1
                        self.failed_items_report.pop(task.file_name, None)
                    
                    with self.db_lock:
                        with sqlite3.connect(self.db_path, timeout=30) as conn:
                            conn.execute("INSERT OR REPLACE INTO files VALUES (?, ?, 'completed', ?)", (task.item_id, task.file_name, task.size))
                    self.log_event(f"Done: {task.file_name}")
                else:
                    self.log_event(f"Verification Failed: {task.file_name}. Retrying.")
                    if part_dest.exists(): part_dest.unlink()
                    raise Exception("MD5 Hash Mismatch")
            else:
                raise Exception("File size mismatch after download")

        except Exception as e:
            self._handle_error(task, str(e))
        finally:
            with self.worker_lock:
                self.worker_states[worker_id] = {"file": "Idle", "status": "Waiting", "done": 0, "total": 0}

    def _handle_error(self, task, error_msg, fatal=False):
        if not fatal and task.attempts < self.max_retries and not self.stop_event.is_set():
            task.attempts += 1
            with self.lock: self.failed_items_report[task.file_name] = f"Retrying ({task.attempts}): {error_msg[:30]}"
            self.download_queue.put(task)
        else:
            with self.lock: self.failed_items_report[task.file_name] = f"Final Fail: {error_msg[:40]}"
            self.log_event(f"FAILED: {task.file_name}")

    def get_worker_states(self):
        with self.worker_lock: return self.worker_states.copy()
