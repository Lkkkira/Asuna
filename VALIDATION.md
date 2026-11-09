# ASUNA 1.2.0 validation

Checked on Windows with Python 3.11 and the project environment on 2026-11-09.

The following 172 unittest cases passed:

| Suite | Cases |
| --- | ---: |
| verify_natural_actions.py | 27 |
| verify_personal.py | 20 |
| verify_voice.py | 29 |
| verify_browser.py | 5 |
| verify_reactor.py | 6 |
| verify_chrome_profile.py | 16 |
| verify_discord_typing.py | 10 |
| verify_everyday.py | 15 |
| verify_control_center.py | 9 |
| verify_browser_control.py --live | 18 |
| verify_extension_page.py | 12 |
| verify_extension_transport.py | 5 |

The original assertion-based `verify_asuna.py`, `verify_repo.py`, `verify_youtube.py`, and Node `verify_extension.js` also passed. Python compilation and Git whitespace checks passed.

The 1.1.0 native Reactor, Settings, shortcut/backup tabs and task/note Organizer were visually reviewed using a separate temporary data folder. Minimum supported window sizes have layout checks. The 1.1.1 voice test button has visibility/selection checks using mocked playback.

Read-only setup checks found Ollama, both configured models, Whisper Small, pypdf, Chrome and the saved Chrome profile. A live local Qwen3.5 4B check produced valid task-priority and note-search plans and a complete chat reply. Those plans were inspected without executing personal actions. A failed initial task-edit plan led to clearer validation feedback and worked examples before the successful check.

Browser tests used headless Chrome, temporary profiles and local HTML fixtures. A restricted-environment loopback connection initially blocked profile-bridge tests; rerunning those checks with local network access passed. Automated tests did not record a real microphone, play sound, use personal browser accounts, like actual videos or send messages. They do not establish model/speech accuracy for arbitrary requests or compatibility with every website. Earlier Python-only fixes used extension 1.1.0; the current 1.2.0 recovery update requires manually reloading the installed extension to 1.2.0.

The 1.1.1 regression cases use the user's exact `open youtube and play music` and `first video` commands, assert the search/open/play sequence without invoking the model, check that disconnected page control fails and speaks the failure, and reject/repair model plans that drop the website. Voice on/off persistence and the explicit test button are checked with playback mocked. Connection checks distinguish an already paired profile from the page/button needed for fresh pairing. User Chrome pairing and audible output still need an interactive check on the actual machine.

A live local Qwen3.5 4B request for the exact YouTube phrase also produced the correct three steps without executing them. Windows System.Speech listed two installed voices, including one female voice. Spoken replies were enabled in this user's ignored local settings and ASUNA 1.1.1 was launched. Native window capture/activation did not provide a usable app view in that session, so this does not verify audible output or a completed personal-profile pairing. Playback tests remain mocked.

The 1.1.2 feedback regression uses a YouTube page dump with a URL and numbered Guide/Search/Pause controls. The complete search/open/play request produces exactly one spoken and saved chat acknowledgement, “Playing music on YouTube.” The full dump remains in the child and parent Activity records. Additional mocked-playback cases verify that explicit page/tab inventories remain visible without narration, page dumps attached to failures stay out of speech, and an action preamble stays silent before a generated answer. No audio was played in these checks.

The first concurrent browser run completed its behavior assertions but one fixture cleanup hit a Windows lock on its temporary Chrome Crashpad metrics file. That case passed when rerun alone, including cleanup. No personal Chrome profile was used or deleted.

The 1.2.0 transport fixture runs the packaged background worker in Node against a real temporary Python HTTP bridge, with only Chrome UI/DOM APIs replaced. Cases cover assistant restart with the same token, pairing rotation while a poll is pending, a reconnect tab closing before a page command can run, and a lost result acknowledgement being retried without repeating the action. Authorization checks reject wrong origins/tokens, incorrect or replayed wake nonces, and verify that unsuccessful waking queues no page command. Expected socket closures during shutdown are handled without traceback noise.

A fifth case holds an old unauthorized poll response until after a new wake succeeds. It verifies that the queued reconnect request restarts polling immediately when that old response is released, without an alarm firing or an action being repeated.

The supplied transcript is replayed with an initial connection failure followed by `play it`, repeated `the first video u found on youtube`, `opwn youtube and play the first video`, and the corrected spelling. All follow-ups execute the expected YouTube search/open/play sequence without calling the model or asking a document question. Additional cases use a known current YouTube search/video, and ensure no prior search query is invented when context is absent.

The user's local Windows shortcut was checked read-only and points to the canonical launcher. It is left unchanged and untracked. This release still needs a manual reload of the installed 1.2.0 extension and restart of the assistant before validating the user's live signed-in profile; automated checks do not establish playback on every YouTube layout or speak through the user's speakers.
