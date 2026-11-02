---
title_es: Cada servidor, uno por uno
title_en: Each server, one by one
icon: 🧩
---
<!-- ES -->
Cada ficha dice **qué es**, **cómo se enciende y apaga solo** y **qué hacer si falla**. Para encender todo junto, usa `start-all.sh`.

### 📚 CaciqueLibrary (Kiwix) · puerto 8080
- **Qué es:** enciclopedias y libros sin internet (archivos `.zim` en `Library/Kiwix`).
- **Encender:** `kiwix-serve --port 8080 /media/$USER/Library/Kiwix/*.zim`
- **Apagar:** `pkill kiwix-serve`
- **Libros nuevos no aparecen:** Kiwix solo lee los libros al arrancar. Apágalo y enciéndelo.
- **"Unable to instantiate the HTTP Daemon":** ya hay otro Kiwix corriendo. `pkill kiwix-serve` y vuelve a encender.
- **"Unable to add the ZIM file":** ese archivo está incompleto o duplicado (`(1)` en el nombre). Bórralo y vuelve a descargarlo.

### 🎬 CaciqueFlix (Jellyfin, versión Flatpak) · puerto 8096
- **Encender:** `flatpak run org.jellyfin.JellyfinServer`
- **Apagar:** `flatpak kill org.jellyfin.JellyfinServer`
- **Nombres de archivos:** `Movies/Coco (2017)/Coco (2017).mkv` · `Series/Show (2005)/Season 01/Show S01E01.mkv`
- **No aparece una película:** revisa el nombre y en Dashboard → **Scan All Libraries**.

### 📄 CaciqueDocs (Paperless-ngx) · puerto 8000
- **Encender / apagar:** `cd ~/elcaciquedeck/paperless` y luego `docker compose up -d` / `docker compose down`
- **Olvidé la contraseña:** `docker compose exec webserver python3 manage.py changepassword USUARIO`
- **Error 500:** casi siempre son permisos. `sudo chown -R 1000:1000 /media/$USER/Vault/paperless` y `docker compose restart`.
- **Agregar documentos:** arrastrarlos a la página o copiarlos a `Vault/paperless/consume`.

### 📸 CaciquePhotos (Immich) · puerto 2283
- **Encender / apagar:** `cd ~/elcaciquedeck/immich` y `docker compose up -d` / `docker compose down`
- **Teléfonos:** app **Immich**, servidor `http://<número de la laptop>:2283`, activar **Backup**.
- **El servidor se apagó al empezar:** la base de datos aún se estaba preparando. `docker compose up -d` otra vez.

### 🏠 CaciqueHome (Home Assistant) · puerto 8123
- **Encender / apagar:** `cd ~/elcaciquedeck/homeassistant` y `docker compose up -d` / `docker compose down`
- **Philips Hue:** aparece solo; se presiona el botón grande del Hue Bridge y luego Submit.
- **"400: Bad Request" en caciquehome.home:** correr `bash ~/elcaciquedeck/homeassistant/setup-homeassistant.sh` otra vez.

### 🕹️ CaciqueArcade (RomM) · puerto 8090
- **Encender / apagar:** `cd ~/elcaciquedeck/arcade` y `docker compose up -d` / `docker compose down`
- **Agregar juegos:** copiarlos a `Library/Arcade/library/roms/<consola>/` y luego **Scan** en la página.
- **Solo juegos legales:** juegos tuyos o gratis con permiso de su autor.

### 🏎️ CaciqueDash · puerto 8888
- **Encender:** `python3 ~/elcaciquedeck/caciquedash.py` · **Apagar:** Ctrl+C o `pkill -f caciquedash.py`
- **Registro:** un renglón por minuto en `~/deck-logs/`.

### 🛡️ CaciqueGuard + nombres (AdGuard Home + Caddy) · puertos 3000, 53, 80
- **Encender / apagar:** `cd ~/elcaciquedeck/adguard` y `docker compose up -d` / `docker compose down`
- **Página principal en blanco o vieja:** `bash ~/elcaciquedeck/homepage/setup-homepage.sh` (también recarga Caddy).

<!-- EN -->
Each card says **what it is**, **how to start and stop it on its own**, and **what to do if it fails**. To start everything together, use `start-all.sh`.

### 📚 CaciqueLibrary (Kiwix) · port 8080
- **What it is:** encyclopedias and books with no internet (`.zim` files in `Library/Kiwix`).
- **Start:** `kiwix-serve --port 8080 /media/$USER/Library/Kiwix/*.zim`
- **Stop:** `pkill kiwix-serve`
- **New books don't show up:** Kiwix only reads books when it starts. Stop it and start it again.
- **"Unable to instantiate the HTTP Daemon":** another Kiwix is already running. `pkill kiwix-serve` and start again.
- **"Unable to add the ZIM file":** that file is incomplete or a duplicate (`(1)` in the name). Delete it and download it again.

### 🎬 CaciqueFlix (Jellyfin, Flatpak version) · port 8096
- **Start:** `flatpak run org.jellyfin.JellyfinServer`
- **Stop:** `flatpak kill org.jellyfin.JellyfinServer`
- **File names:** `Movies/Coco (2017)/Coco (2017).mkv` · `Series/Show (2005)/Season 01/Show S01E01.mkv`
- **A movie doesn't show up:** check the name, then Dashboard → **Scan All Libraries**.

### 📄 CaciqueDocs (Paperless-ngx) · port 8000
- **Start / stop:** `cd ~/elcaciquedeck/paperless` then `docker compose up -d` / `docker compose down`
- **Forgot the password:** `docker compose exec webserver python3 manage.py changepassword USERNAME`
- **Error 500:** almost always permissions. `sudo chown -R 1000:1000 /media/$USER/Vault/paperless` and `docker compose restart`.
- **Adding documents:** drag them onto the page or copy them into `Vault/paperless/consume`.

### 📸 CaciquePhotos (Immich) · port 2283
- **Start / stop:** `cd ~/elcaciquedeck/immich` and `docker compose up -d` / `docker compose down`
- **Phones:** the **Immich** app, server `http://<laptop number>:2283`, turn on **Backup**.
- **The server stopped right after starting:** the database was still getting ready. Run `docker compose up -d` again.

### 🏠 CaciqueHome (Home Assistant) · port 8123
- **Start / stop:** `cd ~/elcaciquedeck/homeassistant` and `docker compose up -d` / `docker compose down`
- **Philips Hue:** shows up by itself; press the big button on the Hue Bridge, then Submit.
- **"400: Bad Request" at caciquehome.home:** run `bash ~/elcaciquedeck/homeassistant/setup-homeassistant.sh` again.

### 🕹️ CaciqueArcade (RomM) · port 8090
- **Start / stop:** `cd ~/elcaciquedeck/arcade` and `docker compose up -d` / `docker compose down`
- **Adding games:** copy them into `Library/Arcade/library/roms/<console>/`, then **Scan** on the page.
- **Legal games only:** games you own, or free ones their authors allow.

### 🏎️ CaciqueDash · port 8888
- **Start:** `python3 ~/elcaciquedeck/caciquedash.py` · **Stop:** Ctrl+C or `pkill -f caciquedash.py`
- **Log:** one line per minute in `~/deck-logs/`.

### 🛡️ CaciqueGuard + names (AdGuard Home + Caddy) · ports 3000, 53, 80
- **Start / stop:** `cd ~/elcaciquedeck/adguard` and `docker compose up -d` / `docker compose down`
- **Front page blank or out of date:** `bash ~/elcaciquedeck/homepage/setup-homepage.sh` (it also reloads Caddy).
