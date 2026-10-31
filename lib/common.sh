#!/usr/bin/env bash
# ElCaciqueDeck - shared helpers for the setup scripts.
# Every script that sources this gets: a saved report, [ OK ]/[WARN]/[FAIL] lines,
# the laptop's number, and a few safe checks.

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC2034  # used by the scripts that source this file
DATA="$HOME/elcaciquedeck-data"          # app data that lives on the laptop's own disk
LIBRARY="/media/$USER/Library"           # the Library drive
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
    ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}'
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

need_library() {
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
