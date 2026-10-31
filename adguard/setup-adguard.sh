#!/usr/bin/env bash
# ElCaciqueDeck - CaciqueGuard setup (AdGuard Home + Caddy easy names)
#
# Run once:   bash ~/elcaciquedeck/adguard/setup-adguard.sh
#
# What it does (it asks for your password for the system steps):
#   1. Checks Docker works
#   2. Frees port 53 (Ubuntu's built-in DNS helper normally holds it)
#   3. Makes the Cacique names work on this laptop itself
#   4. Opens the firewall for DNS (53), names (80) and the AdGuard page (3000)
#   5. Downloads and starts AdGuard Home and Caddy
#   6. Tests everything and saves a report you can share
#
# Safe to run again: every step checks first and skips what is already done.

DIR="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$DIR/.." && pwd)"
REPORT_DIR="$REPO/reports"
mkdir -p "$REPORT_DIR"
REPORT="$REPORT_DIR/adguard-setup-$(date +%Y-%m-%d_%H%M).txt"
exec > >(tee "$REPORT") 2>&1

NAMES="cacique.home caciquelibrary.home caciqueflix.home caciquedocs.home caciquedash.home caciqueguard.home caciquephotos.home caciquehome.home caciquearcade.home"
OK=0; WARN=0
ok()   { echo "  [ OK ]  $*"; OK=$((OK+1)); }
warn() { echo "  [WARN]  $*"; WARN=$((WARN+1)); }
fail() { echo "  [FAIL]  $*"; echo; echo "Stopped. Report saved to: $REPORT"; exit 1; }
step() { echo; echo "== $* =="; }

echo "ElCaciqueDeck - CaciqueGuard setup"
echo "Date: $(date)   Host: $(hostname)"

# ---------------------------------------------------------------- 1
step "1/6  Checking Docker"
command -v docker >/dev/null || fail "Docker is not installed."
docker info >/dev/null 2>&1 || fail "Docker is installed but you can't use it. Fix: sudo usermod -aG docker \$USER, then reboot."
docker compose version >/dev/null 2>&1 || fail "'docker compose' is missing. Fix: sudo apt install -y docker-compose-v2"
ok "Docker and Docker Compose work"
if ! command -v curl >/dev/null; then
    echo "  Installing curl (used for the tests)..."
    sudo apt-get install -y curl >/dev/null 2>&1 && ok "curl installed" || warn "Could not install curl; tests will be skipped"
fi

LAPTOP_IP="$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src"){print $(i+1); exit}}')"
[ -n "$LAPTOP_IP" ] && ok "Laptop number (IP): $LAPTOP_IP" || warn "Could not find the laptop's IP (is the network cable in?)"

# ---------------------------------------------------------------- 2
step "2/6  Freeing port 53 for AdGuard"
if sudo ss -lunp 2>/dev/null | grep -qE '127\.0\.0\.5[34][%a-z]*:53[[:space:]]'; then
    echo "  Ubuntu's DNS helper is using port 53. Moving it out of the way (internet keeps working)."
    sudo mkdir -p /etc/systemd/resolved.conf.d
    printf '[Resolve]\nDNSStubListener=no\n' | sudo tee /etc/systemd/resolved.conf.d/caciqueguard.conf >/dev/null
    if [ ! -e /etc/resolv.conf.before-caciqueguard ]; then
        sudo cp -P /etc/resolv.conf /etc/resolv.conf.before-caciqueguard
    fi
    sudo ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf
    sudo systemctl restart systemd-resolved
    sleep 2
    ok "Port 53 freed"
else
    ok "Port 53 already free"
fi
if getent hosts github.com >/dev/null 2>&1; then
    ok "Laptop can still look up websites"
else
    warn "Laptop can't look up websites right now. Undo with: sudo rm /etc/systemd/resolved.conf.d/caciqueguard.conf && sudo ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf && sudo systemctl restart systemd-resolved"
