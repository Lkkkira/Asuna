"""Local memory, recurrence, catch-up and UI integration checks."""
import io
import json
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import asuna
from actions import Actions
from personal import PersonalStore, next_occurrence
from planner import step, plan_of, exact_plan, validate_plan, make_plan, clock_times


def repeat(cadence='daily', at='20:00', kind='reminder', weekday=0):
    return {'cadence': cadence, 'time': at, 'weekday': weekday, 'kind': kind}


class PersonalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name)
        self.personal = PersonalStore(self.data)
        self.actions = Actions(self.data)

    def tearDown(self):
        self.temp.cleanup()

    def test_memory_restart_update_archive_restore_and_context_boundary(self):
        self.personal.save_memory('I prefer short answers')
        self.personal.save_memory('I prefer detailed answers', 1, context_floor=4)
        restored = PersonalStore(self.data)
        self.assertEqual(restored.memories()[0]['text'], 'I prefer detailed answers')
        self.assertEqual(restored.state['context_floor'], 4)
        restored.archive_memory(1, context_floor=8)
        restarted = PersonalStore(self.data)
        self.assertFalse(restarted.memories())
        self.assertNotIn('detailed answers', restarted.show_memories())
        self.assertEqual(restarted.state['context_floor'], 8)
        restarted.archive_memory(1, restore=True)
        self.assertEqual(len(restarted.memories()), 1)

    def test_duplicate_memory_does_not_add_another_record(self):
        self.personal.save_memory('I like tea')
        self.personal.save_memory('i like tea')
        self.assertEqual(len(self.personal.memories()), 1)

    def test_failed_save_does_not_activate_memory(self):
        with patch.object(Path, 'replace', side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError):
                self.personal.save_memory('must not become active')
        self.assertFalse(self.personal.memories())

    def test_daily_and_weekday_wall_clock_times(self):
        friday = datetime(2026, 11, 6, 20, 0)
        self.assertEqual(next_occurrence(repeat(), friday), datetime(2026, 11, 7, 20))
        self.assertEqual(next_occurrence(repeat('weekdays'), friday), datetime(2026, 11, 9, 20))
        self.assertEqual(next_occurrence(repeat('weekly', weekday=0), friday), datetime(2026, 11, 9, 20))

    def test_invalid_schedule_is_rejected_before_write(self):
        for schedule in [repeat(at='25:00'), repeat(at='8:00'), repeat('monthly'), repeat(weekday=7)]:
            with self.assertRaises(ValueError):
                self.personal.add_routine('test', schedule)
        self.assertFalse(self.personal.state['routines'])

    def test_overdue_routine_catches_up_once_then_skips_backlog(self):
        self.personal.add_routine('stretch', repeat(), now=datetime(2026, 11, 5, 12))
        restarted = PersonalStore(self.data)
        now = datetime(2026, 11, 9, 21)
        due = restarted.due(now)
        self.assertEqual(len(due), 1)
        restarted.acknowledge(due[0]['id'], due[0]['next_due'], now)
        self.assertFalse(PersonalStore(self.data).due(now))
        self.assertEqual(restarted.state['routines'][0]['next_due'], '2026-11-10T20:00:00')

    def test_pause_resume_and_update_persist(self):
        self.personal.add_routine('stretch', repeat(), now=datetime(2026, 11, 5, 12))
        self.personal.pause_routine(1)
        self.assertFalse(PersonalStore(self.data).due(datetime(2026, 11, 10)))
        self.personal.pause_routine(1, resume=True, now=datetime(2026, 11, 10, 21))
        self.assertEqual(self.personal.state['routines'][0]['next_due'], '2026-11-11T20:00:00')
        self.personal.add_routine('walk', repeat(at='07:30'), number=1, now=datetime(2026, 11, 10, 21))
        self.assertEqual(len(self.personal.state['routines']), 1)
        self.assertEqual(self.personal.state['routines'][0]['next_due'], '2026-11-11T07:30:00')

    def test_generated_task_is_idempotent_across_restart(self):
        self.personal.add_routine('review expenses', repeat(kind='task'), now=datetime(2026, 11, 5, 12))
        routine = self.personal.due(datetime(2026, 11, 5, 21))[0]
        first = self.actions.add_routine_task(routine)
        reopened = Actions(self.data)
        second = reopened.add_routine_task(routine)
        self.assertEqual(first['id'], second['id'])
        self.assertEqual(len(reopened.state['tasks']), 1)
        reopened.execute('complete task 1')
        self.assertTrue(Actions(self.data).state['tasks'][0]['done'])

    def test_overview_includes_open_tasks_and_excludes_tomorrow(self):
        self.actions.execute('add task: buy groceries')
        self.actions.state['reminders'] = [
            {'id': 1, 'text': 'today', 'due': '2026-11-07T18:00:00', 'delivered': False},
            {'id': 2, 'text': 'tomorrow only', 'due': '2026-11-08T18:00:00', 'delivered': False}]
        overview = self.personal.overview(self.actions, datetime(2026, 11, 7, 12))
        self.assertIn('buy groceries', overview)
        self.assertIn('today', overview)
        self.assertNotIn('tomorrow only', overview)

    def test_exact_commands_and_schedule_validation(self):
        self.assertEqual(exact_plan('remember: I prefer tea')['steps'][0]['tool'], 'save_memory')
        self.assertEqual(exact_plan('show notes')['steps'][0]['tool'], 'show_notes')
        self.assertEqual(exact_plan('daily reminder at 20:00: stretch')['steps'][0]['repeat'], repeat())
        self.assertEqual(exact_plan('monday task at 09:00: review expenses')['steps'][0]['repeat'], repeat('weekly', '09:00', 'task'))
        with self.assertRaises(ValueError):
            validate_plan(plan_of(step('add_routine', 'stretch')))
        with self.assertRaises(ValueError):
            validate_plan(plan_of(step('time', repeat=repeat())))

    def planned(self, text, payloads, context=None):
        calls = []
        def request(path, body):
            calls.append(body)
            plan = payloads[min(len(calls) - 1, len(payloads) - 1)]
            return io.BytesIO(json.dumps({'done': True, 'message': {'content': json.dumps(plan)}}).encode())
        return make_plan(request, 'fixture', text, context or {})

    def test_clock_time_is_required_even_when_model_guesses(self):
        guessed = plan_of(step('add_routine', 'stretch', repeat=repeat(at='08:00')))
        result = self.planned('Remind me every day to stretch', [guessed])
        self.assertEqual(result['kind'], 'clarify')
        self.assertFalse(result['steps'])
        self.assertEqual(clock_times('at eight in the evening'), {'20:00'})
        self.assertEqual(clock_times('at 8'), set())
        self.assertEqual(clock_times('at 8 PM'), {'20:00'})

    def test_wrong_am_pm_gets_corrected_before_any_action(self):
        wrong = plan_of(step('add_routine', 'stretch', repeat=repeat(at='08:00')))
        right = plan_of(step('add_routine', 'stretch', repeat=repeat(at='20:00')))
        result = self.planned('Remind me every day at 8 PM to stretch', [wrong, right])
        self.assertEqual(result['steps'][0]['repeat']['time'], '20:00')

    def test_weekly_routine_needs_a_weekday(self):
        guessed = plan_of(step('add_routine', 'expenses', repeat=repeat('weekly')))
        result = self.planned('Add a weekly task at 20:00 to review expenses', [guessed])
        self.assertEqual(result['kind'], 'clarify')
        self.assertIn('weekday', result['question'])

    def test_routine_cancellation_cannot_cancel_matching_one_time_id(self):
        context = {'routines': [{'id': 1, 'text': 'stretch'}], 'reminders': [{'id': 1, 'text': 'dentist'}]}
        wrong = plan_of(step('cancel_reminder', number=1))
        right = plan_of(step('pause_routine', number=1))
        result = self.planned('Stop my daily stretch reminder', [wrong, right], context)
        self.assertEqual(result['steps'][0]['tool'], 'pause_routine')

    def test_no_unsolicited_memory_save_but_followup_consent_is_allowed(self):
        save = plan_of(step('save_memory', 'I like tea'))
        chat = {'kind': 'chat', 'question': '', 'needs_reply': False, 'steps': []}
        result = self.planned('I like tea', [save, chat])
        self.assertEqual(result['kind'], 'chat')
        result = self.planned('yes', [save], {'clarification': {
            'original_request': 'I like tea', 'question': 'Would you like me to remember that?'}})
        self.assertEqual(result['steps'][0]['tool'], 'save_memory')

    def test_monthly_schedule_is_not_silently_converted_to_daily(self):
        wrong = plan_of(step('add_routine', 'expenses', repeat=repeat()))
        result = self.planned('Create a monthly task at 20:00 to review expenses', [wrong])
        self.assertEqual(result['kind'], 'clarify')


