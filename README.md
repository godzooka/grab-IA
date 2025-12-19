 # 🏛️ grab-IA: Internet Archive Mass Downloader
 
 **grab-IA** is a high-performance, multi-threaded archival tool designed to mirror Internet Archive (IA) items with precision. It features a real-time terminal dashboard, bandwidth throttling, and persistent resume capabilities.
 
 <p align="center">
   <img src="img/grab-IA_dash.png" alt="grab-IA Dashboard" width="700">
 </p>
 
 ---
 
 ## 🚀 Key Features
 
 * **Smart Resuming:** Uses a local SQLite database (`grabia_state.db`) to track every byte. If a connection drops, it picks up exactly where it left off.
 * **Threaded Architecture:** Separate pools for metadata scanning and file downloading ensure maximum throughput.
 * **Precision Filtering:** Support for both simple extension filtering (e.g., `mp3,pdf`) and complex Regex patterns.
 * **Bandwidth Management:** Built-in "token-bucket" throttling to respect your network's limits.
 * **Container Ready:** Includes deployment logic to maintain a `deploy/` folder for easy environment isolation.
 
 ## 📦 Self-Packaging Logic
 
 `grab-IA` includes a built-in deployment initializer. When the script runs, it automatically prepares a `deploy/` directory containing:
 * A standalone `requirements.txt`
 * Portable copies of the core logic (`grabIA.py` and `grabia_core.py`)
 
 ---
 
 ## 🔄 Smart Resuming & Data Integrity
 
 **grab-IA** is built for reliability over long-running archival sessions. It uses a local SQLite database to ensure no bandwidth is wasted on redundant data.
 
 ### How it Works:
 * **State Tracking:** Every successfully downloaded file is logged in the database with its item ID, filename, and size.
 * **Pre-Download Verification:** Before a worker starts a download, the engine verifies if the file is already complete in the database.
 * **Interruption Recovery:** If you stop the script (Ctrl+C), all progress is saved. Restarting will skip completed files and resume partial `.part` downloads.
 
 ---
 
 ## 🛠️ Installation & Setup
 
 It is highly recommended to run this tool in a Python Virtual Environment (venv).
 
 ### 1. Clone or Save the Files
 Ensure `grabIA.py` and `grabia_core.py` are in the same directory.
 
 ### 2. Create the Virtual Environment
 ```bash
 python3 -m venv venv
 ```
 
 ### 3. Activate and Install Dependencies
 ```bash
 # On macOS/Linux:
 source venv/bin/activate
 
 # On Windows:
 # venv\Scripts\activate
 
 pip install internetarchive rich requests python-dotenv
 ```
 
 ---
 
 ## ⚙️ Command Line Arguments
 
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
 
 ### Example Usage
 ```bash
 python3 <path/to/grabIA.py> <path/to/my_items.txt> -w 8 -f mp4 --limit 5m
 ```
 
 ---
 
 ## ❤️ Support the Internet Archive
 
 **grab-IA** is a tool built to interface with the [Internet Archive](https://archive.org), a 501(c)(3) non-profit digital library.
 
 ### 🏛️ Their Mission
 The Internet Archive's mission is to provide **"Universal Access to All Knowledge."** Since 1996, they have been building a digital library of cultural artifacts in digital form, providing free access to researchers, historians, and the general public.
 
 ### 📊 Why Your Support Matters
 Unlike commercial services, the Internet Archive does not charge for access or sell user data. They rely on donations to:
 * **Maintain Infrastructure:** They store over **100 Petabytes** of data.
 * **Preserve History:** They archive 100 million web pages daily and host millions of books, movies, and software programs.
 * **Fight Link Rot:** The Wayback Machine keeps the web's citations alive by fixing broken links.

 ### 💳 How to Donate
 * **Main Donation Page:** [archive.org/donate](https://archive.org/donate)
 * **Payment Methods:** They accept Credit Cards, PayPal, Venmo, Apple/Google Pay, and Cryptocurrency.
 
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
