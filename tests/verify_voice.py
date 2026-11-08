"""Offline voice control/UI checks; never opens a real microphone or speaker."""
import io
import gc
import json
import queue
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from voice import VoiceController, spoken_text, resample_pcm, choose_mixed_language, expected_script
import asuna


class VoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.voice = VoiceController(queue.Queue(), self.path, self.path)

    def tearDown(self):
        self.voice.close()
        self.temp.cleanup()

    def events(self):
        return list(self.voice.events.queue)

    def fake_capture(self, silence=False, overflow=False):
        import numpy as np
        voice = self.voice
        class Stream:
            def __init__(self, **kwargs):
                self.callback = kwargs['callback']
            def __enter__(self):
                data = np.zeros(16000, dtype=np.int16) if silence else (np.sin(np.arange(16000) * .1) * 16000).astype(np.int16)
                self.callback(data.tobytes(), len(data), None, 'overflow' if overflow else '')
                voice.stop_recording.set()
                return self
            def __exit__(self, *args):
                return False
        return types.SimpleNamespace(query_devices=lambda *args: {'default_samplerate': 16000},
                                     check_input_settings=lambda **kwargs: None, RawInputStream=Stream)

    def test_silence_does_not_become_a_command(self):
        with patch.dict(sys.modules, {'sounddevice': self.fake_capture(silence=True)}), patch.object(self.voice, 'transcribe') as transcribe:
            self.voice.input_busy = True
            self.voice.capture(None, 'en')
        transcribe.assert_not_called()
        self.assertTrue(any(k == 'voice_error' for k, _ in self.events()))
        self.assertFalse(self.voice.input_busy)

    def test_fake_microphone_transcribes_locally_without_auto_execution(self):
        with patch.dict(sys.modules, {'sounddevice': self.fake_capture()}), patch.object(self.voice, 'transcribe', return_value='open youtube') as transcribe:
            self.voice.input_busy = True
            self.voice.capture(2, 'hi')
        self.assertIn(('voice_transcript', 'open youtube'), self.events())
        self.assertTrue(any(k == 'voice_level' and 0 < v <= 1 for k, v in self.events()))
        self.assertEqual(transcribe.call_args.args[1], 'hi')
        self.assertFalse(self.voice.input_busy)
        self.assertFalse(list(self.path.iterdir()))

    def test_overflow_does_not_send_incomplete_transcript(self):
        with patch.dict(sys.modules, {'sounddevice': self.fake_capture(overflow=True)}), patch.object(self.voice, 'transcribe') as transcribe:
            self.voice.capture(None, None)
        transcribe.assert_not_called()
        self.assertFalse(any(k == 'voice_transcript' for k, _ in self.events()))

    def test_resampling_matches_whisper_input(self):
        import numpy as np
        pcm = np.zeros(48000, dtype=np.int16).tobytes()
        samples = resample_pcm([pcm], 48000)
        self.assertEqual(len(samples), 16000)
        self.assertEqual(samples.dtype, np.float32)

    def test_speech_strips_code_urls_and_caps_long_replies(self):
        cleaned = spoken_text('**Hello** [friend](https://example.com) ```python\nprint(1)\n```')
        self.assertNotIn('print(1)', cleaned)
        self.assertNotIn('https://', cleaned)
        self.assertIn('friend', cleaned)
        self.assertLess(len(spoken_text('word ' * 1000)), 1900)

    def test_missing_setup_is_clear_and_opens_no_devices(self):
        with patch.object(self.voice, 'ready', return_value=False):
            with self.assertRaisesRegex(RuntimeError, 'Setup Voice.bat'):
                self.voice.start_recording()

    def test_stale_speech_worker_cannot_start(self):
        self.voice.stop_speaking()
        with patch('voice.subprocess.Popen') as process:
            self.voice.speech_worker('old reply', '', 0)
        process.assert_not_called()

    def test_text_goes_through_stdin_not_shell(self):
        proc = MagicMock()
        proc.communicate.return_value = (b'', b'')
        proc.returncode = 0
        with patch('voice.subprocess.Popen', return_value=proc) as process:
            self.voice.speech_worker('Literal text: $(do not execute)', 'Microsoft Zira Desktop', 0)
        command = process.call_args.args[0]
        self.assertNotIn('Literal text', ' '.join(command))
        payload = json.loads(proc.communicate.call_args.args[0])
        self.assertEqual(payload['voice'], 'Microsoft Zira Desktop')
        self.assertIn('$(do not execute)', payload['text'])

    def test_stop_speaking_terminates_current_process(self):
        process = MagicMock()
        process.poll.return_value = None
        self.voice.speech_process = process
        self.voice.stop_speaking()
        process.terminate.assert_called_once()

    def test_recognizer_never_downloads_at_runtime(self):
        module = types.ModuleType('faster_whisper')
        module.WhisperModel = MagicMock()
        module.WhisperModel.return_value.transcribe.return_value = ([types.SimpleNamespace(text='hello')], None)
        with patch.dict(sys.modules, {'faster_whisper': module}):
            self.assertEqual(self.voice.transcribe('fixture'), 'hello')
        self.assertTrue(module.WhisperModel.call_args.kwargs['local_files_only'])
        self.assertEqual(module.WhisperModel.call_args.kwargs['device'], 'cpu')

    def test_english_is_forced_instead_of_auto_detection(self):
        self.voice.model = MagicMock()
        self.voice.model.transcribe.return_value = ([types.SimpleNamespace(text='open calculator')], None)
        self.voice.transcribe('fixture')
        arguments = self.voice.model.transcribe.call_args.kwargs
        self.assertEqual(arguments['language'], 'en')
        self.assertEqual(arguments['task'], 'transcribe')
        self.assertEqual(arguments['temperature'], 0.0)
        self.voice.model.detect_language.assert_not_called()

    def test_mixed_profile_is_limited_to_english_and_hindi(self):
        self.assertEqual(choose_mixed_language([('ja', .9), ('en', .07), ('hi', .03)]), 'en')
        self.assertEqual(choose_mixed_language([('de', .6), ('en', .1), ('hi', .3)]), 'hi')
        self.assertEqual(choose_mixed_language([('en', .4), ('hi', .42)]), 'en')
        self.voice.model = MagicMock()
        self.voice.model.detect_language.return_value = ('ja', .9, [('ja', .9), ('en', .07), ('hi', .03)])
        self.voice.model.transcribe.return_value = ([types.SimpleNamespace(text='hello')], None)
        import numpy as np
        self.voice.transcribe(np.zeros(16000, dtype=np.float32), 'mixed')
        self.assertEqual(self.voice.model.transcribe.call_args.kwargs['language'], 'en')

    def test_unexpected_script_is_rejected_in_selected_profiles(self):
        self.assertTrue(expected_script('Hello नमस्ते ASUNA'))
        self.assertFalse(expected_script('これは日本語です'))
        self.voice.model = MagicMock()
        self.voice.model.transcribe.return_value = ([types.SimpleNamespace(text='これは日本語です')], None)
        with self.assertRaisesRegex(RuntimeError, 'unexpected language'):
            self.voice.transcribe('fixture', 'en')
        self.assertEqual(self.voice.transcribe('fixture', None), 'これは日本語です')

    def test_small_model_is_selected_only_when_download_is_complete(self):
        folder = self.path / 'voice-model-small'
        folder.mkdir()
        (folder / 'model.bin').touch()
        incomplete = VoiceController(queue.Queue(), self.path, self.path)
        self.assertEqual(incomplete.model_name, 'Base')
        for name in ('config.json', 'tokenizer.json', 'vocabulary.txt'):
            (folder / name).touch()
        complete = VoiceController(queue.Queue(), self.path, self.path)
        self.assertEqual(complete.model_name, 'Small')

    def test_resampler_filters_out_of_band_microphone_noise(self):
        import numpy as np
        t = np.arange(48000) / 48000
        low = (np.sin(2 * np.pi * 1000 * t) * 16000).astype(np.int16)
        high = (np.sin(2 * np.pi * 12000 * t) * 16000).astype(np.int16)
        low_output = resample_pcm([low.tobytes()], 48000)[100:-100]
        high_output = resample_pcm([high.tobytes()], 48000)[100:-100]
        self.assertLess(float(np.sqrt(np.mean(high_output ** 2))), float(np.sqrt(np.mean(low_output ** 2))) * .1)


