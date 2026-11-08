"""Chrome routing checks; never launches a real browser."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from browser import chrome_path, open_chrome
from actions import Actions
from jarvis import Jarvis
from planner import exact_plan


class ChromeTests(unittest.TestCase):
    def setUp(self):
        self.profile_settings = patch('browser_profile.settings', return_value=None)
        self.profile_settings.start()
        self.addCleanup(self.profile_settings.stop)

    def test_launches_chrome_with_separate_url_argument(self):
        path = Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
        with patch('browser_control.session.available', return_value=False), patch('browser.chrome_path', return_value=path), patch('browser.subprocess.Popen') as launch:
            open_chrome('https://youtube.com')
        launch.assert_called_once_with([str(path), '--new-tab', 'https://youtube.com'], shell=False)

    def test_no_chrome_gives_error_instead_of_system_browser_fallback(self):
        with patch('browser_control.session.available', return_value=False), patch('browser.Path.is_file', return_value=False), patch('browser.subprocess.Popen') as launch:
            with self.assertRaisesRegex(FileNotFoundError, 'Chrome was not found'):
                open_chrome('https://youtube.com')
        launch.assert_not_called()

    def test_finds_standard_installation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'Google/Chrome/Application/chrome.exe'
            path.parent.mkdir(parents=True)
            path.touch()
            with patch.dict('os.environ', {'ProgramFiles': folder}):
                self.assertEqual(chrome_path(), path)

    def test_rejects_non_web_urls_and_flags(self):
        for url in ['file:///C:/test.exe', 'javascript:alert(1)', '--incognito', 'https://example.com bad']:
            with self.assertRaises(ValueError):
                open_chrome(url)

    def test_named_sites_and_searches_use_same_chrome_helper(self):
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder)
            with patch('jarvis.open_chrome') as chrome:
                bot = Jarvis(data)
                bot.execute_query('open youtube')
                bot.execute_query('search youtube: Python')
                self.assertEqual(chrome.call_count, 2)
            with patch('actions.open_chrome') as chrome:
                actions = Actions(data)
                actions.execute('open chrome')
                actions.execute('search web for: hello')
                actions.execute('open https://example.com')
                self.assertEqual(chrome.call_count, 3)
        self.assertEqual(exact_plan('open chrome')['steps'][0]['tool'], 'open_app')


if __name__ == '__main__':
    unittest.main(verbosity=2)
