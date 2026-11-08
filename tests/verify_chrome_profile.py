"""Profile routing and authenticated loopback bridge tests. No personal Chrome I/O."""
import concurrent.futures
import http.client
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import browser_profile
from browser import open_chrome
from browser_control import BrowserSession
from chrome_bridge import ProfileBridge


class ProfileTests(unittest.TestCase):
    def test_profile_metadata_and_settings_never_copy_account_data(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'Profile 1').mkdir()
            (root / 'Local State').write_text(json.dumps({'profile': {'info_cache': {
                'Profile 1': {'name': 'Chosen profile', 'user_name': 'private@example.test'},
                '../bad': {'name': 'Invalid'}}}}))
            _, profiles = browser_profile.profiles(root)
            self.assertEqual(len(profiles), 1)
            browser_profile.save(profiles[0], root / 'data')
            value = browser_profile.settings(root / 'data')
            self.assertEqual(value['profile_directory'], 'Profile 1')
            self.assertNotIn('private@example.test', json.dumps(value))

    def test_invalid_or_missing_profile_does_not_open_a_different_one(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for value in ([], {'profile_directory':'../Default','user_data_dir':folder},
                          {'profile_directory':'Profile 1','user_data_dir':folder}):
                browser_profile.save(value, root)
                with self.assertRaises(ValueError):
                    browser_profile.settings(root)

    def test_unpaired_open_always_launches_selected_profile(self):
        profile = {'profile_directory':'Profile 1','user_data_dir':'C:/Chrome/User Data'}
        bridge = MagicMock()
        bridge.connected.return_value = False
        with patch('browser_profile.settings', return_value=profile), patch('browser.chrome_path', return_value=Path('chrome.exe')), \
                patch('browser_control.session.profile_bridge', return_value=bridge), patch('browser_profile.subprocess.Popen') as launch:
            open_chrome('https://example.test')
        launch.assert_called_once_with(['chrome.exe','--user-data-dir=C:/Chrome/User Data',
                                        '--profile-directory=Profile 1','--new-tab','https://example.test'], shell=False)

    def test_paired_open_uses_extension_not_separate_chrome(self):
        bridge = MagicMock()
        bridge.connected.return_value = True
        with patch('browser_profile.settings', return_value={'profile_directory':'Profile 1'}), \
                patch('browser_control.session.profile_bridge', return_value=bridge), \
                patch('browser_control.session.call', return_value={'detail':'Opened'}) as call, patch('browser_profile.launch') as launch:
            open_chrome('https://example.test')
        call.assert_called_once_with('open','https://example.test')
        launch.assert_not_called()

    def test_browser_commands_route_to_profile_even_without_playwright(self):
        with tempfile.TemporaryDirectory() as folder:
            session = BrowserSession(folder)
            session.extension_bridge = MagicMock()
            with patch('browser_profile.settings', return_value={'profile_directory':'Profile 1'}), patch.object(session,'available',return_value=False):
                session.call('read')
            session.extension_bridge.call.assert_called_once_with('read','',0)
            self.assertIsNone(session.context)
            session.close()


class BridgeTests(unittest.TestCase):
    ORIGIN = 'chrome-extension://' + 'a' * 32

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.bridge = ProfileBridge(self.temp.name, port=0)
        self.bridge.start()

    def tearDown(self):
        self.bridge.close()
        self.temp.cleanup()

    def post(self, path, value=None, origin=None, token=None, host=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.bridge.port, timeout=3)
        headers = {'Content-Type':'application/json','Origin':origin or self.ORIGIN,
                   'Authorization':'Bearer ' + (token or self.bridge.token)}
        if host:
            headers['Host'] = host
        connection.request('POST',path,json.dumps(value or {}),headers)
        response = connection.getresponse()
        result = response.status,json.loads(response.read())
        connection.close()
        return result

    def pair(self, **kwargs):
        self.bridge.pair_code = '1' * 64
        self.bridge.pair_deadline = time.monotonic() + 30
        kwargs.setdefault('token', self.bridge.pair_code)
        return self.post('/pair', **kwargs)

    def test_only_token_authenticated_extension_origin_and_loopback_host(self):
        self.assertEqual(self.bridge.server.server_address[0], '127.0.0.1')
        for kwargs in ({'origin':'https://evil.test'},{'token':'wrong'},{'host':'evil.test'}):
            self.assertEqual(self.pair(**kwargs)[0],403)
        self.assertEqual(self.pair()[0],200)
        self.assertTrue(self.bridge.connected())
        self.assertEqual(self.post('/poll',origin='chrome-extension://'+'b'*32)[0],403)

    def test_pairing_code_is_one_use_and_rotates_the_persistent_secret(self):
        old_token = self.bridge.token
        self.assertEqual(self.pair()[0],200)
        self.assertNotEqual(self.bridge.token,old_token)
        self.assertEqual(self.post('/pair',token='1'*64)[0],403)
        self.assertEqual(self.post('/result',token=old_token)[0],403)

    def test_status_cannot_create_a_fake_connection(self):
        self.assertFalse(self.post('/status')[1]['connected'])
        self.assertFalse(self.bridge.connected())
        self.pair()
        self.assertTrue(self.post('/status')[1]['connected'])

    def test_connection_page_does_not_serve_the_pairing_secret(self):
        connection = http.client.HTTPConnection('127.0.0.1',self.bridge.port)
        connection.request('GET','/connect')
        response = connection.getresponse()
        self.assertEqual(response.status,200)
        self.assertNotIn(self.bridge.token,response.read().decode())
        connection.close()

    def test_command_result_and_duplicate_acknowledgement(self):
        self.pair()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self.bridge.call,'read')
            _, reply = self.post('/poll')
            job = reply['job']
            self.assertEqual(job['action'],'read')
            result = {'detail':'Read fixture','snapshot':{'token':'test','url':'https://example.test',
                       'title':'Fixture','items':[],'text':'Reference only'}}
            self.assertTrue(self.post('/result',{'id':job['id'],'result':result})[1]['ok'])
            self.assertEqual(future.result(timeout=2),{'detail':'Read fixture'})
            self.assertFalse(self.post('/result',{'id':job['id'],'result':result})[1]['ok'])
        self.assertNotIn('text',self.bridge.cached())

    def test_disconnect_cancels_pending_commands_and_cached_targets(self):
        self.pair()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self.bridge.call,'read')
            self.post('/poll')
            self.post('/disconnect')
            with self.assertRaisesRegex(RuntimeError,'disconnected'):
                future.result(timeout=2)
        self.assertFalse(self.bridge.connected())
        self.assertEqual(self.bridge.cached()['token'],'')

    def test_unpaired_and_arbitrary_commands_fail_without_launching(self):
        with self.assertRaisesRegex(RuntimeError,'page-control connection is not ready'):
            self.bridge.call('read')
        for action in ('evaluate','shell','download'):
            with self.assertRaises(ValueError):
                self.bridge.call(action)


if __name__ == '__main__':
    unittest.main(verbosity=2)
