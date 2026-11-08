"""Bounded local backups and validated, rollback-capable state restoration."""
import hashlib
import json
import os
import stat
import re
import tempfile
import zipfile
from datetime import date,datetime
from pathlib import Path

FILES = {'conversation.json','organizer.json','personal.json','notes.json','notes.txt','preferences.json',
         'shortcuts.json','voice-settings.json','ui-settings.json','browser-settings.json'}
MAX_FILE = 5 * 1024 * 1024
MAX_TOTAL = 20 * 1024 * 1024


def allowed_name(name):
    return name in FILES or bool(re.fullmatch(r'conversations/[0-9]{8}-[0-9]{6}-[a-f0-9]{8}\.json',name))


def validate_state(name, body):
    if name=='notes.txt':
        body.decode('utf-8')
        return
    value = json.loads(body)
    if name=='conversation.json' or name.startswith('conversations/'):
        if not isinstance(value,list) or any(not isinstance(m,dict) or m.get('role') not in ('user','assistant') or not isinstance(m.get('content'),str) for m in value):
            raise ValueError('Conversation backup is invalid.')
    elif name=='preferences.json':
        from preferences import validate_preferences
        validate_preferences(value)
    elif name=='shortcuts.json':
        from shortcuts import validate_shortcuts
        validate_shortcuts(value)
    elif name=='notes.json':
        from notes import validate_notes
        validate_notes(value)
    elif name=='organizer.json':
        if not isinstance(value,dict) or not all(isinstance(value.get(k),list) for k in ('tasks','reminders')) or not isinstance(value.get('search_folder',''),str):
            raise ValueError('Organizer backup is invalid.')
        for kind in ('tasks','reminders'):
            ids = set()
            for item in value[kind]:
                flag = 'done' if kind=='tasks' else 'delivered'
                if (not isinstance(item,dict) or type(item.get('id')) is not int or item['id']<1 or item['id'] in ids or
                        not isinstance(item.get('text'),str) or type(item.get(flag)) is not bool):
                    raise ValueError('Organizer item is invalid.')
                ids.add(item['id'])
                if kind=='reminders':
                    if datetime.fromisoformat(item['due']).tzinfo is not None:
                        raise ValueError('Reminder timestamps must use the PC’s local time.')
                else:
                    if type(item.get('archived',False)) is not bool or item.get('priority','normal') not in ('low','normal','high') or not isinstance(item.get('due',''),str):
                        raise ValueError('Task status, priority or due date is invalid.')
                    if item.get('due') and date.fromisoformat(item['due']).isoformat()!=item['due']:
                        raise ValueError('Task due dates must use YYYY-MM-DD.')
                    if 'routine_key' in item and not isinstance(item['routine_key'],str):
                        raise ValueError('Recurring task reference is invalid.')
    elif name=='personal.json':
        from personal import validate_repeat
        if not isinstance(value,dict) or not all(isinstance(value.get(k),list) for k in ('memories','routines')) or type(value.get('context_floor',0)) is not int or value.get('context_floor',0)<0:
            raise ValueError('Personal backup is invalid.')
        for kind in ('memories','routines'):
            ids = set()
            flag = 'archived' if kind=='memories' else 'active'
            for item in value[kind]:
                if (not isinstance(item,dict) or type(item.get('id')) is not int or item['id']<1 or item['id'] in ids or
                        not isinstance(item.get('text'),str) or type(item.get(flag)) is not bool):
                    raise ValueError('Saved memory or routine is invalid.')
                ids.add(item['id'])
                if kind=='memories':
                    datetime.fromisoformat(item['updated_at'])
                else:
                    validate_repeat(item['repeat'])
                    if datetime.fromisoformat(item['next_due']).tzinfo is not None:
                        raise ValueError('Routine timestamps must use the PC’s local time.')
    elif not isinstance(value,dict):
        raise ValueError('Settings backup is invalid.')


