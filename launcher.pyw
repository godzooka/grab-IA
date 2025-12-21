import os
import sys
import subprocess
import platform
import stat
from pathlib import Path

def ensure_shortcut(python_exe_path):
    """
    Creates a desktop shortcut. 
    Manual implementation for Linux to ensure compatibility with GNOME/Ubuntu.
    """
    try:
        base_path = Path(__file__).parent.resolve()
        is_win = platform.system() == "Windows"
        is_linux = platform.system() == "Linux"
        
        # Determine the best icon path [cite: 2]
        icon_path = base_path / "img" / "icon.ico"
        icon_str = str(icon_path) if icon_path.exists() else "python"

        if is_linux:
            # Move to applications folder so it appears in the OS menu 
            apps_path = Path.home() / ".local" / "share" / "applications"
            apps_path.mkdir(parents=True, exist_ok=True)
            shortcut_file = apps_path / "grab-IA.desktop"
            
            # Use absolute paths and quotes to handle spaces 
            exec_cmd = f'python3 "{base_path / "launcher.pyw"}"'
            
            desktop_entry = [
                "[Desktop Entry]",
                "Type=Application",
                "Name=grab-IA",
                "Comment=Internet Archive Downloader",
                f"Exec={exec_cmd}",
                f"Icon={icon_str}",
                "Terminal=false",
                "Categories=Utility;Application;",
            ]
            
            # Write the file [cite: 5]
            with open(shortcut_file, "w") as f:
                f.write("\n".join(desktop_entry))
            
            # Make the file executable [cite: 6]
            st = os.stat(shortcut_file)
            os.chmod(shortcut_file, st.st_mode | stat.S_IEXEC)
            
        elif is_win:
            # Add the venv to the system path so we can import pyshortcuts immediately 
            venv_lib = Path(python_exe_path).parent.parent / "Lib" / "site-packages"
            if str(venv_lib) not in sys.path:
                sys.path.append(str(venv_lib))
            
            from pyshortcuts import make_shortcut
            make_shortcut(str(base_path / 'launcher.pyw'), name='grab-IA', terminal=False, icon=icon_str)

    except Exception as e:
        # Since this is .pyw, this only shows if run from terminal
        print(f"Shortcut Sync Warning: {e}")

def setup_and_launch():
    base_path = Path(__file__).parent.resolve()
    venv_path = base_path / "venv" # [cite: 7]
    gui_script = base_path / "grabia_gui.py"
    
    is_win = platform.system() == "Windows"
    bin_dir = "Scripts" if is_win else "bin"
    python_exe = venv_path / bin_dir / ("pythonw.exe" if is_win else "python")
    pip_exe = venv_path / bin_dir / ("pip.exe" if is_win else "pip")

    # 1. Initialize Virtual Environment [cite: 7]
    if not venv_path.exists():
        subprocess.check_call([sys.executable, "-m", "venv", str(venv_path)])
    
    # 2. Sync Dependencies 
    try:
        subprocess.check_call([
            str(pip_exe), "install", "-q", 
            "customtkinter", "internetarchive", "requests", "rich", "python-dotenv", "pyshortcuts"
        ])
    except Exception:
        pass

    # 3. Handle System Shortcut (Passing the venv python path to help find pyshortcuts)
    ensure_shortcut(str(python_exe))

    # 4. Launch the Main Application [cite: 9]
    cmd = [str(python_exe), str(gui_script)]
    if is_win:
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        subprocess.Popen(cmd)

if __name__ == "__main__":
    setup_and_launch()
