# ASUNA 1.1.2 — everyday use

ASUNA is a free local Windows assistant. Ollama supplies conversation and natural-language planning; exact commands, organizer data and utilities also work when Ollama is unavailable. Website services still need internet. No paid API key is required.

## After updating

1. Close old ASUNA windows and reopen **Start ASUNA.bat**. Existing data stays under `data/`.
2. Run **Setup ASUNA.bat** once if you want selectable-text PDF attachments. On the original development computer this package is already installed.
3. In your chosen Chrome profile, open `chrome://extensions` and manually reload **ASUNA Browser Companion**. It should show **1.1.0**. Use `connect browser` if the extension popup reports disconnected.
4. Open **Settings → Check setup**. It checks local services without recording audio or changing accounts.

## Your main controls

| Control | Use |
| --- | --- |
| Fast / Deep | Switch models while keeping the current conversation. Settings can change the model names. Models must already be installed in Ollama. |
| Settings | Models, reply style, response/context limits, custom shortcuts, Chrome profile, diagnostics and local backups. Larger context can use more RAM/VRAM; the response limit must leave room for the request. |
| Organizer | Tasks, notes and routines with visible controls. Refresh shows changes made in chat. |
| Activity | Inspect actual actions, status and results while work happens in the background. |
| Stop | Interrupt local generation or stop the plan before its next operation. Completed actions are kept. Some running operations finish before stopping. |
| New chat | Archive the current conversation, detach its document and begin a new one. Memories, tasks and notes remain. |
| Chat history | Search and read up to 100 matching saved conversations. Viewing an archive does not feed it to the model. |

ASUNA runs one request at a time. The app needs to stay open for reminders, timers and recurring routines; minimizing keeps it running. Restart delivers overdue reminders and one catch-up per missed routine. It does not operate while the PC is off or ASUNA is closed.

## Apps, websites and browser work

Use `open discord` for the installed app (official web app fallback), or `open discord in Chrome` for its web app. Explicit browser destinations preserve the service name. Unknown browser destinations open a named web search so you can choose the correct result.

In **Settings → Shortcuts**, add an installed `.exe`, a website address or a folder. Give it a name such as `My editor`, then say `open My editor`. Shortcuts cannot override built-in names such as Chrome and do not accept scripts or shell arguments. Enable/disable them in the panel.

`open youtube and play music` searches for music, opens the first video and requests playback. `play lo-fi music on YouTube` searches that phrase. This needs connected page control; site consent/autoplay restrictions may still require interaction. `first video` and `second result` are direct follow-ups on the current page. ASUNA rejects plans that drop a named destination and merely open Chrome.

Successful browser work gets a short acknowledgement, such as “Playing music on YouTube.” Detailed page/control output stays in Activity instead of being read aloud or added to ordinary action replies. Explicit `read page` and `show browser tabs` still display the lists so you can choose targets. Summaries and document answers continue to speak normally. **Stop speaking** interrupts a current response.

For website control, use `read page`, `open the first result`, `click` with an exact displayed label/ID, or `type: your draft`. `type Discord in the search box` selects the page's search field. Ordinary field entry is reviewed and does not automatically press Enter or send. Use the explicit site-search command when you want a search submitted. Generic buttons and sensitive links also require review. Login, passwords, payment details, CAPTCHAs, browser permission prompts and native dialogs remain manual. See [browser details](BROWSER.md).

When pairing, type `connect browser` and click **Connect ASUNA inside the Chrome tab**, then wait for **Connected**. The tab opening by itself is not a completed connection.

## Tasks, notes and daily tools

Try these exact commands without a model connection:

```text
add task: Pack the charger
task 1 priority: high
task 1 due: 2026-12-20
edit task 1: Pack the charger and headphones
complete task 1
reopen task 1
archive task 1
restore task 1
show tasks
show archived tasks

save note: Weekend ideas: go for a walk
read note 1
update note 1: Weekend ideas: walk and tidy the desk
search notes: weekend
archive note 1
restore note 1
show archived notes

calculate: (12 + 3) * 4
convert 5 km to miles
convert 30 c to f
days until 2026-12-20
focus for 25 minutes
timer 10 minutes: Check the oven
daily reminder at 20:00: Stretch
daily overview
```

