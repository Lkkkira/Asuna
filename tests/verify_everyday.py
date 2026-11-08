"""Everyday assistant state, utilities, backups and PDF regression tests."""
import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from actions import Actions,read_document
from backups import create_backup,inspect_backup,restore_backup,daily_backup,validate_state
from chat_history import archive_chat,archived_chats
from everyday import TaskService,calculate,convert_units
from notes import Notes
from preferences import Preferences
from shortcuts import Shortcuts
from single_instance import SingleInstance
from planner import exact_plan,validate_plan,plan_of,step
from jarvis import Jarvis
from tools_local import ToolExecutor


class EverydayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_preferences_roundtrip_and_failed_save_preserves_active_values(self):
        preferences = Preferences(self.data)
        changed = preferences.values | {'fast_model':'another:4b','reply_style':'Brief'}
        preferences.save(changed)
        self.assertEqual(Preferences(self.data).models['Fast'],'another:4b')
        with patch.object(Path,'replace',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):preferences.save(changed|{'fast_model':'different:4b'})
        self.assertEqual(preferences.models['Fast'],'another:4b')
        with self.assertRaises(ValueError):preferences.save(changed|{'fast_model':'https://not-a-model'})
        with self.assertRaises(ValueError):preferences.save(changed|{'context_tokens':2048,'reply_tokens':2048})

    def test_shortcuts_only_launch_selected_executables_and_respect_disabled_state(self):
        executable = self.data/'Example App.exe'
        executable.touch()
        shortcuts = Shortcuts(self.data)
        shortcuts.set('My editor','app',str(executable))
        with patch('shortcuts.subprocess.Popen') as launch:
            shortcuts.open('my editor')
        launch.assert_called_once_with([str(executable)],shell=False)
        shortcuts.toggle('My editor')
        with self.assertRaises(ValueError):shortcuts.open('My editor')
        for name,kind,target in (('chrome','site','https://example.test'),('Script','app',str(self.data/'run.bat')),
                                 ('Account','site','https://user:password@example.test')):
            with self.assertRaises(ValueError):shortcuts.set(name,kind,target)

    def test_notes_migrate_without_deleting_source_and_support_archive_restore(self):
        legacy = self.data/'notes.txt'
        legacy.write_text('[old] A saved thought.',encoding='utf-8')
        notes = Notes(self.data)
        self.assertIn('saved thought',notes.read(1))
        self.assertTrue(legacy.exists())
        notes.save('A new thought')
        notes.save('Edited thought',2)
        self.assertIn('Edited',notes.listing('thought'))
        notes.archive(2)
        self.assertNotIn('Edited',Notes(self.data).listing())
        notes.archive(2,restore=True)
        self.assertIn('Edited',Notes(self.data).read(2))
        self.assertEqual(len(Notes(self.data).state['notes']),2)

    def test_tasks_due_priority_archive_restore_and_failed_save(self):
        actions = Actions(self.data)
        service = TaskService(actions)
        service.add('Take a walk')
        service.edit(1,{'due':'2026-11-12','priority':'high','done':True})
        self.assertIn('[done]',service.listing())
        service.edit(1,{'done':False,'archived':True})
        self.assertNotIn('Take a walk',service.listing())
        service.edit(1,{'archived':False})
        with self.assertRaises(ValueError):service.edit(1,{'due':'tomorrow'})
        with patch.object(Path,'replace',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):service.edit(1,{'text':'Unsaved change'})
        self.assertEqual(actions.state['tasks'][0]['text'],'Take a walk')
        self.assertEqual(Actions(self.data).state['tasks'][0]['priority'],'high')

    def test_reminder_save_failure_does_not_silently_mark_it_delivered(self):
        from datetime import datetime,timedelta
        actions = Actions(self.data)
        actions.execute('remind me in 1 second to stretch')
        actions.state['reminders'][0]['due']=(datetime.now()-timedelta(seconds=2)).isoformat()
        actions.save()
        with patch.object(Path,'replace',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):actions.due()
        self.assertFalse(actions.state['reminders'][0]['delivered'])

    def test_bounded_calculator_rejects_code_and_huge_work(self):
        self.assertEqual(calculate('(12+3)*4'),'(12+3)*4 = 60')
        self.assertIn('= 2',calculate('sqrt(4)'))
        for expression in ('__import__("os").system("anything")','[1,2]','2**100000000','1/0','True+1'):
            with self.assertRaises(ValueError):calculate(expression)
        self.assertIn('= 0.3',calculate('0.1+0.2'))

    def test_compatible_units_and_temperatures(self):
        self.assertIn('= 1609.344 m',convert_units('1 mile to m'))
        self.assertIn('= 32 f',convert_units('0 c to f'))
        self.assertIn('= 1024 b',convert_units('1 kib to b'))
        for text in ('1 kg to m','-300 c to f','20 usd to inr'):
            with self.assertRaises(ValueError):convert_units(text)

    def test_offline_command_plans_and_execution_share_the_same_notes_tasks(self):
        actions,repo = Actions(self.data),Jarvis(self.data)
        executor = ToolExecutor(actions,repo,lambda kind:'')
        executor.execute(step('save_note','Buy groceries'))
        self.assertIn('groceries',executor.execute(step('read_note',number=1)).detail)
        actions.execute('add task: stretch')
        plan = exact_plan('task 1 priority high')
        executor.execute(plan['steps'][0])
        self.assertEqual(actions.state['tasks'][0]['priority'],'high')
        self.assertEqual(exact_plan('start focus for 25 minutes')['steps'][0]['number'],1500)
        with self.assertRaises(ValueError):validate_plan(plan_of(step('edit_task','{"shell":"anything"}',1)))
        self.assertEqual(exact_plan('open Work portal',[{'name':'Work portal','kind':'site'}])['steps'][0]['tool'],'open_shortcut')

    def test_backups_include_archived_chats_and_exclude_cookies_tokens_models(self):
        notes = Notes(self.data)
        notes.save('First note')
        messages = [{'role':'user','content':'Hello from an archived chat'}]
        (self.data/'conversation.json').write_text(json.dumps(messages))
        archive_chat(self.data,messages)
        (self.data/'chrome-bridge.json').write_text('{"token":"private"}')
        (self.data/'chrome-profile').mkdir()
        (self.data/'chrome-profile/Cookies').write_text('private')
        backup = create_backup(self.data)
        payload = inspect_backup(backup)
        self.assertIn('notes.json',payload)
        self.assertTrue(any(n.startswith('conversations/') for n in payload))
        self.assertNotIn('chrome-bridge.json',payload)
        self.assertNotIn('chrome-profile/Cookies',payload)
        notes.save('Changed',1)
        restore_backup(self.data,backup)
        self.assertIn('First note',Notes(self.data).read(1))
        self.assertIsNone(daily_backup(self.data))

    def test_restore_can_recover_corrupt_current_state_and_preserves_its_bytes(self):
        notes = Notes(self.data)
        notes.save('Recoverable')
        good = create_backup(self.data)
        (self.data/'notes.json').write_bytes(b'corrupt original bytes')
        safety = restore_backup(self.data,good)
        self.assertIn('Recoverable',Notes(self.data).read(1))
        with zipfile.ZipFile(safety) as archive:
            self.assertEqual(archive.read('notes.json'),b'corrupt original bytes')

    def test_restore_rejects_traversal_and_tampering_before_writing(self):
        Notes(self.data).save('Keep me')
        original = (self.data/'notes.json').read_bytes()
        bad = self.data/'bad.zip'
        with zipfile.ZipFile(bad,'w') as archive:
            archive.writestr('../notes.json','bad')
            archive.writestr('manifest.json','{}')
        with self.assertRaises(ValueError):restore_backup(self.data,bad)
        self.assertEqual((self.data/'notes.json').read_bytes(),original)
        with zipfile.ZipFile(bad,'w') as archive:
            archive.writestr('notes.json',original)
            archive.writestr('manifest.json',json.dumps({'version':1,'files':{'notes.json':'wrong'}}))
        with self.assertRaises(ValueError):inspect_backup(bad)

    def test_partial_restore_failure_rolls_back_preceding_files(self):
        Notes(self.data).save('New note')
        (self.data/'conversation.json').write_text('[{"role":"user","content":"New chat"}]')
        backup = create_backup(self.data)
        Notes(self.data).save('Old note',1)
        old_chat=b'[{"role":"user","content":"Old chat"}]'
        (self.data/'conversation.json').write_bytes(old_chat)
        replace = Path.replace
        def fail_note(path,target):
            if path.name=='notes.json.restore-tmp':raise OSError('simulated disk failure')
            return replace(path,target)
        with patch.object(Path,'replace',fail_note):
            with self.assertRaises(OSError):restore_backup(self.data,backup)
        self.assertEqual((self.data/'conversation.json').read_bytes(),old_chat)
        self.assertIn('Old note',Notes(self.data).read(1))
        self.assertFalse(list(self.data.glob('*.restore-tmp')))

    def test_restore_rejects_state_that_would_break_the_organizer_or_memory_reader(self):
        invalid = [
            ('personal.json',{'memories':[{'id':1,'text':'Missing timestamp','archived':False}],'routines':[]}),
            ('organizer.json',{'tasks':[{'id':1,'text':'Invalid due date','done':False,'due':'tomorrow'}],'reminders':[]}),
            ('organizer.json',{'tasks':[],'reminders':[{'id':1,'text':'Wrong timezone','delivered':False,'due':'2026-11-09T20:00:00+00:00'}]})]
        for name,value in invalid:
            with self.assertRaises((ValueError,KeyError)):
                validate_state(name,json.dumps(value).encode())
        with self.assertRaises(ValueError):create_backup(self.data,self.data/'notes.json',overwrite=True)

    def test_single_instance_lock_is_released_and_chat_history_is_searchable(self):
        with SingleInstance(self.data):
            with self.assertRaises(RuntimeError):
                with SingleInstance(self.data):pass
        with SingleInstance(self.data):pass
        archive_chat(self.data,[{'role':'user','content':'My travel plan'}])
        self.assertEqual(len(archived_chats(self.data,'travel')),1)
        self.assertEqual(archived_chats(self.data,'no such phrase'),[])

    def test_text_pdf_extraction_and_scanned_encrypted_rejection(self):
        from pypdf import PdfWriter
        from pypdf.generic import NameObject,DictionaryObject,DecodedStreamObject
        writer=PdfWriter()
        page=writer.add_blank_page(width=300,height=200)
        font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):font})})
        stream=DecodedStreamObject()
        stream.set_data(b'BT /F1 12 Tf 10 50 Td (Local PDF text works.) Tj ET')
        page[NameObject('/Contents')]=writer._add_object(stream)
        pdf=self.data/'sample.pdf'
        writer.write(pdf)
        self.assertIn('Local PDF text works',read_document(pdf)[1])
        blank=PdfWriter();blank.add_blank_page(width=100,height=100);blank.write(self.data/'scan.pdf')
        with self.assertRaisesRegex(ValueError,'no selectable text'):read_document(self.data/'scan.pdf')
        writer.encrypt('fixture-password');writer.write(self.data/'locked.pdf')
        with self.assertRaisesRegex(ValueError,'encrypted'):read_document(self.data/'locked.pdf')


if __name__=='__main__':unittest.main(verbosity=2)
