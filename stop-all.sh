#!/usr/bin/env bash
# ElCaciqueDeck - stop every server with one command
#   bash ~/elcaciquedeck/stop-all.sh

REPO="$(cd "$(dirname "$0")" && pwd)"
echo
echo "  ELCACIQUEDECK · stopping servers"
echo "  ---------------------------------"
for d in homepage homeassistant immich adguard paperless; do
    if [ -f "$REPO/$d/docker-compose.yml" ] && (cd "$REPO/$d" && docker compose ps -q 2>/dev/null | grep -q .); then
        (cd "$REPO/$d" && docker compose down >/dev/null 2>&1) && echo "  $d stopped"
    fi
done
pkill -f "[c]aciquedash.py" && echo "  CaciqueDash stopped"
flatpak kill org.jellyfin.JellyfinServer 2>/dev/null && echo "  CaciqueFlix stopped"
pkill -x kiwix-serve && echo "  CaciqueLibrary stopped"
echo
echo "  All stopped. Start again with:  bash ~/elcaciquedeck/start-all.sh"
echo
