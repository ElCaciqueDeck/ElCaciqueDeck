#!/usr/bin/env bash
# El Cacique Home Lab - start here on a fresh Ubuntu computer.
#
# Open the Terminal and type this ONE line:
#   wget -qO- https://raw.githubusercontent.com/ElCaciqueDeck/ElCaciqueDeck/main/install.sh | bash
#
# It downloads El Cacique into ~/elcaciquedeck, adds "El Cacique Setup" to the apps menu,
# and opens the setup window. Everything else is done in that window (no more typing).
# Safe to run again: it only updates.

set -e
REPO_URL="https://github.com/ElCaciqueDeck/ElCaciqueDeck.git"
DIR="$HOME/elcaciquedeck"

echo
echo "  EL CACIQUE HOME LAB - preparing the setup window"
echo "  -------------------------------------------------"
if ! grep -qi ubuntu /etc/os-release 2>/dev/null; then
    echo "  This computer is not running Ubuntu. Install Ubuntu (22.04 or newer) first."; exit 1
fi
echo "  Your computer password is needed to install two small programs (git and the window toolkit)."
sudo apt-get -o DPkg::Lock::Timeout=600 update -q
sudo apt-get -o DPkg::Lock::Timeout=600 install -y -q git python3-tk

if [ -d "$DIR/.git" ]; then
    echo "  Updating $DIR"
    git -C "$DIR" pull --ff-only || echo "  (could not update - using the copy already here)"
else
    git clone "$REPO_URL" "$DIR"
fi

mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/elcaciquedeck-setup.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=El Cacique Setup
Comment=Instalar o cambiar El Cacique Home Lab
Exec=/usr/bin/python3 $DIR/installer/cacique_installer.py
Icon=$DIR/homepage/custom-icons/cacique-emblem.svg
Terminal=false
Categories=Utility;
DESK
echo "  Added \"El Cacique Setup\" to the apps menu."

if [ -n "$DISPLAY" ] || [ -n "$WAYLAND_DISPLAY" ]; then
    echo "  Opening the setup window..."
    nohup /usr/bin/python3 "$DIR/installer/cacique_installer.py" >/dev/null 2>&1 &
else
    echo "  No screen found. Open \"El Cacique Setup\" from the apps menu on the computer's screen."
fi
echo
