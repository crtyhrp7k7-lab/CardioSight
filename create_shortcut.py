"""
Create desktop shortcut for CardioSight Shunt Digital Twin
"""
import os
import sys
from pathlib import Path

try:
    import win32com.client
    has_win32 = True
except ImportError:
    has_win32 = False

def create_shortcut():
    """Create desktop shortcut"""

    # Get paths
    desktop = Path.home() / 'Desktop'
    app_dir = Path(__file__).parent
    python_exe = sys.executable
    script_path = app_dir / 'launcher.py'
    icon_path = app_dir / 'cardiosight_icon.ico'

    if has_win32:
        # Use win32com to create proper shortcut
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut_path = str(desktop / "CardioSight Shunt Simulator.lnk")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = python_exe
        shortcut.Arguments = f'"{script_path}"'
        shortcut.WorkingDirectory = str(app_dir)
        shortcut.IconLocation = str(icon_path)
        shortcut.Description = "CardioSight Shunt Digital Twin Simulator"
        shortcut.save()
        print(f"Desktop shortcut created: {shortcut_path}")
    else:
        # Fallback: Create batch file
        batch_path = desktop / "CardioSight Shunt Simulator.bat"
        with open(batch_path, 'w') as f:
            f.write(f'@echo off\n')
            f.write(f'cd /d "{app_dir}"\n')
            f.write(f'"{python_exe}" "{script_path}"\n')
        print(f"Desktop batch file created: {batch_path}")
        print("Note: Install pywin32 for proper shortcut with icon:")
        print("  pip install pywin32")

if __name__ == "__main__":
    create_shortcut()
