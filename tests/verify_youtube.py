import sys, tempfile, time, runpy
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import asuna
with tempfile.TemporaryDirectory() as folder:
    asuna.DATA = Path(folder)
    root = asuna.tk.Tk()
    root.withdraw()
    app = asuna.Asuna(root)
    with patch('jarvis.webbrowser.open_new_tab') as browser:
        app.submit('open youtube')
        deadline = time.monotonic() + 5
        while app.busy and time.monotonic() < deadline:
            root.update()
            time.sleep(.02)
        browser.assert_called_once_with('https://youtube.com')
        assert not app.busy
        assert 'Requested your default browser to open youtube.' in app.chat.get('1.0', 'end')
        assert 'Repo edition' in root.title()
    root.destroy()
print('PASS: YouTube UI command reaches the browser function in the repo edition.')
