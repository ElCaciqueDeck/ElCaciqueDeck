#!/usr/bin/env bash
# ElCaciqueDeck - back up what can't be replaced (the family's photos, documents, stories, passwords and settings)
#
#   bash ~/elcaciquedeck/tools/backup.sh --check    only SHOW what it would copy and whether there's room
#   bash ~/elcaciquedeck/tools/backup.sh            make the backup (safe to run any time, as often as you like)
#
# Two copies on two different drives, so one broken drive never takes the family's memories:
#   1. Settings: this server's private settings, passwords and keys (~/elcaciquedeck-data and the .env files)
#      -> a dated, private file in  Vault/Backups/server-settings/   (the last 8 are kept)
#   2. Databases: a clean copy of CaciquePhotos' database (only when CaciquePhotos is running)
#      -> Vault/Backups/databases/
#   3. The whole Vault drive (photos, documents, Raíces, password safe, the two folders above)
#      -> Library/Backups/vault-copy/   (an exact copy)
#      Files you changed or deleted since the last backup are kept 60 days in Library/Backups/vault-changed/<date>/
#
# It never deletes anything from the Vault. Best moment: at night, when nobody is uploading photos.
# A real 3-2-1 backup also needs one copy OUTSIDE the house (see docs/AUDIT-2026-11-16.md).
# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
start_report "backup"
CHECK=0; [ "$1" = "--check" ] && CHECK=1
STAMP="$(date +%Y-%m-%d_%H%M)"
DEST="$LIBRARY/Backups"

step "1/4  The two drives"
mountpoint -q "$VAULT" 2>/dev/null || fail "The Vault drive isn't connected. Nothing to back up from."
mountpoint -q "$LIBRARY" 2>/dev/null || fail "The Library drive isn't connected. The copy goes there."
SRC_DEV="$(findmnt -no SOURCE "$VAULT")"; DST_DEV="$(findmnt -no SOURCE "$LIBRARY")"
[ "${SRC_DEV%[0-9]*}" != "${DST_DEV%[0-9]*}" ] || fail "Vault and Library are on the SAME drive ($SRC_DEV). A backup needs two different drives."
ok "Vault ($SRC_DEV) and Library ($DST_DEV) are two different drives"
USED_KB="$(sudo du -sk --exclude='lost+found' "$VAULT" 2>/dev/null | awk '{print $1}')"
HAVE_KB="$(sudo du -sk "$DEST/vault-copy" 2>/dev/null | awk '{print $1}')"; HAVE_KB="${HAVE_KB:-0}"
FREE_KB="$(df -k --output=avail "$LIBRARY" | tail -1 | tr -d ' ')"
NEED_KB=$(( USED_KB > HAVE_KB ? USED_KB - HAVE_KB : 0 ))
info "Vault holds $(( USED_KB / 1048576 )) GB; the copy already has $(( HAVE_KB / 1048576 )) GB; Library has $(( FREE_KB / 1048576 )) GB free"
[ "$FREE_KB" -gt $(( NEED_KB + ${BACKUP_SPARE_KB:-5242880} )) ] || fail "Not enough room on Library for the copy (needs about $(( NEED_KB / 1048576 )) GB more + 5 GB spare)."
ok "There's room for the copy"

step "2/4  Settings, passwords and keys"
SET="$VAULT/Backups/server-settings"
if [ "$CHECK" = 1 ]; then
    echo "  would save: ~/elcaciquedeck-data (without the live database files) + every .env  ->  $SET/settings-$STAMP.tar.gz"
