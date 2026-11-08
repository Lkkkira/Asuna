"""Settings/organizer and cancellation without personal data, accounts or audio."""
import gc
import json
import queue
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import asuna
from planner import plan_of,step


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def button(window,label):
    return next(w for w in descendants(window) if isinstance(w,asuna.tk.Button) and w.cget('text')==label)


class ControlCenterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_data = asuna.DATA
        asuna.DATA = Path(self.temp.name)
        self.root = asuna.tk.Tk()
        self.root.withdraw()
        self.app = asuna.Asuna(self.root)

    def tearDown(self):
        self.app.cancel_requested.set()
        self.app.voice.close()
        for callback in self.root.tk.call('after','info'):
            self.root.after_cancel(callback)
        self.root.destroy()
        self.app = self.root = None
        gc.collect()
        asuna.DATA = self.old_data
        self.temp.cleanup()

    def test_settings_save_models_style_and_default_mode_without_clearing_chat(self):
        self.app.history = [{'role':'user','content':'A current conversation'}]
        self.app.show_settings()
        self.root.update()
        self.app.fast_model_choice.set('custom:4b')
        self.app.deep_model_choice.set('custom:8b')
        button(self.app.settings_window,'Save settings').invoke()
        self.assertEqual(self.app.models,{'Fast':'custom:4b','Deep':'custom:8b'})
        self.assertEqual(self.app.history[0]['content'],'A current conversation')
        self.assertEqual(json.loads((asuna.DATA/'preferences.json').read_text())['fast_model'],'custom:4b')
        with patch('control_center.messagebox.showinfo') as info:
            self.app.busy = True
            self.app.fast_model_choice.set('should-not-save:4b')
            button(self.app.settings_window,'Save settings').invoke()
        self.assertEqual(self.app.models['Fast'],'custom:4b')
        info.assert_called_once()

    def test_organizer_task_actions_and_note_editor_share_chat_stores(self):
        self.app.show_organizer()
        self.root.update()
        window = self.app.organizer_window
        with patch('control_center.simpledialog.askstring',return_value='Plan the weekend'):
            button(window,'Add task').invoke()
        trees = [w for w in descendants(window) if isinstance(w,asuna.ttk.Treeview)]
        tasks = trees[0]
        tasks.selection_set('1')
        button(window,'Done / reopen').invoke()
        self.assertTrue(self.app.actions.state['tasks'][0]['done'])
        button(window,'Done / reopen').invoke()
        self.assertFalse(self.app.actions.state['tasks'][0]['done'])
        button(window,'Add note').invoke()
        editor = next(w for w in window.winfo_children() if isinstance(w,asuna.tk.Toplevel))
        body = next(w for w in descendants(editor) if isinstance(w,asuna.scrolledtext.ScrolledText))
        body.insert('1.0','Remember the charger')
        button(editor,'Save note').invoke()
        self.assertIn('charger',self.app.repo_commands.notes.read(1))
        self.assertEqual(len(trees[1].get_children()),1)

    def test_new_chat_archives_and_history_is_read_only(self):
        self.app.history = [{'role':'user','content':'Weekend plans'},{'role':'assistant','content':'Take a walk.'}]
        self.app.persist()
        self.app.clear()
        self.assertEqual(self.app.history,[])
        self.app.show_history()
        self.root.update()
        window = self.app.history_window
        view = next(w for w in descendants(window) if isinstance(w,asuna.ttk.Treeview))
        view.selection_set(view.get_children()[0])
        view.event_generate('<<TreeviewSelect>>')
        self.root.update()
        body = next(w for w in descendants(window) if isinstance(w,asuna.scrolledtext.ScrolledText))
        self.assertEqual(body.cget('state'),'disabled')
        self.assertIn('Take a walk',body.get('1.0','end'))

    def test_setup_check_selection_refreshes_without_audio_capture(self):
        expected = ([('Ollama','Running','Ready')],['local:4b'])
        with patch('diagnostics.setup_report',return_value=expected) as report:
            self.app.show_settings('health')
            self.root.update()
            # Bounded queue wait allows the diagnostic thread to finish without Tk calls.
            if not self.app.health_tree.get_children():
                event = self.app.events.get(timeout=2)
                self.assertEqual(event,('setup_health',expected))
                self.app.events.put(event)
        self.app.poll()
        self.assertEqual(self.app.health_tree.item('0','values'),('Ollama','Running','Ready'))
        self.assertEqual(tuple(self.app.fast_model_choice.cget('values')),('local:4b',))
        report.assert_called_once()

    def test_stop_keeps_completed_action_and_skips_remaining_steps(self):
        self.app.begin_job('Two tasks')
        self.app.busy = True
        original = asuna.ToolExecutor.execute
        calls = []
        def execute(executor,action):
            calls.append(action)
            result = original(executor,action)
            self.app.cancel_requested.set()
            return result
        plan = plan_of(step('add_task','First task'),step('add_task','Second task'))
        with patch('asuna.exact_plan',return_value=plan),patch.object(asuna.ToolExecutor,'execute',execute):
            self.app.action_worker('Two tasks')
        self.app.poll()
        self.assertEqual(len(calls),1)
        self.assertEqual([t['text'] for t in self.app.actions.state['tasks']],['First task'])
        self.assertFalse(self.app.busy)
        self.assertIn('Cancelled',self.app.status.get())
        self.assertIn('First task',self.app.chat.get('1.0','end'))
        self.assertIn('First task',self.app.history[-1]['content'])
        self.assertIn('Stopped at your request',self.app.history[-1]['content'])

    def test_stop_before_planning_or_review_runs_nothing(self):
        self.app.cancel_requested.set()
        with patch('asuna.exact_plan') as plan,patch('asuna.request') as request:
            self.app.action_worker('open something')
        plan.assert_not_called()
        request.assert_not_called()
        answer = queue.Queue()
        self.app.events.put(('browser_confirm',('Click button',answer)))
        with patch('asuna.messagebox.askyesno') as confirm:
            self.app.poll()
        self.assertFalse(answer.get_nowait())
        confirm.assert_not_called()

    def test_stop_during_stream_preserves_partial_answer_and_releases_response(self):
        app = self.app
        class Response:
            closed = False
            def __enter__(self):return self
            def __exit__(self,*args):self.closed = True
            def __iter__(self):
                yield json.dumps({'message':{'content':'A partial answer'}}).encode()
                app.cancel_requested.set()
                yield json.dumps({'done':True}).encode()
        response = Response()
        app.begin_job('Explain something')
        app.busy = True
        with patch('asuna.request',return_value=response):
            app.work('qwen3.5:4b',[],'Explain something')
        app.poll()
        self.assertTrue(response.closed)
        self.assertIsNone(app.active_response)
        self.assertFalse(app.busy)
        self.assertIn('A partial answer',app.history[-1]['content'])
        self.assertIn('[Stopped before completion]',app.history[-1]['content'])
        self.assertEqual(app.stop_button.cget('state'),'disabled')

    def test_stopping_waiting_worker_cannot_launch_a_later_action(self):
        errors = []
        def waiting():
            try:self.app.wait_for_answer(queue.Queue())
            except InterruptedError:errors.append('cancelled')
        thread = threading.Thread(target=waiting)
        thread.start()
        self.app.cancel_requested.set()
        thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors,['cancelled'])

    def test_settings_and_organizer_buttons_fit_the_minimum_windows(self):
        self.root.deiconify()
        for show,attr in ((self.app.show_settings,'settings_window'),(self.app.show_organizer,'organizer_window')):
            show()
            window = getattr(self.app,attr)
            width,height = window.minsize()
            window.geometry(f'{width}x{height}')
            self.root.update()
            for w in descendants(window):
                if isinstance(w,asuna.tk.Button) and w.winfo_ismapped():
                    self.assertLessEqual(w.winfo_rooty()+w.winfo_height(),window.winfo_rooty()+window.winfo_height(),w.cget('text'))


if __name__=='__main__':unittest.main(verbosity=2)
