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

    def test_script_errors_are_returned_without_rejected_injection(self):
        self.page.locator('video').evaluate('e=>e.remove()')
        result = self.page.evaluate("runPageCommand('actOnPage',['media',{value:'pause'}])")
        self.assertFalse(result['ok'])
        self.assertIn('No HTML video/audio',result['error'])

    def test_media_waits_for_a_player_loaded_after_navigation(self):
        self.page.locator('video').evaluate('e=>e.remove()')
        self.page.evaluate("setTimeout(()=>document.body.appendChild(document.createElement('video')),150)")
        state = self.act('media',value='mute')
        self.assertTrue(state['muted'])

    def like_fixture(self, pressed='false'):
        self.page.set_content('''<button id="like" aria-label="like this video along with 191,712 other people" aria-pressed="''' + pressed + '''"
            onclick="window.clicks=(window.clicks||0)+1;this.setAttribute('aria-pressed',this.getAttribute('aria-pressed')==='true'?'false':'true')">191K</button>
            <button aria-label="Like this comment along with 10 other people" aria-pressed="false">10</button>
            <button aria-label="Dislike this video" aria-pressed="false">Dislike</button>''')
        self.snapshot = self.page.evaluate("observePage('abcdef0123456789')")
        return self.item('like this video along with 191,712 other people')

    def test_like_toggles_only_the_video_and_returns_verified_state(self):
        item = self.like_fixture()
        self.assertEqual(item['pressed'],'false')
        # Counts change independently of the user's reviewed video/action.
        self.page.locator('#like').evaluate("e=>e.setAttribute('aria-label','like this video along with 191,713 other people')")
        self.assertTrue(self.act('like',item)['liked'])
        self.assertEqual(self.page.locator('#like').get_attribute('aria-pressed'),'true')
        self.assertEqual(self.page.evaluate('window.clicks'),1)
        self.assertTrue(self.act('like',item)['alreadyLiked'])
        self.assertEqual(self.page.evaluate('window.clicks'),1)

    def test_like_never_clicks_a_comment_or_unknown_state(self):
        item = self.like_fixture()
        with self.assertRaisesRegex(Exception,'not the video Like'):
            self.act('like',self.item('Like this comment along with 10 other people'))
        self.page.locator('#like').evaluate("e=>e.removeAttribute('aria-pressed')")
        with self.assertRaisesRegex(Exception,'state is unknown'):
            self.act('like',item)
        self.assertIsNone(self.page.evaluate('window.clicks'))

    def test_like_button_stays_discoverable_after_long_comment_lists(self):
        self.like_fixture()
        self.page.locator('#like').evaluate("e=>{for(let i=0;i<180;i++){let b=document.createElement('button');b.textContent='Comment '+i;document.body.prepend(b)}}")
        snapshot = self.page.evaluate("observePage('abcdef0123456789')")
        self.assertEqual(snapshot['items'][0]['name'],'like this video along with 191,712 other people')


if __name__ == '__main__':
    unittest.main(verbosity=2)
