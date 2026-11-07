# ASUNA — local Windows edition

This is a local adaptation of [GauravSingh9356/J.A.R.V.I.S](https://github.com/GauravSingh9356/J.A.R.V.I.S), based on commit `a1227a79bc8d27bf9a8369830c977f493418b9b5`.
The upstream MIT license and author credit remain in LICENSE. The original command script is saved as jarvis_legacy.py. README-UPSTREAM.md describes the upstream application; this file describes the adapted edition. The canonical ASUNA repository is https://github.com/Lkkkira/Asuna.

## Start

1. Keep Ollama running with `qwen3.5:4b` and `qwen3.5:9b` installed.
2. Double-click **Start ASUNA.bat** in this folder.

Uses your existing Python 3 installation, tkinter, and the standard library. **Do not install the old requirements.txt for this edition.** No paid API keys are needed. Local chat and dictionary work offline after model download; website searches require internet.

## Commands to try

Natural requests are now supported using your selected Fast/Deep model. For example, “Find my physics notes in Downloads,” “Remind me to study in half an hour,” or “Read this document and make five practice questions.” Known exact commands below bypass model planning and continue to work offline. Unsupported capabilities prompt a clarification instead of running arbitrary commands.

Use Show / hide activity to view requests and their individual actions, status, and result details. The panel can be opened while ASUNA is busy, including by typing “show your work” and pressing Enter. Work records last for this app session. Plans are validated before execution, contain at most six supported actions, run in order, and stop after a failure or cancellation. Earlier completed actions are not undone. No automatic retries of side effects occur.

| Request | Result |
| --- | --- |
| `help` | Show all supported commands |
| `open youtube` | Open the default browser |
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
| `remember that: my exam is Friday` | Save a local note |
| `what do you remember` / `show notes` | Read saved notes |
| `switch to deep` / `switch to fast` | Change model without clearing the conversation |
| `show your work` / `hide activity` | Show or hide action status |

Reminders require ASUNA to stay open. They appear in the chat, sound a bell, and raise the window. While a reply/action is in progress, delivery waits until it finishes. Overdue reminders are delivered on restart. No Windows scheduled tasks or external automation service is used.

The background worker keeps the window responsive. One request runs at a time. Closing the app stops its worker; minimizing keeps it running. Activity shows actual actions and status, not hidden model reasoning.

Search skips linked subfolders and common build folders; limits are 30 matches, 20,000 entries, or about 15 seconds (slow/network folders may take longer). Document reading supports TXT, MD, CSV, PY, JSON, LOG and DOCX up to 5 MB, and supplies only the first 10,000 characters. PDF reading and screen-image analysis are not included.

Recent 20 conversation messages are supplied to either model, within the model's context limit. Attachments last for the current session only. New conversation detaches the current document and clears saved chat; notes, tasks, reminders and screenshots remain.

## What changed from upstream

- Refactored jarvis.py's command routing into a text-returning engine with no import-time device/network activity.
- Reused website opening, YouTube/Maps searches, time, remember/recall, and dictionary matching logic plus the original data.json dictionary.
- Replaced fixed Chrome/music/editor paths with the default browser and Windows app commands.
- Added the working ASUNA interface, Fast/Deep Ollama chat, background workers, local tasks, scoped file search and document reading.
- Added structured natural-language planning, follow-up clarification, and a status/results work view. Model planning receives request context, not attached document text. The answer-writing stage cannot execute actions.
- Replaced the placeholder screenshot destination with timestamped PNGs using built-in Windows screen capture.
- The original voice/Google speech, face authentication, weather/news API, SMTP email, forced shutdown, downloader and OCR paths are not wired into the ASUNA launcher. They require separate adaptation; the upstream scripts remain for reference.

On the original development computer, earlier notes and conversation were copied from the first ASUNA folder at migration time. The older launcher now redirects to this edition. Fresh GitHub clones start with empty personal data. Personal data is excluded from Git using .gitignore; it remains plain text on each computer.

If Ollama is unavailable, open Ollama and retry. If a model is missing, run `ollama pull qwen3.5:4b` or `ollama pull qwen3.5:9b`. Screenshot capture may be blocked by Windows PowerShell policy; ASUNA reports that failure instead of claiming success.
