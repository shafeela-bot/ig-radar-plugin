#!/usr/bin/env python3
"""
Switch which Instagram page this plugin is pointed at. Works on macOS, Linux and
Windows.

    python3 switch-page.py                 show which page is active
    python3 switch-page.py <handle>        switch to that page
    python3 switch-page.py --new <handle>  create an empty page, then switch to it

(On Windows, run it as `py -3 switch-page.py ...` unless you've set up the python3
shim described in docs/windows-setup.md.)

How it works: the plugin reads fixed paths (config/user_config.json, data/, ...).
Those paths are links. Switching repoints them at a different folder under
profiles/. Nothing in lib/ or skills/ knows profiles exist, which is why adding a
second page needed no code changes.

Everything private to a page lives in profiles/<handle>/ and is git-ignored.

WHY THIS EXISTS ALONGSIDE switch-page.sh
----------------------------------------
The shell version uses `ln -s`, which is fine on macOS and Linux but effectively
unavailable to a normal Windows user: CreateSymbolicLink needs either an elevated
prompt or Developer Mode, so a teammate on Windows ends up with no config at all and
every skill fails on its first step.

Windows does, however, give you two link types that need no special rights:

- **Directory junctions** (`mklink /J`) for folders — used for data/
- **Hard links** (os.link) for files — used for the three config files

Both behave like the symlinks the rest of the plugin expects: one copy of the bytes,
edits visible through either path. So the fixed-path design survives unchanged.

Copying is the last resort and is announced loudly, because two real copies silently
drift apart — which is worse than failing.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROFILES = ROOT / "profiles"
ACTIVE_FILE = PROFILES / ".active"

# Personal files that get repointed. 'data' is a whole directory; these are single
# files inside config/.
LINKED_FILES = ("user_config.json", "voice_fingerprint.json", "banned_phrases.txt")

WINDOWS = os.name == "nt"


# ---------------------------------------------------------------- terminal output

def _supports_color() -> bool:
    if not sys.stdout.isatty():
        return False
    if WINDOWS:
        # Windows Terminal and PowerShell 7 handle ANSI; older conhost needs VT
        # switched on explicitly. If that fails, fall back to plain text.
        try:
            import ctypes
            k = ctypes.windll.kernel32
            return bool(k.SetConsoleMode(k.GetStdHandle(-11), 7))
        except Exception:
            return False
    return True


COLOR = _supports_color()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if COLOR else text


def bold(t: str) -> str:
    return _c("1", t)


def die(msg: str) -> "typing.NoReturn":  # noqa: F821
    print(f"{_c('31', 'error:')} {msg}", file=sys.stderr)
    raise SystemExit(1)


# ------------------------------------------------------------------- link helpers

def _is_junction(p: Path) -> bool:
    """A Windows directory junction. os.path.islink() returns False for these."""
    if not WINDOWS:
        return False
    if hasattr(os.path, "isjunction"):          # Python 3.12+
        return os.path.isjunction(p)
    try:
        return bool(p.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except (OSError, AttributeError):
        return False


def _is_hardlink(p: Path) -> bool:
    """
    A file with more than one directory entry pointing at the same data.

    This is how we recognise a config file we linked on Windows. Without it the
    "don't clobber a real file" guard below would refuse to switch pages, because a
    hard link is indistinguishable from an ordinary file by name alone.
    """
    try:
        return p.is_file() and p.stat().st_nlink > 1
    except OSError:
        return False


def _is_managed_link(p: Path) -> bool:
    """Is this path something we created, and therefore safe to replace?"""
    return p.is_symlink() or _is_junction(p) or _is_hardlink(p)


def _clear(p: Path) -> None:
    """Remove an existing link so it can be repointed."""
    if p.is_symlink() or _is_junction(p):
        # Junctions and directory symlinks must be removed with rmdir, not unlink.
        try:
            p.unlink()
        except (OSError, PermissionError):
            os.rmdir(p)
    elif p.exists():
        p.unlink()


def link_file(target: Path, link: Path) -> str:
    """Point `link` at the file `target`. Returns the mechanism used."""
    _clear(link)
    rel = os.path.relpath(target, link.parent)
    try:
        os.symlink(rel, link)
        return "symlink"
    except (OSError, NotImplementedError):
        pass
    try:
        os.link(target, link)                    # hard link — no elevation needed
        return "hardlink"
    except (OSError, NotImplementedError):
        pass
    shutil.copy2(target, link)
    return "copy"


def link_dir(target: Path, link: Path) -> str:
    """Point `link` at the directory `target`. Returns the mechanism used."""
    _clear(link)
    rel = os.path.relpath(target, link.parent)
    try:
        os.symlink(rel, link, target_is_directory=True)
        return "symlink"
    except (OSError, NotImplementedError):
        pass
    if WINDOWS:
        # Junctions need no elevation, which is the whole reason this branch exists.
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                           capture_output=True, text=True)
        if r.returncode == 0:
            return "junction"
        die(f"could not link {link} -> {target}.\n"
            f"       mklink said: {(r.stderr or r.stdout).strip()}\n"
            f"       Try running this from a terminal opened as Administrator, or "
            f"turn on Developer Mode in Windows Settings.")
    die(f"could not link {link} -> {target}")


# ------------------------------------------------------------------------ actions

def current() -> str:
    return ACTIVE_FILE.read_text().strip() if ACTIVE_FILE.is_file() else ""


def pages() -> list[str]:
    if not PROFILES.is_dir():
        return []
    return sorted(p.name for p in PROFILES.iterdir() if p.is_dir())


def summary(handle: str) -> None:
    root = PROFILES / handle
    cfg = root / "user_config.json"
    if not cfg.is_file():
        print("   (no config yet — run /ig-setup to fill it in)")
        return
    d = json.loads(cfg.read_text(encoding="utf-8"))
    comp = d.get("competitors", {})
    active = sum(len(v) for k, v in comp.items()
                 if isinstance(v, list) and k != "excluded")
    tags = len(d.get("hashtags", {}).get("tracked", []))
    pitch = (d.get("niche", {}).get("one_line_pitch") or "not set")
    print(f"   niche        {pitch[:66]}")
    print(f"   competitors  {active} tracked")
    print(f"   hashtags     {tags}")
    for label, sub in (("baselines", "data/baselines"),
                       ("postmortems", "data/postmortems")):
        d_ = root / sub
        n = len(list(d_.glob("*.json"))) if d_.is_dir() else 0
        print(f"   {label:<12} {n}")
    q = root / "data/queue/current.json"
    if q.is_file():
        try:
            n = len(json.loads(q.read_text(encoding="utf-8")).get("queue", []))
            print(f"   queue        {n} ideas")
        except Exception:
            print("   queue        unreadable")


def scaffold(handle: str) -> None:
    p = PROFILES / handle
    if p.exists():
        die(f"page '{handle}' already exists at {p}")
    for sub in ("baselines", "postmortems", "queue", "outliers", "scripts",
                "transcripts"):
        (p / "data" / sub).mkdir(parents=True, exist_ok=True)
    for src, dst in ((ROOT / "config/user_config.template.json", p / "user_config.json"),
                     (ROOT / "config/voice_fingerprint.template.json", p / "voice_fingerprint.json"),
                     (ROOT / "config/banned_phrases.template.txt", p / "banned_phrases.txt")):
        shutil.copyfile(src, dst)
    (p / "data/queue/current.json").write_text('{\n "queue": []\n}\n', encoding="utf-8")

    cfg = p / "user_config.json"
    d = json.loads(cfg.read_text(encoding="utf-8"))
    d.pop("_comment", None)
    d.setdefault("accounts", {})["primary_handle"] = handle
    # The template carries one null-handle row per tier to show the shape. Left in, a
    # radar sweep would try to scrape a competitor literally named null — so drop any
    # entry without a real handle and start the page genuinely empty.
    for tier, rows in list(d.get("competitors", {}).items()):
        if isinstance(rows, list):
            d["competitors"][tier] = [r for r in rows
                                      if isinstance(r, dict) and r.get("handle")]
    cfg.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f'{_c("32", "created")} page "{handle}"')


def activate(handle: str) -> None:
    p = PROFILES / handle
    if not p.is_dir():
        die(f"no page '{handle}'. Available: {' '.join(pages()) or '(none)'}")

    # Refuse to clobber real data — only ever replace a link we made, or nothing.
    for f in LINKED_FILES:
        dst = ROOT / "config" / f
        if dst.exists() and not _is_managed_link(dst):
            die(f"config/{f} is a real file, not a link. "
                f"Move it into {p}/ first so it isn't lost.")
    data = ROOT / "data"
    if data.exists() and not _is_managed_link(data):
        die(f"data/ is a real directory, not a link. "
            f"Move it into {p}/ first so it isn't lost.")

    methods = set()
    for f in LINKED_FILES:
        methods.add(link_file(p / f, ROOT / "config" / f))
    methods.add(link_dir(p / "data", data))
    ACTIVE_FILE.write_text(handle + "\n", encoding="utf-8")

    if "copy" in methods:
        print(_c("33",
                 "warning: your system allowed neither symlinks nor hard links, so "
                 "config was COPIED.\n         Edits made through config/ will not "
                 "reach profiles/, and switching pages\n         will overwrite them. "
                 "See docs/windows-setup.md."))


# --------------------------------------------------------------------------- main

def main(argv: list[str]) -> int:
    PROFILES.mkdir(exist_ok=True)
    arg = argv[1] if len(argv) > 1 else ""

    if arg in ("-h", "--help"):
        print(__doc__.split("WHY THIS EXISTS")[0].strip())
        return 0

    if arg == "--new":
        if len(argv) < 3:
            die("usage: python3 switch-page.py --new <handle>")
        scaffold(argv[2])
        activate(argv[2])
        print(f"{bold('active page:')} {argv[2]}")
        summary(argv[2])
        print()
        print("Next: run /ig-setup to give this page its niche, competitors and hashtags.")
        return 0

    if not arg:
        c = current()
        if not c:
            print("No page is active. Available:")
            for name in pages() or ["(none)"]:
                print(f"   {name}")
            return 0
        print(f"{bold('active page:')} {c}")
        summary(c)
        others = [p for p in pages() if p != c]
        if others:
            print()
            print("other pages:")
            for name in others:
                print(f"   {name}")
        return 0

    prev = current()
    activate(arg)
    if prev and prev != arg:
        print(f"switched from {prev}")
    print(f"{bold('active page:')} {arg}")
    summary(arg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
