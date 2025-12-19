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
 
 ## 🛠️ Quick Start
 
 ### Prerequisites
 * Python 3.8+
 * Internet Archive Account (Optional, but recommended for higher rate limits)
 
 ### Installation
 1. Clone the repo: `git clone https://github.com/yourusername/grab-IA.git`
 2. Install dependencies: `pip install -r requirements.txt`
 3. (Optional) Set up credentials: Copy `.env.example` to `.env` and add your IA email/password.
 
 ### Usage
 ```bash
 python grabIA.py ids.txt --output ./my_archive --workers 8 --limit 5MB
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
