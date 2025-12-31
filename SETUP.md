# grab-IA Setup Guide

## Quick Start

### Windows
1. Double-click `launch.bat`
2. The launcher will automatically:
   - Create a virtual environment
   - Install dependencies
   - Launch the GUI

### Linux / macOS
1. Make the launcher executable:
   ```bash
   chmod +x launch.sh
   ```

2. Run the launcher:
   ```bash
   ./launch.sh
   ```

3. The launcher will automatically:
   - Create a virtual environment
   - Install dependencies
   - Launch the GUI

## First-Time Setup

### Prerequisites
- **Python 3.8+** must be installed
- **Internet connection** for downloading dependencies

### Project Structure
Ensure your project directory looks like this:
```
grab-ia/
├── img/
│   └── grabia_icon.png
├── grabia_core.py
├── grabia_gui.py
├── launch.py
├── launch.bat (Windows)
├── launch.sh (Linux/macOS)
├── requirements.txt
└── README.md
```

## Using the Application

1. **Load Item List**: Click "Browse" next to "Item list" and select a TXT or CSV file containing Internet Archive identifiers (one per line)

2. **Set Output Directory**: Choose where to save downloaded files

3. **Configure Options**:
   - **Max workers**: Number of concurrent downloads (1-64)
   - **Speed limit**: Bandwidth cap in MB/s (0 = unlimited)
   - **Sync mode**: Skip files that already exist locally
   - **Dynamic scaling**: Auto-adjust worker count
   - **Metadata only**: Download only metadata files

4. **Start Download**: Click "START" to begin downloading

## Creating a Desktop Shortcut (Optional)

If you want a desktop shortcut, you can create one manually:

### Windows
1. Right-click on `launch.bat`
2. Select "Send to" → "Desktop (create shortcut)"

### Linux (Ubuntu 24.04)
Create a file `~/Desktop/grab-IA.desktop` with this content:
```desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=grab-IA
Comment=Internet Archive Downloader
Exec=/full/path/to/launch.sh
Icon=/full/path/to/img/grabia_icon.png
Terminal=false
Categories=Network;Utility;
```
Then make it executable:
```bash
chmod +x ~/Desktop/grab-IA.desktop
```

### macOS
Create a file `~/Desktop/grab-IA.command` with this content:
```bash
#!/bin/bash
cd "/full/path/to/grab-ia"
./launch.sh
```
Then make it executable:
```bash
chmod +x ~/Desktop/grab-IA.command
```

## Troubleshooting

### "Python not found"
- Ensure Python 3.8+ is installed and in your PATH
- Windows: Download from [python.org](https://www.python.org/downloads/)
- Linux: `sudo apt install python3 python3-venv`
- macOS: `brew install python3`

### Permission Denied (Linux/macOS)
```bash
chmod +x launch.sh
```

### Virtual Environment Issues
Delete the `venv` folder and run the launcher again:
```bash
rm -rf venv
./launch.sh
```

## Manual Installation

If you prefer manual setup:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# Linux/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run GUI
python grabia_gui.py
```

## Uninstallation

1. Delete the project directory
2. Remove any desktop shortcuts you created
3. Delete downloads from the configured output directory

## Advanced Configuration

### Custom Virtual Environment Location
Edit `launch.py` and modify:
```python
self.venv_dir = self.project_dir / "venv"
```

### Proxy Settings
Set environment variables before running:
```bash
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080
./launch.sh
```

## Support

For issues, check:
1. Console output during launch
2. `grabia_debug.log` in the project directory
3. Ensure all core files are present and unmodified
