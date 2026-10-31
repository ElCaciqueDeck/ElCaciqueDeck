#!/usr/bin/env bash
# ElCaciqueDeck - which servers are up right now
#   bash ~/elcaciquedeck/status.sh

up()   { curl -s -o /dev/null --max-time 2 "http://127.0.0.1:$1" 2>/dev/null || (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }
line() { printf "  %-16s %-6s %s\n" "$1" "$2" "$3"; }
IP="$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}')"

echo
line "SERVER" "STATUS" "ADDRESS"
line "------" "------" "-------"
for s in "Cacique:80" "CaciqueLibrary:8080" "CaciqueFlix:8096" "CaciqueDocs:8000" "CaciquePhotos:2283" \
         "CaciqueHome:8123" "CaciqueDash:8888" "CaciqueGuard:3000"; do
    name="${s%%:*}"; port="${s#*:}"
    addr="http://${IP:-<laptop>}"; [ "$port" != "80" ] && addr="$addr:$port"
    if up "$port"; then line "$name" "UP" "$addr"; else line "$name" "--" "not running (or not set up yet)"; fi
done
echo
echo "  Family front door:  http://${IP:-<laptop number>}"
echo
