# ASUNA 1.1.1 validation

Checked on Windows with Python 3.11 and the project environment on 2026-11-08.

The following 158 unittest cases passed:

| Suite | Cases |
| --- | ---: |
| verify_natural_actions.py | 25 |
| verify_personal.py | 20 |
| verify_voice.py | 25 |
| verify_browser.py | 5 |
| verify_reactor.py | 6 |
| verify_chrome_profile.py | 14 |
| verify_discord_typing.py | 9 |
| verify_everyday.py | 15 |
| verify_control_center.py | 9 |
| verify_browser_control.py --live | 18 |
| verify_extension_page.py | 12 |

The original assertion-based `verify_asuna.py`, `verify_repo.py`, `verify_youtube.py`, and Node `verify_extension.js` also passed. Python compilation and Git whitespace checks passed.

The 1.1.0 native Reactor, Settings, shortcut/backup tabs and task/note Organizer were visually reviewed using a separate temporary data folder. Minimum supported window sizes have layout checks. The 1.1.1 voice test button has visibility/selection checks using mocked playback.

Read-only setup checks found Ollama, both configured models, Whisper Small, pypdf, Chrome and the saved Chrome profile. A live local Qwen3.5 4B check produced valid task-priority and note-search plans and a complete chat reply. Those plans were inspected without executing personal actions. A failed initial task-edit plan led to clearer validation feedback and worked examples before the successful check.

Browser tests used headless Chrome, temporary profiles and local HTML fixtures. A restricted-environment loopback connection initially blocked profile-bridge tests; rerunning those checks with local network access passed. Automated tests did not record a real microphone, play sound, use personal browser accounts, like actual videos or send messages. They do not establish model/speech accuracy for arbitrary requests or compatibility with every website. An older installed extension needs a manual reload to 1.1.0; the 1.1.1 patch changes Python code and uses that same extension version.

The 1.1.1 regression cases use the user's exact `open youtube and play music` and `first video` commands, assert the search/open/play sequence without invoking the model, check that disconnected page control fails and speaks the failure, and reject/repair model plans that drop the website. Voice on/off persistence and the explicit test button are checked with playback mocked. Connection checks distinguish an already paired profile from the page/button needed for fresh pairing. User Chrome pairing and audible output still need an interactive check on the actual machine.

A live local Qwen3.5 4B request for the exact YouTube phrase also produced the correct three steps without executing them. Windows System.Speech listed two installed voices, including one female voice. Spoken replies were enabled in this user's ignored local settings and ASUNA 1.1.1 was launched. Native window capture/activation did not provide a usable app view in that session, so this does not verify audible output or a completed personal-profile pairing. Playback tests remain mocked.
