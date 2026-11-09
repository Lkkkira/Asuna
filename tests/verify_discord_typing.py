"""Discord routing, browser fallback and typing commands; no real apps/accounts."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from actions import Actions
from actions import normalize
from desktop_apps import discord_executable
from jarvis import Jarvis
from planner import exact_plan, validate_plan


class DiscordTypingTests(unittest.TestCase):
    def test_discord_desktop_and_browser_intents_stay_distinct(self):
        self.assertEqual(validate_plan(exact_plan('open discord'))['steps'][0]['tool'],'open_app')
        for text in ('open Discord in chrome','open discord in crome','launch Discord in the browser','open discord website'):
            self.assertEqual(exact_plan(text)['steps'][0]['text'],'discord')
            self.assertEqual(exact_plan(text)['steps'][0]['tool'],'open_site')

    def test_unknown_browser_target_is_a_search_not_an_empty_browser(self):
        plan = exact_plan('open A Newly Named Service in Chrome')
        self.assertEqual(plan['steps'][0]['tool'],'search_web')
        self.assertEqual(plan['steps'][0]['text'],'A Newly Named Service')
        self.assertEqual(exact_plan('open example.org/path in Chrome')['steps'][0]['text'],'https://example.org/path')
        self.assertIsNone(exact_plan('open YouTube and search Python in Chrome'))
        for url in ('file:///C:/private.txt','javascript:alert(1)'):
            with self.assertRaises(ValueError):
                exact_plan('open '+url+' in Chrome')

    def test_desktop_launch_uses_latest_existing_executable_and_separate_arguments(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for version in ('1.0.9','1.0.20'):
                app = root / 'Discord' / ('app-'+version)
                app.mkdir(parents=True)
                (app/'Discord.exe').touch()
            with patch.dict('os.environ',{'LOCALAPPDATA':folder}):
                executable = discord_executable()
            self.assertEqual(executable.parent.name,'app-1.0.20')
            with patch('actions.discord_executable',return_value=executable), patch('actions.subprocess.Popen') as launch, patch('actions.open_chrome') as browser:
                result = Actions(root).execute('open discord')
            launch.assert_called_once_with([str(executable)],shell=False)
            browser.assert_not_called()
            self.assertIn('Requested Windows',result)

    def test_missing_desktop_app_opens_official_web_app_once(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('actions.discord_executable',side_effect=FileNotFoundError), patch('actions.subprocess.Popen') as launch, patch('actions.open_chrome') as browser:
                result = Actions(Path(folder)).execute('open discord')
            launch.assert_not_called()
            browser.assert_called_once_with('https://discord.com/app')
            self.assertIn('Chrome instead',result)
            with patch('jarvis.open_chrome') as browser:
                Jarvis(folder).execute_query('open discord')
            browser.assert_called_once_with('https://discord.com/app')

    def test_failed_desktop_launch_uses_web_fallback_without_retrying(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch('actions.discord_executable',return_value=Path(folder)/'Discord.exe'), patch('actions.subprocess.Popen',side_effect=PermissionError) as launch, patch('actions.open_chrome') as browser:
                Actions(Path(folder)).execute('open discord')
            self.assertEqual(launch.call_count,1)
            browser.assert_called_once_with('https://discord.com/app')

    def test_typing_preserves_literal_text_and_does_not_plan_submit(self):
        for command, field, value in (
            ('type "Discord & friends!" in the search box','@search','Discord & friends!'),
            ('type: Hello, world!','@focused','Hello, world!'),
            ('enter "a draft" into the focused field','@focused','a draft')):
            steps = exact_plan(command)['steps']
            self.assertEqual(len(steps),1)
            self.assertEqual(steps[0]['tool'],'browser_fill')
            self.assertEqual(json.loads(steps[0]['text']),{'field':field,'value':value})

    def test_search_browser_commands_preserve_requested_query(self):
        for command in ('search Chrome for Discord','search for Discord in the browser'):
            step = exact_plan(command)['steps'][0]
            self.assertEqual((step['tool'],step['text']),('search_web','Discord'))

    def test_explicit_youtube_playback_preserves_query_and_orders_steps(self):
        for text,query in (('open youtube and play music','music'),('play lo-fi music on YouTube','lo-fi music'),
                           ('Open YouTube in Chrome and then play some jazz','jazz')):
            steps = exact_plan(text)['steps']
            self.assertEqual([(s['tool'],s['text'],s['number']) for s in steps],
                             [('search_youtube',query,0),('browser_open_item','video',1),('browser_media','play',0)])
        for text in ("open youtube and play jazz then like the video",'open youtube and play my playlist'):
            self.assertIsNone(exact_plan(text))

    def test_short_numbered_followups_remain_browser_commands(self):
        for text,kind,number in (('first video','video',1),('the second result','result',2),('3 link','link',3)):
            step = exact_plan(text)['steps'][0]
            self.assertEqual((step['tool'],step['text'],step['number']),('browser_open_item',kind,number))
        self.assertEqual(len(exact_plan('play the first video')['steps']),2)

    def test_playback_uses_current_video_or_search_and_only_reuses_an_explicit_recent_query(self):
        context={'youtube_query':'music','browser':{'url':'https://www.youtube.com/watch?v=fixture'}}
        self.assertEqual([s['tool'] for s in exact_plan('play it',context=context)['steps']],['browser_media'])
        context['browser']['url']='https://www.youtube.com/results?search_query=music'
        self.assertEqual([s['tool'] for s in exact_plan('play it',context=context)['steps']],['browser_open_item','browser_media'])
        self.assertEqual([s['tool'] for s in exact_plan('open youtube and play the first video')['steps']],['open_site','browser_open_item','browser_media'])
        self.assertEqual([s['tool'] for s in exact_plan('play it')['steps']],['browser_media'])
        self.assertEqual(normalize('opwn youtube and play the first video'),'open youtube and play the first video')
        self.assertEqual(normalize('type: opwn my draft'),'type: opwn my draft')


if __name__ == '__main__':
    unittest.main(verbosity=2)
