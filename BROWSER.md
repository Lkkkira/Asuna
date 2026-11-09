# Browser control

ASUNA can use your chosen everyday Chrome profile through the free local **ASUNA Browser Companion** extension. Profile selection and pairing stay under ignored `data/`; account names, tokens, cookies and login files are not included in the repository. There is no paid API.

## Use your existing Chrome profile

1. Run **Choose Chrome Profile.bat**, choose the profile you want, then reopen **Start ASUNA.bat**. The original development computer has already been configured with the user's chosen profile.
2. In that Chrome profile, open `chrome://extensions`. Turn on **Developer mode**, press **Load unpacked**, and select this repository's **chrome-extension** folder. Chrome shows the extension's permissions; loading it is a manual step.
3. In ASUNA type **connect browser**. It opens a local connection page in your selected profile. Press **Connect ASUNA** there. You only need to pair once. For the 1.2.0 update, restart ASUNA and manually reload the extension once so both versions are 1.2.0. Use the popup's **Reconnect now** for an existing pairing; pair again only when it reports missing/invalid pairing.
4. Ask ASUNA to open a page, then try `read page` or `open the first video`.

All links and searches open with the saved Chrome profile, even before the extension is paired. Page control waits for the extension; it never silently opens another profile. Closing ASUNA stops its local bridge and leaves your ordinary Chrome windows open. The extension can act on the active ordinary webpage in the connected profile, so check the active tab before issuing a command. Numbered controls and approvals are bound to the observed page/tab. `show browser tabs` lists ordinary web tabs in that profile; use its numbers to switch.

When a page-control request needs to wake the paired extension, ASUNA opens a temporary local reconnect tab. The extension validates the local request and closes that owned tab before acknowledging its one-use nonce. Only then can a new control command be queued against the original webpage. It does not silently re-pair or retry an uncertain action. Reconnect alarms are recreated at worker startup, and transient connection failures receive bounded retries; lost result acknowledgements may resend the result without performing the action again.

Playback follow-ups including `play it`, `the first video u found on youtube`, and `open youtube and play the first video` use browser actions directly. A completed YouTube search keeps its query in the current chat for 30 minutes, allowing an explicit follow-up to search again and play after a connection failure. This context clears on New chat and is not personal memory. Constraints, unsupported actions and missing actual page controls may still require your input.

The extension needs permission to read/change HTTP(S) pages so it can operate across websites. It sends visible page excerpts and observed controls to ASUNA on **127.0.0.1:17653**, authenticated with a local pairing secret. It does not use an external server, read Chrome passwords/cookies, or accept arbitrary code from the model. Use the extension popup's **Disconnect this profile** to disconnect. ASUNA supplies requested excerpts to the local Ollama model as untrusted reference data.

