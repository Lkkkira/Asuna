"""Conversation archives are local, explicit and never silently re-fed to a model."""
import json
import uuid
from datetime import datetime
from pathlib import Path


def archive_chat(data,messages):
    if not messages:
        return None
    folder = Path(data)/'conversations'
    folder.mkdir(parents=True,exist_ok=True)
    name = datetime.now().strftime('%Y%m%d-%H%M%S-')+uuid.uuid4().hex[:8]+'.json'
    destination = folder/name
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(messages,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(destination)
    return destination


def archived_chats(data,query=''):
    folder = Path(data)/'conversations'
    result = []
    total = 0
    for path in sorted(folder.glob('*.json'),reverse=True):
        if path.is_symlink() or path.stat().st_size>10*1024*1024:
            continue
        total += path.stat().st_size
        if total>50*1024*1024 or len(result)>=100:
            break
        try:
            messages = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(messages,list) or any(not isinstance(m,dict) or m.get('role') not in ('user','assistant') or not isinstance(m.get('content'),str) for m in messages):
                continue
            if query and not any(query.casefold() in m['content'].casefold() for m in messages):
                continue
            title = next((m['content'] for m in messages if m['role']=='user'),'Conversation')[:100]
            result.append((path,title,messages))
        except (ValueError,OSError):
            continue
    return result
