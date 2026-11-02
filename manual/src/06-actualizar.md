---
title_es: Actualizaciones y GitHub
title_en: Updates and GitHub
icon: 🔄
---
<!-- ES -->
## Cómo llegan las mejoras

Todos los programas del Home Lab viven en **GitHub** (`github.com/ElCaciqueDeck/elcaciquedeck`). Es público: **nunca** se suben contraseñas, direcciones de la casa ni listas privadas. Los archivos `.env` (contraseñas) se quedan en la laptop gracias a `.gitignore`.

**Traer la última versión y aplicarla:**

**1.**
```
cd ~/elcaciquedeck && git pull
```
**2.**
```
bash ~/elcaciquedeck/tools/update.sh
```

`update.sh` instala el manual nuevo en CaciqueLibrary, recarga los nombres y la página principal, y deja un reporte.

## Qué hay en la carpeta
| Carpeta | Qué tiene |
|---|---|
| `paperless/ immich/ homeassistant/ arcade/ adguard/ homepage/` | Un servidor Docker cada una |
| `academy/` | El juego CaciqueAcademy |
| `manual/` | Este manual (fuente y archivo `.zim`) |
| `tools/` | Herramientas: discos, mover a Vault, respaldo Arweave, actualizar |
| `docs/` | Planes: red y VLANs, cuentas familiares |
| `reports/` | Reportes de cada instalación (solo en la laptop) |

<!-- EN -->
## How improvements arrive

All the Home Lab programs live on **GitHub** (`github.com/ElCaciqueDeck/elcaciquedeck`). It's public: **never** upload passwords, home addresses or private lists. The `.env` files (passwords) stay on the laptop thanks to `.gitignore`.

**Get the latest version and apply it:**

**1.**
```
cd ~/elcaciquedeck && git pull
```
**2.**
```
bash ~/elcaciquedeck/tools/update.sh
```

`update.sh` installs the new manual into CaciqueLibrary, reloads the names and the front page, and leaves a report.

## What's in the folder
| Folder | What it holds |
|---|---|
| `paperless/ immich/ homeassistant/ arcade/ adguard/ homepage/` | One Docker server each |
| `academy/` | The CaciqueAcademy game |
| `manual/` | This manual (source and `.zim` file) |
| `tools/` | Tools: drives, move to Vault, Arweave backup, update |
| `docs/` | Plans: network and VLANs, family accounts |
| `reports/` | Reports from each setup (on the laptop only) |
