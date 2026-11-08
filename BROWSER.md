# Browser control

Close ASUNA and run **Setup Browser.bat**, then reopen **Start ASUNA.bat**. This installs Playwright in the local runtime and reuses your installed Chrome; no paid API or extra browser download is required. Setup is already installed on the original development computer.

ASUNA owns a separate Chrome window/profile in `data/chrome-profile/`. It follows pages opened through ASUNA, rather than attaching to personal Chrome tabs. Cookies and sessions persist locally and remain excluded from Git. Log in manually if needed. Closing ASUNA closes its controlled session; ordinary Chrome windows are separate.

Try these requests:

| Request | Behavior |
| --- | --- |
| `search youtube: Python tutorials` | Open search results in controlled Chrome |
| `open the first video` | Open a recognizable video link at that position |
| `search web for: Python tutorials` then `open the first result` | Follow the first recognizable search result |
| `read page` | List observed links, buttons and fields with numbered IDs |
| `summarize this page` | Supply visible text to the local answer model as reference data |
| `click About` / `click 12` | Use a unique exact label or observed ID |
| `fill 8: your text` | Review and fill an ordinary text field |
| `search this site for cats` | Review and submit the current site's unique search field |
| `go back` / `go forward` / `reload page` | Navigate the current tab |
| `scroll down` / `scroll up` / `scroll top` / `scroll bottom` | Move around the page |
| `show browser tabs` / `switch to tab 2` | Inspect/switch controlled tabs |
| `pause` / `resume` / `mute` / `unmute` | Control the first HTML video/audio on the current page |

Generic buttons, sensitive links, and field entry require a concrete review in ASUNA. Password, payment-code and upload fields are manual. Targets are checked against the observed page; navigation invalidates old numbered targets. After a page changes, read it again before choosing its IDs. Missing/ambiguous targets fail with details instead of using guessed coordinates.

Visible webpage text is untrusted reference data. It cannot become code, change the tool allowlist, or grant permission. Browser summaries use the local model and may be inaccurate. The planner sees a bounded list of observed controls, not the full page body; answer generation can read the page body but cannot execute actions.

This version supports ordinary accessible HTML pages, not all browser/app interactions. Embedded cross-origin frame controls, canvas-only apps, CAPTCHAs, login/security prompts, browser settings/extensions, and native dialogs require manual work. Downloads/uploads are manual. Video/result detection relies on recognizable links and common result containers, so some layouts will need a listed target instead. A fresh logged-out YouTube homepage may have no videos; search first. Autoplay restrictions and site consent pages may require manual interaction.

Without browser setup, ASUNA can still launch links in ordinary Chrome, but cannot inspect/control those tabs. Restart after setup to use the controlled window.

Checks: `python tests/verify_browser_control.py` runs offline unit checks. `.venv-voice\Scripts\python.exe tests/verify_browser_control.py --live` additionally runs headless, muted Chrome against a temporary local HTTP fixture/profile. These never use your personal browser session or an external website.
