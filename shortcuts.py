"""User-configured app/site/folder shortcuts; model output never supplies paths."""
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

RESERVED = {'chrome','google chrome','browser','web browser','youtube','google','amazon','github',
            'stackoverflow','discord','downloads','documents','desktop','calculator','paint','notepad',
            'explorer','file explorer','task manager','settings'}


def validate_shortcuts(value):
    if not isinstance(value, dict) or set(value) != {'items'} or not isinstance(value['items'], list):
        raise ValueError('Shortcuts have an invalid format.')
    seen = set()
    for item in value['items']:
        if not isinstance(item, dict) or set(item) != {'name','kind','target','enabled'}:
            raise ValueError('A shortcut needs a name, kind, target and enabled state.')
        name = item['name']
        if not isinstance(name,str) or not re.fullmatch(r'[\w][\w .-]{0,49}',name) or name.casefold() in seen or name.casefold() in RESERVED or re.fullmatch(r'result \d+',name,re.I):
            raise ValueError('Choose a unique shortcut name that does not replace a built-in command.')
        seen.add(name.casefold())
        if item['kind'] not in ('app','site','folder') or type(item['enabled']) is not bool or not isinstance(item['target'],str):
            raise ValueError('Choose an app, website or folder shortcut.')
        target = item['target']
        if item['kind'] == 'site':
            parsed = urlparse(target)
            if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password or any(c.isspace() for c in target):
                raise ValueError('A website shortcut needs an ordinary http(s) address without credentials.')
        elif not Path(target).is_absolute() or item['kind']=='app' and Path(target).suffix.lower()!='.exe':
            raise ValueError('Select an absolute folder path or an installed .exe file. Commands/scripts are not shortcuts.')
    return value


class Shortcuts:
    def __init__(self,data):
        self.path = Path(data)/'shortcuts.json'
        self.state = validate_shortcuts(json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {'items':[]})

    def save(self, items):
        value = validate_shortcuts({'items':items})
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
        temporary.replace(self.path)
        self.state = value

    def set(self,name,kind,target):
        name = name.strip()
        items = [dict(i) for i in self.state['items'] if i['name'].casefold()!=name.casefold()]
        items.append({'name':name,'kind':kind,'target':target.strip(),'enabled':True})
        self.save(items)

    def toggle(self,name):
        items = [dict(i) for i in self.state['items']]
        item = next((i for i in items if i['name'].casefold()==name.casefold()),None)
        if item is None:
            raise ValueError('Shortcut not found.')
        item['enabled'] = not item['enabled']
        self.save(items)

    def get(self,name):
        return next((i for i in self.state['items'] if i['enabled'] and i['name'].casefold()==name.casefold()),None)

    def open(self,name):
        item = self.get(name)
        if not item:
            raise ValueError('That shortcut is unavailable. Open Settings to check it.')
        if item['kind']=='site':
            from browser import open_chrome
            open_chrome(item['target'])
        else:
            path = Path(item['target'])
            if item['kind']=='app':
                if not path.is_file():
                    raise FileNotFoundError('The shortcut app is unavailable. Select its installed .exe in Settings.')
                subprocess.Popen([str(path)],shell=False)
            else:
                if not path.is_dir():
                    raise FileNotFoundError('The shortcut folder is unavailable. Check its location in Settings.')
                os.startfile(str(path))
        return 'Opened shortcut '+item['name']+'.'
