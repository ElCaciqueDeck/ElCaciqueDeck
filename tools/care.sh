#!/usr/bin/env bash
# ElCaciqueDeck - the server's check-up (run it once a week, like checking the oil)
#
#   bash ~/elcaciquedeck/tools/care.sh          CHECK-UP: only looks and tells you what it found (changes nothing)
#   bash ~/elcaciquedeck/tools/care.sh --fix    applies the safe fixes it recommends (asks for your password)
#
# What it looks at:
#   1. Battery   - a laptop that is always plugged in should hold its charge near 60% ("conservation mode"),
#                  so the battery lasts for years and doesn't swell
#   2. Space     - the computer's own disk, the two drives, and how big the apps' log files have grown
#   3. Drives    - each drive's own health report (SMART): the earliest warning before a drive fails
#   4. Updates   - Ubuntu's security fixes installing by themselves
#   5. Firewall  - on or off (only reported; turned on later, with the network plan)
#   6. Backup    - how long since tools/backup.sh last ran
#
# --fix does only this: turns on conservation mode, installs the drive-health tool, limits the apps' log files
# (10 MB x 3 each), and turns on automatic security updates. It never touches your data or the apps' settings.
# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
start_report "care"
FIX=0; [ "$1" = "--fix" ] && FIX=1
TODO=0
need() { warn "$*"; TODO=$((TODO+1)); }
[ "$FIX" = 1 ] && { sudo -v || fail "This needs your password."; }

step "1/6  Battery"
BAT="$(ls -d /sys/class/power_supply/BAT* 2>/dev/null | head -1)"
if [ -n "$BAT" ]; then
    NOW="$(cat "$BAT/capacity" 2>/dev/null)"
    FULL="$(cat "$BAT/energy_full" 2>/dev/null || cat "$BAT/charge_full" 2>/dev/null)"
    DESIGN="$(cat "$BAT/energy_full_design" 2>/dev/null || cat "$BAT/charge_full_design" 2>/dev/null)"
    [ -n "$FULL" ] && [ -n "$DESIGN" ] && [ "$DESIGN" -gt 0 ] && HEALTH=$(( FULL * 100 / DESIGN ))
    ok "Charge now: ${NOW:-?}%   Battery health: ${HEALTH:-?}% of what it held when new"
    CONS="$(ls /sys/bus/platform/drivers/ideapad_acpi/*/conservation_mode 2>/dev/null | head -1)"
    if [ -z "$CONS" ]; then
        info "This computer doesn't offer conservation mode (fine on a desktop or mini PC)"
    elif [ "$(cat "$CONS")" = "1" ]; then
        ok "Conservation mode is ON (holds the charge near 60%: best for a laptop that is always plugged in)"
    elif [ "$FIX" = 1 ]; then
        echo 1 | sudo tee "$CONS" >/dev/null && ok "Conservation mode turned ON (the charge will settle near 60% over the next days: that's correct)" \
            || warn "Could not turn on conservation mode"
    else
        need "Conservation mode is OFF: always plugged in at ~100% wears the battery (and can make it swell). --fix turns it on"
    fi
else
    info "No battery (desktop or mini PC)"
fi

step "2/6  Space"
space() {   # space <path> <name>
    [ -d "$1" ] || return
    local pct free
    pct="$(df --output=pcent "$1" | tail -1 | tr -dc '0-9')"; free="$(df -h --output=avail "$1" | tail -1 | tr -d ' ')"
    if [ "${pct:-0}" -ge 90 ]; then need "$2 is ${pct}% full (only $free free): make room soon"
    elif [ "${pct:-0}" -ge 80 ]; then warn "$2 is ${pct}% full ($free free)"
    else ok "$2: ${pct}% used, $free free"; fi
}
space / "This computer's disk"
mountpoint -q "$LIBRARY" 2>/dev/null && space "$LIBRARY" "Library drive"
mountpoint -q "$VAULT" 2>/dev/null && space "$VAULT" "Vault drive"
if command -v docker >/dev/null; then
    LOGS_MB="$(sudo -n du -cm /var/lib/docker/containers/*/*-json.log 2>/dev/null | tail -1 | awk '{print $1}')"
    [ -n "$LOGS_MB" ] && info "The apps' log files take ${LOGS_MB} MB"
    if grep -qs '"max-size"' /etc/docker/daemon.json; then
        ok "The apps' log files are limited (they can't fill the disk)"
    elif [ "$FIX" = 1 ]; then
        sudo python3 - <<'PY' && ok "Log files limited to 10 MB x 3 per app (applies to apps the next time they are created)" || warn "Could not write /etc/docker/daemon.json"
