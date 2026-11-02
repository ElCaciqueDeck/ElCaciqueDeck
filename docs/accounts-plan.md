# 👨‍👩‍👧 ElCaciqueDeck — Family Accounts Plan

> **Status: BUILT (Nov 2026).** `accounts/` + `vaultwarden/`. *Construido.*

## Decisions / Decisiones
| Decision | Choice |
|---|---|
| Shared account | **Familia** — tap to enter, **no password**, **view only** |
| Movie limit for Familia | **PG** (blocks PG-13 and up) |
| Personal accounts | One per adult: private photos/documents, can **upload** from their phone, can share albums |
| Admin | **El Cacique** — an independent admin account in every app; whoever manages the Home Lab uses it. Every person (the owner included) is a regular adult |
| Guest account | **Invitado** — movies up to **PG-13**, the **Familia Abierta** photo slideshow, the Arcade (no login) |
| Passwords | **CaciqueVault** (Vaultwarden, self-hosted Bitwarden): each adult's own vault, + El Cacique's vault for the server logins |
| Language | Bilingual (Spanish + English) |
| Single sign-on (one login for all apps) | Later, on the rig (**Pocket ID** simple, or **Authentik** powerful) |

## Per app / Por aplicación
| App | Familia | Personal | Notes |
|---|---|---|---|
| CaciqueFlix (Jellyfin) | Profile with no password, **max rating PG**, only Movies/Series/Anime libraries chosen | Own profile, all libraries | Parental control by rating needs correct movie info (scan) |
| CaciquePhotos (Immich) | — (no shared login) | Own private library + phone backup; **shared albums** for family | |
| CaciqueDocs (Paperless) | — | Own documents private; a "Familia" group for shared ones | |
| CaciqueArcade (RomM) | **Viewer** role | Viewer or Editor | |
| CaciqueHome (Home Assistant) | — | Regular user (lights, no settings) | |
| CaciqueLibrary (Kiwix) | Open | Open | Add kid-friendly books (**Vikidia**, **Wikipedia for Schools**) for the Familia profile; full Wikipedia includes adult topics |
| Cacique front page | Open | Open | Directory only |

## Privacy rules / Reglas
- Names and passwords are entered **on the laptop** by a setup script; they are **never** stored on GitHub.
- Each adult's photos and documents are private unless they share them.

## As built / Cómo quedó
| App | El Cacique | Adults | Familia | Invitado |
|---|---|---|---|---|
| CaciqueFlix | admin, hidden from the TV picker | own profile | tap, no password, **PG**, unrated movies hidden | tap, no password, **PG-13**, unrated hidden |
| CaciquePhotos | admin, owns **Familia Abierta** | own private library, can add to Familia Abierta | slideshow link (no login) | slideshow link (no login) |
| CaciqueDocs | superuser | own private documents (group **Adultos**) | — | — |
| CaciqueArcade | admin | own login | play, no login (**kiosk mode**) | play, no login (kiosk mode) |
| CaciqueHome | admin | regular user, home network only | — | — |
| CaciqueVault | own vault (server logins) | own vault | — | — |

- People list: `~/elcaciquedeck-data/accounts/people.txt` (on the laptop only) — `accounts/people.sh add <login> <nickname>`.
- Create/refresh: `accounts/create-accounts.sh` (safe to re-run; asks "whose account is this?" for the admin logins
  used today so nobody gets a duplicate; never deletes, resets or demotes).
- Starter passwords: one per adult (word-word-word-00), on a card in `~/elcaciquedeck-data/accounts/cards/`;
  El Cacique gets a different strong password per app, ready to import into CaciqueVault. Delete the files with
  `people.sh forget-passwords` once saved.
- Wrong answer to "whose account is this?": `accounts/fix-owners.sh` lists the older accounts in each app,
  lets you say whose each one is, and offers to delete an extra account made by mistake (only if it was
  never used, and only when you type y). Then it makes anything missing and rewrites the cards.
- Removing admin rights from today's admin accounts is done by hand, after El Cacique is tested.

## ▶️ Pick up here
Single sign-on (Pocket ID / Authentik) on the rig; kid-friendly Kiwix books for Familia.
