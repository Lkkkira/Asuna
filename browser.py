"""Open ASUNA links explicitly in Chrome, independent of Windows associations."""
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse


def chrome_path():
    candidates = []
    for variable, suffix in [('ProgramFiles', 'Google/Chrome/Application/chrome.exe'),
                             ('ProgramFiles(x86)', 'Google/Chrome/Application/chrome.exe'),
                             ('LOCALAPPDATA', 'Google/Chrome/Application/chrome.exe')]:
        if os.environ.get(variable):
            candidates.append(Path(os.environ[variable]) / suffix)
    try:
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, r'Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe') as key:
                    candidates.append(Path(winreg.QueryValue(key, None).strip('"')))
            except OSError:
                pass
    except ImportError:
        pass
    for path in candidates:
        if path.is_file():
            return path
    raise FileNotFoundError('Google Chrome was not found. Install Chrome, then retry. ASUNA will not switch to another browser.')


def open_chrome(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or any(c.isspace() for c in url):
        raise ValueError('Only ordinary http(s) web links can be opened.')
    from browser_control import session
    if session.available():
        session.call('open', url)
        return True
    subprocess.Popen([str(chrome_path()), '--new-tab', url], shell=False)
    return True
