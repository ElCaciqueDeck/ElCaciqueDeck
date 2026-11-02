#!/usr/bin/env bash
# ElCaciqueDeck - CaciqueCalendar (Radicale) setup
#   bash ~/elcaciquedeck/calendar/setup-calendar.sh
# Calendars live on the Vault (irreplaceable). Accounts are made by accounts/create-accounts.sh.
# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
DIR="$REPO/calendar"
start_report "calendar-setup"
step "1/3  Checks"
need_docker
need_vault
CAL="$VAULT/calendar"
step "2/3  Folders and settings"
mkdir -p "$CAL/collections" && touch "$CAL/users" && chmod 644 "$CAL/users"   # readable by the calendar program (only password codes inside)
[ -f "$DIR/.env" ] || printf '# CaciqueCalendar settings - stays on this laptop\nCALENDAR_DIR=%s\n' "$CAL" > "$DIR/.env"
ok "Calendars stored in: $CAL"
open_port 5232 "CaciqueCalendar"
step "3/3  Downloading and starting"
cd "$DIR" || fail "Can't open $DIR"
docker compose pull || fail "Download failed. Check the internet and run this again."
docker compose up -d || fail "Could not start CaciqueCalendar."
if wait_for "http://127.0.0.1:5232" 60; then ok "CaciqueCalendar answers on port 5232"; else warn "Not answering yet"; fi
finish
