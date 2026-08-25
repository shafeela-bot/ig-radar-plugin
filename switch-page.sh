#!/usr/bin/env bash
# Switch which Instagram page this plugin is pointed at.
#
#   ./switch-page.sh                 show which page is active
#   ./switch-page.sh <handle>        switch to that page
#   ./switch-page.sh --new <handle>  create an empty page, then switch to it
#
# How it works: the plugin reads fixed paths (config/user_config.json, data/, ...).
# Those paths are symlinks. Switching repoints them at a different folder under
# profiles/. Nothing in lib/ or skills/ knows profiles exist, which is why adding a
# second page needed no code changes.
#
# Everything private to a page lives in profiles/<handle>/ and is git-ignored.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

PROFILES="profiles"
ACTIVE_FILE="$PROFILES/.active"

# Personal files that get repointed. Left side = the path the plugin reads.
# 'data' is a whole directory; the rest are single files inside config/.
LINKED_FILES=(user_config.json voice_fingerprint.json banned_phrases.txt)

die() { printf '\033[31merror:\033[0m %s\n' "$1" >&2; exit 1; }

current() { [[ -f $ACTIVE_FILE ]] && cat "$ACTIVE_FILE" || echo ""; }

summary() {
  local h="$1"; local cfg="$PROFILES/$h/user_config.json"
  [[ -f $cfg ]] || { echo "   (no config yet — run /ig-setup to fill it in)"; return; }
  python3 - "$cfg" "$PROFILES/$h" <<'PY'
import json, sys, pathlib
cfg, root = sys.argv[1], pathlib.Path(sys.argv[2])
d = json.load(open(cfg))
comp = d.get("competitors", {})
active = sum(len(v) for k, v in comp.items()
             if isinstance(v, list) and k != "excluded")
tags = len(d.get("hashtags", {}).get("tracked", []))
pitch = (d.get("niche", {}).get("one_line_pitch") or "not set")
print(f"   niche        {pitch[:66]}")
print(f"   competitors  {active} tracked")
print(f"   hashtags     {tags}")
for label, sub, pat in (("baselines", "data/baselines", "*.json"),
                        ("postmortems", "data/postmortems", "*.json")):
    n = len(list((root / sub).glob(pat))) if (root / sub).is_dir() else 0
    print(f"   {label:<12} {n}")
q = root / "data/queue/current.json"
if q.is_file():
    try:
        print(f"   queue        {len(json.load(open(q)).get('queue', []))} ideas")
    except Exception:
        print("   queue        unreadable")
PY
}

scaffold() {
  local h="$1"; local p="$PROFILES/$h"
  [[ -e $p ]] && die "page '$h' already exists at $p"
  mkdir -p "$p"/data/{baselines,postmortems,queue,outliers,scripts,transcripts}
  # Seed from the shared templates so /ig-setup has the right shape to fill in.
  cp config/user_config.template.json        "$p/user_config.json"
  cp config/voice_fingerprint.template.json  "$p/voice_fingerprint.json"
  cp config/banned_phrases.template.txt      "$p/banned_phrases.txt"
  printf '{\n "queue": []\n}\n' > "$p/data/queue/current.json"
  python3 - "$p/user_config.json" "$h" <<'PY'
import json, sys
path, handle = sys.argv[1], sys.argv[2]
d = json.load(open(path))
d.pop("_comment", None)
d.setdefault("accounts", {})["primary_handle"] = handle
# The template carries one null-handle row per tier to show the shape. Left in, a
# radar sweep would try to scrape a competitor literally named null — so drop any
# entry without a real handle and start the page genuinely empty.
for tier, rows in list(d.get("competitors", {}).items()):
    if isinstance(rows, list):
        d["competitors"][tier] = [r for r in rows
                                  if isinstance(r, dict) and r.get("handle")]
json.dump(d, open(path, "w"), indent=2, ensure_ascii=False)
open(path, "a").write("\n")
PY
  printf '\033[32mcreated\033[0m page "%s"\n' "$h"
}

activate() {
  local h="$1"; local p="$PROFILES/$h"
  [[ -d $p ]] || die "no page '$h'. Available: $(ls "$PROFILES" 2>/dev/null | tr '\n' ' ')"

  # Refuse to clobber a real file — only ever replace a symlink or nothing.
  for f in "${LINKED_FILES[@]}"; do
    if [[ -e "config/$f" && ! -L "config/$f" ]]; then
      die "config/$f is a real file, not a link. Move it into $p/ first so it isn't lost."
    fi
  done
  if [[ -e data && ! -L data ]]; then
    die "data/ is a real directory, not a link. Move it into $p/ first so it isn't lost."
  fi

  for f in "${LINKED_FILES[@]}"; do
    ln -sfn "../$p/$f" "config/$f"
  done
  ln -sfn "$p/data" data
  echo "$h" > "$ACTIVE_FILE"
}

case "${1-}" in
  "")
    c="$(current)"
    if [[ -z $c ]]; then
      echo "No page is active. Available:"
      ls "$PROFILES" 2>/dev/null | sed 's/^/   /' || echo "   (none)"
      exit 0
    fi
    printf '\033[1mactive page:\033[0m %s\n' "$c"
    summary "$c"
    others=$(ls "$PROFILES" 2>/dev/null | grep -vx "$c" || true)
    if [[ -n $others ]]; then
      echo; echo "other pages:"; echo "$others" | sed 's/^/   /'
    fi
    ;;
  --new)
    [[ -n ${2-} ]] || die "usage: ./switch-page.sh --new <handle>"
    scaffold "$2"; activate "$2"
    printf '\033[1mactive page:\033[0m %s\n' "$2"
    summary "$2"
    echo
    echo "Next: run /ig-setup to give this page its niche, competitors and hashtags."
    ;;
  -h|--help)
    sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    ;;
  *)
    prev="$(current)"
    activate "$1"
    if [[ -n $prev && $prev != "$1" ]]; then
      printf 'switched from %s\n' "$prev"
    fi
    printf '\033[1mactive page:\033[0m %s\n' "$1"
    summary "$1"
    ;;
esac
