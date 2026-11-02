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
         "CaciqueHome:8123" "CaciqueArcade:8090" "CaciqueAcademy:8095" "CaciqueDash:8888" "CaciqueGuard:3000" "CaciqueVault:8222"; do
    name="${s%%:*}"; port="${s#*:}"
    addr="http://${IP:-<laptop>}"; [ "$port" != "80" ] && addr="$addr:$port"
    [ "$port" = "8222" ] && addr="https://${IP:-<laptop>}:8443"   # the safe is only reachable through the secure door
    c="$(code "$port")"
    if [ "$c" = "000" ]; then line "$name" "--" "not running (or not set up yet)"
    elif [ "$c" -ge 500 ]; then line "$name" "ERROR" "on but failing (code $c) - see the Field Manual, Troubleshooting"
    else line "$name" "UP" "$addr"; fi
done
echo
for d in Library Vault; do
    if mountpoint -q "/media/$USER/$d" 2>/dev/null; then
        df -h "/media/$USER/$d" | awk -v n="$d" 'NR==2 {printf "  %-16s %-6s %s used of %s, %s free\n", n" drive", "OK", $3, $2, $4}'
    else
        printf "  %-16s %-6s %s\n" "$d drive" "--" "not connected"
    fi
done
echo
echo "  Family front door:  http://${IP:-<laptop number>}"
echo
