"""Explicit local actions. Model replies never execute commands."""
import json
import os
import re
import stat
import subprocess
from browser import open_chrome
from desktop_apps import discord_executable
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote_plus, urlparse

HELP = '''Here’s what I can do:
Ask naturally, for example: “Find my physics notes in Downloads” or
“Remind me to study in half an hour.” I’ll ask if details are missing.
Use “show your work” to inspect each action and its result, even while busy.

• Open YouTube, Google, Amazon, Stack Overflow (open stackoverflow), or GitHub
• Search YouTube: a topic / Wikipedia: a topic / Location: a place
• Define: a word (bundled offline dictionary with spelling suggestions)
• Take a screenshot / What time is it / What is today's date
• Remember: a personal fact / Show memories / Update memory 1: a correction
• Forget memory 1 / Restore memory 1 (forget archives it locally)
• Daily reminder at 20:00: stretch / Monday task at 09:00: review expenses
• Show routines / Pause routine 1 / Resume routine 1 / Daily overview
• Open calculator, notepad, paint, explorer, task manager, settings, or browser
• Open downloads, documents, desktop, or a website (open https://example.com)
• Search web for: your question (opens your browser)
• Choose search folder, then find file: part of its name
• Open result 1 (documents, pictures, and folders only)
• Read document — choose a text file or Word .docx; then ask me about it
• Add task: finish assignment / Show tasks / Complete task 1
• Remind me in 20 minutes to take a break / Show reminders / Cancel reminder 1
• Save note: your note / Show notes
• Switch to fast / Switch to deep / Show activity / Hide activity
• Read page / Summarize this page / Open the first result / Open the first video
• Click 12 / Click About / Fill 8: your text (use displayed IDs or exact labels)
• Go back / Go forward / Reload page / Scroll down / Show browser tabs / Switch to tab 2
• Pause / Resume / Mute / Unmute (HTML video/audio on the current page)
• Like the video — reviewed Like action on the current YouTube video; skips videos already liked
• Connect browser — pair the local extension in your chosen Chrome profile
• Open Discord / Open Discord in Chrome (desktop with web fallback, or explicit web app)
• Open a service name in Chrome (known address, otherwise a web search for that name)
• Type Discord in the search box / Type: your draft (reviewed webpage typing; no automatic send)

Reminders appear here while ASUNA is open. Overdue reminders appear on restart.
Personal memory is saved only when you ask. Routines use your PC's local clock.
Missed routine occurrences catch up once, rather than replaying every missed day.
File search stays inside your chosen folder and returns up to 30 matches.
Document reading includes up to 10,000 characters. No PDF reader yet.'''


def normalize(text):
    text = re.sub(r'^\s*(?:hey\s+)?asuna[,!:\s]+', '', text, flags=re.I)
    text = re.sub(r'^(?:could you|can you|please)\s+', '', text, flags=re.I)
    return text.strip()


