#!/usr/bin/env bash
# ElCaciqueDeck - move the irreplaceable data from the Library drive to the Vault drive
#
#   bash ~/elcaciquedeck/tools/move-to-vault.sh
#
# Moves:
#   CaciqueDocs   (Paperless)  Library/Vault/paperless  ->  Vault/paperless
#   CaciquePhotos (Immich)     Library/Photos/immich    ->  Vault/Photos/immich
#
# How it stays safe:
#   1. Stops only those two servers
#   2. COPIES everything (nothing is deleted)
#   3. Checks the copy: same number of files and same total size
#   4. Only then points the servers to Vault and starts them again
#   5. Renames the old folders on Library to _old-...-<date> so you can check
#      everything works before deleting them yourself (see the end of the report)
#
# Safe to run again: anything already moved is skipped.

# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
start_report "move-to-vault"
STAMP="$(date +%Y-%m-%d)"

step "1/6  Checks"
need_docker
need_library
need_vault
[ "$(findmnt -no FSTYPE "$VAULT")" = "ext4" ] && ok "Vault is ext4" || fail "Vault isn't ext4. Format it as Ext4 in the Disks app first."
[ -w "$VAULT" ] || fail "Vault isn't writable by you. Fix: sudo chown -R \$USER:\$USER $VAULT"
if ! command -v rsync >/dev/null; then
    sudo apt-get install -y rsync >/dev/null 2>&1 && ok "rsync (copy tool) installed" || fail "Could not install rsync (the copy tool). Check the internet and run this again."
fi
sudo -v || fail "This needs your password (the photo files belong to the system)."

# what to move:  name | old location | new location | compose folder | .env line to set
MOVES=(
  "CaciqueDocs|$LIBRARY/Vault/paperless|$VAULT/paperless|paperless|PAPERLESS_DIR"
  "CaciquePhotos|$LIBRARY/Photos/immich|$VAULT/Photos/immich|immich|UPLOAD_LOCATION"
)

NEED=0
for m in "${MOVES[@]}"; do
    IFS='|' read -r _ src _ _ _ <<< "$m"
    [ -d "$src" ] && NEED=$((NEED + $(sudo du -sb "$src" | cut -f1)))
done
FREE=$(df -B1 --output=avail "$VAULT" | tail -1)
info "To copy: $((NEED/1024/1024/1024)) GB   Free on Vault: $((FREE/1024/1024/1024)) GB"
[ "$NEED" -lt "$FREE" ] && ok "Enough space on Vault" || fail "Not enough space on Vault."

for m in "${MOVES[@]}"; do
    IFS='|' read -r name src dst stack key <<< "$m"
    envf="$REPO/$stack/.env"

    step "$name"
    if [ -f "$envf" ] && grep -q "^$key=$dst\$" "$envf"; then
        ok "Already on Vault - skipping"
        continue
    fi
    if [ ! -d "$src" ]; then
        info "Nothing at $src - $name not set up yet, skipping (new data will go straight to Vault next time it's set up)"
        continue
    fi

    echo "  2/6  Stopping $name..."
    (cd "$REPO/$stack" && docker compose down >/dev/null 2>&1)
    ok "$name stopped"

    echo "  3/6  Copying (keeps owners and permissions; big photo libraries take a while)..."
    sudo mkdir -p "$dst"
    sudo rsync -aHAX --info=progress2 "$src/" "$dst/" || fail "Copy failed - nothing was changed. $name is stopped; start it with start-all.sh"

    echo "  4/6  Checking the copy..."
    sf=$(sudo find "$src" -type f | wc -l);  df_=$(sudo find "$dst" -type f | wc -l)
    ss=$(sudo du -sb --apparent-size "$src" | cut -f1); ds=$(sudo du -sb --apparent-size "$dst" | cut -f1)
    if [ "$sf" = "$df_" ] && [ "$ss" = "$ds" ]; then
        ok "Copy verified: $df_ files, $((ds/1024/1024)) MB - identical"
    else
        fail "Copy doesn't match (files $sf vs $df_, bytes $ss vs $ds). Nothing was switched; the original is untouched. Send this report to Claude."
    fi

    echo "  5/6  Pointing $name to Vault..."
    if grep -q "^$key=" "$envf" 2>/dev/null; then
        sed -i "s|^$key=.*|$key=$dst|" "$envf"
    else
        echo "$key=$dst" >> "$envf"
    fi
    ok "$stack/.env now uses $dst"

    echo "  6/6  Starting $name again..."
    (cd "$REPO/$stack" && docker compose up -d >/dev/null 2>&1) && ok "$name started" || warn "$name didn't start - run: cd ~/elcaciquedeck/$stack && docker compose up -d"

    old="$(dirname "$src")/_old-$(basename "$src")-moved-$STAMP"
    sudo mv "$src" "$old" && ok "Old copy kept as: $old"
done

step "Testing"
wait_for "http://127.0.0.1:8000" 120 && ok "CaciqueDocs answers" || warn "CaciqueDocs not answering yet (give it a minute)"
wait_for "http://127.0.0.1:2283" 180 && ok "CaciquePhotos answers" || warn "CaciquePhotos not answering yet (give it a minute)"

finish
cat <<EOT

 CHECK BEFORE DELETING ANYTHING:
  1. Open CaciqueDocs and CaciquePhotos - your documents and photos should all be there.
  2. Use them for a few days.
  3. Then (and only then) delete the old copies on Library to free the space:
       sudo rm -rf $LIBRARY/Vault/_old-paperless-moved-$STAMP
       sudo rm -rf $LIBRARY/Photos/_old-immich-moved-$STAMP

 See both drives any time:  bash ~/elcaciquedeck/tools/drives.sh

EOT
