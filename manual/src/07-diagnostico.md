---
title_es: Diagnóstico — cuando algo está en rojo
title_en: Troubleshooting — when something is red
icon: 🩺
---
<!-- ES -->
## El método en 5 pasos

**Paso 1 — ¿Está conectado el disco?**
```
bash ~/elcaciquedeck/tools/drives.sh
```
**Paso 2 — ¿Qué servidores responden?**
```
bash ~/elcaciquedeck/status.sh
```
**Paso 3 — ¿Qué contesta el servidor?** (cambia el puerto)
```
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/
```
**Paso 4 — ¿Qué dice su registro?** (dentro de la carpeta del servidor)
```
docker compose logs --tail 20
```
**Paso 5 — Arreglar una sola cosa, y probar otra vez.**

## Qué significan los códigos
| Código | Significa | Qué hacer |
|---|---|---|
| **200** / **302** | Todo bien (302 = te manda a la página de entrada) | Nada |
| **400** / **403** | El servidor no acepta ese nombre o dirección | Revisar el nombre; correr su `setup-…sh` otra vez |
| **404** | Esa página no existe | Revisar la dirección |
| **500** | El servidor está encendido pero **falla por dentro** | Ver su registro (paso 4). Casi siempre: permisos |
| **502** | El ayudante de nombres no encuentra el servidor | El servidor está apagado: `start-all.sh` |
| **000** | Nadie contesta | Apagado o puerto equivocado |

## Errores que ya resolvimos (y su arreglo)
| Mensaje | Causa | Arreglo |
|---|---|---|
| `invalid magic number` al instalar Linux | USB mal hecho o Secure Boot | Apagar Secure Boot en el BIOS (F1) o rehacer el USB |
| No copia archivos de más de 4 GB | Disco en FAT32 | Formatear en ext4 |
| `Unable to instantiate the HTTP Daemon` | Puerto ocupado | `pkill kiwix-serve` |
| Kiwix muestra "Usage…" | Error al escribir la orden | Revisar `--port 8080` y la `L` mayúscula de Library |
| La línea empieza con `>` | Falta terminar la orden | Escribir lo que falta o Ctrl+C |
| `wc: invalid option -- 1` | Número 1 en vez de letra l | `wc -l` |
| `permission denied … docker API` | Tu usuario no está en el grupo docker | `sudo usermod -aG docker $USER` y reiniciar |
| Paperless: usuario o contraseña incorrectos | Error al crearla | `changepassword` (ver capítulo de servidores) |
| CaciqueDocs **500** después de mover a Vault | Permisos | `sudo chown -R 1000:1000 /media/$USER/Vault/paperless` |
| `No such file or directory` en /media | El disco no está montado | Clic en el disco en Archivos |
| `.home` no abre en el teléfono o TV | Ese equipo no usa CaciqueGuard | Usar `http://<número de la laptop>` |

<!-- EN -->
## The 5-step method

**Step 1 — Is the drive connected?**
```
bash ~/elcaciquedeck/tools/drives.sh
```
**Step 2 — Which servers answer?**
```
bash ~/elcaciquedeck/status.sh
```
**Step 3 — What does the server answer?** (change the port)
```
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/
```
**Step 4 — What does its log say?** (inside the server's folder)
```
docker compose logs --tail 20
```
**Step 5 — Fix one thing only, then test again.**

## What the codes mean
| Code | Means | What to do |
|---|---|---|
| **200** / **302** | All good (302 = sends you to the login page) | Nothing |
| **400** / **403** | The server doesn't accept that name or address | Check the name; run its `setup-…sh` again |
| **404** | That page doesn't exist | Check the address |
| **500** | The server is on but **failing inside** | Read its log (step 4). Almost always: permissions |
| **502** | The name helper can't find the server | The server is off: `start-all.sh` |
| **000** | Nobody answers | Off, or the wrong port |

## Errors we already solved (and the fix)
| Message | Cause | Fix |
|---|---|---|
| `invalid magic number` installing Linux | Bad USB or Secure Boot | Turn off Secure Boot in the BIOS (F1) or remake the USB |
| Won't copy files over 4 GB | Drive is FAT32 | Format as ext4 |
| `Unable to instantiate the HTTP Daemon` | Port in use | `pkill kiwix-serve` |
| Kiwix shows "Usage…" | Typo in the command | Check `--port 8080` and the capital L in Library |
| Line starts with `>` | Command not finished | Type what's missing, or Ctrl+C |
| `wc: invalid option -- 1` | Number 1 instead of letter l | `wc -l` |
| `permission denied … docker API` | Your user isn't in the docker group | `sudo usermod -aG docker $USER` and reboot |
| Paperless: wrong user or password | Typo when created | `changepassword` (see the servers chapter) |
| CaciqueDocs **500** after moving to Vault | Permissions | `sudo chown -R 1000:1000 /media/$USER/Vault/paperless` |
| `No such file or directory` in /media | Drive not mounted | Click the drive in Files |
| `.home` won't open on a phone or TV | That device doesn't use CaciqueGuard | Use `http://<laptop number>` |
