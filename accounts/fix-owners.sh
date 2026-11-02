#!/usr/bin/env bash
# ElCaciqueDeck - fix a wrong answer to "whose account is this?" in create-accounts.sh
#
#   bash ~/elcaciquedeck/accounts/fix-owners.sh
#
# For each app it shows the accounts you had before (like your old admin login) and asks whose each one is.
# Then, if the tool made a second account for someone by mistake, it offers to delete that extra one
# (only if it was never used, and only if you type y). Finally it makes anything missing and
# rewrites the cards. Needs create-accounts.sh to have run once (El Cacique logs in for you).

# shellcheck source=../lib/common.sh
source "$(dirname "$0")/../lib/common.sh"
start_report "fix-owners"
python3 "$REPO/accounts/create_accounts.py" --fix-owners
finish
