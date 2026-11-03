# 💰 CaciqueFinanzas — the family budget + money coach

> **Status: BUILT (Nov 2026), waiting for its first real run on the IdeaPad.**
> *Presupuesto de la familia (Actual Budget) + un coach que avisa y pronostica. Todo se queda en la casa.*

## What it is
| Part | What it does | Where |
|---|---|---|
| **Actual Budget** (open source) | Envelope budget: every category gets a $ limit ("Eating out: $40"). Accounts, transactions, CSV import, reports | `https://<laptop>:5443` |
| **Money coach** (`finanzas/caciquefinanzas.py`) | Year-end forecast at this pace, "what if I save $X/week", over-limit alerts, "times per month" limits, monthly report | `https://<laptop>:5444` |
| **Reading helper** (actual-http-api) | Lets the coach read the budgets; only inside the laptop | `127.0.0.1:5007` |
| **Local AI** (optional, CaciqueGuía's Ollama) | Writes the monthly report and answers questions from the numbers only | — |

Budgets are stored on the **Vault** drive (`Vault/finanzas`). Coach limits: `~/elcaciquedeck-data/finanzas/rules.json`.
The family password: `~/elcaciquedeck-data/accounts/finanzas-password.txt` (keep a copy in CaciqueVault).

## First time (5 minutes)
1. Phones/computers need the Cacique certificate once: `http://<laptop>/cacique-ca.crt` (same as CaciqueVault).
2. Open `https://<laptop>:5443` → type the family password → **Start fresh** → name it (e.g. *Familia*).
3. Add accounts (checking, savings, cards) with today's balance.
4. Make categories and give each a monthly $ limit (Rent, Groceries, Eating out $40, Gas, Baby, Savings…).
5. Each week: import the bank's CSV (or type purchases) and pick a category for each line.
6. Open the coach `https://<laptop>:5444`: forecast, alerts, and set **Máx. veces** (e.g. Eating out: 4).

## How the coach decides
- **Forecast** = cash in on-budget accounts today + average monthly (income − spending) of the last 3 full months × months left in the year.
- **Over limit** = spent more than the category's $ budget, or more purchases than its "max times".
- **Pace warning** = from day 5, if spending speed would pass the limit by >10% at month's end.
- Transfers between your own accounts are ignored; split purchases count in each category.
- It coaches budgeting only. It never recommends investments, loans or financial products.

## Notes
- Actual Budget needs **https** to run in a browser, which is why it only opens through Caddy's secure door.
- One family password (Actual's simple login). A budget can be given its own **encryption password** inside Actual
  for privacy; the coach then can't read that budget (shown with 🔒).
- Automatic bank download is possible later with SimpleFIN (paid, ~$15/year) inside Actual; CSV import is free.