fi
for P in 80 3000; do
    USER_OF_PORT="$(sudo ss -ltnp 2>/dev/null | awk -v p=":$P" '$4 ~ p"$" {print $NF; exit}')"
    if [ -n "$USER_OF_PORT" ] && ! echo "$USER_OF_PORT" | grep -qE 'caddy|AdGuardHome'; then
        warn "Port $P is already used by: $USER_OF_PORT"
    else
        ok "Port $P available"
    fi
done

# ---------------------------------------------------------------- 3
step "3/6  Cacique names on this laptop"
if grep -q '# >>> elcaciquedeck names >>>' /etc/hosts; then
    ok "Names already set up on this laptop"
else
    {
        echo ""
        echo "# >>> elcaciquedeck names >>>"
        echo "127.0.0.1 $NAMES"
        echo "# <<< elcaciquedeck names <<<"
    } | sudo tee -a /etc/hosts >/dev/null
    ok "Added the Cacique names to /etc/hosts"
fi

# ---------------------------------------------------------------- 4
step "4/6  Firewall"
if sudo ufw status 2>/dev/null | grep -q "Status: active"; then
    sudo ufw allow 53/udp  >/dev/null
    sudo ufw allow 53/tcp  >/dev/null
    sudo ufw allow 80/tcp  >/dev/null
    sudo ufw allow 3000/tcp >/dev/null
    ok "Opened 53 (DNS), 80 (names), 3000 (AdGuard page)"
else
    ok "Firewall is off, nothing to open"
fi

# ---------------------------------------------------------------- 5
step "5/6  Downloading and starting AdGuard Home + Caddy (first time takes a few minutes)"
mkdir -p "$DIR/work" "$DIR/conf"
cd "$DIR" || fail "Can't open $DIR"
docker compose pull || fail "Download failed. Check the internet connection and run the script again."
docker compose up -d || fail "Could not start the containers."
ok "Containers started"

# ---------------------------------------------------------------- 6
step "6/6  Testing"
sleep 5
docker ps --format '{{.Names}}' | grep -q '^caciqueguard$' && ok "CaciqueGuard (AdGuard) is running" || warn "CaciqueGuard is not running. See: docker compose logs adguard"
docker ps --format '{{.Names}}' | grep -q '^caciquenames$'  && ok "CaciqueNames (Caddy) is running"   || warn "Caddy is not running. See: docker compose logs caddy"
if curl -s -o /dev/null --max-time 5 http://127.0.0.1:3000; then
    ok "AdGuard page answers on port 3000"
else
    warn "AdGuard page not answering yet on port 3000 (give it a minute)"
fi
CODE="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://cacique.home/)"
[ "$CODE" = "200" ] && ok "http://cacique.home works on this laptop" || warn "http://cacique.home answered $CODE"
for pair in "caciquelibrary.home:8080:Kiwix" "caciqueflix.home:8096:Jellyfin" "caciquedocs.home:8000:Paperless" "caciquedash.home:8888:Dashboard"; do
    N="${pair%%:*}"; rest="${pair#*:}"; P="${rest%%:*}"; S="${rest#*:}"
    if curl -s -o /dev/null --max-time 3 "http://127.0.0.1:$P"; then
        C="$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://$N/")"
        case "$C" in 2*|3*) ok "$N -> $S works" ;; *) warn "$N -> $S answered $C" ;; esac
    else
        echo "  [ -- ]  $N -> $S is not running right now (start it, then the name works)"
    fi
done

echo
echo "=================================================================="
echo " Done: $OK OK, $WARN warnings.   Report: $REPORT"
echo "=================================================================="
echo
echo " FAMILY FRONT PAGE (works on every device, no settings):  http://${LAPTOP_IP:-<laptop number>}"
echo
echo " NEXT - finish in the browser (one time only):"
echo "  1. Open  http://localhost:3000"
echo "  2. Click 'Get Started'"
echo "  3. Admin Web Interface: 'All interfaces', port  3000   <-- NOT 80"
echo "     DNS server:          'All interfaces', port  53"
echo "  4. Create your CaciqueGuard username and password"
echo "  5. After logging in:  Filters -> DNS rewrites -> Add DNS rewrite"
echo "        Domain:  *.home"
echo "        Answer:  ${LAPTOP_IP:-<laptop number>}"
echo
