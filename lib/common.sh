#!/usr/bin/env bash
# ElCaciqueDeck - shared helpers for the setup scripts.
# Every script that sources this gets: a saved report, [ OK ]/[WARN]/[FAIL] lines,
# the laptop's number, and a few safe checks.

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC2034  # used by the scripts that source this file
DATA="$HOME/elcaciquedeck-data"          # app data that lives on the laptop's own disk
LIBRARY="/media/$USER/Library"           # drive 1: media, games, encyclopedia (replaceable)
VAULT="/media/$USER/Vault"               # drive 2: documents, photos, backups (irreplaceable)
CACIQUE_LEVEL=2                          # 1 = Laptop (programs only), 2 = Deck (+ drives), 3 = Lab (the rig)
# The installer saves the choices here (level, where Library and Vault are). Older setups don't have it.
CACIQUE_CONF="$DATA/cacique.conf"
# shellcheck disable=SC1090
[ -f "$CACIQUE_CONF" ] && . "$CACIQUE_CONF"
REPORT_DIR="$REPO/reports"
OK=0; WARN=0

start_report() {   # start_report <name>
    mkdir -p "$REPORT_DIR"
    REPORT="$REPORT_DIR/$1-$(date +%Y-%m-%d_%H%M).txt"
    exec > >(tee "$REPORT") 2>&1
    echo "ElCaciqueDeck - $1"
    echo "Date: $(date)   Host: $(hostname)"
}
ok()   { echo "  [ OK ]  $*"; OK=$((OK+1)); }
warn() { echo "  [WARN]  $*"; WARN=$((WARN+1)); }
info() { echo "  [ -- ]  $*"; }
fail() { echo "  [FAIL]  $*"; echo; echo "Stopped. Report saved to: $REPORT"; exit 1; }
step() { echo; echo "== $* =="; }
finish() {
    echo
    echo "=================================================================="
    echo " Done: $OK OK, $WARN warnings.   Report: $REPORT"
    echo "=================================================================="
}

laptop_ip() {
    # the house address of this computer (Wi-Fi or cable) - never Docker's inside-the-computer networks (172.x)
    ip -4 -o addr show scope global 2>/dev/null | awk '$2 !~ /^(docker|br-|veth|virbr|tailscale|lo)/ {split($4,a,"/"); print a[1]; exit}'
}

need_docker() {
    command -v docker >/dev/null || fail "Docker is not installed."
    docker info >/dev/null 2>&1 || fail "You can't use Docker yet. Fix: sudo usermod -aG docker \$USER, then reboot."
    docker compose version >/dev/null 2>&1 || fail "'docker compose' is missing. Fix: sudo apt install -y docker-compose-v2"
    ok "Docker works"
    if ! command -v curl >/dev/null; then
        sudo apt-get install -y curl >/dev/null 2>&1 && ok "curl installed" || warn "Could not install curl"
    fi
}

drive_ready() {   # drive_ready <path>: a connected drive, or a plain folder on Laptop level / folder setups
    mountpoint -q "$1" 2>/dev/null && return 0
    { [ "$CACIQUE_LEVEL" = "1" ] || [ "$VAULT_IS_FOLDER" = "1" ]; } && [ -d "$1" ]
}

need_vault() {
    if [ "$CACIQUE_LEVEL" = "1" ]; then mkdir -p "$VAULT"; ok "Vault folder (Laptop level, on this disk): $VAULT"; return; fi
    if mountpoint -q "$VAULT" 2>/dev/null || [ "$VAULT_IS_FOLDER" = "1" ] && [ -d "$VAULT" ]; then
        ok "Vault drive is connected"
    else
        fail "The Vault drive isn't connected. Open the Files app, click 'Vault', then run this again."
    fi
}

need_library() {
    if [ "$CACIQUE_LEVEL" = "1" ]; then mkdir -p "$LIBRARY/Kiwix"; ok "Library folder (Laptop level, on this disk): $LIBRARY"; return; fi
    if mountpoint -q "$LIBRARY" 2>/dev/null || [ -d "$LIBRARY/Kiwix" ]; then
        ok "Library drive is connected"
    else
        fail "The Library drive isn't connected. Open the Files app, click 'Library', then run this again."
    fi
}

open_port() {      # open_port <port> <what>
    if sudo ufw status 2>/dev/null | grep -q "Status: active"; then
        sudo ufw allow "$1/tcp" >/dev/null && ok "Firewall open for $2 (port $1)"
    fi
}

random_password() {   # letters and numbers only
    tr -dc 'A-Za-z0-9' </dev/urandom | head -c 32
}

total_ram_gb() {
    awk '/MemTotal/ {printf "%.1f", $2/1048576}' /proc/meminfo
}

wait_for() {       # wait_for <url> <seconds> ; returns 0 when it answers
    local url="$1" secs="$2" i=0
    while [ "$i" -lt "$secs" ]; do
        curl -s -o /dev/null --max-time 3 "$url" && return 0
        sleep 3; i=$((i+3))
    done
    return 1
}
