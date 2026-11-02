#!/usr/bin/env bash
# ElCaciqueDeck - choose the ONE admin name + password used in every Cacique app
#
#   bash ~/elcaciquedeck/accounts/set-admin.sh ElCaciqueAdmin
#
# It asks for the password twice (it won't show while you type) and saves it only on this laptop.
# Then run:  bash ~/elcaciquedeck/accounts/create-accounts.sh   (it makes that admin in every app)
python3 "$(dirname "$0")/create_accounts.py" --set-admin "${1:-ElCaciqueAdmin}"
