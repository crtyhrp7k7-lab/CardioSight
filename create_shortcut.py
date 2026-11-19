"""
Create Desktop and Start Menu shortcuts for the CardioSight Shunt Simulator.

Run with the Python that should launch the app (install.bat uses the app's own .venv).
The shortcut uses pythonw.exe next to that Python, so no console window opens.
"""
import os
import sys
from pathlib import Path

try:
    import win32com.client
    has_win32 = True
except ImportError:
    has_win32 = False

NAME = "CardioSight Shunt Simulator"


def gui_python():
    exe = Path(sys.executable)
    w = exe.with_name('pythonw.exe')
    return w if w.exists() else exe


def locations():
    out = [Path.home() / 'Desktop']
    appdata = os.environ.get('APPDATA')
    if appdata:
        out.append(Path(appdata) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs')
    return [d for d in out if d.is_dir()]


def create_shortcut():
    app_dir = Path(__file__).resolve().parent
    python_exe = gui_python()
    script_path = app_dir / 'launcher.py'
    icon_path = app_dir / 'cardiosight_icon.ico'

    for folder in locations():
        if has_win32:
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut_path = str(folder / f"{NAME}.lnk")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = str(python_exe)
            shortcut.Arguments = f'"{script_path}"'
            shortcut.WorkingDirectory = str(app_dir)
            if icon_path.exists():
                shortcut.IconLocation = str(icon_path)
            shortcut.Description = "CardioSight Shunt Digital Twin Simulator"
            shortcut.save()
            print(f"Shortcut created: {shortcut_path}")
        else:
            batch_path = folder / f"{NAME}.bat"
            with open(batch_path, 'w') as f:
                f.write('@echo off\n')
                f.write(f'cd /d "{app_dir}"\n')
                f.write(f'start "" "{python_exe}" "{script_path}"\n')
            print(f"Shortcut (batch file) created: {batch_path}")
    if not has_win32:
        print("Note: install pywin32 for a proper shortcut with icon:  pip install pywin32")


if __name__ == "__main__":
    create_shortcut()
