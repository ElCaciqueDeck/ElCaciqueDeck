#!/usr/bin/env bash
# ElCaciqueDeck - put Library and Vault back on the right drives (after an install that mixed them up)
#
#   bash ~/elcaciquedeck/tools/fix-drives.sh --check   (only SHOWS what it would do; changes nothing)
#   bash ~/elcaciquedeck/tools/fix-drives.sh           (does it, after you type "yes")
#
# The mix-up it repairs: the installer saw only the Vault drive, so it used
#   Library = /media/<you>/Vault        and   Vault = /media/<you>/Vault/Vault  (a folder)
# It fixes it to
#   Library = /media/<you>/Library      and   Vault = /media/<you>/Vault
#
#   1. Stops every server
#   2. Vault apps:   Vault/Vault/<app>  ->  Vault/<app>   (same drive: an instant rename)
#      If an older copy (e.g. from the ThinkPad) is already there, it's set aside in Vault/_old-<date>/ (nothing deleted)
#   3. Library apps: Vault/{Kiwix,Arcade,Cameras,Movies,Shows,Music} -> Library/  (copies; never overwrites a file
#      already on Library; the copy on the Vault drive is removed only after the copy succeeds)
#   4. Rewrites the paths in the settings (.env files, Jellyfin's library links, Syncthing) and cacique.conf
#   5. Starts everything again and shows the status
# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
CHECK=0; [ "$1" = "--check" ] && CHECK=1
start_report "fix-drives"
L="${FIX_L:-/media/$USER/Library}"; V="${FIX_V:-/media/$USER/Vault}"; STAMP="$(date +%Y-%m-%d_%H%M)"
do_() { if [ "$CHECK" = 1 ]; then echo "  would run: $*"; else "$@"; fi; }

step "1/5  Checks"
if [ -z "$FIX_TEST" ]; then
    mountpoint -q "$L" && ok "Library drive open at $L" || fail "The Library drive isn't open at $L (see docs: fstab step)"
    mountpoint -q "$V" && ok "Vault drive open at $V" || fail "The Vault drive isn't open at $V"
    SL="$(findmnt -no SOURCE "$L")"; SV="$(findmnt -no SOURCE "$V")"
    info "Library is $SL, Vault is $SV"
    [ -n "$SL" ] && [ "$SL" != "$SV" ] || fail "Library and Vault look like the same drive ($SL / $SV). Send a photo of: df -h $L $V"
fi
info "Now:  LIBRARY=$LIBRARY   VAULT=$VAULT"
if [ "$LIBRARY" = "$L" ] && [ "$VAULT" = "$V" ]; then ok "Settings already correct - nothing to fix"; finish; exit 0; fi
if [ "$CHECK" = 0 ]; then
    echo; read -r -p "  Move the app folders to the right drives now? Type yes: " A; [ "$A" = "yes" ] || fail "Nothing changed."
    sudo -v || fail "This needs your password."
    [ -n "$FIX_TEST" ] || bash "$REPO/stop-all.sh" >/dev/null 2>&1; ok "All servers stopped"
fi

step "2/5  Vault apps -> the Vault drive"
move_vault() {   # move_vault <folder inside Vault/Vault> <same place on the Vault drive>
    local from="$1" to="$2" item name
    for item in "$from"/* "$from"/.[!.]*; do
        [ -e "$item" ] || continue
        name="$(basename "$item")"
        # Photos holds the family's own pictures too: only the app's folder inside it is moved, nothing set aside
        if [ "$name" = "Photos" ] && [ -d "$to/Photos" ]; then move_vault "$item" "$to/Photos"; do_ rmdir "$item" 2>/dev/null; continue; fi
        if [ -e "$to/$name" ]; then
            do_ sudo mkdir -p "$V/_old-$STAMP"
            do_ sudo mv "$to/$name" "$V/_old-$STAMP/$name" && info "older Vault${to#$V}/$name set aside in Vault/_old-$STAMP/"
        fi
        do_ sudo mv "$item" "$to/$name" && ok "Vault${to#$V}/$name"
    done
}
# Where the mixed-up install put the Vault apps: Vault/Vault, or Library/Vault when the Library drive had been
# opened under the name Vault (a wrong /etc/fstab line). mv works across drives (it copies, then removes).
VSRC=""
[ -d "$V/Vault" ] && VSRC="$V/Vault"
[ -z "$VSRC" ] && [ -d "$L/Vault" ] && VSRC="$L/Vault"
if [ -n "$VSRC" ]; then
    info "Vault apps found in: $VSRC"
    move_vault "$VSRC" "$V"
    do_ rmdir "$VSRC" 2>/dev/null
else
    info "no misplaced Vault folder"
fi

step "3/5  Library apps -> the Library drive"
for name in Kiwix Arcade Cameras Movies Shows Music; do
    s="$V/$name"; d="$L/$name"
    [ -d "$s" ] || continue
    if [ -z "$(ls -A "$s" 2>/dev/null)" ]; then do_ rmdir "$s"; info "Vault/$name was empty (removed)"; continue; fi
    do_ sudo mkdir -p "$d"
    if [ "$CHECK" = 1 ]; then echo "  would copy: $s -> $d (no overwrite), then remove $s"; continue; fi
    if sudo cp -a -n "$s/." "$d/"; then sudo rm -rf "$s"; ok "Library/$name"; else warn "Could not copy $name - left on Vault"; fi
done
do_ sudo chown "$USER:$USER" "$L" "$V"

step "4/5  Settings"
# order matters: first Vault/Vault -> Vault, then Vault/<library folder> -> Library/<folder>
FILES="$(ls "$REPO"/*/.env 2>/dev/null; grep -rlI "$V" "$DATA" "$HOME/.var/app/org.jellyfin.JellyfinServer" \
         "$HOME/.local/state/syncthing" "$HOME/.config/syncthing" 2>/dev/null | grep -v '/reports/')"
for f in $FILES; do
    grep -q "$V" "$f" 2>/dev/null || continue
    if [ "$CHECK" = 1 ]; then echo "  would update paths in: $f"; continue; fi
    sed -i -e "s#$V/Vault#$V#g" -e "s#$V/\(Kiwix\|Arcade\|Cameras\|Movies\|Shows\|Music\)#$L/\1#g" "$f" && ok "updated: $f"
done
if [ "$CHECK" = 1 ]; then
    echo "  would set in $CACIQUE_CONF:  LIBRARY=$L  VAULT=$V  VAULT_IS_FOLDER=0"
else
    sed -i -e "s#^LIBRARY=.*#LIBRARY=$L#" -e "s#^VAULT=.*#VAULT=$V#" -e "s#^VAULT_IS_FOLDER=.*#VAULT_IS_FOLDER=0#" "$CACIQUE_CONF"
    ok "cacique.conf: Library=$L  Vault=$V"
fi

step "5/5  Start again"
if [ "$CHECK" = 1 ]; then
    echo; echo "  CHECK ONLY - nothing was changed. To do it:  bash ~/elcaciquedeck/tools/fix-drives.sh"
else
    [ -n "$FIX_TEST" ] || bash "$REPO/start-all.sh"
fi
finish
