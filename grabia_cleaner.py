#!/usr/bin/env python3
"""
grab-IA Directory Cleaner
==========================
Standalone GUI tool for ensuring 1:1 parity between item lists and download directories.

Features:
- Dry-run mode for safe preview
- Respects all filter arguments (extensions, regex, metadata-only)
- README preservation option
- Removes orphaned files and .part files
- Themed to match main grab-IA GUI
"""

import sys
import csv
import re
import requests
from pathlib import Path
from typing import Set, List, Dict, Tuple

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QFileDialog, QLabel, QPushButton,
    QCheckBox, QLineEdit, QTextEdit,
    QSpinBox, QProgressBar,
    QHBoxLayout, QVBoxLayout, QGridLayout,
    QFrame, QMessageBox
)
from PySide6.QtGui import QTextCursor, QFont

# Connection timeout for metadata fetching
CONNECTION_TIMEOUT = 15
USER_AGENT = "grab-IA/2.0 (Archive Mirroring Tool)"

# Anti-Clutter Filter (same as main core)
SYSTEM_FILE_PATTERNS = [
    r'_meta\.xml$',
    r'_meta\.sqlite$',
    r'_files\.xml$',
    r'_thumb\.jpg$',
    r'_itemimage\.jpg$'
]


class CleanerWorker(QThread):
    """Background thread for cleaning operations."""
    
    log_signal = Signal(str, str)  # (message, level)
    progress_signal = Signal(int)
    finished_signal = Signal(dict)  # Final stats
    
    def __init__(self, config: Dict):
        super().__init__()
        self.config = config
        self.should_stop = False
        
    def log(self, message: str, level: str = "info"):
        """Emit log message."""
        self.log_signal.emit(message, level)
    
    def run(self):
        """Main cleaning operation."""
        try:
            self.log("=" * 70, "info")
            self.log("🧹 Starting directory cleaning operation", "info")
            self.log("=" * 70, "info")
            
            # Load identifiers
            identifiers = self._load_identifiers()
            if not identifiers:
                self.log("❌ No identifiers loaded", "error")
                return
            
            self.log(f"✓ Loaded {len(identifiers)} identifiers", "success")
            
            # Fetch manifests from Internet Archive
            expected_files = self._fetch_manifests(identifiers)
            
            if self.should_stop:
                return
            
            # Scan local directory
            local_files = self._scan_local_directory()
            
            if self.should_stop:
                return
            
            # Calculate differences
            stats = self._calculate_differences(expected_files, local_files)
            
            if self.should_stop:
                return
            
            # Execute cleaning (or dry-run)
            if self.config['dry_run']:
                self._report_dry_run(stats)
            else:
                self._execute_cleaning(stats)
            
            self.finished_signal.emit(stats)
            
        except Exception as e:
            self.log(f"❌ Critical error: {e}", "error")
            import traceback
            self.log(traceback.format_exc(), "error")
    
    def stop(self):
        """Signal worker to stop."""
        self.should_stop = True
    
    def _load_identifiers(self) -> List[str]:
        """Load identifiers from TXT or CSV file."""
        path = Path(self.config['item_list'])
        
        if not path.exists():
            self.log(f"❌ Item list not found: {path}", "error")
            return []
        
        identifiers = []
        
        if path.suffix.lower() == '.csv':
            with open(path, 'r') as f:
                for row in csv.reader(f):
                    if row:
                        identifiers.append(row[0].strip())
        else:
            identifiers = [
                line.strip() 
                for line in path.read_text().splitlines() 
                if line.strip()
            ]
        
        return identifiers
    
    def _fetch_manifests(self, identifiers: List[str]) -> Dict[str, Set[str]]:
        """
        Fetch file manifests from Internet Archive for all identifiers.
        
        Returns:
            Dictionary mapping item_id -> set of expected filenames
        """
        expected_files = {}
        session = requests.Session()
        session.headers.update({'User-Agent': USER_AGENT})
        
        total = len(identifiers)
        
        for idx, identifier in enumerate(identifiers):
            if self.should_stop:
                break
            
            self.log(f"📡 Fetching manifest [{idx+1}/{total}]: {identifier}", "info")
            self.progress_signal.emit(int((idx / total) * 50))  # First 50% is fetching
            
            try:
                url = f"https://archive.org/metadata/{identifier}"
                response = session.get(url, timeout=CONNECTION_TIMEOUT)
                
                if response.status_code != 200:
                    self.log(f"⚠️  Failed to fetch metadata: {identifier}", "warning")
                    continue
                
                data = response.json()
                files = data.get('files', [])
                
                expected = set()
                
                for file_info in files:
                    file_name = file_info.get('name', '')
                    file_size = int(file_info.get('size', 0))
                    
                    if not file_name or file_size == 0:
                        continue
                    
                    # Apply filters (same as core)
                    if not self._should_include_file(file_name):
                        continue
                    
                    # Sanitize filename (same as core)
                    safe_name = re.sub(r'[<>:"/\\|?*]', '_', file_name)
                    expected.add(safe_name)
                
                expected_files[identifier] = expected
                
                # Add README if configured to keep
                if self.config['keep_readme']:
                    expected.add('README.txt')
                
            except Exception as e:
                self.log(f"❌ Error fetching {identifier}: {e}", "error")
        
        return expected_files
    
    def _should_include_file(self, filename: str) -> bool:
        """
        Apply filters to determine if file should be included.
        
        Respects: extension whitelist, regex filter, metadata-only mode, anti-clutter
        """
        lower_name = filename.lower()
        
        # Anti-clutter filter (system files)
        if any(re.search(pattern, filename) for pattern in SYSTEM_FILE_PATTERNS):
            return False
        
        # Extension whitelist
        if self.config['extensions']:
            if not any(lower_name.endswith(ext.lower()) for ext in self.config['extensions']):
                return False
        
        # Regex filter
        if self.config['filter_regex']:
            if not self.config['filter_regex'].search(filename):
                return False
        
        # Metadata-only mode
        if self.config['metadata_only']:
            if not any(ext in lower_name for ext in ['.xml', '.json', '.txt', 'readme']):
                return False
        
        return True
    
    def _scan_local_directory(self) -> Dict[str, Set[str]]:
        """
        Scan local download directory for existing files.
        
        Returns:
            Dictionary mapping item_id -> set of local filenames
        """
        base_dir = Path(self.config['output_dir'])
        
        if not base_dir.exists():
            self.log(f"⚠️  Output directory does not exist: {base_dir}", "warning")
            return {}
        
        self.log(f"🔍 Scanning local directory: {base_dir}", "info")
        
        local_files = {}
        
        # Iterate through item subdirectories
        for item_dir in base_dir.iterdir():
            if not item_dir.is_dir():
                continue
            
            item_id = item_dir.name
            files = set()
            
            for file_path in item_dir.rglob('*'):
                if file_path.is_file():
                    # Get relative path from item directory
                    rel_path = file_path.relative_to(item_dir)
                    files.add(str(rel_path))
            
            local_files[item_id] = files
        
        return local_files
    
    def _calculate_differences(self, expected: Dict[str, Set[str]], 
                               local: Dict[str, Set[str]]) -> Dict:
        """
        Calculate differences between expected and local files.
        
        Returns:
            Statistics dictionary with files to delete and missing files
        """
        self.log("📊 Calculating differences...", "info")
        
        to_delete = []
        missing_files = []
        kept_files = 0
        
        # Find orphaned files (exist locally but not in manifest)
        for item_id, local_set in local.items():
            expected_set = expected.get(item_id, set())
            
            for filename in local_set:
                if filename not in expected_set:
                    file_path = Path(self.config['output_dir']) / item_id / filename
                    to_delete.append(str(file_path))
                else:
                    kept_files += 1
        
        # Find orphaned item directories (not in identifier list)
        base_dir = Path(self.config['output_dir'])
        if base_dir.exists():
            for item_dir in base_dir.iterdir():
                if item_dir.is_dir() and item_dir.name not in expected:
                    to_delete.append(str(item_dir))
        
        # Find missing files (in manifest but not local)
        for item_id, expected_set in expected.items():
            local_set = local.get(item_id, set())
            
            for filename in expected_set:
                if filename not in local_set:
                    missing_files.append(f"{item_id}/{filename}")
        
        stats = {
            'to_delete': to_delete,
            'missing_files': missing_files,
            'kept_files': kept_files,
            'expected_items': len(expected),
            'local_items': len(local)
        }
        
        self.log(f"✓ Analysis complete:", "success")
        self.log(f"  - Files to delete: {len(to_delete)}", "info")
        self.log(f"  - Missing files: {len(missing_files)}", "info")
        self.log(f"  - Files to keep: {kept_files}", "info")
        
        return stats
    
    def _report_dry_run(self, stats: Dict):
        """Report dry-run results without making changes."""
        self.log("=" * 70, "info")
        self.log("🔍 DRY-RUN MODE - No files will be deleted", "warning")
        self.log("=" * 70, "info")
        
        if stats['to_delete']:
            self.log(f"\n📋 Files that WOULD BE DELETED ({len(stats['to_delete'])}):", "warning")
            for path in stats['to_delete'][:50]:  # Limit to first 50
                self.log(f"  - {path}", "warning")
            
            if len(stats['to_delete']) > 50:
                self.log(f"  ... and {len(stats['to_delete']) - 50} more", "warning")
        
        if stats['missing_files']:
            self.log(f"\n📋 Missing files (not in local directory) ({len(stats['missing_files'])}):", "info")
            for path in stats['missing_files'][:50]:
                self.log(f"  - {path}", "info")
            
            if len(stats['missing_files']) > 50:
                self.log(f"  ... and {len(stats['missing_files']) - 50} more", "info")
        
        self.log("\n✓ Dry-run complete. Enable 'Execute Cleaning' to make changes.", "success")
    
    def _execute_cleaning(self, stats: Dict):
        """Execute actual file deletion."""
        self.log("=" * 70, "info")
        self.log("🗑️  EXECUTING CLEANING OPERATION", "warning")
        self.log("=" * 70, "info")
        
        deleted_count = 0
        failed_count = 0
        total = len(stats['to_delete'])
        
        for idx, path_str in enumerate(stats['to_delete']):
            if self.should_stop:
                break
            
            self.progress_signal.emit(50 + int((idx / max(total, 1)) * 50))  # Second 50%
            
            path = Path(path_str)
            
            try:
                if path.is_file():
                    path.unlink()
                    self.log(f"🗑️  Deleted file: {path.name}", "info")
                    deleted_count += 1
                elif path.is_dir():
                    import shutil
                    shutil.rmtree(path)
                    self.log(f"🗑️  Deleted directory: {path.name}", "info")
                    deleted_count += 1
            except Exception as e:
                self.log(f"❌ Failed to delete {path}: {e}", "error")
                failed_count += 1
        
        self.log("\n" + "=" * 70, "info")
        self.log("✅ CLEANING COMPLETE", "success")
        self.log("=" * 70, "info")
        self.log(f"Deleted: {deleted_count} items", "success")
        self.log(f"Failed: {failed_count} items", "error" if failed_count > 0 else "info")
        self.log(f"Kept: {stats['kept_files']} files", "success")


