# ASUNA — local Windows edition

This is a local adaptation of [GauravSingh9356/J.A.R.V.I.S](https://github.com/GauravSingh9356/J.A.R.V.I.S), based on commit `a1227a79bc8d27bf9a8369830c977f493418b9b5`.
The upstream MIT license and author credit remain in LICENSE. The original command script is saved as jarvis_legacy.py. README-UPSTREAM.md describes the upstream application; this file describes the adapted edition. The canonical ASUNA repository is https://github.com/Lkkkira/Asuna.

## Start

1. Keep Ollama running with `qwen3.5:4b` and `qwen3.5:9b` installed.
2. Double-click **Start ASUNA.bat** in this folder.

Text mode uses your existing Python 3 installation, tkinter, and the standard library. **Do not install the old requirements.txt for this edition.** Optional microphone input uses Setup Voice.bat, which creates a local voice environment and downloads a recognition model. Start ASUNA.bat uses that environment automatically if present. No paid API keys are needed. Local chat, dictionary, and configured voice work offline after model download; website searches require internet.

Voice controls: Record → speak → Stop recording → review the transcript → Send. Speak replies enables local Windows speech; Stop speaking interrupts it. Voice settings selects microphone, installed voice, and recognition profile. English is the default; Mixed English + Hindi restricts language selection to those two per recording. General Auto is opt-in. Setup now downloads Whisper Small; an existing Base download remains a fallback. Spoken responses are capped at about 1,800 characters; code blocks and URLs are shortened for speech. Full replies stay in chat. Audio is kept in memory and never automatically submitted as a command. Close the app to stop recording and speech. Detailed setup and limitations are in README.md.

## Commands to try

Browser/profile setup is described in [BROWSER.md](BROWSER.md). Choose Chrome Profile.bat selects your everyday profile; load the free local extension and type connect browser to enable page control there. Links always use the selected profile. Without a selection, Setup Browser.bat enables the separate Chrome profile instead. Both modes support reading pages, numbered links/results/videos, reviewed clicks/field entry, navigation, tabs, scrolling, and HTML media on ordinary websites.

Natural requests are now supported using your selected Fast/Deep model. For example, “Find my physics notes in Downloads,” “Remind me to study in half an hour,” or “Read this document and make five practice questions.” Known exact commands below bypass model planning and continue to work offline. Unsupported capabilities prompt a clarification instead of running arbitrary commands.

The Halo / Reactor interface shows cyan rings beside chat and a live activity summary. Its state follows actual listening, local-model thinking, work, speech playback, waiting, and errors. The recording visualization uses microphone volume; the speaking pattern is decorative and follows playback status. Motion turns off continuous movement and is saved locally. There are no new interface dependencies.

Use Activity to view requests and their individual actions, status, and result details. The panel can be opened while ASUNA is busy, including by typing “show your work” and pressing Enter. Chat and the input box remain visible; smaller windows use a compact work view. Work records last for this app session. Plans are validated before execution, contain at most six supported actions, run in order, and stop after a failure or cancellation. Earlier completed actions are not undone. No automatic retries of side effects occur.

| Request | Result |
| --- | --- |
| `help` | Show all supported commands |
| `open youtube` / `open chrome` | Open Google Chrome |
| `search youtube: Python basics` | Open YouTube search results |
| `wikipedia: photosynthesis` | Open Wikipedia search results |
| `location: Delhi` | Open Maps results |
| `define: algorithm` | Look up the bundled offline dictionary |
| `take a screenshot` | Save all monitors to data/screenshots |
| `open calculator` / `open paint` / `open settings` | Open a Windows app |
| `open downloads` / `open documents` | Open a Windows folder |
| `choose search folder` then `find file: chapter` | Search names inside a folder you choose |
| `open result 1` | Open a document, picture, or folder from that search |
| `read document` | Attach a text or Word DOCX document for local questions |
| `forget document` | Remove the attached document from future requests |
| `add task: review chapter 2` | Save a task |
| `show tasks` / `complete task 1` | View or complete tasks |
| `remind me in 20 minutes to stretch` | Schedule an in-app reminder |
| `show reminders` / `cancel reminder 1` | Manage reminders |
| `save note: my exam is Friday` | Save an ordinary local note |
| `remember: I prefer short answers` | Save personal memory for future replies |
| `show memories` / `what do you remember` | Read personal memories |
| `update memory 1: a correction` | Update an active personal memory |
| `forget memory 1` / `restore memory 1` | Archive or restore personal memory |
| `show notes` | Read ordinary saved notes |
| `daily reminder at 20:00: stretch` | Save a daily reminder routine |
| `monday task at 09:00: review expenses` | Save a weekly task routine |
| `show routines` / `pause routine 1` / `resume routine 1` | Manage recurring routines |
| `daily overview` | View open tasks and remaining reminders/routines due today |
| `switch to deep` / `switch to fast` | Change model without clearing the conversation |
| `show your work` / `hide activity` | Show or hide action status |

Reminders require ASUNA to stay open. They appear in the chat, sound a bell, and raise the window. While a reply/action is in progress, delivery waits until it finishes. Overdue reminders are delivered on restart. No Windows scheduled tasks or external automation service is used.

Personal memories and recurring routines are saved in data/personal.json. Memory is explicit: ordinary chat/documents are not automatically remembered. The most recent 20 active memories (up to 300 characters each) are supplied as reference data to local replies. Updating/archiving a memory stops older chat context from being supplied, to avoid reintroducing the old fact. Archived memories remain on disk and can be restored; prior visible chat remains on disk too. New conversation clears chat context but keeps active memories and routines.

Routines use your PC's local time, with daily, weekdays, or weekly schedules. Missed occurrences produce one catch-up on restart rather than a backlog; task occurrence IDs prevent duplicate to-dos after retry/restart. Pause stops future deliveries; resume schedules the next future occurrence. Both reminder routines and to-do routines require ASUNA to be running. New routines first trigger at the next future time.

The background worker keeps the window responsive. One request runs at a time. Closing the app stops its worker; minimizing keeps it running. Activity shows actual actions and status, not hidden model reasoning.

Search skips linked subfolders and common build folders; limits are 30 matches, 20,000 entries, or about 15 seconds (slow/network folders may take longer). Document reading supports TXT, MD, CSV, PY, JSON, LOG and DOCX up to 5 MB, and supplies only the first 10,000 characters. PDF reading and screen-image analysis are not included.

Recent 20 conversation messages are supplied to either model, within the model's context limit. Attachments last for the current session only. New conversation detaches the current document and clears saved chat; notes, tasks, reminders and screenshots remain.

## What changed from upstream

- Refactored jarvis.py's command routing into a text-returning engine with no import-time device/network activity.
- Reused website opening, YouTube/Maps searches, time, remember/recall, and dictionary matching logic plus the original data.json dictionary.
- Replaced fixed user-specific music/editor paths with Windows app commands. Web actions now locate Chrome explicitly in standard install locations or Windows App Paths, rather than using the Windows default browser.
- Added the working ASUNA interface, Fast/Deep Ollama chat, background workers, local tasks, scoped file search and document reading.
- Added structured natural-language planning, follow-up clarification, and a status/results work view. Model planning receives request context, not attached document text. The answer-writing stage cannot execute actions.
- Replaced the placeholder screenshot destination with timestamped PNGs using built-in Windows screen capture.
- Replaced the original Google speech input with optional offline recognition, and added local Windows speech with recording/review, voice/device selection and stop controls.
- The original face authentication, weather/news API, SMTP email, forced shutdown, downloader and OCR paths are not wired into the ASUNA launcher. They require separate adaptation; the upstream scripts remain for reference.

On the original development computer, earlier notes and conversation were copied from the first ASUNA folder at migration time. The older launcher now redirects to this edition. Fresh GitHub clones start with empty personal data. Personal data is excluded from Git using .gitignore; it remains plain text on each computer.

If Ollama is unavailable, open Ollama and retry. If a model is missing, run `ollama pull qwen3.5:4b` or `ollama pull qwen3.5:9b`. Screenshot capture may be blocked by Windows PowerShell policy; ASUNA reports that failure instead of claiming success.
