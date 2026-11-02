#!/usr/bin/env bash
# ElCaciqueDeck - apply the latest update after "git pull"
#
#   cd ~/elcaciquedeck && git pull
#   bash ~/elcaciquedeck/tools/update.sh
#
# Safe to run any time (it only refreshes; it never deletes your data):
#   1. Installs the newest Field Manual into CaciqueLibrary
#   2. Opens the firewall for new servers and adds new Cacique names to this laptop
#   3. Reloads the name helper (Caddy) - this also serves CaciqueAcademy
#   4. Refreshes the Cacique front page (buttons, icons, drives)
#   5. Restarts CaciqueLibrary and CaciqueDash so they use the new files
#   6. Shows the status of everything and saves a report

# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
start_report "update"
RUN="$REPO/reports/run"; mkdir -p "$RUN"
NAMES="cacique.home caciquelibrary.home caciqueflix.home caciquedocs.home caciquedash.home caciqueguard.home caciquephotos.home caciquehome.home caciquearcade.home caciqueacademy.home"

step "1/6  Field Manual -> CaciqueLibrary"
need_library
ZIM="$REPO/manual/dist/elcaciquedeck-manual.zim"
DEST="$LIBRARY/Kiwix/elcaciquedeck-manual.zim"
if [ ! -f "$ZIM" ]; then
    warn "Manual file not found in the repo (run git pull first)"
elif cmp -s "$ZIM" "$DEST"; then
    ok "Manual already up to date"
else
    cp -f "$ZIM" "$DEST" && ok "Manual installed: $DEST" || warn "Could not copy the manual to Library/Kiwix"
fi

step "2/6  Firewall and names"
sudo -v || fail "This needs your password."
open_port 8095 "CaciqueAcademy"
if grep -q '# >>> elcaciquedeck names >>>' /etc/hosts; then
    for n in $NAMES; do
        if ! grep -qw "$n" /etc/hosts; then
            sudo sed -i "/# >>> elcaciquedeck names >>>/{n;s/\$/ $n/}" /etc/hosts && ok "Added name $n"
        fi
    done
    ok "Cacique names on this laptop are complete"
else
    info "Names not set up yet on this laptop (run adguard/setup-adguard.sh once)"
fi

step "3/6  Name helper (Caddy) + CaciqueAcademy"
if [ -d "$REPO/adguard/conf" ] || docker ps -a --format '{{.Names}}' | grep -qx caciquenames; then
    (cd "$REPO/adguard" && docker compose up -d --force-recreate caddy >"$RUN/caddy.log" 2>&1) \
        && ok "Caddy reloaded" || warn "Caddy reload failed - see $RUN/caddy.log"
else
    warn "CaciqueGuard isn't set up yet - run adguard/setup-adguard.sh first"
fi

step "4/6  Cacique front page"
if [ -f "$REPO/homepage/.env" ]; then
    bash "$REPO/homepage/setup-homepage.sh" >"$RUN/homepage-refresh.log" 2>&1 \
        && ok "Front page refreshed (buttons, icons, drives)" || warn "Front page refresh had problems - see $RUN/homepage-refresh.log"
else
    info "Front page not set up yet (homepage/setup-homepage.sh)"
fi

step "5/6  Restarting CaciqueLibrary and CaciqueDash"
pkill -x kiwix-serve 2>/dev/null; sleep 1
if ls "$LIBRARY"/Kiwix/*.zim >/dev/null 2>&1; then
    nohup kiwix-serve --port 8080 "$LIBRARY"/Kiwix/*.zim >"$RUN/kiwix.log" 2>&1 &
    ok "CaciqueLibrary restarted (now includes the manual)"
fi
pkill -f "[c]aciquedash.py" 2>/dev/null; sleep 1
nohup python3 "$REPO/caciquedash.py" >"$RUN/dash.log" 2>&1 &
ok "CaciqueDash restarted (new health checks)"

step "6/6  Status (waiting 15 seconds for everything to answer)"
sleep 15
bash "$REPO/status.sh"

finish
IP="$(laptop_ip)"
cat <<EOT

 NEW:
  🎓 CaciqueAcademy:   http://${IP:-<laptop number>}:8095
  📘 Field Manual:     http://${IP:-<laptop number>}:8080/content/elcaciquedeck-manual/
     (also on the Cacique front page, under "Aprender · Learn")

EOT
