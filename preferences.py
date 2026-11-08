"""Validated local assistant preferences with atomic saves."""
import json
import re
from pathlib import Path

DEFAULTS = {'fast_model':'qwen3.5:4b', 'deep_model':'qwen3.5:9b', 'default_mode':'Fast',
            'reply_style':'Balanced', 'context_tokens':8192, 'reply_tokens':2048, 'auto_backup':True}


def validate_preferences(value):
    if not isinstance(value, dict) or set(value) - set(DEFAULTS):
        raise ValueError('Assistant settings have an invalid format.')
    result = DEFAULTS | value
    for key in ('fast_model','deep_model'):
        if not isinstance(result[key], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/+-]{0,159}', result[key]) or '://' in result[key]:
            raise ValueError('Choose an Ollama model name, such as qwen3.5:4b.')
    if result['default_mode'] not in ('Fast','Deep') or result['reply_style'] not in ('Brief','Balanced','Detailed'):
        raise ValueError('Choose a supported default mode and reply style.')
    if result['context_tokens'] not in (2048,4096,8192,16384) or type(result['context_tokens']) is not int:
        raise ValueError('Choose a context size from 2,048 to 16,384.')
    if result['reply_tokens'] not in (512,1024,2048,4096) or type(result['reply_tokens']) is not int:
        raise ValueError('Choose a response limit from 512 to 4,096.')
    if result['reply_tokens'] >= result['context_tokens']:
        raise ValueError('Choose a response limit smaller than the context size, leaving room for your request.')
    if type(result['auto_backup']) is not bool:
        raise ValueError('Automatic backup must be enabled or disabled.')
    return result


class Preferences:
    def __init__(self, data):
        self.path = Path(data) / 'preferences.json'
        self.values = validate_preferences(json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else {})

    def save(self, values):
        checked = validate_preferences(values)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(checked, indent=2), encoding='utf-8')
        temporary.replace(self.path)
        self.values = checked

    @property
    def models(self):
        return {'Fast':self.values['fast_model'],'Deep':self.values['deep_model']}