class Actions:
    def __init__(self, data):
        self.data = data
        self.path = data / 'organizer.json'
        self.state = {'tasks': [], 'reminders': [], 'search_folder': ''}
        if self.path.exists():
            saved = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(saved, dict) or any(not isinstance(saved.get(k), list) for k in ('tasks', 'reminders')):
                raise ValueError('Organizer data has an invalid format. Please preserve it and restore from a backup.')
            self.state.update(saved)
        self.results = []

    def save(self):
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(self.state, ensure_ascii=False, indent=2), encoding='utf-8')
        temp.replace(self.path)

    def choose_folder(self, folder):
        self.state['search_folder'] = str(Path(folder).resolve())
        self.save()
        self.results = []

    def add_routine_task(self, routine, now=None):
        key = str(routine['id']) + ':' + routine['next_due']
        existing = next((t for t in self.state['tasks'] if t.get('routine_key') == key), None)
        if existing:
            return existing
        task = {'id': max([t['id'] for t in self.state['tasks']], default=0) + 1,
                'text': routine['text'], 'done': False, 'routine_key': key}
        self.state['tasks'].append(task)
        try:
            self.save()
        except OSError:
            self.state['tasks'].remove(task)
            raise
        return task

    def due(self):
        due = [r for r in self.state['reminders'] if not r['delivered'] and datetime.fromisoformat(r['due']) <= datetime.now()]
        if due:
            for reminder in due:
                reminder['delivered'] = True
            self.save()
        return due

    def execute(self, text):
        raw = normalize(text)
        key = raw.lower().rstrip('.!?')
        apps = {'calculator': ['calc.exe'], 'notepad': ['notepad.exe'], 'paint': ['mspaint.exe'],
                'explorer': ['explorer.exe'], 'file explorer': ['explorer.exe'], 'task manager': ['taskmgr.exe']}
        if key.startswith(('open ', 'launch ', 'start ')):
            target = raw.split(' ', 1)[1].strip().removeprefix('the ')
            name = target.lower().rstrip('.!?')
            if name in apps:
                subprocess.Popen(apps[name], shell=False)
                return 'Requested Windows to open ' + name + '.'
            if name == 'discord':
                try:
                    subprocess.Popen([str(discord_executable())], shell=False)
                    return 'Requested Windows to open Discord.'
                except OSError:
                    open_chrome('https://discord.com/app')
                    return 'Could not start the Discord desktop app; opened Discord in Chrome instead.'
            if name == 'settings':
                os.startfile('ms-settings:')
                return 'Opened Windows Settings.'
            if name in ('browser', 'web browser', 'chrome', 'google chrome'):
                open_chrome('https://www.google.com')
                return 'Requested Google Chrome.'
            if name in ('downloads', 'documents', 'desktop'):
                # Use Windows known folders, including redirected Documents/Desktop.
                import ctypes
                import uuid
                ids = {'downloads': '374DE290-123F-4565-9164-39C4925E467B',
                       'documents': 'FDD39AD0-238F-46AF-ADB4-6C85480369C7',
                       'desktop': 'B4BFCC3A-DB2C-424C-B029-7FE99A87C641'}
                guid = (ctypes.c_ubyte * 16).from_buffer_copy(uuid.UUID(ids[name]).bytes_le)
                pointer = ctypes.c_wchar_p()
                code = ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(pointer))
                if code != 0:
                    raise OSError('Windows could not locate ' + name)
                try:
                    path = pointer.value
                finally:
                    ctypes.windll.ole32.CoTaskMemFree(ctypes.cast(pointer, ctypes.c_void_p))
                os.startfile(path)
                return 'Opened ' + name + '.'
            if target.lower().startswith(('https://', 'http://')) and urlparse(target).hostname:
                open_chrome(target)
                return 'Requested Chrome to open ' + target
        match = re.fullmatch(r'search (?:the )?web for\s*:?\s*(.+)', raw, re.I)
        if match:
            open_chrome('https://www.google.com/search?q=' + quote_plus(match[1]))
            return 'Opened web search in Chrome. I have not read the results.'
        match = re.fullmatch(r'(?:find file|search files)\s*:\s*(.+)', raw, re.I)
        if match:
            return self.find(match[1])
        match = re.fullmatch(r'open result (\d+)', key)
        if match:
            index = int(match[1]) - 1
            if not 0 <= index < len(self.results):
                return 'Choose a number from the latest file search results.'
            path = self.results[index].resolve()
            root = Path(self.state['search_folder']).resolve()
            if not path.is_relative_to(root) or not path.exists():
                return 'That result is no longer available inside your search folder.'
            if not path.is_dir() and path.suffix.lower() not in {'.txt', '.md', '.pdf', '.docx', '.png', '.jpg', '.jpeg', '.gif', '.bmp'}:
                return 'I only open folders, plain documents, PDFs, and pictures from search results.'
            os.startfile(str(path))
            return 'Requested Windows to open ' + str(path)
        match = re.fullmatch(r'add task\s*:\s*(.+)', raw, re.I)
        if match:
            tasks = self.state['tasks']
            tasks.append({'id': max([t['id'] for t in tasks], default=0) + 1, 'text': match[1], 'done': False})
            self.save()
            return 'Added task ' + str(tasks[-1]['id']) + ': ' + match[1]
        if key in ('show tasks', 'my tasks'):
            return '\n'.join(f"{t['id']}. {'[done]' if t['done'] else '[ ]'} {t['text']}" for t in self.state['tasks']) or 'No tasks yet. Try: add task: review chapter 2'
        match = re.fullmatch(r'complete task (\d+)', key)
        if match:
            for task in self.state['tasks']:
                if task['id'] == int(match[1]):
                    task['done'] = True
                    self.save()
                    return 'Completed task ' + match[1] + '.'
            return 'Task number not found.'
        match = re.fullmatch(r'remind me in (\d+) (second|minute|hour|day)s? to (.+)', raw, re.I)
        if match:
            seconds = int(match[1]) * {'second': 1, 'minute': 60, 'hour': 3600, 'day': 86400}[match[2].lower()]
            if not 1 <= seconds <= 366 * 86400:
                return 'Choose a delay between 1 second and 366 days.'
            reminders = self.state['reminders']
            reminder = {'id': max([r['id'] for r in reminders], default=0) + 1,
                        'due': (datetime.now() + timedelta(seconds=seconds)).isoformat(timespec='seconds'),
                        'text': match[3], 'delivered': False}
            reminders.append(reminder)
            self.save()
            return f"Reminder {reminder['id']} set for {datetime.fromisoformat(reminder['due']):%d %b %Y, %I:%M %p}. Keep ASUNA open."
        if key == 'show reminders':
            return '\n'.join(f"{r['id']}. {r['due'].replace('T', ' ')} — {r['text']}" for r in self.state['reminders'] if not r['delivered']) or 'No pending reminders.'
        match = re.fullmatch(r'cancel reminder (\d+)', key)
        if match:
            for reminder in self.state['reminders']:
                if reminder['id'] == int(match[1]) and not reminder['delivered']:
                    reminder['delivered'] = True
                    self.save()
                    return 'Cancelled reminder ' + match[1] + '.'
            return 'Pending reminder number not found.'
        # Prevent unsupported action requests from being misrepresented as executed.
        if re.match(r'^(open|launch|start|find file|search files|add task|complete task|remind me|cancel reminder)\b', key):
            return 'I could not match that action. Type help to see supported commands.'
        return None

    def find(self, query):
        folder = self.state['search_folder']
        if not folder:
            return 'Choose a search folder first using “Choose search folder”.'
        root = Path(folder).resolve()
        if not root.is_dir():
            return 'Your search folder is unavailable. Choose it again.'
        self.results = []
        scanned = 0
        import time
        deadline = time.monotonic() + 15
        def ordinary_folder(path):
            try:
                return not (path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
            except (OSError, AttributeError):
                return not path.is_symlink()

        for current, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in {'.git', 'node_modules', '__pycache__'} and ordinary_folder(Path(current) / d))
            for name in sorted(dirs + files):
                scanned += 1
                path = Path(current) / name
                if query.casefold() in name.casefold() and path.resolve().is_relative_to(root):
                    self.results.append(path)
                if len(self.results) >= 30 or scanned >= 20000 or time.monotonic() >= deadline:
                    break
            if len(self.results) >= 30 or scanned >= 20000 or time.monotonic() >= deadline:
                break
        results = '\n'.join(f'{i}. {p}' for i, p in enumerate(self.results, 1)) or 'No matching names found.'
        return results + '\nSearch limited to 30 matches, 20,000 entries, or about 15 seconds. Try “open result 1”.'


def read_document(filename):
    path = Path(filename)
    if path.stat().st_size > 5 * 1024 * 1024:
        raise ValueError('Choose a document smaller than 5 MB.')
    if path.suffix.lower() == '.docx':
        with zipfile.ZipFile(path) as archive:
            if archive.getinfo('word/document.xml').file_size > 10 * 1024 * 1024:
                raise ValueError('This Word document expands beyond the reading limit.')
            tree = ET.fromstring(archive.read('word/document.xml'))
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            text = '\n'.join(''.join(p.itertext()) for p in tree.findall('.//w:p', ns))
    elif path.suffix.lower() in {'.txt', '.md', '.csv', '.py', '.json', '.log'}:
        text = path.read_text(encoding='utf-8-sig', errors='replace')
    else:
        raise ValueError('Supported: TXT, MD, CSV, PY, JSON, LOG and DOCX. PDF support is not included yet.')
    if not text.strip():
        raise ValueError('No readable text found in this file.')
    return path.name, text[:10000], len(text) > 10000
