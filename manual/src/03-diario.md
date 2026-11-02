---
title_es: Operación diaria
title_en: Daily operation
icon: ▶️
---
<!-- ES -->
## Encender y apagar todo

Primero inicia sesión en la ThinkPad y confirma que **Library** y **Vault** aparecen en el panel izquierdo de Archivos (haz clic en cada uno si no están montados).

**1. Encender todos los servidores**
```
bash ~/elcaciquedeck/start-all.sh
```
**2. Ver cuáles están funcionando**
```
bash ~/elcaciquedeck/status.sh
```
**3. Apagar todos los servidores**
```
bash ~/elcaciquedeck/stop-all.sh
```

Los servidores **siguen funcionando** aunque cierres la Terminal. CaciquePhotos y CaciqueHome tardan 1–2 minutos en despertar.

## Desconectar un disco de forma segura

1. `bash ~/elcaciquedeck/stop-all.sh`
2. En Archivos, botón **⏏** al lado del disco. Espera a que desaparezca.
3. Desconéctalo.

**Al reconectar:** haz clic en el disco en Archivos y luego `start-all.sh`. Si aparece como `Library1` en vez de `Library`, desconéctalo, borra la carpeta vacía con `sudo rmdir /media/$USER/Library` y vuelve a conectarlo.

## Si se va la luz
La batería de la laptop la mantiene viva un rato. Si se apagó: enciéndela, inicia sesión, monta los discos, `start-all.sh`.

## Reportes
Todo programa de instalación guarda lo que pasó en `~/elcaciquedeck/reports/`. Si cerraste la Terminal por accidente:
```
ls -t ~/elcaciquedeck/reports/
```

<!-- EN -->
## Turning everything on and off

First log in to the ThinkPad and check that **Library** and **Vault** show in the Files app's left panel (click each one if it isn't mounted).

**1. Start every server**
```
bash ~/elcaciquedeck/start-all.sh
```
**2. See which ones are running**
```
bash ~/elcaciquedeck/status.sh
```
**3. Stop every server**
```
bash ~/elcaciquedeck/stop-all.sh
```

The servers **keep running** even after you close the Terminal. CaciquePhotos and CaciqueHome take 1–2 minutes to wake up.

## Unplugging a drive safely

1. `bash ~/elcaciquedeck/stop-all.sh`
2. In Files, the **⏏** button next to the drive. Wait until it disappears.
3. Unplug it.

**When reconnecting:** click the drive in Files, then `start-all.sh`. If it shows as `Library1` instead of `Library`, unplug it, remove the empty folder with `sudo rmdir /media/$USER/Library`, and plug it back in.

## If the power goes out
The laptop's battery keeps it alive for a while. If it shut down: turn it on, log in, mount the drives, `start-all.sh`.

## Reports
Every setup script saves what happened in `~/elcaciquedeck/reports/`. If you closed the Terminal by accident:
```
ls -t ~/elcaciquedeck/reports/
```
