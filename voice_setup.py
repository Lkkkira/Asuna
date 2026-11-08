"""One-time optional voice setup in a project-local environment."""
import subprocess
import os
import sys
import venv
import argparse
from pathlib import Path

BASE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--download-only', action='store_true')
    parser.add_argument('--model', choices=['base', 'small'], default='small')
    args = parser.parse_args()
    if args.download_only:
        os.environ.setdefault('HF_HOME', str(BASE / 'data' / 'voice-cache'))
        os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
        os.environ.setdefault('HF_HUB_DOWNLOAD_TIMEOUT', '60')
        from faster_whisper.utils import download_model
        directory = BASE / 'data' / ('voice-model-small' if args.model == 'small' else 'voice-model')
        directory.mkdir(parents=True, exist_ok=True)
        download_model(args.model, output_dir=str(directory))
        from faster_whisper import WhisperModel
        WhisperModel(str(directory), device='cpu', compute_type='int8', local_files_only=True)
        print('Offline recognition model is ready.', flush=True)
        return
    env = BASE / '.venv-voice'
    python = env / 'Scripts' / 'python.exe'
    if not python.exists():
        print('Creating a local voice environment…', flush=True)
        venv.EnvBuilder(with_pip=True).create(env)
    subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(BASE / 'requirements-voice.txt')], check=True)
    subprocess.run([str(python), str(Path(__file__).resolve()), '--download-only', '--model', args.model], check=True)
    print('Voice setup complete. Reopen Start ASUNA.bat.', flush=True)


if __name__ == '__main__':
    main()
