"""Install browser control into ASUNA's local runtime; reuse installed Chrome."""
import subprocess
import venv
from pathlib import Path

BASE = Path(__file__).resolve().parent
if __name__ == '__main__':
    python = BASE / '.venv-voice' / 'Scripts' / 'python.exe'
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(python.parent.parent)
    subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(BASE / 'requirements-browser.txt')], check=True)
    print('Browser control is ready. Reopen Start ASUNA.bat. Chrome must already be installed.')
