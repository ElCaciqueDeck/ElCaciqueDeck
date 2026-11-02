---
title_es: Discos y almacenamiento
title_en: Drives and storage
icon: 💽
---
<!-- ES -->
## Dos discos, dos trabajos

| Disco | Guarda | Por qué |
|---|---|---|
| 🎬 **Library** | Enciclopedia, películas, juegos | Grande, pero se puede volver a bajar o copiar |
| 🔐 **Vault** | Documentos, fotos, respaldos | **Irremplazable**. Junto es más fácil respaldarlo |

**Ver los dos discos, su espacio y qué tienen:**
```
bash ~/elcaciquedeck/tools/drives.sh
```

## Formatos: por qué ext4
- **FAT32** no guarda archivos de más de **4 GB**. Lo aprendimos con Wikipedia.
- **NTFS / exFAT** (de Windows) no guardan los permisos de Linux; Paperless e Immich fallan ahí.
- **ext4** es el formato de Linux: confiable, sin límite práctico, guarda permisos. **Usar siempre ext4** para el Home Lab. (Windows no lo puede leer, y está bien.)

## Preparar un disco nuevo (borra todo lo que tenga)
1. App **Discos** → elegir el disco correcto (**revisar tamaño y nombre dos veces**).
2. **⋮ → Format Disk → GPT**, luego **+** → nombre → **Ext4** → Create.
3. **▶** para montarlo.
4. Hacerlo tuyo: `sudo chown -R $USER:$USER /media/$USER/NOMBRE`

## Borrar no siempre libera espacio
Lo que se borra de un disco externo en Archivos va a **su propia Papelera**. Para recuperar el espacio: clic derecho en **Papelera → Vaciar papelera**.

## Mover datos de forma segura
`tools/move-to-vault.sh` **copia**, **verifica** que la copia sea idéntica, cambia la configuración y **guarda la copia vieja** como `_old-…`. Nunca borra nada: las copias viejas se borran a mano después de comprobar que todo funciona.

<!-- EN -->
## Two drives, two jobs

| Drive | Holds | Why |
|---|---|---|
| 🎬 **Library** | Encyclopedia, movies, games | Big, but can be re-downloaded or re-copied |
| 🔐 **Vault** | Documents, photos, backups | **Irreplaceable**. Kept together so it's easy to back up |

**See both drives, their space and what's on them:**
```
bash ~/elcaciquedeck/tools/drives.sh
```

## Formats: why ext4
- **FAT32** can't store files bigger than **4 GB**. We learned that with Wikipedia.
- **NTFS / exFAT** (Windows formats) don't keep Linux permissions, so Paperless and Immich fail on them.
- **ext4** is the Linux format: reliable, no practical size limit, keeps permissions. **Always use ext4** for the Home Lab. (Windows can't read it, and that's fine.)

## Preparing a new drive (erases everything on it)
1. **Disks** app → pick the right drive (**check the size and name twice**).
2. **⋮ → Format Disk → GPT**, then **+** → name → **Ext4** → Create.
3. **▶** to mount it.
4. Make it yours: `sudo chown -R $USER:$USER /media/$USER/NAME`

## Deleting doesn't always free space
Files deleted from an external drive in the Files app go to **that drive's own Trash**. To get the space back: right-click **Trash → Empty Trash**.

## Moving data safely
`tools/move-to-vault.sh` **copies**, **verifies** the copy is identical, switches the settings, and **keeps the old copy** as `_old-…`. It never deletes anything: you delete the old copies by hand after checking everything works.
