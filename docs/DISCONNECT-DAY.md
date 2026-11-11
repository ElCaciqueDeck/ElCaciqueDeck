# 🔒 Disconnect Day · el día de la desconexión

> The final goal: after 90 days of uptime/downtime data, the full story recorded in CaciqueAcademy and the coding
> games, El Cacique runs, maintains and diagnoses itself. A local AI guide (CaciqueGuía, offline) helps any family
> member or the expert user fix problems. Nobody (no outside AI, no other person) can change the project or log in.
> *Meta final: El Cacique vive solo, con su propia guía, sin conexiones de afuera.*

## Checklist (do these in order, on that day)
1. **Last pull:** `cd ~/elcaciquedeck && git pull` on every server. The repo is public; pulling never needs a login.
2. **Revoke outside access on GitHub** (a security key protects *logins*, not connections that were already approved):
   - Settings → Applications → **Installed GitHub Apps**: remove the Claude app (or limit it to no repositories).
   - Settings → Applications → **Authorized OAuth Apps**: revoke anything not needed.
   - Settings → Developer settings → **Personal access tokens**: delete all.
   - Settings → **SSH and GPG keys**: remove keys you no longer use.
   - Settings → **Sessions**: sign out every other session.
3. **Repo safety:** Settings → Branches → protect `main` (no force-push, no deletion). Optional: archive the repo (read-only).
4. **Account lock:** GitHub + Proton both on password + **Ledger Nano S security key (with its PIN)**. Recovery codes,
   recovery phrase and the 24 words on paper in the safe, kept apart from the Ledger if possible.
5. **Offline copy:** keep a copy of the whole repo on the Library drive (`git bundle create`), so El Cacique can be
   reinstalled without the internet.
6. **Forget:** ask the AI assistant to delete what it remembers about this project.
