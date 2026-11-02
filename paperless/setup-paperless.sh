#!/usr/bin/env bash
# ElCaciqueDeck - CaciqueDocs (Paperless-ngx) setup
#
#   bash ~/elcaciquedeck/paperless/setup-paperless.sh
#
# Safe to run again (keeps your settings and documents).
#   1. Checks Docker and the Vault (documents are irreplaceable: they live on Vault)
#   2. Writes the private settings (.env) with a random secret key
#   3. Makes the folders, owned by user 1000 (what Paperless runs as - wrong owners = Error 500)
#   4. Downloads and starts CaciqueDocs
# The installer passes the admin name/password in CQ_ADMIN_USER / CQ_ADMIN_PW (first start creates it).

# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
DIR="$REPO/paperless"
start_report "paperless-setup"

step "1/4  Checks"
need_docker
need_vault
PDIR="$VAULT/paperless"

step "2/4  Private settings (.env)"
if [ -f "$DIR/.env" ]; then
    ok ".env already exists - keeping it"
    PDIR="$(grep -E '^PAPERLESS_DIR=' "$DIR/.env" | cut -d= -f2- || true)"; PDIR="${PDIR:-$VAULT/paperless}"
else
    {
        echo "# CaciqueDocs private settings - stays on this laptop"
        echo "PAPERLESS_DIR=$PDIR"
        echo "PAPERLESS_SECRET_KEY=$(random_password)$(random_password)"
        if [ -n "$CQ_ADMIN_USER" ] && [ -n "$CQ_ADMIN_PW" ]; then
            echo "PAPERLESS_ADMIN_USER=$CQ_ADMIN_USER"
            echo "PAPERLESS_ADMIN_PASSWORD=$CQ_ADMIN_PW"
            echo "PAPERLESS_ADMIN_MAIL=$(echo "$CQ_ADMIN_USER" | tr '[:upper:]' '[:lower:]')@cacique.home"
        fi
    } > "$DIR/.env"
    chmod 600 "$DIR/.env"
    ok "Created .env"
fi

step "3/4  Folders (owned by user 1000)"
mkdir -p "$PDIR"/{data,media,export,consume} 2>/dev/null || sudo mkdir -p "$PDIR"/{data,media,export,consume}
sudo chown -R 1000:1000 "$PDIR" && ok "Documents folder: $PDIR"
open_port 8000 "CaciqueDocs"

step "4/4  Downloading and starting (first time: a few minutes)"
cd "$DIR" || fail "Can't open $DIR"
docker compose pull || fail "Download failed. Check the internet and run this again."
docker compose up -d || fail "Could not start CaciqueDocs."
if wait_for "http://127.0.0.1:8000" 240; then ok "CaciqueDocs answers on port 8000"; else warn "Not answering yet (first start can take a few minutes)"; fi
finish
