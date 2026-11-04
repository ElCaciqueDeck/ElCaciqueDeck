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
VAULT="/media/$USER/Vault"
CACIQUE_LEVEL=2
# shellcheck disable=SC1091
[ -f "$HOME/elcaciquedeck-data/cacique.conf" ] && . "$HOME/elcaciquedeck-data/cacique.conf"
RUN="$REPO/reports/run"
mkdir -p "$RUN"

up() {   # true if something answers on the port (even with an error - we only avoid starting it twice)
    if command -v curl >/dev/null; then [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 3 "http://127.0.0.1:$1")" != "000" ]
    else (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; fi
}

echo
echo "  ELCACIQUEDECK · starting servers"
echo "  ---------------------------------"

if [ -d "$LIBRARY/Kiwix" ]; then
    echo "  Library drive: connected   (media, games, encyclopedia)"
else
    echo "  Library drive: NOT connected - click 'Library' in the Files app, then run this again."
    echo "  (Servers that need it - Library, Flix, Arcade - may not work until then.)"
fi
if mountpoint -q "$VAULT" 2>/dev/null || { { [ "$CACIQUE_LEVEL" = "1" ] || [ "$VAULT_IS_FOLDER" = "1" ]; } && [ -d "$VAULT" ]; }; then
    echo "  Vault drive:   connected   (documents, photos, backups)"
    PDIR="$(grep -sE '^PAPERLESS_DIR=' "$REPO/paperless/.env" | tail -1 | cut -d= -f2- | tr -d '"'"'")"
    if [ -n "$PDIR" ] && [ -d "$PDIR" ] && [ -n "$(find "$PDIR" -maxdepth 2 \( ! -uid 1000 -o ! -gid 1000 \) -print -quit 2>/dev/null)" ]; then
        echo "  WARNING: some CaciqueDocs files aren't owned by 1000 (this causes Error 500)."
        echo "           Fix:  bash ~/elcaciquedeck/tools/fix-docs.sh"
    fi
elif grep -qs "$VAULT" "$REPO/paperless/.env" "$REPO/immich/.env"; then
    echo "  Vault drive:   NOT connected - click 'Vault' in the Files app, then run this again."
    echo "  (CaciqueDocs and CaciquePhotos live on Vault and won't start correctly without it.)"
    echo "  Stopping here so they don't start with an empty drive."
    exit 1
fi
echo

# --- non-Docker servers --------------------------------------------------
if up 8080; then
    echo "  CaciqueLibrary already running"
elif find "$LIBRARY/Kiwix" -maxdepth 4 -name '*.zim' 2>/dev/null | grep -q .; then
    # every encyclopedia file in Kiwix, also inside sub-folders (backups often keep their own folder)
    mapfile -t ZIMS < <(find "$LIBRARY/Kiwix" -maxdepth 4 -name '*.zim' -size +0 2>/dev/null | sort)
    nohup kiwix-serve --port 8080 "${ZIMS[@]}" >"$RUN/kiwix.log" 2>&1 &
    echo "  CaciqueLibrary starting with ${#ZIMS[@]} book(s)..."
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
start_stack arcade        "CaciqueArcade" ".env"
start_stack vaultwarden   "CaciqueVault"  ".env"
start_stack calendar      "CaciqueCalendar" ".env"
start_stack finanzas      "CaciqueFinanzas" ".env"
start_stack office        "CaciqueOffice" ".env"
start_stack cameras       "CaciqueCams"   ".env"
start_stack guide         "CaciqueGuía (AI engine)" ".env"
[ -f "$REPO/homepage/.env" ] && bash "$REPO/homepage/make-live-config.sh" >/dev/null
start_stack homepage      "Cacique"       ".env"

# --- programs that are not in Docker, added by the installer --------------
if [ -f "$REPO/guide/.env" ] && ! up 8070; then
    nohup python3 "$REPO/guide/caciqueguia.py" >"$RUN/guide.log" 2>&1 &
    echo "  CaciqueGuía (chat page) starting..."
fi
if [ -f "$REPO/finanzas/.env" ] && ! up 8075; then
    nohup python3 "$REPO/finanzas/caciquefinanzas.py" >"$RUN/finanzas.log" 2>&1 &
    echo "  CaciqueFinanzas coach starting..."
fi
if command -v syncthing >/dev/null && [ -f "$HOME/elcaciquedeck-data/sync.enabled" ] && ! up 8384; then
    nohup syncthing serve --no-browser --gui-address=0.0.0.0:8384 >"$RUN/syncthing.log" 2>&1 &
    echo "  CaciqueSync starting..."
fi

# --- status -------------------------------------------------------------
echo
echo "  Waiting for everything to wake up..."
sleep 20
bash "$REPO/status.sh"

# write what happened into the logbook (CaciqueGuía reads it)
python3 "$REPO/tools/logbook.py" add start-all info "start-all.sh ran" 2>/dev/null
python3 "$REPO/tools/logbook.py" collect >/dev/null 2>&1 &
