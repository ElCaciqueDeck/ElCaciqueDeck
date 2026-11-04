#!/usr/bin/env bash
# ElCaciqueDeck - CaciqueDash always on (the ONE thing that runs by itself, chosen by the owner)
#
#   bash ~/elcaciquedeck/tools/dash-always-on.sh        turn it on (starts now and at every power-on)
#   bash ~/elcaciquedeck/tools/dash-always-on.sh --off  back to normal (only start-all.sh starts it)
#
# Why: the gauges are how you see the Home Lab's health. They must keep running while you stop, update or
# restart the other servers. If the gauges ALSO go dark, the problem is bigger than one app:
# power, the network/Wi-Fi, or the computer itself.
# stop-all.sh never stops it. If it crashes, it restarts itself after 5 seconds.
# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
UNIT=/etc/systemd/system/caciquedash.service
start_report "dash-always-on"

if [ "$1" = "--off" ]; then
    sudo systemctl disable --now caciquedash.service 2>/dev/null
    sudo rm -f "$UNIT" && sudo systemctl daemon-reload
    ok "CaciqueDash is back to normal: start-all.sh starts it, stop-all.sh stops it"
    finish; exit 0
fi

step "CaciqueDash always on"
sudo -v || fail "This needs your password."
sudo tee "$UNIT" >/dev/null <<UNITFILE
[Unit]
Description=ElCaciqueDeck - CaciqueDash gauges (always on)
After=network-online.target
Wants=network-online.target

[Service]
User=$USER
Environment=HOME=$HOME
ExecStart=/usr/bin/python3 $REPO/caciquedash.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNITFILE
pkill -f "[c]aciquedash.py" 2>/dev/null; sleep 1        # the copy start-all.sh started, if any
sudo systemctl daemon-reload
sudo systemctl enable --now caciquedash.service >/dev/null 2>&1 || fail "Could not start the CaciqueDash service"
sleep 3
if wait_for "http://127.0.0.1:8888" 20; then ok "CaciqueDash running: http://$(laptop_ip):8888 (on at every power-on)"
else warn "CaciqueDash did not answer yet. See: systemctl status caciquedash"; fi
finish
