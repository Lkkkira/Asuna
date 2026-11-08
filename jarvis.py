"""ASUNA command engine adapted from GauravSingh9356/J.A.R.V.I.S.

Original MIT copyright is retained in LICENSE. Original implementation is
preserved in jarvis_legacy.py. Importing this module starts no devices/network.
"""
import json
import re
import subprocess
from browser import open_chrome
from datetime import datetime
from difflib import get_close_matches
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent


class Jarvis:
    """Upstream command dispatch modernized for ASUNA's background worker."""

    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir else ROOT / 'data'
        self.dictionary = None
        self.word_index = None

    def execute_query(self, query):
        key = query.strip().lower().rstrip('.!?')
        sites = {'youtube': 'https://youtube.com', 'amazon': 'https://amazon.com',
                 'google': 'https://google.com', 'stackoverflow': 'https://stackoverflow.com',
                 'github': 'https://github.com'}
        if key.startswith('open ') and key[5:] in sites:
            open_chrome(sites[key[5:]])
            return 'Requested Chrome to open ' + key[5:] + '.'
        if key in ('what time is it', 'the time', 'time', 'tell me the time'):
            return 'The time is ' + datetime.now().strftime('%I:%M %p') + '.'
        if key in ('date', 'what is the date', "what is today's date"):
            return datetime.now().strftime('%A, %d %B %Y')
        if key in ('your name', 'what is your name', 'who are you'):
            return 'I’m ASUNA, your local personal assistant.'
        if key in ('are you there', 'asuna are you there'):
            return 'I’m here. What shall we work on?'
        if key in ('who made you', 'who created you'):
            return 'This ASUNA version adapts GauravSingh9356’s J.A.R.V.I.S project with a local chat interface and Ollama models.'
        match = re.fullmatch(r'(?:search youtube|youtube search)\s*:?\s+(.+)', query, re.I)
        if match:
            return self.open_search('https://www.youtube.com/results?search_query=', match[1], 'YouTube')
        match = re.fullmatch(r'(?:location|search maps|find on maps)\s*:\s*(.+)', query, re.I)
        if match:
            return self.open_search('https://www.google.com/maps/search/?api=1&query=', match[1], 'Maps')
        match = re.fullmatch(r'(?:wikipedia|search wikipedia)\s*:?\s+(.+)', query, re.I)
        if match:
            return self.open_search('https://en.wikipedia.org/w/index.php?search=', match[1], 'Wikipedia')
        match = re.fullmatch(r'(?:dictionary|define)\s*:?\s+(.+)', query, re.I)
        if match:
            return self.translate(match[1].strip())
        if key in ('screenshot', 'take screenshot', 'take a screenshot'):
            return self.screenshot()
        if key in ('remember that', 'remember this'):
            return 'Try “remember that: your note” to save it locally.'
        match = re.fullmatch(r'remember (?:that|this)\s*:?\s+(.+)', query, re.I)
        if match:
            with (self.data_dir / 'notes.txt').open('a', encoding='utf-8') as file:
                file.write(f'[{datetime.now():%Y-%m-%d %H:%M}] {match[1]}\n')
            return 'Saved your note.'
        if key in ('do you remember anything', 'what do you remember'):
            notes = self.data_dir / 'notes.txt'
            return notes.read_text(encoding='utf-8') if notes.exists() else 'No saved notes yet.'
        if key in ('shutdown', 'shut down', 'restart', 'send email', 'youtube downloader', 'face recognition'):
            return 'That upstream feature is not enabled in this ASUNA version. Type help to see available commands.'
        return None

    @staticmethod
    def open_search(base, term, site):
        open_chrome(base + quote_plus(term))
        return f'Opened {site} search for “{term}” in Chrome. I have not read the results.'

    def translate(self, word):
        # Reuses upstream data.json and its difflib spelling suggestion behavior.
        if self.dictionary is None:
            self.dictionary = json.loads((ROOT / 'data.json').read_text(encoding='utf-8'))
            self.word_index = {key.casefold(): key for key in self.dictionary}
        key = self.word_index.get(word.casefold())
        if key is not None:
            definitions = self.dictionary[key]
            return key + ':\n' + '\n'.join(definitions if isinstance(definitions, list) else [str(definitions)])
        matches = get_close_matches(word.casefold(), self.word_index, n=3)
        if matches:
            return 'Word not found. Did you mean ' + ', '.join(self.word_index[m] for m in matches) + '? Try “define WORD”.'
        return 'That word is not in the bundled offline dictionary.'

    def screenshot(self):
        directory = self.data_dir / 'screenshots'
        directory.mkdir(exist_ok=True)
        output = directory / (datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.png')
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-File',
                                 str(ROOT / 'capture-screen.ps1'), '-OutputPath', str(output)],
                                capture_output=True, text=True, timeout=30,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode or not output.exists():
            raise RuntimeError('Windows could not capture the screen. ' + result.stderr[-500:])
        return 'Screenshot saved locally: ' + str(output) + '\nI have not analyzed the image.'


if __name__ == '__main__':
    from asuna import Asuna, tk
    root = tk.Tk()
    Asuna(root)
    root.mainloop()