import json, os
p = "/etc/docker/daemon.json"
try:
    cfg = json.load(open(p))
except FileNotFoundError:
    cfg = {}
if os.path.exists(p):
    open(p + ".before-elcacique", "w").write(open(p).read())
cfg.setdefault("log-driver", "json-file")
cfg.setdefault("log-opts", {}).update({"max-size": "10m", "max-file": "3"})
json.dump(cfg, open(p, "w"), indent=2)
PY
        info "To apply it now (when nobody is using the apps): stop-all.sh, then  sudo systemctl restart docker , then start-all.sh --light"
    else
        need "The apps' log files have no size limit: over months they can fill the disk. --fix limits them"
    fi
fi

step "3/6  Drive health"
if command -v smartctl >/dev/null; then
    for dev in $(lsblk -dno NAME,TYPE | awk '$2=="disk"{print $1}'); do
        OUT="$(sudo -n smartctl -H -d auto "/dev/$dev" 2>/dev/null || sudo -n smartctl -H -d sat "/dev/$dev" 2>/dev/null)"
        MODEL="$(lsblk -dno MODEL "/dev/$dev" | sed 's/ *$//')"
        if echo "$OUT" | grep -qiE "PASSED|OK"; then ok "/dev/$dev (${MODEL:-drive}): health PASSED"
        elif echo "$OUT" | grep -qi "FAILED"; then need "/dev/$dev (${MODEL:-drive}): health FAILING - back up now and replace this drive"
        else info "/dev/$dev (${MODEL:-drive}): no health report (some USB cases hide it; run with your password: sudo smartctl -H /dev/$dev)"; fi
    done
elif [ "$FIX" = 1 ]; then
    sudo apt-get install -y smartmontools >/dev/null 2>&1 && ok "Drive-health tool installed (run the check-up again to see each drive)" \
        || warn "Could not install smartmontools (internet?)"
else
    need "The drive-health tool isn't installed: you'd get no early warning before a drive fails. --fix installs it"
fi

step "4/6  Security updates"
if grep -qs 'Unattended-Upgrade "1"' /etc/apt/apt.conf.d/20auto-upgrades; then
    ok "Ubuntu installs its security fixes by itself"
elif [ "$FIX" = 1 ]; then
    sudo apt-get install -y unattended-upgrades >/dev/null 2>&1
    printf 'APT::Periodic::Update-Package-Lists "1";\nAPT::Periodic::Unattended-Upgrade "1";\n' | sudo tee /etc/apt/apt.conf.d/20auto-upgrades >/dev/null \
        && ok "Automatic security updates turned on (Ubuntu's own fixes only; the Cacique apps are not touched)" || warn "Could not turn them on"
else
    need "Automatic security updates are off. --fix turns them on (Ubuntu's fixes only)"
fi
[ -f /var/run/reboot-required ] && warn "Ubuntu wants a restart to finish an update (when convenient: sudo systemctl reboot -i, then start-all.sh --light)"

step "5/6  Firewall"
if sudo -n ufw status 2>/dev/null | grep -q "Status: active"; then ok "Firewall is on"
else info "Firewall is off or needs your password to check. It gets turned on with the network plan (ER605), with every app's door listed first"; fi

step "6/6  Backup"
if [ -f "$DATA/last-backup" ]; then
    DAYS=$(( ( $(date +%s) - $(cat "$DATA/last-backup") ) / 86400 ))
    if [ "$DAYS" -le 7 ]; then ok "Last backup: $DAYS day(s) ago"
    else need "Last backup was $DAYS days ago. Run: bash ~/elcaciquedeck/tools/backup.sh"; fi
else
    need "No backup has ever been made. Run: bash ~/elcaciquedeck/tools/backup.sh --check"
fi

echo
if [ "$FIX" = 1 ]; then echo "  Fixes applied. Run the check-up again any time:  bash ~/elcaciquedeck/tools/care.sh"
elif [ "$TODO" -gt 0 ]; then echo "  $TODO thing(s) need attention. The safe ones are fixed with:  bash ~/elcaciquedeck/tools/care.sh --fix"
else echo "  Everything looks cared for."; fi
finish
