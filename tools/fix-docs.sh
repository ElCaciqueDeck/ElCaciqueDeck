#!/usr/bin/env bash
# ElCaciqueDeck - find and fix "Server Error (500)" on CaciqueDocs (Paperless)
#
#   bash ~/elcaciquedeck/tools/fix-docs.sh
#
# Safe to run any time. It never deletes anything:
#   1. Checks that the Vault drive is connected
#   2. Finds where CaciqueDocs keeps its files (paperless/.env -> PAPERLESS_DIR)
#   3. Checks who owns those files (Paperless works as user 1000)
#   4. Reads what Paperless itself says is wrong (its log)
#   5. Gives the files back to user 1000 if needed (asks for your password)
#   6. Restarts CaciqueDocs from zero so it sees the Vault drive
#   7. Tests it, and saves a report you can send to Claude

# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
start_report "fix-docs"
DIR="$REPO/paperless"
RUN="$REPO/reports/run"; mkdir -p "$RUN"

docs_code() { curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:8000/; }

step "1/7  Vault drive"
need_vault
need_docker
sudo -v || fail "This needs your password."

step "2/7  Where CaciqueDocs keeps its files"
[ -f "$DIR/.env" ] || fail "paperless/.env is missing - CaciqueDocs was never set up on this laptop."
PDIR="$(grep -E '^PAPERLESS_DIR=' "$DIR/.env" | tail -1 | cut -d= -f2- | tr -d '"'"'")"
[ -n "$PDIR" ] || PDIR="/media/$USER/Library/Vault/paperless"
info "Folder: $PDIR"
case "$PDIR" in
    "$VAULT"/*) ok "It's on the Vault drive" ;;
    *) warn "It's NOT on the Vault drive. (If you moved it with move-to-vault.sh, PAPERLESS_DIR in paperless/.env should be $VAULT/paperless)" ;;
esac
[ -d "$PDIR" ] || fail "That folder doesn't exist. Check that the Vault drive is the right one (Files app -> Vault -> paperless)."
for sub in data media export consume; do
    if [ -d "$PDIR/$sub" ]; then ok "Found $sub/"; else warn "Missing $sub/ (it will be created)"; fi
done

step "3/7  Who owns the files (should be 1000)"
ls -lnd "$PDIR" "$PDIR"/* 2>/dev/null | awk '{printf "  %s %s:%s  %s\n", $1, $3, $4, $NF}'
BAD="$(sudo find "$PDIR" \( ! -uid 1000 -o ! -gid 1000 \) 2>/dev/null | wc -l)"
if [ "$BAD" -gt 0 ]; then
    warn "$BAD files/folders are NOT owned by 1000 - Paperless can't write to them (this causes the 500)"
else
    ok "Every file belongs to 1000"
fi
FREE="$(df -Pk "$PDIR" | awk 'NR==2 {print $4}')"
if [ "${FREE:-0}" -lt 1048576 ]; then warn "Less than 1 GB free on the drive - Paperless needs room to work"; else ok "Free space is fine"; fi

step "4/7  What Paperless says (its log)"
CODE="$(docs_code)"
info "CaciqueDocs answers now with code: $CODE   (200/302 = fine, 500 = broken, 000 = off)"
(cd "$DIR" && docker compose logs --no-color --tail 300 webserver 2>&1) >"$RUN/paperless-log.txt"
# hide anything that looks like a password or secret before showing it
sed -i -E 's/((PASS|SECRET|KEY|TOKEN)[A-Z_]*[=:] *)[^ ]+/\1••••••/Ig' "$RUN/paperless-log.txt"
grep -iE "error|denied|traceback|exception|locked|readonly|read-only|no such|disallowed|fatal" "$RUN/paperless-log.txt" \
    | grep -v "^\s*$" | tail -12 | sed 's/^/  | /'
info "Full log saved: $RUN/paperless-log.txt"

step "5/7  Fixing the owner"
if [ "$BAD" -gt 0 ]; then
    sudo chown -R 1000:1000 "$PDIR" && ok "Files given back to user 1000" || warn "chown failed"
else
    ok "Nothing to fix"
fi
mkdir -p "$PDIR"/{data,media,export,consume} 2>/dev/null || sudo mkdir -p "$PDIR"/{data,media,export,consume}
sudo chown 1000:1000 "$PDIR"/{data,media,export,consume}

step "6/7  Restarting CaciqueDocs from zero (keeps every document)"
(cd "$DIR" && docker compose down >"$RUN/paperless-restart.log" 2>&1 && docker compose up -d >>"$RUN/paperless-restart.log" 2>&1) \
    && ok "CaciqueDocs restarted" || fail "Could not restart - see $RUN/paperless-restart.log"

step "7/7  Testing (Paperless takes up to 2 minutes to wake up)"
i=0; CODE="000"
while [ "$i" -lt 150 ]; do
    CODE="$(docs_code)"
    case "$CODE" in 2*|3*) break ;; esac
    sleep 5; i=$((i+5))
done
case "$CODE" in
    2*|3*) ok "CaciqueDocs works again (code $CODE)" ;;
    *)  warn "CaciqueDocs still answers $CODE"
        (cd "$DIR" && docker compose logs --no-color --tail 300 webserver 2>&1) >"$RUN/paperless-log-after.txt"
        sed -i -E 's/((PASS|SECRET|KEY|TOKEN)[A-Z_]*[=:] *)[^ ]+/\1••••••/Ig' "$RUN/paperless-log-after.txt"
        echo "  Last error lines:"
        grep -iE "error|denied|traceback|exception|locked|no such|disallowed|fatal" "$RUN/paperless-log-after.txt" | tail -12 | sed 's/^/  | /'
        echo
        echo "  Send Claude the report (path below) - it has what's needed to find the cause." ;;
esac

finish
