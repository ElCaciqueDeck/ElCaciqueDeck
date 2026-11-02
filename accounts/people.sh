#!/usr/bin/env bash
# ElCaciqueDeck - the list of people who get accounts
#
# The list lives ONLY on this laptop: ~/elcaciquedeck-data/accounts/people.txt
# (names never go to GitHub). Three accounts are always there:
#   elcacique  "El Cacique"  admin   - the Home Lab's own administrator (whoever manages the lab uses it)
#   familia    "Familia"     family  - tap to enter, no password, movies up to PG
#   invitado   "Invitado"    guest   - visitors: movies up to PG-13, Familia Abierta photos, the Arcade
#
#   bash ~/elcaciquedeck/accounts/people.sh add maria Mari         # an adult: login name, then nickname
#   bash ~/elcaciquedeck/accounts/people.sh add pedro            # an adult with no nickname
#   bash ~/elcaciquedeck/accounts/people.sh list
#   bash ~/elcaciquedeck/accounts/people.sh remove pedro         # only from the list (accounts stay)
#   bash ~/elcaciquedeck/accounts/people.sh forget-passwords     # delete the starter-password files

ACC="$HOME/elcaciquedeck-data/accounts"
LIST="$ACC/people.txt"
mkdir -p "$ACC" && chmod 700 "$ACC"

if [ ! -f "$LIST" ]; then
    cat > "$LIST" <<'EOF'
# ElCaciqueDeck - people with accounts (stays on this laptop)
# login|nickname|type   (type: admin, adult, family, guest)
elcacique|El Cacique|admin
familia|Familia|family
invitado|Invitado|guest
EOF
    chmod 600 "$LIST"
fi

case "$1" in
    add)
        login="$(echo "$2" | tr '[:upper:]' '[:lower:]')"
        if ! echo "$login" | grep -qE '^[a-z][a-z0-9]{1,30}$'; then
            echo "  Login names: letters and numbers only, no spaces or accents (example: maria)"; exit 1
        fi
        nick="${3:-}"
        [ -n "$nick" ] || nick="$(echo "${login:0:1}" | tr '[:lower:]' '[:upper:]')${login:1}"
        if grep -q "^$login|" "$LIST"; then
            echo "  $login is already on the list"
        else
            echo "$login|$nick|adult" >> "$LIST"
            echo "  Added: $login (shows as \"$nick\")"
        fi ;;
    remove)
        case "$2" in elcacique|familia|invitado) echo "  $2 is a built-in account and stays on the list"; exit 1 ;; esac
        if grep -q "^$2|" "$LIST"; then sed -i "/^$2|/d" "$LIST"; echo "  Removed $2 from the list (their accounts were NOT deleted)"
        else echo "  $2 is not on the list"; fi ;;
    list|"")
        echo
        printf "  %-12s %-14s %s\n" "LOGIN" "NICKNAME" "TYPE"
        grep -v '^#' "$LIST" | while IFS='|' read -r l n t; do printf "  %-12s %-14s %s\n" "$l" "$n" "$t"; done
        echo ;;
    forget-passwords)
        rm -f "$ACC"/passwords.json "$ACC"/for-vaultwarden-import.csv
        rm -rf "$ACC/cards"
        echo "  Starter passwords deleted from this laptop (make sure they're saved in CaciqueVault first)." ;;
    *)
        echo "  Use: add <login> [nickname] | remove <login> | list | forget-passwords"; exit 1 ;;
esac
