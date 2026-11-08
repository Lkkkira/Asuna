"""Install the small local assistant extras in the project environment."""
import subprocess
import sys
import venv
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    python = root/'.venv-voice/Scripts/python.exe'
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(root/'.venv-voice')
    subprocess.run([str(python),'-m','pip','install','-r',str(root/'requirements-assistant.txt')],check=True)
    print('Assistant extras are ready. Reopen ASUNA. Voice and browser setup remain available from their setup files.')


if __name__=='__main__':
    main()