else
    sudo mkdir -p "$SET" && sudo chown "$USER" "$VAULT/Backups" "$SET" && chmod 700 "$SET"
    ENVS="$(cd "$REPO" && ls ./*/.env 2>/dev/null | sed 's|^\./||')"
    [ -d "$REPO/adguard/conf" ] && ENVS="$ENVS adguard/conf"
    # shellcheck disable=SC2086
    sudo tar -czf "$SET/settings-$STAMP.tar.gz" --exclude='elcaciquedeck-data/immich-postgres' \
            -C "$HOME" elcaciquedeck-data -C "$REPO" $ENVS 2>/dev/null
    if [ $? -le 1 ] && [ -s "$SET/settings-$STAMP.tar.gz" ]; then      # 1 = a file changed while it was read: fine
        sudo chown "$USER" "$SET/settings-$STAMP.tar.gz"; chmod 600 "$SET/settings-$STAMP.tar.gz"
        ok "Saved: Backups/server-settings/settings-$STAMP.tar.gz ($(du -h "$SET/settings-$STAMP.tar.gz" | cut -f1))"
        ls -1t "$SET"/settings-*.tar.gz 2>/dev/null | tail -n +9 | xargs -r rm -f      # keep the last 8
    else
        warn "Could not save the settings file"
    fi
fi

step "3/4  Databases"
DBS="$VAULT/Backups/databases"
if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx immich_postgres; then
    if [ "$CHECK" = 1 ]; then
        echo "  would save: CaciquePhotos' database  ->  $DBS/immich-$STAMP.sql.gz"
    else
        sudo mkdir -p "$DBS" && sudo chown "$USER" "$DBS" && chmod 700 "$DBS"
        if docker exec immich_postgres pg_dumpall --clean --if-exists -U postgres 2>/dev/null | gzip > "$DBS/immich-$STAMP.sql.gz" \
                && [ "$(stat -c %s "$DBS/immich-$STAMP.sql.gz" 2>/dev/null || echo 0)" -gt 1000 ]; then
            chmod 600 "$DBS/immich-$STAMP.sql.gz"
            ok "CaciquePhotos database saved ($(du -h "$DBS/immich-$STAMP.sql.gz" | cut -f1))"
            ls -1t "$DBS"/immich-*.sql.gz 2>/dev/null | tail -n +9 | xargs -r rm -f
        else
            rm -f "$DBS/immich-$STAMP.sql.gz"; warn "Could not save CaciquePhotos' database (the photos themselves are still copied)"
        fi
    fi
else
    info "CaciquePhotos isn't running: its database is skipped this time (the photos are still copied)"
fi

step "4/4  The Vault drive -> Library/Backups/vault-copy"
if [ "$CHECK" = 1 ]; then
    echo "  would copy everything new or changed (nothing is deleted from the Vault):"
    sudo rsync -a --delete --dry-run --stats --exclude='lost+found' "$VAULT/" "$DEST/vault-copy/" 2>/dev/null \
        | grep -E "Number of regular files transferred|Total transferred file size|Number of deleted files" | sed 's/^/    /'
    echo; echo "  CHECK ONLY - nothing was copied. To do it:  bash ~/elcaciquedeck/tools/backup.sh"
    finish; exit 0
fi
sudo mkdir -p "$DEST/vault-copy" "$DEST/vault-changed"
if sudo rsync -a --delete --backup --backup-dir="$DEST/vault-changed/$STAMP" --exclude='lost+found' \
        --info=stats1 "$VAULT/" "$DEST/vault-copy/" | tail -3 | sed 's/^/    /'; then
    ok "Copy finished: Library/Backups/vault-copy is the same as the Vault"
    sudo find "$DEST/vault-changed" -mindepth 1 -maxdepth 1 -type d -mtime +60 -exec rm -rf {} + 2>/dev/null
    sudo rmdir "$DEST/vault-changed/$STAMP" 2>/dev/null     # empty = nothing changed or deleted this time
    date +%s > "$DATA/last-backup"
    ok "Older versions of changed/deleted files are kept 60 days in Library/Backups/vault-changed"
else
    fail "The copy stopped with an error (see above). Run it again; it continues where it stopped."
fi
python3 "$REPO/tools/logbook.py" add backup info "backup.sh finished" 2>/dev/null
echo
echo "  Two copies now exist on two drives. For fire, theft or a hurricane, keep a third copy outside the house."
finish
