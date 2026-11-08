"""Packaged extension page functions against an isolated, local Chrome fixture."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from browser import chrome_path
from playwright.sync_api import sync_playwright

HTML = '''<title>Extension fixture</title><h1>Fixture page</h1>
<a href="https://example.test/next"><h3>First result</h3></a>
<a href="https://example.test/clip.mp4">First video</a>
<label>Search<input name="q" type="search"></label>
<label>Password<input type="password"></label>
<button onclick="this.textContent='Clicked'">Submit</button><video></video>'''


class ExtensionPageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = sync_playwright().start()
        cls.browser = cls.engine.chromium.launch(executable_path=str(chrome_path()), headless=True, args=['--mute-audio'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.engine.stop()

    def setUp(self):
        self.page = self.browser.new_page()
        self.page.set_content(HTML)
        self.page.add_script_tag(path=str(Path(__file__).resolve().parents[1] / 'chrome-extension/page.js'))
        self.snapshot = self.page.evaluate("observePage('abcdef0123456789')")

    def tearDown(self):
        self.page.close()

    def item(self, name):
        return next(i for i in self.snapshot['items'] if i['name'] == name)

    def act(self, operation, item=None, value=''):
        return self.page.evaluate('([operation,payload])=>actOnPage(operation,payload)',
                                  [operation,{'item':item,'value':value,'url':self.snapshot['url']}])

    def test_observed_results_and_videos(self):
        self.assertTrue(self.item('First result')['result'])
        self.assertTrue(self.item('First video')['video'])
        self.assertIn('Fixture page',self.snapshot['text'])

    def test_literal_field_text_and_button(self):
        self.act('fill',self.item('Search'),'Literal <script>not code</script>')
        self.assertEqual(self.page.locator('input[name=q]').input_value(),'Literal <script>not code</script>')
        self.act('click',self.item('Submit'))
        self.assertEqual(self.page.locator('button').inner_text(),'Clicked')

    def test_password_and_changed_controls_are_rejected(self):
        with self.assertRaisesRegex(Exception,'authentication'):
            self.act('fill',self.item('Password'),'never entered')
        self.page.locator('button').evaluate("e=>e.textContent='Delete'")
        with self.assertRaisesRegex(Exception,'changed'):
            self.act('click',self.item('Submit'))

    def test_autocomplete_payment_and_missing_targets_are_rejected(self):
        self.page.locator('input[name=q]').evaluate("e=>e.autocomplete='cc-number'")
        with self.assertRaisesRegex(Exception,'payment'):
            self.act('fill',self.item('Search'),'never entered')
        self.page.locator('button').evaluate('e=>e.remove()')
        with self.assertRaisesRegex(Exception,'changed'):
            self.act('click',self.item('Submit'))

    def test_media_and_unsupported_code(self):
        state = self.act('media',value='mute')
        self.assertTrue(state['muted'])
        with self.assertRaisesRegex(Exception,'Unsupported'):
            self.act('evaluate',value='alert(1)')


if __name__ == '__main__':
    unittest.main(verbosity=2)
