# ASUNA project instructions

- Canonical repository: https://github.com/Lkkkira/Asuna.git
- This is the user's ASUNA project. Use this repository for future ASUNA changes.
- The user has requested that completed ASUNA changes be committed and pushed here. Run relevant checks before pushing. Preserve remote changes and never force-push without explicit authorization.
- Keep conversations, notes, organizer data, screenshots, credentials, and local environments out of Git. User-generated data lives under data/.
- Keep the upstream MIT license and attribution intact.
- Entry point: asuna.py; launcher: Start ASUNA.bat. Do not wire in legacy import-time speech, camera, email, or network side effects.
- Run checks from the repository folder: python tests/verify_asuna.py; python tests/verify_repo.py; python tests/verify_youtube.py.