class PersonalUI(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old_data = asuna.DATA
        asuna.DATA = Path(self.temp.name)
        self.root = asuna.tk.Tk()
        self.root.withdraw()
        self.app = asuna.Asuna(self.root)

    def tearDown(self):
        for callback in self.root.tk.call('after', 'info'):
            self.root.after_cancel(callback)
        self.root.destroy()
        asuna.DATA = self.old_data
        self.temp.cleanup()

    def wait(self):
        until = time.monotonic() + 5
        while self.app.busy and time.monotonic() < until:
            self.root.update()
            time.sleep(.01)
        self.assertFalse(self.app.busy)

    def ask(self, text):
        chat = {'kind': 'chat', 'question': '', 'needs_reply': False, 'steps': []}
        stream = io.BytesIO((json.dumps({'done': True, 'message': {'content': 'Test answer'}}) + '\n').encode())
        with patch('asuna.make_plan', return_value=chat), patch('asuna.request', return_value=stream) as request:
            self.app.submit(text)
            self.wait()
        return request.call_args.args[1]['messages']

    def test_memory_is_used_in_replies_and_archive_removes_old_chat_context(self):
        self.app.submit('remember: I like jasmine tea')
        self.wait()
        messages = self.ask('Suggest a drink')
        self.assertIn('jasmine tea', json.dumps(messages))
        self.app.submit('forget memory 1')
        self.wait()
        self.app.submit('show memories')
        self.wait()
        messages = self.ask('What should I drink?')
        self.assertNotIn('jasmine tea', json.dumps(messages))
        self.assertIn('jasmine tea', self.app.chat.get('1.0', 'end'))
        self.assertEqual(self.app.personal.memories(), [])

    def test_ordinary_conversation_does_not_save_memory(self):
        self.ask('I sometimes like coffee')
        self.assertFalse(self.app.personal.memories())

    def test_restart_keeps_routines_and_new_conversation_keeps_memory(self):
        self.app.submit('remember: I prefer short replies')
        self.wait()
        self.app.submit('daily task at 20:00: tidy desk')
        self.wait()
        restarted = PersonalStore(asuna.DATA)
        self.assertEqual(len(restarted.state['routines']), 1)
        self.app.clear()
        self.assertEqual(len(self.app.personal.memories()), 1)
        self.assertEqual(self.app.personal.state['context_floor'], 0)

    def test_routine_task_retry_after_ack_failure_does_not_duplicate(self):
        now = datetime(2026, 11, 7, 21)
        self.app.personal.add_routine('tidy desk', repeat(kind='task'), now=datetime(2026, 11, 7, 12))
        with patch.object(self.app.personal, 'acknowledge', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.app.process_routines(now)
        with patch.object(self.root, 'bell'), patch.object(self.root, 'deiconify'), patch.object(self.root, 'lift'):
            self.app.process_routines(now)
        self.assertEqual(len(self.app.actions.state['tasks']), 1)
        self.assertFalse(self.app.personal.due(now))


if __name__ == '__main__':
    unittest.main(verbosity=2)
