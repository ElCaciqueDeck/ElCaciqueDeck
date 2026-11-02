#!/usr/bin/env bash
# ElCaciqueDeck - take a "photo" of the deck for El Cacique Admin (CaciqueAcademy 2.0)
#
#   bash ~/elcaciquedeck/tools/snapshot.sh
#   bash ~/elcaciquedeck/tools/snapshot.sh --no-screenshots     (faster, no page pictures)
#
# update.sh runs this by itself at the end, so normally you never need to.
# Saved ONLY on this laptop in ~/elcaciquedeck-data/twin/ (never uploaded to GitHub).
# Passwords are masked, Vault shows only folder sizes, no file contents are read.
# Then open:  http://<laptop number>:8095/admin.html

# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
start_report "snapshot"
mkdir -p "$DATA/twin"
step "El Cacique Admin snapshot"
export REPO LIBRARY VAULT TWIN_DIR="$DATA/twin"
if python3 "$REPO/tools/snapshot.py" "$@"; then ok "El Cacique Admin is up to date"
else warn "The snapshot had problems (the real deck is fine)"; fi
finish
echo
IP="$(laptop_ip)"; echo " Open:  http://${IP:-<laptop number>}:8095/admin.html"
