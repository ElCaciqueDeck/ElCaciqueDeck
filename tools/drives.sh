#!/usr/bin/env bash
# ElCaciqueDeck - show both drives: connected?, space, and what's on each
#
#   bash ~/elcaciquedeck/tools/drives.sh
#
#   Library = media, games, encyclopedia (can be re-downloaded or re-ripped)
#   Vault   = documents, family photos, backups (irreplaceable)

show_drive() {   # show_drive <name> <purpose>
    local name="$1" purpose="$2" path="/media/$USER/$1"
    echo
    if mountpoint -q "$path" 2>/dev/null; then
        df -h "$path" | awk -v n="$name" -v p="$purpose" 'NR==2 {
            printf "  %-8s CONNECTED   %s used of %s (%s)   %s free\n           %s\n", n, $3, $2, $5, $4, p }'
        local fs; fs="$(findmnt -no FSTYPE "$path")"
        [ "$fs" != "ext4" ] && echo "           note: format is $fs (ext4 recommended)"
        echo "           ----------------------------------------"
        # size of each top-level folder, biggest first
        sudo -n true 2>/dev/null && SUDO="sudo" || SUDO=""
        $SUDO du -sh "$path"/*/ 2>/dev/null | sort -rh | head -12 | \
            awk -v base="$path/" '{ sub(base, "", $2); sub("/$", "", $2); printf "           %-8s %s\n", $1, $2 }'
    else
        echo "  $name     NOT CONNECTED  - plug it in and click '$name' in the Files app"
        echo "           ($purpose)"
    fi
}

echo
echo "  ELCACIQUEDECK · DRIVES"
echo "  ======================"
show_drive "Library" "Media, games, encyclopedia (replaceable)"
show_drive "Vault"   "Documents, family photos, backups (irreplaceable)"
echo
echo "  (Folder sizes of protected app data show fully if you run: sudo -v  first)"
echo
