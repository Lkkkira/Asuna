"""Read-only setup checks; does not record audio or open accounts."""
import importlib.util
import json
import sys
import urllib.request
from pathlib import Path


def installed_models():
    with urllib.request.urlopen('http://127.0.0.1:11434/api/tags',timeout=4) as response:
        value = json.load(response)
    return [m['name'] for m in value.get('models',[]) if isinstance(m,dict) and isinstance(m.get('name'),str)]


def setup_report(data,models):
    rows = [('Python',sys.version.split()[0],'Ready' if sys.version_info>=(3,11) else 'Install Python 3.11 or newer')]
    try:
        from browser import chrome_path
        chrome_path()
        rows.append(('Chrome','Installed','Ready'))
    except OSError:
        rows.append(('Chrome','Not found','Install Google Chrome'))
    try:
        names = installed_models()
        rows.append(('Ollama','Running','Ready'))
        for mode,name in models.items():
            rows.append((mode+' model',name,'Ready' if name in names else 'Download this model with Ollama, or select an installed model in Settings'))
    except (OSError,ValueError):
        rows.append(('Ollama','Unavailable','Start Ollama, then check again'))
        names = []
    from voice import VoiceController
    import queue
    voice = VoiceController(queue.Queue(),Path(__file__).resolve().parent,Path(data))
    rows.append(('Microphone transcription','Whisper '+voice.model_name,'Ready' if voice.ready() else 'Run Setup Voice.bat'))
    rows.append(('PDF text reading','pypdf','Ready' if importlib.util.find_spec('pypdf') else 'Run Setup ASUNA.bat'))
    try:
        from browser_profile import settings
        profile = settings(data)
        if profile:
            rows.append(('Chrome profile',profile.get('profile_name',profile['profile_directory']),'Selected'))
            token_path = Path(data)/'chrome-bridge.json'
            if token_path.exists():
                # Online status is shown by the extension popup; no fake heartbeats here.
                rows.append(('Browser control','Personal-profile extension','Open the extension popup to check; use connect browser if needed'))
            else:
                rows.append(('Browser control','Not paired','Load the extension, then type connect browser'))
        else:
            rows.append(('Chrome profile','Separate ASUNA window','Choose a profile in Settings to use your everyday Chrome'))
    except (ValueError,OSError,KeyError):
        rows.append(('Chrome profile','Unavailable','Choose the Chrome profile again in Settings'))
    return rows,names


if __name__=='__main__':
    from preferences import Preferences,DEFAULTS
    data = Path(__file__).resolve().parent/'data'
    try:models = Preferences(data).models
    except (OSError,ValueError) as exc:
        print('Assistant settings: Needs attention — '+str(exc))
        models = {'Fast':DEFAULTS['fast_model'],'Deep':DEFAULTS['deep_model']}
    for component,status,help_text in setup_report(data,models)[0]:
        print(component+': '+status+' — '+help_text)