Use displayed IDs; examples assume ID 1 exists. Clear a task date with `task 1 due:`. Priorities are `low`, `normal` or `high`. Archived tasks and notes stay on disk and can be restored. Notes are separate from explicit personal memory (`remember: I prefer brief replies`). Existing legacy notes are imported once without deleting the source file.

Arithmetic supports parentheses, +, -, *, /, //, %, powers (`^` or `**`), pi/e/tau and sqrt/sin/cos/tan/log/log10/abs/round/min/max. Trigonometry uses radians. Calculations are bounded and do not run code. Conversion supports common length, mass, time, temperature and byte-storage units (MB decimal; MiB binary). Currency conversion needs current rates and is not included.

## Documents and voice

Attach text, DOCX or selectable-text PDF with **Document** or `read document`, then ask questions about the excerpt. Files are limited to 5 MB and 10,000 extracted characters. PDFs examine up to 100 pages with a page-stream size limit. Large or complex documents can be incomplete; check source material for exact formatting. Scans without text need OCR and encrypted PDFs need a readable copy. PDF extraction uses [pypdf](https://pypdf.readthedocs.io/en/stable/user/extract-text.html).

Voice remains explicit: **Record → Stop recording → review/edit → Send**. Whisper runs locally; English is the default, with Mixed English + Hindi available. No continuous listening, wake word or automatic voice execution is enabled. Female Windows speech is available through **Speak replies** and can be interrupted with **Stop speaking**. See [voice setup](README.md#voice-interaction).

The main checkbox shows **Speak replies: On/Off**. Type `voice on` or `voice off` to save the same setting in chat. **Voice settings → Test voice** is an explicit test of the selected voice and does not enable automatic replies. If there is still no audio, inspect the displayed speech error and Windows output-device/volume controls yourself. Automated checks mock playback and cannot establish that sound reached your speakers.

## Backups and recovery

**Settings → Data & history** can export the current chat or create/restore a ZIP backup. By default, ASUNA creates at most one daily backup when it opens, under `data/backups/`. Old backups are retained; manage their storage yourself. Automatic backup can be disabled in Settings.

Backups include saved conversation state/archives, notes, tasks/reminders, memories/routines, shortcuts and assistant/browser/voice/interface settings. They exclude cookies, Chrome profile contents, microphone recordings, screenshots, model weights, logs and extension pairing secrets. They contain personal information in ordinary readable form, so store them privately. They are not uploaded or committed to Git.

Archives are limited to 5 MB per state file, 20 MB total and 1,000 state files. Export or move older conversation archives separately if needed. Restoring validates paths, types, size limits and integrity before writing. It replaces only files present in that archive, makes a safety backup first, and rolls back preceding replacements if a write fails. It closes the main app after success so restored state loads on restart. Unrelated files and archived conversations absent from the backup remain.

If ASUNA cannot start, close it and run **Restore ASUNA Backup.bat** to choose an existing backup without starting the main assistant. Corrupt original state is retained in the safety backup for manual recovery; it may itself need repair before normal restore. **Check ASUNA.bat** reports setup issues. Interface/startup errors are written to local rotating `data/asuna.log` files. Preserve the data folder when troubleshooting.

New launches enforce one writer for the data folder. Close pre-update ASUNA windows first, as older versions do not hold that lock.

## Current boundaries

This release covers local conversation, supported Windows apps/shortcuts, ordinary browser controls, organization, voice and document help. It does not promise universal computer control. Email/calendar service integrations, autonomous message sending, purchases, arbitrary terminal commands, image/OCR interpretation, always-on listening and operation while ASUNA is closed are not included. Unsupported requests should ask for clarification or explain the limitation. Model answers and speech recognition can still make mistakes.
