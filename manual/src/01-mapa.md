---
title_es: Mapa del sistema
title_en: System map
icon: 🗺️
---
<!-- ES -->
## ¿Qué es ElCaciqueDeck?

Una laptop ThinkPad con **Ubuntu Linux** que funciona como **servidor de la casa**. Sirve películas, fotos, documentos, juegos, una enciclopedia y la casa inteligente a todos los equipos del hogar, **con o sin internet**.

### Las piezas

| Pieza | Qué es | Dónde |
|---|---|---|
| **ThinkPad** (`elcaciquedeck-00`) | El servidor. Siempre encendido, tapa cerrada | En una esquina, conectado por cable |
| **Library** | Disco 1: películas, juegos, enciclopedia (se pueden reemplazar) | `/media/<usuario>/Library` |
| **Vault** | Disco 2: documentos, fotos, respaldos (**irremplazables**) | `/media/<usuario>/Vault` |
| **Deeper Mini** | Bloquea anuncios para toda la casa | Entre el router y la red |
| **GitHub** | Donde viven los programas y este manual | `github.com/ElCaciqueDeck` |

### Los servidores

| Nombre | Programa | Puerto | Para qué |
|---|---|---|---|
| 🧭 Cacique | Homepage | 80 | Página principal con botones a todo |
| 📚 CaciqueLibrary | Kiwix | 8080 | Enciclopedia sin internet (y este manual) |
| 🎬 CaciqueFlix | Jellyfin | 8096 | Películas, series, anime |
| 📄 CaciqueDocs | Paperless-ngx | 8000 | Documentos escaneados |
| 📸 CaciquePhotos | Immich | 2283 | Fotos y videos de la familia |
| 🏠 CaciqueHome | Home Assistant | 8123 | Luces Hue y casa inteligente |
| 🕹️ CaciqueArcade | RomM | 8090 | Juegos clásicos en el navegador |
| 🎓 CaciqueAcademy | (juego propio) | 8095 | Aprender a cuidar el Home Lab |
| 🏎️ CaciqueDash | caciquedash.py | 8888 | Indicadores estilo JDM y registro |
| 🛡️ CaciqueGuard | AdGuard Home + Caddy | 3000 / 53 | Nombres fáciles (`.home`) |

**Cómo se entra:** desde cualquier equipo de la casa, `http://<número de la laptop>` abre la página Cacique. Cada botón lleva a su servidor.

<!-- EN -->
## What is ElCaciqueDeck?

A ThinkPad laptop running **Ubuntu Linux** that works as the **home server**. It serves movies, photos, documents, games, an encyclopedia and the smart home to every device in the house, **with or without internet**.

### The pieces

| Piece | What it is | Where |
|---|---|---|
| **ThinkPad** (`elcaciquedeck-00`) | The server. Always on, lid closed | In a corner, wired by cable |
| **Library** | Drive 1: movies, games, encyclopedia (replaceable) | `/media/<user>/Library` |
| **Vault** | Drive 2: documents, photos, backups (**irreplaceable**) | `/media/<user>/Vault` |
| **Deeper Mini** | Blocks ads for the whole house | Between the router and the network |
| **GitHub** | Where the programs and this manual live | `github.com/ElCaciqueDeck` |

### The servers

| Name | Program | Port | What for |
|---|---|---|---|
| 🧭 Cacique | Homepage | 80 | Front page with a button for everything |
| 📚 CaciqueLibrary | Kiwix | 8080 | Offline encyclopedia (and this manual) |
| 🎬 CaciqueFlix | Jellyfin | 8096 | Movies, series, anime |
| 📄 CaciqueDocs | Paperless-ngx | 8000 | Scanned documents |
| 📸 CaciquePhotos | Immich | 2283 | Family photos and videos |
| 🏠 CaciqueHome | Home Assistant | 8123 | Hue lights and smart home |
| 🕹️ CaciqueArcade | RomM | 8090 | Retro games in the browser |
| 🎓 CaciqueAcademy | (our own game) | 8095 | Learn to care for the Home Lab |
| 🏎️ CaciqueDash | caciquedash.py | 8888 | JDM-style gauges and log |
| 🛡️ CaciqueGuard | AdGuard Home + Caddy | 3000 / 53 | Easy names (`.home`) |

**How to get in:** from any device in the house, `http://<laptop number>` opens the Cacique page. Each button leads to its server.
