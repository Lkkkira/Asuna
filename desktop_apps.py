"""Find explicitly supported desktop apps in standard install locations."""
import os
import re
from pathlib import Path


def discord_executable():
    roots = []
    if os.environ.get('LOCALAPPDATA'):
        local = Path(os.environ['LOCALAPPDATA'])
        roots.extend((local / 'Discord', local / 'Programs/Discord'))
    for name in ('ProgramFiles', 'ProgramFiles(x86)'):
        if os.environ.get(name):
            roots.append(Path(os.environ[name]) / 'Discord')
    for root in roots:
        direct = root / 'Discord.exe'
        if direct.is_file():
            return direct
        versions = sorted(root.glob('app-*'), key=lambda p: tuple(int(n) for n in re.findall(r'\d+', p.name)), reverse=True)
        for version in versions:
            executable = version / 'Discord.exe'
            if executable.is_file():
                return executable
    raise FileNotFoundError('Discord was not found in its standard installation locations.')
