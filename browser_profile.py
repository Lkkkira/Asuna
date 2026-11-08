"""Local-only selection of an existing Chrome profile; never copies login data."""
import json
import os
import re
import subprocess
from pathlib import Path

DATA = Path(__file__).resolve().parent / 'data'


def settings(data=None):
    path = Path(data or DATA) / 'browser-settings.json'
    if not path.exists():
        return None
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError('Invalid Chrome settings. Run Choose Chrome Profile.bat again.')
    directory = value.get('profile_directory', '')
    if not isinstance(directory, str) or not re.fullmatch(r'Default|Profile [1-9][0-9]*', directory):
        raise ValueError('The saved Chrome profile is invalid. Run Choose Chrome Profile.bat again.')
    if not isinstance(value.get('user_data_dir'), str):
        raise ValueError('The saved Chrome location is invalid. Run Choose Chrome Profile.bat again.')
    root = Path(value['user_data_dir'])
    if not root.is_absolute() or not (root / directory).is_dir():
        raise ValueError('The selected Chrome profile is unavailable. Run Choose Chrome Profile.bat again.')
    return value


def launch(url, profile):
    from browser import chrome_path
    subprocess.Popen([str(chrome_path()), '--user-data-dir=' + profile['user_data_dir'],
                      '--profile-directory=' + profile['profile_directory'], '--new-tab', url], shell=False)


def profiles(root=None):
    root = Path(root) if root else Path(os.environ['LOCALAPPDATA']) / 'Google/Chrome/User Data'
    info = json.loads((root / 'Local State').read_text(encoding='utf-8'))['profile']['info_cache']
    return root, [{'profile_directory': key, 'profile_name': value.get('name', key), 'user_data_dir': str(root)}
                  for key, value in info.items()
                  if re.fullmatch(r'Default|Profile [1-9][0-9]*', key) and (root / key).is_dir()]


def save(profile, data=None):
    folder = Path(data or DATA)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'browser-settings.json'
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Choose the Chrome profile ASUNA should always open.')
    parser.add_argument('--profile')
    parser.add_argument('--root')
    args = parser.parse_args()
    try:
        _, options = profiles(args.root)
        if args.profile:
            chosen = next(p for p in options if p['profile_directory'] == args.profile)
        else:
            for index, item in enumerate(options, 1):
                print(f"{index}. {item['profile_name']} ({item['profile_directory']})")
            index = int(input('Choose a profile number: '))
            if not 1 <= index <= len(options):
                raise ValueError('Choose a displayed number.')
            chosen = options[index - 1]
        save(chosen)
        print('ASUNA will use ' + chosen['profile_name'] + '. Reopen ASUNA, then type connect browser.')
    except (OSError, ValueError, KeyError, IndexError, StopIteration) as exc:
        parser.exit(1, 'Could not select the Chrome profile: ' + str(exc) + '\n')
