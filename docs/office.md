# 📝 CaciqueOffice — LibreOffice in the browser, files kept at home

> **Status: BUILT (Nov 2026), waiting for a computer with ~12 GB+ of memory.** On smaller computers the installer
> greys it out and downloads nothing; it stays here, ready for the Lab rig.
> *LibreOffice en el navegador, con cuenta y archivos privados para cada adulto.*

## What it is
| Part | Role | Where |
|---|---|---|
| **Nextcloud** | Logins, each person's private files, sharing between family members, phone/desktop sync apps | `https://<laptop>:5445` |
| **Collabora Online (CODE)** | LibreOffice's own online version: Writer, Calc, Impress open right in the browser; opens/saves Word, Excel, PowerPoint and ODF | `https://<laptop>:5446` (used by Nextcloud) |
| **Postgres + Redis** | Database and speed for Nextcloud | inside the laptop only |
| **"Enviar a CaciqueDocs" folder** | Every account sees it; a PDF saved there is archived by CaciqueDocs (Paperless) automatically | = Paperless' consume folder |

Accounts: the installer's admin (ElCaciqueAdmin, in the *admin* group) and every adult, made by `accounts/create-accounts.sh`
like the other apps. Familia/Invitado don't get Office accounts. Files and database live on the **Vault** drive (`Vault/office`).

## Why it is gated
Nextcloud + the LibreOffice engine use ~3 GB of memory on their own. With ~6 GB (IdeaPad S340) the rest of the Home Lab would
starve, so `installer/engine.py` (`APP_MIN_RAM = {"office": 11.5}`) leaves it unticked and greyed out. "Show everything" on the
apps page, or `CQ_FORCE=1 bash office/setup-office.sh`, installs it anyway.

## Using it
1. Once per device: install the Cacique certificate (`http://<laptop>/cacique-ca.crt`).
2. Open `https://<laptop>:5445`, log in, **+ New → Document / Spreadsheet / Presentation**, or upload a .docx/.xlsx/.pptx and click it.
3. To archive something in CaciqueDocs: save/download it as **PDF** and put the PDF in **Enviar a CaciqueDocs**
   (Paperless takes it, reads it and files it; the folder empties itself).

## Not tested yet
Built and checked here (installer gating, accounts, Caddy config); the containers run for the first time on a 12 GB+ computer.
If the editor doesn't open documents, check `docker logs caciqueoffice-editor` and the Nextcloud admin page *Office*.
