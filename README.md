# ASUNA

A personal Windows assistant with a chat interface, local Ollama models, and explicit desktop commands. No paid API keys are required for the ASUNA app.

## Start

1. Install Python 3.11 or newer with tkinter (included in the standard Windows installer).
2. Install and start [Ollama](https://ollama.com/download/windows).
3. Download the models:

   ```powershell
   ollama pull qwen3.5:4b
   ollama pull qwen3.5:9b
   ```

4. Double-click **Start ASUNA.bat**, or run `python asuna.py`.

The window title is **ASUNA — Reactor · Repo edition · 1.2.0**. Basic text mode uses Python's standard library; the old upstream `requirements.txt` is not needed to run it. Run **Setup ASUNA.bat** once for optional PDF text reading. Optional voice setup is below.

## Reliable browser reconnect — 1.2.0

Close/reopen ASUNA and manually reload **ASUNA Browser Companion** once in `chrome://extensions`, in your selected profile. Both versions should show **1.2.0**. Existing valid pairing is retained; there are no new extension permissions. The extension popup also has **Reconnect now**. Pair again with `connect browser` only if the popup reports missing/invalid pairing.

If the page-control connection has gone idle, ASUNA opens a temporary local reconnect tab. The already paired extension closes that tab before acknowledging readiness, so the following command targets the original webpage. Reconnection happens before a new control action is queued. Failed or timed-out actions are never automatically replayed.

The worker now recreates its reconnect alarm at startup, retries transient connection failures briefly, and continues correctly if pairing changes while an old poll is pending. A lost result acknowledgement can resend that result without performing the action again. This follows Chrome's documented [worker lifecycle](https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle) and [alarm persistence guidance](https://developer.chrome.com/docs/extensions/reference/api/alarms).

`play it`, `the first video u found on youtube`, and `open youtube and play the first video` now use browser actions directly. A successful YouTube search is remembered for up to 30 minutes within the open chat, so an explicit playback follow-up can repeat that search and continue after a connection failure. New chat clears this context. `opwn` is accepted as a leading typo for `open`; draft text is unchanged. Connection failures are reported as connection failures rather than document questions or claims that browser access is unavailable.

## Short action replies — 1.1.2

Routine browser actions now use brief chat and voice acknowledgements. A successful `open youtube and play music` says **“Playing music on YouTube.”** Full tool output, page addresses and numbered controls remain in **Activity**. Explicit `read page` and `show browser tabs` requests still display their lists for choosing targets; speech acknowledges the request without narrating the list. Page questions and article summaries still speak the generated answer. Browser errors speak a short failure, retaining diagnostic details in Activity. Reopen ASUNA to load this Python update; the existing extension is unchanged.

## Browser and speech fix — 1.1.1

`open youtube and play music` now runs three direct actions: search YouTube for music, open the first video, then play it. `play lo-fi music on YouTube` uses that search phrase. Short follow-ups such as `first video` and `second result` also work directly. A model plan that replaces a named destination with an empty Chrome window is rejected before it runs.

For your selected profile, page control still needs the extension connection. Type `connect browser`, then click **Connect ASUNA inside the Chrome page** and wait for **Connected**. Opening that tab alone does not pair it. If already connected, ASUNA reports that without opening another pairing page. Missing connections stop the remaining actions and show the actual failure.

Spoken replies need **Speak replies: On**, or type `voice on` (`voice off` mutes them). This choice is saved locally. **Voice settings → Test voice** lets you check an installed Windows voice explicitly, even with automatic replies off. Action failures are also spoken when replies are enabled; speech-backend errors are displayed without repeatedly trying to speak the error.

## Everyday assistant update — 1.1.0

Open **Settings** to choose Fast/Deep models, reply length and style, add your own app/site/folder shortcuts, check the local setup, choose a Chrome profile, or back up and restore saved data. Open **Organizer** to edit tasks, due dates and priorities, manage notes, and pause/resume routines. The Reactor interface remains the main place to chat.

- **Stop** interrupts a reply or stops a plan before its next action. Completed actions remain completed; a running file/browser operation may finish before stopping.
- **New chat** archives the previous conversation. Search and read those archives in **Chat history**, or export the current chat from Settings.
- Ordinary notes now support reading, editing, searching, archiving and restoring. Existing `notes.txt` is preserved and imported once.
- Tasks support completion/reopening, due dates, priorities and archiving/restoring. Dates use `YYYY-MM-DD`.
- Offline calculations, common unit conversions, explicit-date countdowns and focus timers work without an AI connection.
- Text PDFs join text and DOCX attachments after **Setup ASUNA.bat**. Image-only scans and encrypted PDFs require manual preparation.
- Daily local backups, validation before restoring, a safety backup before replacement, and a separate **Restore ASUNA Backup.bat** help recover saved data. Backup files contain personal information and stay out of Git.
- **Check ASUNA.bat** helps diagnose Ollama, models, Chrome, PDF and voice setup. New launches prevent two copies from writing the same data.

For the original development computer, close the old ASUNA window and reopen **Start ASUNA.bat** to load the current update. In your selected Chrome profile, manually reload **ASUNA Browser Companion** in `chrome://extensions` once; it should show **1.2.0**. Use **Reconnect now** in its popup for existing pairing. Pair through `connect browser` only if it reports missing/invalid pairing. Your chosen profile remains saved locally.

See [the everyday assistant guide](PERSONAL-ASSISTANT.md) for examples, backups, recovery and limits.

## Features

- Fast / Deep model switching with shared recent conversation.
- The Halo / Reactor interface: animated cyan rings, a live activity summary, and conversation beside the core. Listening, thinking, working, speaking, waiting, and error states follow actual app events.
- Background processing and a show/hide activity panel.
- Natural-language action plans using the selected local model, with follow-up questions when details are missing.
- A work view with request/action status and selectable results. Failed steps stop the remaining plan.
- Opening Windows apps, folders, websites, and browser searches.
- Websites and searches open explicitly in Google Chrome, independently of the Windows default browser. Chrome must be installed; ASUNA reports an error rather than switching browsers when it cannot find Chrome. You can also type `open chrome`.
- Choose an existing Chrome profile and control its pages through the free local ASUNA Browser Companion extension. See [profile setup](BROWSER.md).
- Discord desktop/web opening, named-site search fallback for explicit Chrome requests, and reviewed typing into a focused webpage field or search box.
- An offline dictionary with spelling suggestions, adapted from the original project.
- File-name search inside a folder you choose, and text / Word / selectable-text PDF attachments.
- Local notes, tasks, in-app reminders, and screenshot saving.
- Explicit personal memory, recurring reminders/tasks, and a daily overview.
- Optional local microphone transcription and spoken replies through an installed Windows voice.

Try `help`, `open youtube`, `define: algorithm`, `search youtube: Python basics`, `choose search folder`, or `add task: finish assignment`.

You can also say **“Find my physics notes in Downloads,” “Remind me to study in half an hour,” “Open YouTube and search for Python tutorials,”** or **“Read this document and make five practice questions.”** ASUNA can plan up to six supported actions per request. It asks for missing reminder details; document selection opens a file picker. Known command syntax still works without a model connection.

Use **Activity** or type **“show your work”** to inspect progress. Select a request or individual action to see its result. Chat and the input box remain available alongside Activity; a compact layout makes room when the window is smaller. Work history is for the current app session; saved to-do tasks and reminders remain separate. Reopen the app after updating its files.

The Reactor responds to local microphone volume only while recording. Its speaking pattern is an animation tied to playback status, not a measured speaker waveform. **Motion** pauses ring rotation and decorative movement; the setting is saved locally in `data/ui-settings.json`. Recording levels and status updates still work with Motion off. Animation updates slow down when minimized. The interface adds no packages or paid services.

## Personal memory and routines

Use **Memory** and **My day** in the toolbar, or ask naturally:

- “Remember that I prefer short answers.”
- “What do you remember about me?”
- “Remind me every day at 8 PM to stretch.”
- “Add a task every Monday at 9 AM to review expenses.”
- “Pause my daily stretch reminder.”
- “What do I have to do today?”

Memory is saved only when you explicitly ask; ordinary conversation and documents are not automatically converted into memories. Relevant saved facts/preferences are supplied to subsequent local-model replies, including after restart. `save note:` remains a separate notes feature. Existing notes are not automatically imported into personal memory.

Exact offline commands: `remember: I prefer short answers`, `show memories`, `update memory 1: I prefer detailed answers`, `forget memory 1`, and `restore memory 1`. Forgetting archives a memory so you can undo it. It also stops older conversation context from being sent to the model. The earlier chat and archived record still exist locally; this is not permanent erasure.

Routines support daily, weekdays, or a specific weekday, at an explicit 24-hour clock time. Try `daily reminder at 20:00: stretch` or `monday task at 09:00: review expenses`. Manage them with `show routines`, `pause routine 1`, and `resume routine 1`. Reminder routines notify you; task routines add a new ordinary to-do when due. Both use your PC's local clock and need ASUNA running. Missed occurrences catch up once on restart/resume and skip the backlog. Paused routines resume at their next future time.

`daily overview` lists open tasks (including undated tasks), one-time reminders due today/overdue, and routine occurrences still due today/overdue. This version does not run recurring app actions, hourly/monthly schedules, or reminders while ASUNA is closed.

See [the usage guide](ASUNA-README.md) for supported commands and limitations. Reminders require the app to stay open; overdue reminders are delivered on restart. Browser searches require internet and open results for you to read. Face recognition, email, OCR, video downloading, and weather/news APIs are not connected to the ASUNA launcher yet.

## Browser control

To use an existing Chrome profile, run **Choose Chrome Profile.bat**, load the **chrome-extension** folder manually in that profile, restart ASUNA, and type **connect browser**. The original development computer already has the profile selection saved. Links always use the chosen profile; page control waits for extension pairing. Without a selection, **Setup Browser.bat** enables the separate ASUNA-controlled profile instead. Try `search youtube: Python tutorials` → `open the first video`, or `search web for: Python tutorials` → `open the first result`. Other commands include `read page`, `summarize this page`, `click About`, `click 12`, `fill 8: your text`, `go back`, `scroll down`, `show browser tabs`, `switch to tab 2`, and `pause`/`resume`/`mute`/`unmute`.

See [browser controls and limitations](BROWSER.md). General button clicks and ordinary field entry are reviewed in the app; authentication/payment details and native dialogs remain manual. This works with ordinary HTML controls across websites, rather than every possible browser interaction.

## Voice interaction

On a fresh clone, close ASUNA and run **Setup Voice.bat** once. It installs optional packages in `.venv-voice/` and downloads the multilingual **Whisper Small** recognition model into `data/voice-model-small/`. Internet is needed for setup; no paid API keys are required. On the original development computer, voice setup has already been completed. Small is preferred when fully downloaded; the previous Base model remains a fallback if present. Small may take longer to transcribe on the CPU. To download only the lightweight fallback, use `.venv-voice\Scripts\python.exe voice_setup.py --download-only --model base`.

Reopen **Start ASUNA.bat**, which automatically uses the voice environment when present. Click **Record**, speak, then click **Stop recording** (recordings stop automatically at 30 seconds). The transcript appears in the input box for you to review/edit. **Press Send to submit it**; recognized speech never executes automatically. Existing draft text is preserved and the transcript is appended.

Enable **Speak replies** to hear answers. It is off by default and saved locally when changed. **Stop speaking** interrupts playback. **Voice settings** lets you choose an installed Windows voice, a microphone, and recognition profile. **English is the default** for mostly English speech. **Mixed English + Hindi** chooses a dominant language per recording, restricted to English/Hindi and biased toward English when uncertain; it does not freely choose unrelated languages. Use **Hindi** for Hindi-dominant recordings. **Auto (all languages)** remains an explicit opt-in. Mixing words and accents can still cause mistakes: review the transcript. The default speech selection prefers an installed female voice; this computer has Microsoft Zira Desktop. Hindi recognition does not add a Hindi speaking voice: playback pronunciation depends on the installed voice you select.

English/Hindi profiles reject output dominated by an unexpected writing script. Microphone sample rates are converted with an anti-alias filter before recognition. The recognizer is instructed to transcribe, not translate; decoding uses a five-beam search. These are recognition safeguards, not a guarantee of accuracy on every microphone or accent.

Microphone input is active only after you press Record. Recording is closed before transcription starts. Audio stays in memory; the app does not save recordings or upload audio. The recognizer runs on the CPU to leave the GPU available for Ollama, and loads only the downloaded local model. Dictation transcriptions become ordinary saved chat only after you submit them; unsent transcripts can appear in the current session's work details. No wake word, continuous listening, or voice cloning is included.

Text chat still works if voice setup is absent. If microphone access is blocked, check Windows microphone permissions yourself and select the correct device. If recognition is poor, try a quieter environment or choose English/Hindi instead of auto detection. Speech playback uses [installed Windows speech voices](https://learn.microsoft.com/en-us/dotnet/api/system.speech.synthesis.speechsynthesizer.getinstalledvoices); recognition uses [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

## Personal data

Chat, notes, organizer data, and screenshots are saved in `data/` on your computer. This folder is ignored by Git. They are plain text or ordinary image files; no cloud account or paid AI service is used by the chat interface. Downloaded Ollama models remain outside this repository.

## Checks

On Windows, from the repository folder:

```powershell
python tests/verify_asuna.py
python tests/verify_repo.py
python tests/verify_youtube.py
python tests/verify_natural_actions.py
python tests/verify_personal.py
python tests/verify_voice.py
python tests/verify_browser.py
python tests/verify_reactor.py
python tests/verify_chrome_profile.py
node tests/verify_extension.js
python tests/verify_extension_page.py
python tests/verify_discord_typing.py
python tests/verify_everyday.py
python tests/verify_control_center.py
python tests/verify_browser_control.py --live
python tests/verify_extension_transport.py
```

Checks use temporary data and mock app launches, microphone capture, speech playback, and model responses. Voice checks need NumPy and PDF checks need pypdf, available after setup in `.venv-voice`; use that environment's Python for the suites. They do not record a real microphone, play sound, or operate personal browser accounts. Browser fixture suites launch headless Chrome with temporary profiles and local HTML pages. Coverage includes backups/rollback, task/note editing, cancellation, organizer windows and compact layouts as well as the original features. Natural-language routing requires a running Ollama model; exact commands remain available when it is offline. These checks do not establish recognition or model accuracy for every request.

## Credits

Adapted from [GauravSingh9356/J.A.R.V.I.S](https://github.com/GauravSingh9356/J.A.R.V.I.S), commit `a1227a79bc8d27bf9a8369830c977f493418b9b5`, under the [MIT license](LICENSE). The original command script is preserved as `jarvis_legacy.py`, and [original documentation](README-UPSTREAM.md) remains available. ASUNA adds the local chat interface and modernizes the command engine.
