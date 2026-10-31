#!/usr/bin/env bash
# ElCaciqueDeck - CaciquePhotos (Immich) setup
#
# Run once:   bash ~/elcaciquedeck/immich/setup-immich.sh
#
#   1. Checks Docker and the Library drive
#   2. Creates the photo folder (Library drive) and database folder (laptop disk)
#   3. Writes the private settings file (.env) with a random database password
#   4. Decides if the laptop has enough memory for smart search and face recognition
#   5. Downloads and starts Immich, tests it, and saves a report
#
# Safe to run again: it never replaces your password or deletes photos.

# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
DIR="$REPO/immich"
start_report "immich-setup"

step "1/5  Checks"
need_docker
need_library
IP="$(laptop_ip)"; [ -n "$IP" ] && ok "Laptop number: $IP" || warn "Could not find the laptop number"

step "2/5  Folders"
PHOTOS="$LIBRARY/Photos/immich"
DB="$DATA/immich-postgres"
mkdir -p "$PHOTOS" && ok "Photos will be stored in: $PHOTOS" || fail "Could not create $PHOTOS"
mkdir -p "$DB" && ok "Database will be stored in: $DB" || fail "Could not create $DB"

step "3/5  Private settings (.env)"
RAM="$(total_ram_gb)"
ROOT_DISK="$(lsblk -no PKNAME "$(findmnt -no SOURCE /)" 2>/dev/null | head -1)"
ROTA="$(lsblk -dno ROTA "/dev/$ROOT_DISK" 2>/dev/null | tr -d ' ')"
STORAGE="SSD"; [ "$ROTA" = "1" ] && STORAGE="HDD"
if awk "BEGIN{exit !($RAM >= 7.5)}"; then
    PROFILE="ml"; MLON="true"
    ok "Memory: ${RAM} GB - smart search and face recognition ON"
else
    PROFILE=""; MLON="false"
    warn "Memory: ${RAM} GB - smart search and face recognition OFF to keep the laptop fast (photos and backup still work)"
fi
if [ -f "$DIR/.env" ]; then
    ok ".env already exists - keeping your database password"
    sed -i "s|^COMPOSE_PROFILES=.*|COMPOSE_PROFILES=$PROFILE|; s|^IMMICH_MACHINE_LEARNING_ENABLED=.*|IMMICH_MACHINE_LEARNING_ENABLED=$MLON|" "$DIR/.env"
else
    cat > "$DIR/.env" <<ENV
# CaciquePhotos private settings - stays on this laptop, never uploaded
UPLOAD_LOCATION=$PHOTOS
DB_DATA_LOCATION=$DB
TZ=America/Puerto_Rico
IMMICH_VERSION=v3
DB_PASSWORD=$(random_password)
DB_USERNAME=postgres
DB_DATABASE_NAME=immich
DB_STORAGE_TYPE=$STORAGE
COMPOSE_PROFILES=$PROFILE
IMMICH_MACHINE_LEARNING_ENABLED=$MLON
ENV
    chmod 600 "$DIR/.env"
    ok "Created .env (database on $STORAGE, random password)"
fi

step "4/5  Downloading and starting (first time: several minutes, about 2-3 GB)"
cd "$DIR" || fail "Can't open $DIR"
docker compose pull || fail "Download failed. Check the internet and run this again."
docker compose up -d || fail "Could not start Immich."
ok "Containers started"

step "5/5  Testing (Immich takes 1-2 minutes to wake up the first time)"
# On the very first start the database needs a few minutes to set itself up.
# If the server gave up waiting for it, start it again (up to 3 tries).
for try in 1 2 3; do
    wait_for "http://127.0.0.1:2283" 120 && break
    if ! docker ps --format '{{.Names}}' | grep -qx immich_server; then
        info "Server stopped while the database was getting ready - starting it again (try $try of 3)"
        docker compose up -d >/dev/null 2>&1
    fi
done
if wait_for "http://127.0.0.1:2283" 10; then
    ok "CaciquePhotos answers on port 2283"
else
    warn "Not answering yet. Check in a minute with: docker compose logs immich-server"
fi
for c in immich_server immich_postgres immich_redis; do
    docker ps --format '{{.Names}}' | grep -qx "$c" && ok "$c running" || warn "$c not running"
done
[ "$PROFILE" = "ml" ] && { docker ps --format '{{.Names}}' | grep -qx immich_machine_learning && ok "immich_machine_learning running" || warn "immich_machine_learning not running"; }

finish
cat <<EOT

 NEXT (one time only):
  1. Open  http://${IP:-<laptop number>}:2283   and click "Getting Started"
  2. Create the admin account (this is YOUR account; add family members later
     under Administration -> Users)
  3. Phones: install the "Immich" app, server address:  http://${IP:-<laptop number>}:2283
     then turn on Backup in the app (cloud icon, top right)

EOT
