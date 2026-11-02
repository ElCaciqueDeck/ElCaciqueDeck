#!/usr/bin/env bash
# ElCaciqueDeck - write the live front page settings (homepage/config-live) from homepage/config,
# leaving out the buttons of apps that aren't installed on this computer.
# Run by setup-homepage.sh, start-all.sh and update.sh; safe any time.
DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$DIR/.." && pwd)"
# the live front page config: same as ./config, without the buttons of apps that aren't installed
mkdir -p "$DIR/config-live"
cp -f "$DIR"/config/*.yaml "$DIR"/config/custom.* "$DIR/config-live/" 2>/dev/null
python3 - "$DIR/config/services.yaml" "$DIR/config-live/services.yaml" "$REPO" <<'PY'
import os, re, sys
src, dst, repo = sys.argv[1:4]
out, block, keep = [], [], True
def flush():
    if keep:
        out.extend(block)
for line in open(src, encoding="utf-8").read().splitlines():
    if re.match(r"^    - ", line) or re.match(r"^- ", line):
        flush(); block, keep = [line], True
        continue
    m = re.match(r"^\s+# needs: (\S+)", line)
    if m:
        path = os.path.expanduser(m.group(1))
        keep = os.path.exists(path if os.path.isabs(path) else os.path.join(repo, path))
        continue
    block.append(line)
flush()
# drop groups left without buttons
text, cleaned = out, []
for i, line in enumerate(text):
    if re.match(r"^- ", line):
        nxt = next((l for l in text[i + 1:] if l.strip()), "")
        if not nxt.startswith("    - "):
            continue
    cleaned.append(line)
open(dst, "w", encoding="utf-8").write("\n".join(cleaned) + "\n")
PY
echo "  [ OK ]  Front page buttons: only the apps installed on this computer"
