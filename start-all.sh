#!/usr/bin/env bash
# ElCaciqueDeck - start every server with one command
#
#   bash ~/elcaciquedeck/start-all.sh
#
# Starts only what's set up and not already running, then shows a status table.
# Servers keep running after you close the Terminal. Stop them all with:
#   bash ~/elcaciquedeck/stop-all.sh
#
# Logs of the non-Docker servers: ~/elcaciquedeck/reports/run/

REPO="$(cd "$(dirname "$0")" && pwd)"
LIBRARY="/media/$USER/Library"
RUN="$REPO/reports/run"
mkdir -p "$RUN"

up()   { curl -s -o /dev/null --max-time 2 "http://127.0.0.1:$1" 2>/dev/null || (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

echo
echo "  ELCACIQUEDECK · starting servers"
echo "  ---------------------------------"

if [ -d "$LIBRARY/Kiwix" ]; then
    echo "  Library drive: connected"
else
    echo "  Library drive: NOT connected - click 'Library' in the Files app, then run this again."
    echo "  (Servers that need it - Library, Flix, Docs, Photos - may not work until then.)"
fi
echo

# --- non-Docker servers --------------------------------------------------
if up 8080; then
    echo "  CaciqueLibrary already running"
elif ls "$LIBRARY"/Kiwix/*.zim >/dev/null 2>&1; then
    nohup kiwix-serve --port 8080 "$LIBRARY"/Kiwix/*.zim >"$RUN/kiwix.log" 2>&1 &
    echo "  CaciqueLibrary starting..."
fi

if up 8096; then
    echo "  CaciqueFlix already running"
elif flatpak info org.jellyfin.JellyfinServer >/dev/null 2>&1; then
    nohup flatpak run org.jellyfin.JellyfinServer >"$RUN/jellyfin.log" 2>&1 &
    echo "  CaciqueFlix starting..."
fi

if up 8888; then
    echo "  CaciqueDash already running"
else
    nohup python3 "$REPO/caciquedash.py" >"$RUN/dash.log" 2>&1 &
    echo "  CaciqueDash starting (logging every minute)..."
fi

# --- Docker servers (only the ones that have been set up) ---------------
start_stack() {   # start_stack <folder> <name> <marker file that proves it was set up>
    if [ -e "$REPO/$1/$3" ]; then
        (cd "$REPO/$1" && docker compose up -d >"$RUN/$1.log" 2>&1) \
            && echo "  $2 started" || echo "  $2 FAILED - see $RUN/$1.log"
    fi
}
start_stack paperless     "CaciqueDocs"   ".env"
start_stack adguard       "CaciqueGuard"  "conf"
start_stack immich        "CaciquePhotos" ".env"
start_stack homeassistant "CaciqueHome"   ".env"
start_stack homepage      "Cacique"       ".env"

# --- status -------------------------------------------------------------
echo
echo "  Waiting for everything to wake up..."
sleep 20
bash "$REPO/status.sh"
