#!/usr/bin/env bash
# ElCaciqueDeck - which servers are up right now
#   bash ~/elcaciquedeck/status.sh

# web answer code from a local port: 200/302 = fine, 500+ = on but broken, 000 = nobody answers
code() {
    if command -v curl >/dev/null; then curl -s -o /dev/null -w '%{http_code}' --max-time 3 "http://127.0.0.1:$1"
    else (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null && echo 200 || echo 000; fi
}
line() { printf "  %-16s %-6s %s\n" "$1" "$2" "$3"; }
IP="$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}')"

echo
line "SERVER" "STATUS" "ADDRESS"
line "------" "------" "-------"
for s in "Cacique:80" "CaciqueLibrary:8080" "CaciqueFlix:8096" "CaciqueDocs:8000" "CaciquePhotos:2283" \
         "CaciqueHome:8123" "CaciqueArcade:8090" "CaciqueAcademy:8095" "CaciqueDash:8888" "CaciqueGuard:3000" "CaciqueVault:8222" \
         "CaciqueCalendar:5232" "CaciqueSync:8384" "CaciqueCams:5000" "CaciqueGuia:8070"; do
    name="${s%%:*}"; port="${s#*:}"
    # the newer apps are only listed once they are installed
    case "$name" in
        CaciqueCalendar) [ -f "$(dirname "$0")/calendar/.env" ] || continue ;;
        CaciqueCams)     [ -f "$(dirname "$0")/cameras/.env" ] || continue ;;
        CaciqueGuia)     [ -f "$(dirname "$0")/guide/.env" ] || continue ;;
        CaciqueSync)     [ -f "$HOME/elcaciquedeck-data/sync.enabled" ] || continue ;;
    esac
    addr="http://${IP:-<laptop>}"; [ "$port" != "80" ] && addr="$addr:$port"
    [ "$port" = "8222" ] && addr="https://${IP:-<laptop>}:8443"   # the safe is only reachable through the secure door
    [ "$port" = "5000" ] && addr="http://${IP:-<laptop>}:8971"    # cameras: the page with login
    c="$(code "$port")"
    if [ "$c" = "000" ]; then line "$name" "--" "not running (or not set up yet)"
    elif [ "$c" -ge 500 ]; then line "$name" "ERROR" "on but failing (code $c) - see the Field Manual, Troubleshooting"
    else line "$name" "UP" "$addr"; fi
done
echo
LIBRARY="/media/$USER/Library"; VAULT="/media/$USER/Vault"; CACIQUE_LEVEL=2
# shellcheck disable=SC1091
[ -f "$HOME/elcaciquedeck-data/cacique.conf" ] && . "$HOME/elcaciquedeck-data/cacique.conf"
for d in Library Vault; do
    p="$LIBRARY"; [ "$d" = "Vault" ] && p="$VAULT"
    if mountpoint -q "$p" 2>/dev/null || { { [ "$CACIQUE_LEVEL" = "1" ] || [ "$VAULT_IS_FOLDER" = "1" ]; } && [ -d "$p" ]; }; then
        df -h "$p" | awk -v n="$d" 'NR==2 {printf "  %-16s %-6s %s used of %s, %s free\n", n" drive", "OK", $3, $2, $4}'
    else
        printf "  %-16s %-6s %s\n" "$d drive" "--" "not connected"
    fi
done
echo
echo "  Family front door:  http://${IP:-<laptop number>}"
echo