class GrabIACleaner(QMainWindow):
    """Main window for directory cleaner."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("grab-IA Directory Cleaner")
        self.resize(1200, 800)
        
        self.worker = None
        
        self._build_ui()
        self._apply_theme()
    
    def _build_ui(self):
        """Build user interface."""
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        
        # Header
        header = QLabel("🧹 Directory Cleaner - Ensure 1:1 Parity")
        header.setAlignment(Qt.AlignCenter)
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        root.addWidget(header)
        
        # Body
        body = QHBoxLayout()
        root.addLayout(body, 1)
        
        # Sidebar
        sidebar_widget = QWidget()
        sidebar_widget.setMaximumWidth(380)
        sidebar_widget.setMinimumWidth(360)
        
        sidebar = QGridLayout(sidebar_widget)
        sidebar.setContentsMargins(6, 6, 6, 6)
        sidebar.setVerticalSpacing(6)
        
        r = 0
        
        def add_field(label, widget, tooltip=""):
            nonlocal r
            lbl = QLabel(label)
            if tooltip:
                lbl.setToolTip(tooltip)
                widget.setToolTip(tooltip)
            sidebar.addWidget(lbl, r, 0)
            sidebar.addWidget(widget, r, 1)
            r += 1
        
        # Item list
        self.item_path = QLineEdit()
        btn_items = QPushButton("Browse")
        btn_items.clicked.connect(self.load_items)
        sidebar.addWidget(QLabel("Item list (TXT/CSV)"), r, 0)
        sidebar.addWidget(self.item_path, r, 1)
        sidebar.addWidget(btn_items, r, 2)
        r += 1
        
        # Output directory
        self.output_dir = QLineEdit()
        btn_out = QPushButton("Browse")
        btn_out.clicked.connect(self.select_output)
        sidebar.addWidget(QLabel("Download directory"), r, 0)
        sidebar.addWidget(self.output_dir, r, 1)
        sidebar.addWidget(btn_out, r, 2)
        r += 1
        
        # Filters (same as main GUI)
        self.filter_regex = QLineEdit()
        add_field("Filename regex", self.filter_regex, 
                 "Regular expression to filter filenames")
        
        self.extension_whitelist = QLineEdit()
        add_field("Extensions (comma-separated)", self.extension_whitelist,
                 "e.g., mp3,flac,pdf - leave empty for all")
        
        # Modes
        self.chk_metadata = QCheckBox("Metadata only")
        self.chk_metadata.setToolTip("Only keep metadata files (XML, JSON, TXT)")
        sidebar.addWidget(self.chk_metadata, r, 0, 1, 2)
        r += 1
        
        self.chk_keep_readme = QCheckBox("Keep README files")
        self.chk_keep_readme.setChecked(True)
        self.chk_keep_readme.setToolTip("Preserve grab-IA generated README.txt files")
        sidebar.addWidget(self.chk_keep_readme, r, 0, 1, 2)
        r += 1
        
        self.chk_dry_run = QCheckBox("Dry-run mode (safe preview)")
        self.chk_dry_run.setChecked(True)
        self.chk_dry_run.setToolTip("Preview changes without deleting files")
        sidebar.addWidget(self.chk_dry_run, r, 0, 1, 2)
        r += 1
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        sidebar.addWidget(separator, r, 0, 1, 3)
        r += 1
        
        # Warning label
        warning = QLabel("⚠️  Cleaning will DELETE files not in manifest!")
        warning.setStyleSheet("color: #ff6b35; font-weight: bold;")
        warning.setWordWrap(True)
        sidebar.addWidget(warning, r, 0, 1, 3)
        r += 1
        
        # Control buttons
        self.btn_start = QPushButton("START CLEANING")
        self.btn_start.clicked.connect(self.start_cleaning)
        sidebar.addWidget(self.btn_start, r, 0, 1, 3)
        r += 1
        
        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.stop_cleaning)
        sidebar.addWidget(self.btn_stop, r, 0, 1, 3)
        r += 1
        
        body.addWidget(sidebar_widget, 0)
        
        # Log area
        log_layout = QVBoxLayout()
        body.addLayout(log_layout, 1)
        
        log_label = QLabel("Activity Log")
        log_label.setStyleSheet("font-weight: bold;")
        log_layout.addWidget(log_label)
        
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        log_layout.addWidget(self.log_view, 1)
        
        # Progress bar
        self.progress = QProgressBar()
        root.addWidget(self.progress)
    
    def _apply_theme(self):
        """Apply Ubuntu-inspired theme (matching main GUI)."""
        self.setStyleSheet("""
            QWidget {
                background-color: #3b2f2f;
                color: #ffffff;
                font-family: Ubuntu, Arial, sans-serif;
            }
            QTextEdit {
                background-color: #2a201b;
                border: 1px solid #5a4a3a;
            }
            QLineEdit {
                background-color: #2a201b;
                border: 1px solid #5a4a3a;
                padding: 4px;
            }
            QPushButton {
                background-color: #e95420;
                padding: 6px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff6b35;
            }
            QPushButton:disabled {
                background-color: #5a4a3a;
                color: #888888;
            }
            QProgressBar {
                border: 1px solid #5a4a3a;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #e95420;
            }
            QCheckBox {
                spacing: 8px;
            }
            QLabel {
                padding: 2px;
            }
        """)
    
    def load_items(self):
        """Browse for item list file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select item list", "", "Text/CSV (*.txt *.csv)"
        )
        if path:
            self.item_path.setText(path)
    
    def select_output(self):
        """Browse for output directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select download directory"
        )
        if directory:
            self.output_dir.setText(directory)
    
    def start_cleaning(self):
        """Start cleaning operation."""
        # Validation
        if not self.item_path.text():
            QMessageBox.warning(self, "Error", "Please select an item list file")
            return
        
        if not self.output_dir.text():
            QMessageBox.warning(self, "Error", "Please select a download directory")
            return
        
        # Confirm if not dry-run
        if not self.chk_dry_run.isChecked():
            reply = QMessageBox.question(
                self, "Confirm Deletion",
                "This will permanently DELETE files not in the manifest.\n\n"
                "Are you sure you want to proceed?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
        
        # Clear log
        self.log_view.clear()
        self.progress.setValue(0)
        
        # Parse configuration
        extensions = None
        if self.extension_whitelist.text().strip():
            extensions = [e.strip() for e in self.extension_whitelist.text().split(',')]
        
        filter_regex = None
        if self.filter_regex.text().strip():
            try:
                filter_regex = re.compile(self.filter_regex.text())
            except re.error as e:
                QMessageBox.warning(self, "Regex Error", f"Invalid regex pattern: {e}")
                return
        
        config = {
            'item_list': self.item_path.text(),
            'output_dir': self.output_dir.text(),
            'extensions': extensions,
            'filter_regex': filter_regex,
            'metadata_only': self.chk_metadata.isChecked(),
            'keep_readme': self.chk_keep_readme.isChecked(),
            'dry_run': self.chk_dry_run.isChecked()
        }
        
        # Start worker
        self.worker = CleanerWorker(config)
        self.worker.log_signal.connect(self.append_log)
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.finished_signal.connect(self.cleaning_finished)
        self.worker.start()
        
        # Update UI
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
    
    def stop_cleaning(self):
        """Stop cleaning operation."""
        if self.worker:
            self.worker.stop()
            self.append_log("⏸️  Stopping operation...", "warning")
    
    def append_log(self, message: str, level: str):
        """Append message to log view."""
        cursor = self.log_view.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        # Color based on level
        color_map = {
            'info': '#ffffff',
            'success': '#77dd77',
            'warning': '#ffb347',
            'error': '#ff6b6b'
        }
        
        color = color_map.get(level, '#ffffff')
        cursor.insertHtml(f'<span style="color: {color};">{message}</span><br>')
        
        self.log_view.setTextCursor(cursor)
        self.log_view.ensureCursorVisible()
    
    def cleaning_finished(self, stats: Dict):
        """Handle cleaning completion."""
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress.setValue(100)
        
        # Show summary dialog
        if self.chk_dry_run.isChecked():
            message = (
                f"Dry-run complete!\n\n"
                f"Files that would be deleted: {len(stats['to_delete'])}\n"
                f"Missing files: {len(stats['missing_files'])}\n"
                f"Files that would be kept: {stats['kept_files']}\n\n"
                f"Uncheck 'Dry-run mode' to execute cleaning."
            )
        else:
            message = (
                f"Cleaning complete!\n\n"
                f"Files deleted: {len(stats['to_delete'])}\n"
                f"Files kept: {stats['kept_files']}\n"
                f"Missing files: {len(stats['missing_files'])}"
            )
        
        QMessageBox.information(self, "Complete", message)
    
    def closeEvent(self, event):
        """Handle window close."""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Confirm Exit",
                "Cleaning operation is still running. Exit anyway?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.worker.stop()
                self.worker.wait(2000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    app = QApplication(sys.argv)
    window = GrabIACleaner()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
