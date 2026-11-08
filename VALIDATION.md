# ASUNA 1.1.0 validation

Checked on Windows with Python 3.11 and the project environment on 2026-11-08.

The following 147 unittest cases passed:

| Suite | Cases |
| --- | ---: |
| verify_natural_actions.py | 20 |
| verify_personal.py | 20 |
| verify_voice.py | 22 |
| verify_browser.py | 5 |
| verify_reactor.py | 6 |
| verify_chrome_profile.py | 13 |
| verify_discord_typing.py | 7 |
| verify_everyday.py | 15 |
| verify_control_center.py | 9 |
| verify_browser_control.py --live | 18 |
| verify_extension_page.py | 12 |

The original assertion-based `verify_asuna.py`, `verify_repo.py`, `verify_youtube.py`, and Node `verify_extension.js` also passed. Python compilation and Git whitespace checks passed.

The native Reactor, Settings, shortcut/backup tabs and task/note Organizer were visually reviewed using a separate temporary data folder. Minimum supported window sizes have layout checks. The preview was closed afterward; the existing personal ASUNA window was left running.

Read-only setup checks found Ollama, both configured models, Whisper Small, pypdf, Chrome and the saved Chrome profile. A live local Qwen3.5 4B check produced valid task-priority and note-search plans and a complete chat reply. Those plans were inspected without executing personal actions. A failed initial task-edit plan led to clearer validation feedback and worked examples before the successful check.

Browser tests used headless Chrome, temporary profiles and local HTML fixtures. A restricted-environment loopback connection initially blocked profile-bridge tests; rerunning those checks with local network access passed. Automated tests did not record a real microphone, play sound, use personal browser accounts, like actual videos or send messages. They do not establish model/speech accuracy for arbitrary requests or compatibility with every website. The installed personal extension still needs its manual reload after updating.
