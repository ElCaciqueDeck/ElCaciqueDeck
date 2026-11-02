# 👨‍👩‍👧 ElCaciqueDeck — Family Accounts Plan

> **Status: DECIDED, NOT BUILT YET.** *Decidido, todavía no construido.*

## Decisions / Decisiones
| Decision | Choice |
|---|---|
| Shared account | **Familia** — tap to enter, **no password**, **view only** |
| Movie limit for Familia | **PG** (blocks PG-13 and up) |
| Personal accounts | One per adult: private photos/documents, can **upload** from their phone, can share albums |
| Admin | One (the owner) |
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

## ▶️ Pick up here
Tell Claude: *"Let's build the family accounts from docs/accounts-plan.md"* and give the list of adults' first names.
