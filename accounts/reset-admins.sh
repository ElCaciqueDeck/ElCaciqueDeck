#!/usr/bin/env bash
# ElCaciqueDeck - get admin access to every app WITHOUT the old passwords, then make all the accounts
#
#   bash ~/elcaciquedeck/accounts/reset-admins.sh
#
# Uses each app's own recovery tool on this laptop (works only here, never from the network):
#   CaciqueFlix    Jellyfin's "forgot password" PIN (unlocks the account first if it got locked)
#   CaciquePhotos  immich-admin reset-admin-password
#   CaciqueDocs    makes the El Cacique admin directly (your own account is not touched)
#   CaciqueArcade  new password for the admin you pick
#   CaciqueHome    new password for the login you pick (CaciqueHome restarts once)
# Your admin accounts get NEW passwords: they're shown on screen and saved (private) in
# ~/elcaciquedeck-data/accounts/new-admin-passwords.txt. Nothing is deleted.
# Then it makes El Cacique + everyone's accounts (same as create-accounts.sh).

# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
start_report "reset-admins"
python3 "$REPO/accounts/create_accounts.py" --reset-admins "$@"
finish
echo
echo " Your new admin passwords:  cat ~/elcaciquedeck-data/accounts/new-admin-passwords.txt"
echo
