 # 🏛️ grab-IA: Internet Archive Mass Downloader
  
 **grab-IA** is a high-performance, multi-threaded archival tool designed to mirror Internet Archive (IA) items with precision. It features a real-time terminal dashboard, bandwidth throttling, and persistent resume capabilities.
  
 <p align="center">
   <img src="img/grab-IA_dash.png" alt="grab-IA Dashboard" width="700">
 </p>
 
 ---
  
 ## 🚀 Key Features
  
 * **Smart Resuming:** Uses a local SQLite database to track every byte. If a connection drops, it picks up exactly where it left off.
 * **Threaded Architecture:** Separate pools for metadata scanning and file downloading to ensure the pipe stays full.
 * **Precision Filtering:** Support for both simple extension filtering (e.g., `mp3,pdf`) and complex Regex patterns.
 * **Bandwidth Management:** Built-in "token-bucket" throttling to respect your network's limits.
 * **Container Ready:** Includes a `Dockerfile` for easy deployment in isolated environments.
 
 ## 📦 Self-Packaging Logic
 
 `grab-IA` includes a unique built-in deployment initializer. When the script runs, it can automatically prepare a `deploy/` directory containing:
 * A standalone `requirements.txt`
 * Portable copies of the core logic (`grabIA.py` and `grabia_core.py`)
 
 This is designed for users who want to quickly "bundle" the tool to move it to a remote server or a specific production environment without needing to manage the entire source repository.
 
 > **Note:** The `deploy/` folder is used for temporary build contexts and is excluded from version control via `.gitignore`.
 
 ---
 
 ## 🔄 Smart Resuming & Data Integrity
  
 **grab-IA** is built for reliability over long-running archival sessions. It uses a local SQLite database (`grabia_state.db`) to ensure that no bandwidth or time is wasted on redundant data.
  
 ### How it Works:
 * **State Tracking:** Every successfully downloaded file is logged in the local database with its item ID, filename, and size.
 * **Pre-Download Verification:** Before a worker starts a download, the engine queries the database to check if the file is already complete.
 * **Interruption Recovery:** If you stop the script (Ctrl+C), all progress is saved. Restarting with the same list will skip completed files and resume partial ones.
 
 ---
 
 # ## 🛠️ Installation & Setup
 
 It is highly recommended to run this tool in a Python Virtual Environment (venv) to keep your global system dependencies clean.
 
 ### 1. Clone or Save the Files
 Ensure `grab-IA.py` and `grabia_core.py` are in the same directory.
 
 ### 2. Create the Virtual Environment
 Open your terminal in the project folder and run:
 
 ```bash
 python3 -m venv venv
 ```
 
 ### 3. Activate and Install Dependencies
 Activate the environment and install the required libraries:
 
 ```bash
 # On macOS/Linux:
 source venv/bin/activate
 
 # On Windows:
 # venv\Scripts\activate
 
 pip install internetarchive rich requests
 ```
 
 ### 🛠️ Quick Start
 
 ### Prerequisites
 * Python 3.8+
 * Internet Archive Account (Optional, but recommended for higher rate limits)
 
 ### Installation
 1. Clone the repo: `git clone https://github.com/yourusername/grab-IA.git`
 2. Install dependencies: `pip install -r requirements.txt`
 3. (Optional) Set up credentials: Copy `.env.example` to `.env` and add your IA email/password.
 
 ### Usage
 ```bash
 python3 <path/to/grabIA.py> <path/to/item_list> <arg> 
 
 # ## ⚙️ Command Line Arguments
 
 You can customize the behavior of the downloader using the following flags:
 
 | Argument | Description | Default |
 | :--- | :--- | :--- |
 | `input` | **(Required)** Path to a text file containing Internet Archive Item IDs (one per line). | N/A |
 | `-o`, `--output` | The directory where files will be saved. | `downloads` |
 | `-w`, `--workers` | Number of simultaneous download threads. | `4` |
 | `-f`, `--format` | Comma-separated list of file extensions to download (e.g., `mp3,pdf`). | All |
 | `-l`, `--limit` | Global speed limit (e.g., `500k`, `2m` for 2MB/s). | Unlimited |
 | `--include` | Regex pattern: only download files matching this name. | None |
 | `--exclude` | Regex pattern: skip files matching this name. | None |
 | `--username` | Your Internet Archive email/username. | None |
 | `--password` | Your Internet Archive password. | None |
 
 ### Example Usage
 
 ```bash
 python3 grabIA.py my_items.txt -w 8 -f mp4 --limit 5m
 ```
 ```
 
 ---
 
 ## 🤝 Contributing
  
 Contributions are welcome! Whether it's fixing a bug, improving documentation, or suggesting a new feature:
  
 1. **Fork the Project**
 2. **Create your Feature Branch** (`git checkout -b feature/AmazingFeature`)
 3. **Commit your Changes** (`git commit -m 'Add some AmazingFeature'`)
 4. **Push to the Branch** (`git push origin feature/AmazingFeature`)
 5. **Open a Pull Request**
 
 ## 📄 License
 
 This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
