# Running this plugin on Windows

Everything here is a one-time setup. After it, every command in every skill works
exactly as written, with no Windows-specific variants to remember.

Do these in order. Step 1 is the one that makes the other 33 commands work.

---

## 1. Make `python3` exist (required)

Every skill and doc in this plugin runs Python as **`python3`** — 33 commands across
8 files. On macOS and Linux that is the normal name. On Windows, Python installs as
`python` and `py`, so every one of those commands fails with:

```
'python3' is not recognized as an internal or external command
```

Rather than rewrite 33 commands into something that then breaks on macOS, create a
one-line shim so `python3` means what it means everywhere else.

**Check Python is installed first:**

```powershell
py -3 --version
```

If that fails, install Python from https://www.python.org/downloads/ and tick
**"Add python.exe to PATH"** in the installer.

**Then create the shim.** Pick a folder that is already on your PATH — if you're not
sure, use `%LOCALAPPDATA%\Microsoft\WindowsApps`, which always is:

```powershell
Set-Content -Path "$env:LOCALAPPDATA\Microsoft\WindowsApps\python3.bat" -Value "@py -3 %*"
```

**Verify** in a *new* terminal:

```powershell
python3 --version
```

If that prints a version, every command in every skill now works as written.

> **Note on the Microsoft Store stub.** Windows ships a fake `python3.exe` that just
> opens the Store. If `python3 --version` opens the Store instead of printing a
> version, turn the stub off: **Settings → Apps → Advanced app settings → App
> execution aliases**, and switch off both **python.exe** and **python3.exe**.

---

## 2. Set up your page (required)

The plugin reads fixed paths — `config/user_config.json`, `data/`, and two more.
Those paths are **links** pointing into `profiles/<your-page>/`, and they are
git-ignored, so a fresh clone does not have them. Nothing works until they exist.

Use the Python version of the switcher, **not** the `.sh` one:

```powershell
python3 switch-page.py --new yourhandle
```

or, to point at a page that already exists:

```powershell
python3 switch-page.py yourhandle
```

`switch-page.sh` is bash and will not run on Windows.

### How the links are made, and why you don't need admin rights

`switch-page.py` tries three mechanisms in order and tells you if it lands on the
last one:

| Mechanism | Used for | Needs admin? |
|---|---|---|
| Symbolic link | files and folders | Yes, or Developer Mode |
| **Directory junction** (`mklink /J`) | `data/` | **No** |
| **Hard link** (`os.link`) | the three config files | **No** |
| Copy | last resort only | No — but see the warning |

Windows blocks symlinks unless you are elevated or have Developer Mode on, which is
why a plain `ln -s` port would leave you with nothing. Junctions and hard links have
no such restriction and behave the same way for our purposes: one copy of the bytes,
edits visible through either path.

**If you see the yellow `warning: ... config was COPIED` message**, your system
allowed neither. The plugin will still run, but `config/` and `profiles/` are now two
separate files that will drift apart, and switching pages will overwrite your edits.
Fix it by turning on Developer Mode (**Settings → System → For developers →
Developer Mode**) and running `switch-page.py` again.

---

## 3. Optional: ffmpeg, for pacing analysis and reading on-screen text

Only needed for `/ig-postmortem` and `/ig-voice-profile`. Skip it if you're not
using those — every other skill checks for ffmpeg and degrades gracefully.

```powershell
winget install Gyan.FFmpeg
```

Or, with no package manager and no admin rights:

```powershell
py -3 -m pip install --user static-ffmpeg
static_ffmpeg_paths
```

That prints the two binary paths; add the folder containing them to your PATH. The
plugin needs **both** `ffmpeg` and `ffprobe` on PATH — `lib/ffmpeg_analysis.py`
checks for both and disables itself if either is missing.

---

## 4. Optional: Composio, for your own Instagram metrics

Needed for saves, shares, reach and average watch time — the numbers Apify cannot
see. The `curl | sh` installer in Composio's docs is POSIX-only and will not run in
PowerShell.

```powershell
winget install Composio.Composio
```

or, with Node installed:

```powershell
npm install -g composio
```

Then:

```powershell
composio login
python3 lib/composio_client.py check
```

`check` tells you whether the CLI is found, you're logged in, and an Instagram
account is connected.

---

## Check everything at once

```powershell
python3 --version
python3 switch-page.py
python3 lib/composio_client.py check
ffmpeg -version
```

The second one should print your active page and a summary. If it prints
`No page is active`, go back to step 2.

---

## Known differences from macOS

- **Use `switch-page.py`, never `switch-page.sh`.** The `.sh` is kept for macOS and
  Linux; both scripts do the same thing and are safe to use side by side on a shared
  repo.
- **Line endings.** If Git converts files to CRLF on checkout you may see odd
  behaviour in text config. `git config --global core.autocrlf input` avoids it.
- **Paths with spaces.** Quote them. The repo folder name itself contains a space in
  at least one known checkout, and unquoted paths will split on it.
