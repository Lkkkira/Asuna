"""Allowlisted action execution and factual results for ASUNA."""
from dataclasses import dataclass
from pathlib import Path
from planner import SITES
from actions import read_document


@dataclass
class ToolResult:
    detail: str
    document: tuple | None = None
    reference: str | None = None


def known_folder(name):
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
        return Path(pointer.value)
    finally:
        ctypes.windll.ole32.CoTaskMemFree(ctypes.cast(pointer, ctypes.c_void_p))


class ToolExecutor:
    def __init__(self, actions, repo, choose, personal=None, context_count=0, confirm=None):
        self.actions, self.repo, self.choose = actions, repo, choose
        self.personal = personal
        self.context_count = context_count
        self.confirm = confirm
        from browser_control import session
        self.browser_token = session.cached()['token']

    def execute(self, s):
        tool, text, number = s['tool'], s['text'], s['number']
        if tool.startswith('browser_'):
            from browser_control import session
            if tool in ('browser_click', 'browser_fill') and number and session.cached()['token'] != self.browser_token:
                raise ValueError('The browser page changed after this plan was made. Read the page again and choose the target in a new request.')
            result = session.call(tool.removeprefix('browser_'), text, number)
            if result.get('confirm'):
                if not self.confirm or not self.confirm(result['confirm']):
                    raise InterruptedError('Browser action cancelled; the page control was not used.')
                result = session.call('approve', result['ticket'])
            return ToolResult(result['detail'], reference=result.get('reference'))
        if tool in ('save_memory', 'update_memory'):
            return ToolResult(self.personal.save_memory(text, number if tool == 'update_memory' else 0,
                                                       context_floor=self.context_count + 2))
        if tool in ('forget_memory', 'restore_memory'):
            return ToolResult(self.personal.archive_memory(number, restore=tool == 'restore_memory',
                                                          context_floor=self.context_count + 2))
        if tool == 'show_memories':
            return ToolResult(self.personal.show_memories())
        if tool in ('add_routine', 'update_routine'):
            return ToolResult(self.personal.add_routine(text, s['repeat'], number if tool == 'update_routine' else 0))
        if tool in ('pause_routine', 'resume_routine'):
            return ToolResult(self.personal.pause_routine(number, resume=tool == 'resume_routine'))
        if tool == 'show_routines':
            return ToolResult(self.personal.show_routines())
        if tool == 'daily_overview':
            return ToolResult(self.personal.overview(self.actions))
        if tool == 'find_files':
            folder = s['folder']
            if folder in ('downloads', 'documents', 'desktop'):
                self.actions.choose_folder(known_folder(folder))
            elif folder == 'pick' or not self.actions.state['search_folder']:
                path = self.choose('folder')
                if not path:
                    raise InterruptedError('Folder selection cancelled; no file search was run.')
                self.actions.choose_folder(path)
            return ToolResult(self.actions.find(text))
        if tool == 'read_document':
            path = self.choose('document')
            if not path:
                raise InterruptedError('Document selection cancelled; no document was read.')
            document = read_document(path)
            return ToolResult('Read ' + document[0] + (' (first 10,000 characters only).' if document[2] else '.'), document)
        if tool in ('open_result', 'read_result'):
            if not 1 <= number <= len(self.actions.results):
                raise ValueError('That search result number is unavailable. Search first, then choose a displayed result number.')
            path = self.actions.results[number - 1].resolve()
            scope = Path(self.actions.state['search_folder']).resolve()
            if not path.is_relative_to(scope) or not path.exists():
                raise ValueError('That result is no longer available inside your search folder.')
            if tool == 'read_result':
                document = read_document(path)
                return ToolResult('Read ' + document[0] + (' (first 10,000 characters only).' if document[2] else '.'), document)
        if tool in ('complete_task', 'cancel_reminder'):
            items = self.actions.state['tasks' if tool == 'complete_task' else 'reminders']
            if not any(item['id'] == number and (tool != 'cancel_reminder' or not item['delivered']) for item in items):
                raise ValueError('That task or pending reminder number was not found. Ask to see the current list.')
        commands = {
            'open_app': 'open ' + text, 'open_result': 'open result ' + str(number),
            'search_web': 'search web for: ' + text, 'add_task': 'add task: ' + text,
            'complete_task': 'complete task ' + str(number), 'show_tasks': 'show tasks',
            'set_reminder': f'remind me in {number} seconds to {text}',
            'show_reminders': 'show reminders', 'cancel_reminder': 'cancel reminder ' + str(number)}
        if tool in commands:
            result = self.actions.execute(commands[tool])
            if result is None or result.startswith(('I only open', 'I could not match', 'Choose a ', 'That result')):
                raise ValueError(result or 'The action was not recognized.')
            return ToolResult(result)
        commands = {'open_site': 'open ' + text, 'search_youtube': 'search youtube: ' + text,
                    'search_maps': 'location: ' + text, 'search_wikipedia': 'wikipedia: ' + text,
                    'define': 'define: ' + text, 'screenshot': 'take a screenshot',
                    'save_note': 'remember that: ' + text, 'show_notes': 'what do you remember',
                    'time': 'what time is it', 'date': 'date'}
        if tool == 'open_site' and text not in SITES:
            result = self.actions.execute('open ' + text)
        else:
            result = self.repo.execute_query(commands[tool])
        if result is None:
            raise ValueError('The action was not recognized.')
        return ToolResult(result)
