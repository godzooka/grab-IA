#!/usr/bin/env python3
"""
grab-IA Launcher
================
Cross-platform launcher that:
- Creates/activates virtual environment
- Installs dependencies
- Launches GUI in background
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


class GrabIALauncher:
    def __init__(self):
        self.project_dir = Path(__file__).parent.resolve()
        self.venv_dir = self.project_dir / "venv"
        self.system = platform.system()
        
        # Determine Python executable names based on platform
        if self.system == "Windows":
            self.python_exe = self.venv_dir / "Scripts" / "python.exe"
            self.pip_exe = self.venv_dir / "Scripts" / "pip.exe"
        else:
            self.python_exe = self.venv_dir / "bin" / "python"
            self.pip_exe = self.venv_dir / "bin" / "pip"
    
    def log(self, message):
        """Print status message."""
        print(f"[grab-IA] {message}")
    
    def ensure_venv(self):
        """Create virtual environment if it doesn't exist."""
        if self.venv_dir.exists():
            self.log("Virtual environment found")
            return
        
        self.log("Creating virtual environment...")
        subprocess.run(
            [sys.executable, "-m", "venv", str(self.venv_dir)],
            check=True
        )
        self.log("Virtual environment created")
    
    def install_dependencies(self):
        """Install required packages from requirements.txt."""
        requirements = self.project_dir / "requirements.txt"
        
        if not requirements.exists():
            self.log("ERROR: requirements.txt not found!")
            sys.exit(1)
        
        self.log("Installing dependencies...")
        subprocess.run(
            [str(self.pip_exe), "install", "-q", "-r", str(requirements)],
            check=True
        )
        self.log("Dependencies installed")
    
    def launch_gui(self):
        """Launch the GUI application in background."""
        self.log("Launching grab-IA GUI...")
        
        gui_script = self.project_dir / "grabia_gui.py"
        
        if not gui_script.exists():
            self.log("ERROR: grabia_gui.py not found!")
            sys.exit(1)
        
        # Launch in background based on platform
        if self.system == "Windows":
            # Windows: Use subprocess.CREATE_NO_WINDOW
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(
                [str(self.python_exe), str(gui_script)],
                creationflags=CREATE_NO_WINDOW,
                cwd=str(self.project_dir)
            )
        else:
            # Unix-like: Redirect output and run in background
            subprocess.Popen(
                [str(self.python_exe), str(gui_script)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(self.project_dir),
                start_new_session=True
            )
        
        self.log("GUI launched successfully")
        self.log("Console returning to shell...")
    
    def run(self):
        """Main launcher sequence."""
        self.log("grab-IA Launcher v2.0")
        self.log("=" * 50)
        
        try:
            # Setup phase
            self.ensure_venv()
            self.install_dependencies()
            
            # Launch phase
            self.launch_gui()
            
        except subprocess.CalledProcessError as e:
            self.log(f"ERROR: Command failed: {e}")
            sys.exit(1)
        except Exception as e:
            self.log(f"ERROR: {e}")
            sys.exit(1)


def main():
    launcher = GrabIALauncher()
    launcher.run()


if __name__ == "__main__":
    main()
