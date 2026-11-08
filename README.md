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

The window title is **ASUNA — Reactor · Repo edition**. Text mode uses Python's standard library; the old upstream `requirements.txt` is not needed to run it. Optional voice setup is below.

## Features

- Fast / Deep model switching with shared recent conversation.
- The Halo / Reactor interface: animated cyan rings, a live activity summary, and conversation beside the core. Listening, thinking, working, speaking, waiting, and error states follow actual app events.
- Background processing and a show/hide activity panel.
- Natural-language action plans using the selected local model, with follow-up questions when details are missing.
- A work view with request/action status and selectable results. Failed steps stop the remaining plan.
- Opening Windows apps, folders, websites, and browser searches.
- Websites and searches open explicitly in Google Chrome, independently of the Windows default browser. Chrome must be installed; ASUNA reports an error rather than switching browsers when it cannot find Chrome. You can also type `open chrome`.
- An offline dictionary with spelling suggestions, adapted from the original project.
- File-name search inside a folder you choose, and text / Word document attachments.
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

Run **Setup Browser.bat** once on a fresh clone, then reopen ASUNA. It uses your installed Chrome in a separate ASUNA-controlled profile, not existing personal tabs. Try `search youtube: Python tutorials` → `open the first video`, or `search web for: Python tutorials` → `open the first result`. Other commands include `read page`, `summarize this page`, `click About`, `click 12`, `fill 8: your text`, `go back`, `scroll down`, `show browser tabs`, `switch to tab 2`, and `pause`/`resume`/`mute`/`unmute`.

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
```

Checks use temporary data and mock app/browser launching, microphone capture, speech playback, and model responses. Voice checks need NumPy, available in the voice environment: `.venv-voice\Scripts\python.exe tests/verify_voice.py`. They do not record a real microphone or play sound. They cover organizer persistence, scoped file opening, document reading, background UI results, dictionary lookup, command routing, plan validation, follow-up clarification, partial failures, voice controls, and the work panel layout. They do not test a live screenshot, a real browser window, or model accuracy. Natural-language routing requires a running Ollama model; exact commands remain available when it is offline.

## Credits

Adapted from [GauravSingh9356/J.A.R.V.I.S](https://github.com/GauravSingh9356/J.A.R.V.I.S), commit `a1227a79bc8d27bf9a8369830c977f493418b9b5`, under the [MIT license](LICENSE). The original command script is preserved as `jarvis_legacy.py`, and [original documentation](README-UPSTREAM.md) remains available. ASUNA adds the local chat interface and modernizes the command engine.
