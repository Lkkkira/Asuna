"""Editable, searchable local notes with archive/restore and legacy migration."""
import copy
import json
from datetime import datetime
from pathlib import Path


def validate_notes(value):
    if not isinstance(value,dict) or set(value)!={'notes'} or not isinstance(value['notes'],list):
        raise ValueError('Notes have an invalid format. Restore them from a backup.')
    ids = set()
    for note in value['notes']:
        if (not isinstance(note,dict) or not {'id','text','archived','updated_at'} <= set(note) or
                type(note['id']) is not int or note['id']<1 or note['id'] in ids or
                not isinstance(note['text'],str) or type(note['archived']) is not bool or not isinstance(note['updated_at'],str)):
            raise ValueError('A saved note has an invalid format. Restore it from a backup.')
        ids.add(note['id'])
    return value


class Notes:
    def __init__(self,data):
        self.path = Path(data)/'notes.json'
        self.state = validate_notes(json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {'notes':[]})
        legacy = Path(data)/'notes.txt'
        if not self.path.exists() and legacy.is_file() and legacy.stat().st_size <= 2_000_000:
            text = legacy.read_text(encoding='utf-8').strip()
            if text:
                self.commit({'notes':[{'id':1,'text':text,'archived':False,'updated_at':datetime.now().isoformat()}]})

    def commit(self,value):
        validate_notes(value)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
        temporary.replace(self.path)
        self.state = value

    def save(self,text,number=0):
        text = text.strip()
        if not text or len(text)>20000:
            raise ValueError('A note needs 1–20,000 characters.')
        value = copy.deepcopy(self.state)
        if number:
            note = next((n for n in value['notes'] if n['id']==number and not n['archived']),None)
            if note is None:
                raise ValueError('Active note not found. Ask to show notes.')
        else:
            note = {'id':max([n['id'] for n in value['notes']],default=0)+1,'text':'','archived':False,'updated_at':''}
            value['notes'].append(note)
        note.update(text=text,updated_at=datetime.now().isoformat(timespec='seconds'))
        self.commit(value)
        return f"Saved note {note['id']}: {text[:100]}"

    def archive(self,number,restore=False):
        value = copy.deepcopy(self.state)
        note = next((n for n in value['notes'] if n['id']==number),None)
        if note is None:
            raise ValueError('Note number not found.')
        note['archived'] = not restore
        self.commit(value)
        return ('Restored' if restore else 'Archived')+f' note {number}.'

    def read(self,number):
        note = next((n for n in self.state['notes'] if n['id']==number and not n['archived']),None)
        if note is None:
            raise ValueError('Active note not found. Ask to show notes.')
        return f"Note {number}\n{note['text']}"

    def listing(self,query='',include_archived=False):
        notes = [n for n in self.state['notes'] if (include_archived or not n['archived']) and query.casefold() in n['text'].casefold()]
        return '\n'.join(f"{n['id']}. {'[archived] ' if n['archived'] else ''}{n['text'][:220]}" for n in notes) or 'No matching notes.'