def create_backup(data, destination=None, overwrite=False, validate_contents=True):
    data = Path(data).resolve()
    if destination is None:
        folder = data/'backups'
        folder.mkdir(parents=True,exist_ok=True)
        destination = folder/('asuna-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.zip')
    destination = Path(destination).resolve()
    if destination.suffix.lower()!='.zip':
        raise ValueError('Save backups with a .zip filename.')
    if destination.exists() and not overwrite:
        raise FileExistsError('Choose a new backup filename.')
    payload, total = {}, 0
    names = sorted(FILES)
    history = data/'conversations'
    if history.exists():
        if history.is_symlink() or not history.resolve().is_relative_to(data):
            raise ValueError('Conversation history is linked outside the data folder.')
        names += [p.relative_to(data).as_posix() for p in sorted(history.glob('*.json')) if allowed_name(p.relative_to(data).as_posix())]
    if len(names)>1000:
        raise ValueError('This backup has more than 1,000 state files. Export older chat archives separately.')
    for name in names:
        path = data/name
        if not path.exists():
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(data) or path.stat().st_size>MAX_FILE:
            raise ValueError('A state file is linked or exceeds the 5 MB backup limit: '+name)
        body = path.read_bytes()
        total += len(body)
        if total>MAX_TOTAL:
            raise ValueError('Personal state exceeds the 20 MB backup limit.')
        if validate_contents:
            validate_state(name,body)
        payload[name] = body
    manifest = {'version':1,'created_at':datetime.now().isoformat(),
                'files':{name:hashlib.sha256(body).hexdigest() for name,body in payload.items()}}
    descriptor, temporary = tempfile.mkstemp(prefix='.asuna-backup-',suffix='.tmp',dir=destination.parent)
    os.close(descriptor)
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('manifest.json',json.dumps(manifest))
            for name,body in payload.items():
                archive.writestr(name,body)
        os.replace(temporary,destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return destination


def inspect_backup(filename):
    try:
        with zipfile.ZipFile(filename) as archive:
            members = archive.infolist()
            names = [i.filename for i in members]
            if len(names)>1001 or len(names)!=len(set(names)) or any(n!='manifest.json' and not allowed_name(n) for n in names) or 'manifest.json' not in names:
                raise ValueError('The backup contains unexpected or duplicate paths.')
            if sum(i.file_size for i in members)>MAX_TOTAL+65536 or any(i.file_size>MAX_FILE or stat.S_ISLNK(i.external_attr>>16) for i in members):
                raise ValueError('The backup exceeds the size limits or contains a link.')
            manifest = json.loads(archive.read('manifest.json'))
            if not isinstance(manifest,dict) or manifest.get('version')!=1 or not isinstance(manifest.get('files'),dict) or set(manifest['files'])!=set(names)-{'manifest.json'}:
                raise ValueError('The backup manifest is invalid.')
            payload = {}
            for name,expected in manifest['files'].items():
                body = archive.read(name)
                if not isinstance(expected,str) or hashlib.sha256(body).hexdigest()!=expected:
                    raise ValueError('Backup integrity check failed: '+name)
                validate_state(name,body)
                payload[name] = body
            return payload
    except (zipfile.BadZipFile,KeyError,TypeError,UnicodeError,RuntimeError) as exc:
        raise ValueError('This is not a valid ASUNA backup.') from exc


def restore_backup(data,filename):
    data = Path(data).resolve()
    payload = inspect_backup(filename)  # Validate everything before changing any state.
    if not payload:
        raise ValueError('The backup contains no state files.')
    data.mkdir(parents=True,exist_ok=True)
    safety = create_backup(data,validate_contents=False)
    previous = {}
    for name in payload:
        path = data/name
        if path.is_symlink() or not path.resolve().is_relative_to(data):
            raise ValueError('Restore cannot replace linked state files.')
        previous[name] = path.read_bytes() if path.exists() else None
    changed = []
    try:
        for name,body in payload.items():
            temporary = data/(name+'.restore-tmp')
            temporary.parent.mkdir(parents=True,exist_ok=True)
            temporary.write_bytes(body)
            temporary.replace(data/name)
            changed.append(name)
    except OSError:
        for name in changed:
            if previous[name] is None:
                (data/name).unlink(missing_ok=True)
            else:
                (data/name).write_bytes(previous[name])
        raise
    finally:
        for name in payload:
            try:(data/(name+'.restore-tmp')).unlink(missing_ok=True)
            except OSError:pass
    return safety


def daily_backup(data):
    folder = Path(data)/'backups'
    prefix = 'asuna-backup-'+datetime.now().strftime('%Y%m%d')
    if folder.exists() and any(folder.glob(prefix+'*.zip')):
        return None
    if not any((Path(data)/name).exists() for name in FILES):
        return None
    return create_backup(data)
