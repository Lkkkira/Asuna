"""Reactor regressions without models, real audio, or personal data."""
import gc
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import asuna


class ReactorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous_data = asuna.DATA
        asuna.DATA = Path(self.temp.name)
        self.root = asuna.tk.Tk()
        self.root.withdraw()
        self.app = asuna.Asuna(self.root)

    def tearDown(self):
        self.app.voice.close()
        for callback in self.root.tk.call('after', 'info'):
            self.root.after_cancel(callback)
        self.root.destroy()
        self.app = self.root = None
        gc.collect()
        asuna.DATA = self.previous_data
        self.temp.cleanup()

    def deliver(self, kind, value=None):
        self.app.events.put((kind, value))
        self.app.poll()

    def test_job_states_follow_worker_events(self):
        self.app.begin_job('Open a page and explain it')
        self.app.busy = True
        self.assertEqual(self.app.reactor.mode, 'thinking')
        self.deliver('plan', ['Open page'])
        self.deliver('step', (0, 'Working', 'Running Open page'))
        self.assertEqual(self.app.reactor.mode, 'working')
        self.app.update_job('Working', 'Writing a reply using the local model.')
        self.assertEqual(self.app.reactor.mode, 'thinking')
        self.deliver('action', ('Open a page and explain it', 'Finished the request.'))
        self.assertEqual(self.app.reactor.mode, 'idle')
        self.assertIn('Completed', self.app.status.get())

    def test_recording_levels_and_review_never_send(self):
        self.app.begin_job('Voice input')
        self.app.voice.input_busy = True
        self.deliver('voice_recording')
        self.deliver('voice_level', .75)
        self.assertEqual(self.app.reactor.mode, 'listening')
        self.assertEqual(self.app.reactor.level, .75)
        self.deliver('voice_status', 'Transcribing locally…')
        self.assertEqual(self.app.reactor.mode, 'thinking')
        self.app.voice.input_busy = False
        with patch.object(self.app, 'submit') as submit:
            self.deliver('voice_transcript', 'open youtube')
        submit.assert_not_called()
        self.assertEqual(self.app.reactor.mode, 'waiting')
        self.assertEqual(self.app.entry.get(), 'open youtube')

    def test_stopped_speech_ignores_stale_events(self):
        generation = self.app.voice.speech_generation
        self.deliver('speech_status', (generation, 'Speaking…'))
        self.assertEqual(self.app.reactor.mode, 'speaking')
        self.deliver('speech_status', (generation, 'Voice ready'))
        self.assertEqual(self.app.reactor.mode, 'idle')
        self.deliver('speech_status', (generation, 'Speaking…'))
        self.app.stop_speaking()
        self.deliver('speech_status', (generation, 'Speaking…'))
        self.assertEqual(self.app.reactor.mode, 'idle')

    def test_clarification_failure_and_new_chat(self):
        self.app.begin_job('remind me later')
        self.deliver('clarify', ('remind me later', 'What time?', None))
        self.assertEqual(self.app.reactor.mode, 'waiting')
        self.app.begin_job('Try another request')
        self.deliver('action_error', 'Example failure')
        self.assertEqual(self.app.reactor.mode, 'error')
        self.app.clear()
        self.assertEqual(self.app.reactor.mode, 'idle')
        self.assertEqual(self.app.reactor_task.get(), 'Waiting for your request')

    def test_motion_persistence_and_timer_cleanup(self):
        self.app.motion_enabled.set(False)
        self.app.save_ui_settings()
        self.assertFalse(json.loads((asuna.DATA / 'ui-settings.json').read_text())['motion'])
        self.root.deiconify()
        self.root.update()
        phase = self.app.reactor.phase
        self.root.after(250, self.root.quit)
        self.root.mainloop()
        self.assertEqual(self.app.reactor.phase, phase)
        self.app.voice.close()
        for callback in self.root.tk.call('after', 'info'):
            self.root.after_cancel(callback)
        self.root.destroy()
        self.root = asuna.tk.Tk()
        self.root.withdraw()
        self.app = asuna.Asuna(self.root)
        self.assertFalse(self.app.motion_enabled.get())
        timer = self.app.reactor.after_id
        self.app.reactor.destroy()
        self.assertNotIn(timer, self.root.tk.call('after', 'info'))

    def test_small_window_preserves_chat_work_and_composer(self):
        self.root.deiconify()
        self.app.begin_job('A longer personal request about files and browser work. ' * 5)
        self.app.update_job('Working', 'Understanding your longer request with the local model…')
        for geometry in ('1100x800', '720x680'):
            self.root.geometry(geometry)
            for visible in (True, False, True):
                self.app.show_activity(visible)
                self.root.update()
                self.assertTrue(self.app.entry.winfo_ismapped())
                self.assertTrue(self.app.chat.winfo_ismapped())
                self.assertGreaterEqual(self.app.chat.winfo_height(), 50)
                self.assertEqual(bool(self.app.work_tree.winfo_ismapped()), visible)
                self.assertLessEqual(self.app.entry.winfo_rooty() + self.app.entry.winfo_height(),
                                     self.root.winfo_rooty() + self.root.winfo_height())


if __name__ == '__main__':
    unittest.main(verbosity=2)
