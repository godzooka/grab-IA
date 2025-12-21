# 🏛️ grab-IA: Internet Archive Mass Downloader

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
   * On Windows: `venv\Scripts\activate` 
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
