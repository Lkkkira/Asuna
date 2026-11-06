import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from jarvis import Jarvis
from actions import normalize

with tempfile.TemporaryDirectory() as folder:
    bot = Jarvis(folder)
    assert 'ASUNA' in bot.execute_query('what is your name')
    assert 'time is' in bot.execute_query('what time is it')
    assert bot.execute_query('explain photosynthesis') is None
    assert 'not enabled' in bot.execute_query('shutdown')
    assert 'algorithm:' in bot.execute_query('define: algorithm').lower()
    assert 'Did you mean' in bot.execute_query('define: algorthm')
    with patch('jarvis.webbrowser.open_new_tab') as browser:
        bot.execute_query(normalize('ASUNA, please open youtube'))
        browser.assert_called_once_with('https://youtube.com')
    with patch('jarvis.webbrowser.open_new_tab') as browser:
        bot.execute_query('search youtube: Python & AI')
        browser.assert_called_once_with('https://www.youtube.com/results?search_query=Python+%26+AI')
    with patch('jarvis.webbrowser.open_new_tab') as browser:
        bot.execute_query('location: New Delhi')
        assert 'New+Delhi' in browser.call_args[0][0]
    bot.execute_query('remember that: exam Friday')
    assert 'exam Friday' in Jarvis(folder).execute_query('what do you remember')
    with patch('jarvis.subprocess.run') as capture:
        capture.return_value.returncode = 1
        capture.return_value.stderr = 'capture blocked'
        try:
            bot.execute_query('take a screenshot')
            raise AssertionError('Failed capture was reported as success')
        except RuntimeError as exc:
            assert 'could not capture' in str(exc)
print('PASS: adapted upstream routing, offline dictionary/spelling, encoded browser searches, note persistence, unsupported actions, screenshot failure reporting.')