class VoiceUI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_data = asuna.DATA
        asuna.DATA = Path(self.temp.name)
        self.root = asuna.tk.Tk()
        self.root.withdraw()
        self.app = asuna.Asuna(self.root)

    def tearDown(self):
        self.app.voice.close()
        self.root.update_idletasks()
        for callback in self.root.tk.call('after', 'info'):
            self.root.after_cancel(callback)
        self.root.destroy()
        self.app = self.root = None
        gc.collect()
        asuna.DATA = self.old_data
        self.temp.cleanup()

    def test_transcript_waits_for_review_and_keeps_draft(self):
        self.app.entry.insert(0, 'Please')
        self.app.begin_job('Voice input')
        self.app.events.put(('voice_transcript', 'open youtube'))
        with patch.object(self.app, 'submit') as submit:
            self.app.poll()
        submit.assert_not_called()
        self.assertEqual(self.app.entry.get(), 'Please open youtube')
        self.assertFalse(self.app.history)

    def test_recording_blocks_send_without_losing_draft(self):
        self.app.voice.input_busy = True
        self.app.entry.insert(0, 'unfinished request')
        self.app.send()
        self.assertEqual(self.app.entry.get(), 'unfinished request')
        self.assertFalse(self.app.history)

    def test_recording_suspends_routine_delivery(self):
        self.app.voice.input_busy = True
        with patch.object(self.app.actions, 'due') as due:
            self.app.check_reminders()
        due.assert_not_called()

    def test_speak_reply_toggle_and_streamed_answer(self):
        self.app.speak_replies.set(True)
        self.app.events.put(('begin', None))
        self.app.events.put(('token', 'Hello'))
        self.app.events.put(('done', ('hello', 'Hello')))
        with patch.object(self.app.voice, 'speak') as speak:
            self.app.poll()
        speak.assert_called_once_with('Hello', '')
        self.app.speak_replies.set(False)
        with patch.object(self.app.voice, 'speak') as speak:
            self.app.say('ASUNA', 'silent reply')
        speak.assert_not_called()

    def test_stale_speech_status_does_not_override_stop(self):
        self.app.stop_speaking()
        self.app.events.put(('speech_status', (0, 'Speaking…')))
        self.app.poll()
        self.assertEqual(self.app.voice_status.get(), 'Speech stopped')

    def test_voice_settings_are_saved_locally(self):
        self.app.voice_name = 'Microsoft Zira Desktop'
        self.app.voice_language = 'en'
        self.app.speak_replies.set(True)
        self.app.save_voice_settings()
        settings = json.loads((asuna.DATA / 'voice-settings.json').read_text())
        self.assertEqual(settings['voice'], 'Microsoft Zira Desktop')
        self.assertTrue(settings['speak_replies'])

    def test_voice_on_and_off_are_saved_and_action_replies_are_spoken(self):
        with patch.object(self.app.voice,'speak') as speak:
            self.app.submit('voice on')
            self.assertTrue(self.app.speak_replies.get())
            self.assertIn('On',self.app.speech_label.get())
            self.assertTrue(json.loads((asuna.DATA/'voice-settings.json').read_text())['speak_replies'])
            speak.assert_called_once()
            self.app.submit('voice off')
            self.assertFalse(self.app.speak_replies.get())
            self.assertIn('Off',self.app.speech_label.get())
            self.assertEqual(speak.call_count,1)

    def test_explicit_voice_test_works_without_enabling_reply_playback(self):
        self.assertFalse(self.app.speak_replies.get())
        with patch.object(self.app.voice,'speak') as speak:
            self.app.test_voice('Selected female voice')
        speak.assert_called_once()
        self.assertEqual(speak.call_args.args[1],'Selected female voice')
        self.assertFalse(self.app.speak_replies.get())
        self.app.voice.input_busy = True
        with patch.object(self.app.voice,'speak') as speak:
            self.app.test_voice()
        speak.assert_not_called()

    def test_voice_settings_test_button_is_visible_and_uses_the_selected_voice(self):
        with patch.object(self.app,'voice_options_worker'):
            self.app.show_voice_settings()
        window = self.app.voice_window
        window.geometry('600x390')
        self.root.update()
        bar = next(w for w in window.winfo_children() if isinstance(w,asuna.tk.Frame))
        test_button = next(w for w in bar.winfo_children() if w.cget('text')=='Test voice')
        self.assertTrue(test_button.winfo_ismapped())
        self.assertLessEqual(test_button.winfo_rooty()+test_button.winfo_height(),window.winfo_rooty()+window.winfo_height())
        with patch.object(self.app,'test_voice') as test:
            test_button.invoke()
        test.assert_called_once_with('')

    def test_new_profile_defaults_to_english_and_mixed_is_persisted(self):
        self.assertEqual(self.app.voice_language, 'en')
        self.app.voice_language = 'mixed'
        self.app.save_voice_settings()
        settings = json.loads((asuna.DATA / 'voice-settings.json').read_text())
        self.assertEqual(settings['language'], 'mixed')


if __name__ == '__main__':
    unittest.main(verbosity=2)
