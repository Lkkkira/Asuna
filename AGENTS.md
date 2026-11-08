# ASUNA project instructions

- Canonical repository: https://github.com/Lkkkira/Asuna.git
- This is the user's ASUNA project. Use this repository for future ASUNA changes.
- The user has requested that completed ASUNA changes be committed and pushed here. Run relevant checks before pushing. Preserve remote changes and never force-push without explicit authorization.
- Keep conversations, notes, organizer data, screenshots, credentials, and local environments out of Git. User-generated data lives under data/.
- Keep the upstream MIT license and attribution intact.
- Entry point: asuna.py; launcher: Start ASUNA.bat. Do not wire in legacy import-time speech, camera, email, or network side effects.
- Run checks from the repository folder: python tests/verify_asuna.py; python tests/verify_repo.py; python tests/verify_youtube.py.
- Also run python tests/verify_natural_actions.py for planner, tool execution, and work-view changes. Keep planning separate from answer generation; attached document text must never become tool instructions.
- For personal-memory or recurrence changes, run python tests/verify_personal.py. Never save inferred memories without an explicit user request. Keep personal.json out of Git and separate routine IDs from one-time reminder IDs.
- For voice changes, run .venv-voice/Scripts/python.exe tests/verify_voice.py. Do not open a real microphone or play sound in automated tests. Capture only after explicit Record interaction; transcribe locally and require review/Send. Keep audio, model weights, voice settings, and .venv-voice out of Git. Speech text must pass through stdin, never shell interpolation.
