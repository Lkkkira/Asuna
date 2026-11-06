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

The window title is **ASUNA — Repo edition**. This edition uses Python's standard library; the old upstream `requirements.txt` is not needed to run it.

## Features

- Fast / Deep model switching with shared recent conversation.
- Background processing and a show/hide activity panel.
- Opening Windows apps, folders, websites, and browser searches.
- An offline dictionary with spelling suggestions, adapted from the original project.
- File-name search inside a folder you choose, and text / Word document attachments.
- Local notes, tasks, in-app reminders, and screenshot saving.

Try `help`, `open youtube`, `define: algorithm`, `search youtube: Python basics`, `choose search folder`, or `add task: finish assignment`.

See [the usage guide](ASUNA-README.md) for supported commands and limitations. Reminders require the app to stay open; overdue reminders are delivered on restart. Browser searches require internet and open results for you to read. Voice, face recognition, email, OCR, video downloading, and weather/news APIs are not connected to the ASUNA launcher yet.

## Personal data

Chat, notes, organizer data, and screenshots are saved in `data/` on your computer. This folder is ignored by Git. They are plain text or ordinary image files; no cloud account or paid AI service is used by the chat interface. Downloaded Ollama models remain outside this repository.

## Checks

On Windows, from the repository folder:

```powershell
python tests/verify_asuna.py
python tests/verify_repo.py
python tests/verify_youtube.py
```

Checks use temporary data and mock app/browser launching. They cover organizer persistence, scoped file opening, document reading, background UI results, dictionary lookup, and command routing. They do not test a live screenshot, a real browser window, or model accuracy.

## Credits

Adapted from [GauravSingh9356/J.A.R.V.I.S](https://github.com/GauravSingh9356/J.A.R.V.I.S), commit `a1227a79bc8d27bf9a8369830c977f493418b9b5`, under the [MIT license](LICENSE). The original command script is preserved as `jarvis_legacy.py`, and [original documentation](README-UPSTREAM.md) remains available. ASUNA adds the local chat interface and modernizes the command engine.
