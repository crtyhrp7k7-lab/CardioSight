"""Build the zip to send to a colleague:  python make_release.py

Writes dist/CardioSight-Shunt-Simulator-<date>-<commit>.zip containing one folder with the
program, docs and install.bat. The recipient extracts it and double-clicks install.bat
(see INSTALL.txt).
"""
import datetime
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOP = 'CardioSight-Shunt-Simulator'
FILES = ['install.bat', 'uninstall.bat', 'INSTALL.txt', 'README.md', 'LICENSE', 'CITATION.cff',
         'requirements.txt', 'cardiosight_icon.ico']
DIRS = ['docs', 'expected_output']
SKIP = {'make_release.py'}


def commit():
    try:
        out = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT,
                               capture_output=True, text=True).stdout.strip()
        return out + ('-modified' if dirty else '')
    except (OSError, subprocess.CalledProcessError):
        return 'nogit'


def main():
    icon = ROOT / 'cardiosight_icon.ico'
    if not icon.exists():
        subprocess.run([sys.executable, str(ROOT / 'create_icon.py')], cwd=ROOT, check=False)
    paths = [ROOT / f for f in FILES if (ROOT / f).exists()]
    paths += sorted(p for p in ROOT.glob('*.py') if p.name not in SKIP)
    for d in DIRS:
        paths += sorted(p for p in (ROOT / d).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    missing = [f for f in ('install.bat', 'launcher.py', 'model.py', 'scenario.py', 'requirements.txt')
               if not (ROOT / f).exists()]
    if missing:
        sys.exit(f'missing required files: {missing}')

    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    name = f"{TOP}-{datetime.date.today():%Y%m%d}-{commit()}.zip"
    out = dist / name
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, f"{TOP}/{p.relative_to(ROOT).as_posix()}")
    print(f"{out}  ({out.stat().st_size / 1024:.0f} KB, {len(paths)} files)")
    if not icon.exists():
        print('note: no icon (Pillow missing?); shortcuts will use the Python icon')


if __name__ == '__main__':
    main()