Chrome restricts remote debugging of regular profile directories. This extension uses Chrome's extension APIs instead of starting your personal profile through Playwright. See [Chrome's explanation](https://developer.chrome.com/blog/remote-debugging-port).

## Separate browser mode on a fresh clone

If no personal profile has been selected, close ASUNA and run **Setup Browser.bat**, then reopen it. This installs optional Playwright and reuses installed Chrome in `data/chrome-profile/`. It controls only that separate session. Closing ASUNA closes that session. You can sign in manually there, or select your everyday profile and load the extension instead. No account credentials are copied between profiles.

Try these requests:

| Request | Behavior |
| --- | --- |
| `search youtube: Python tutorials` | Open search results in controlled Chrome |
| `open the first video` | Open a recognizable video link at that position |
| `search web for: Python tutorials` then `open the first result` | Follow the first recognizable search result |
| `read page` | List observed links, buttons and fields with numbered IDs |
| `open Discord in Chrome` | Open Discord's web app in the selected Chrome profile |
| `open Discord` | Start a desktop client found in standard install locations; otherwise open the web app |
| `open a service name in Chrome` | Use a known site address or search the supplied name, preserving the requested destination |
| `type Discord in the search box` | Find one observed search field and review the exact text before filling it |
| `type: your draft` | Review typing into the focused webpage field, or a unique search/sole field if none is focused |
| `summarize this page` | Supply visible text to the local answer model as reference data |
| `click About` / `click 12` | Use a unique exact label or observed ID |
| `fill 8: your text` | Review and fill an ordinary text field |
| `search this site for cats` | Review and submit the current site's unique search field |
| `go back` / `go forward` / `reload page` | Navigate the current tab |
| `scroll down` / `scroll up` / `scroll top` / `scroll bottom` | Move around the page |
| `show browser tabs` / `switch to tab 2` | Inspect/switch controlled tabs |
| `pause` / `resume` / `mute` / `unmute` | Control the first HTML video/audio on the current page |
| `like the video` / `like this video` | Find the current YouTube video's Like control and ask for review before liking it |

Generic buttons, sensitive links, and field entry require a concrete review in ASUNA. Password, payment-code and upload fields are manual. Targets are checked against the observed page; navigation invalidates old numbered targets. After a page changes, read it again before choosing its IDs. Missing/ambiguous targets fail with details instead of using guessed coordinates.

The Like command recognizes English YouTube video labels that include changing reaction counts. It excludes comment Like buttons and Dislike, checks the toggle state, and reports already-liked videos without clicking them again. It requires a unique identifiable control on a YouTube video/Shorts page. The review identifies the actual video and button. If sign-in is required or YouTube does not confirm the reaction, check Chrome manually before retrying. Reload the extension after updates and restart ASUNA when its Python files change.

Typing commands fill ordinary webpage inputs, textareas and supported editable draft areas after review. They do not press Enter or send a message. `search this site for ...` is a separate reviewed submission. If more than one field matches, click the intended webpage field first and use `type: ...`, or choose a displayed field ID with `fill ID: ...`. Password/payment/upload fields, read-only controls, browser address bars and native dialogs remain manual. Some complex editors may reject programmatic text; ASUNA checks whether the field kept its value and reports failure rather than claiming it worked.

For a simple explicit browser request whose site name is unknown, ASUNA searches that exact name instead of guessing a domain or opening an empty Chrome homepage. It leaves the results for you to inspect. This fallback does not retry failed clicks, submissions or account changes. A complete new command also takes precedence over an older clarification question.

Visible webpage text is untrusted reference data. It cannot become code, change the tool allowlist, or grant permission. Browser summaries use the local model and may be inaccurate. The planner sees a bounded list of observed controls, not the full page body; answer generation can read the page body but cannot execute actions.

This version supports ordinary accessible HTML pages, not all browser/app interactions. Embedded cross-origin frame controls, canvas-only apps, CAPTCHAs, login/security prompts, browser settings/extensions, and native dialogs require manual work. Downloads/uploads are manual. Video/result detection relies on recognizable links and common result containers, so some layouts will need a listed target instead. A fresh logged-out YouTube homepage may have no videos; search first. Autoplay restrictions and site consent pages may require manual interaction.

Without either extension pairing or separate-browser setup, ASUNA can still launch links, but cannot inspect/control those tabs. Native Chrome dialogs, internal pages and login/security prompts remain manual.

Checks: `python tests/verify_browser_control.py` runs offline unit checks; its `--live` option uses headless, muted Chrome with a temporary local HTTP fixture/profile. `python tests/verify_chrome_profile.py` checks profile routing and authenticated loopback requests. `node tests/verify_extension.js` checks the packaged worker with a fake Chrome API. `python tests/verify_extension_page.py` checks the packaged page functions in isolated headless Chrome. These do not install the extension in a personal profile or test a signed-in external website. Manual loading/pairing is still required on the user's profile.

`python tests/verify_extension_transport.py` runs the packaged worker through real HTTP against an isolated Python bridge. Chrome UI/DOM APIs are fixtures; it covers restart recovery, in-flight pairing rotation, helper-tab ordering and lost acknowledgements without a personal profile or audible media.
