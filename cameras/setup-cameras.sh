#!/usr/bin/env bash
# ElCaciqueDeck - CaciqueCams (Frigate) setup
#   bash ~/elcaciquedeck/cameras/setup-cameras.sh
# Video lives on the Library drive (replaceable, big). Settings live on this laptop.
# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
DIR="$REPO/cameras"
start_report "cameras-setup"
step "1/3  Checks"
need_docker
need_library
[ "$CACIQUE_LEVEL" = "1" ] && warn "Laptop level: recordings will fill this disk. Cameras are meant for the Deck level (a second drive)."
CONF="$DATA/cameras"; MEDIA="$LIBRARY/Cameras"
step "2/3  Folders and settings"
mkdir -p "$CONF" "$MEDIA"
[ -f "$CONF/config.yml" ] || cp "$DIR/config.template.yml" "$CONF/config.yml"
[ -f "$DIR/.env" ] || printf '# CaciqueCams settings - stays on this laptop\nCAMS_CONFIG=%s\nCAMS_MEDIA=%s\n' "$CONF" "$MEDIA" > "$DIR/.env"
ok "Recordings (deleted after 90 days): $MEDIA"
open_port 8971 "CaciqueCams"
open_port 8554 "CaciqueCams streams"
step "3/3  Downloading and starting (first time: a few minutes, about 1.5 GB)"
cd "$DIR" || fail "Can't open $DIR"
docker compose pull || fail "Download failed. Check the internet and run this again."
docker compose up -d || fail "Could not start CaciqueCams."
if wait_for "http://127.0.0.1:5000/api/version" 180; then ok "CaciqueCams is running"; else warn "Not answering yet"; fi
finish
