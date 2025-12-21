import os
import sys
import subprocess
import platform
from pathlib import Path

def setup_and_launch():
    """
    Automated environment manager. 
    Ensures the venv is healthy and launches the GUI.
    """
    base_path = Path(__file__).parent.resolve()
    venv_path = base_path / "venv"
    gui_script = base_path / "grabia_gui.py"
    
    is_win = platform.system() == "Windows"
    bin_dir = "Scripts" if is_win else "bin"
    python_exe = venv_path / bin_dir / ("pythonw.exe" if is_win else "python")
    pip_exe = venv_path / bin_dir / ("pip.exe" if is_win else "pip")

    # 1. Initialize Virtual Environment
    if not venv_path.exists():
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_path)])
    
    # 2. Sync Dependencies (Quietly)
    try:
        subprocess.check_call([
            str(pip_exe), "install", "-q", 
            "customtkinter", "internetarchive", "requests", "rich", "python-dotenv"
        ])
    except Exception as e:
        print(f"Dependency Sync Warning: {e}")

    # 3. Launch the Main Application
    cmd = [str(python_exe), str(gui_script)]
    if is_win:
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        subprocess.Popen(cmd)

if __name__ == "__main__":
    setup_and_launch()
