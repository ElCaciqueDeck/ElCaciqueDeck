---
title_es: La Terminal sin miedo
title_en: The Terminal without fear
icon: ⌨️
---
<!-- ES -->
## Lo básico

La **Terminal** es donde se le dan órdenes escritas a la computadora. El idioma se llama **Bash**. Ábrela con **Ctrl + Alt + T**.

### Las 7 reglas de oro

1. **Una caja = una línea.** Aunque en pantalla se vea en dos líneas, se escribe todo y se presiona **Enter una sola vez**.
2. **Mayúsculas y minúsculas importan.** `Library` y `library` son cosas diferentes.
3. **L minúscula no es el número 1.** `systemctl`, `wc -l`, `logind` llevan la letra **l**.
4. **`$USER` se llena solo** con tu nombre de usuario. `~` significa tu carpeta personal (Home).
5. **Lo que se cambia** siempre se ve así: `<número de la laptop>`, `TU-USUARIO`, `192.168.x.x`. Todo lo demás se escribe exacto.
6. **Si aparece `>` al principio**, la Terminal está esperando que termines la orden. Termínala o presiona **Ctrl + C** para cancelar.
7. **Ctrl + C** detiene lo que esté corriendo en esa ventana. La flecha **↑** repite la orden anterior.

### Las órdenes que más usamos

| Orden | Qué hace |
|---|---|
| `ls` | Lista lo que hay en una carpeta |
| `cd carpeta` | Entra a una carpeta (`cd ~` = ir a Home) |
| `pwd` | Dice en qué carpeta estás |
| `mkdir nombre` | Crea una carpeta |
| `mv origen destino` | Mueve o renombra |
| `cat archivo` | Muestra lo que dice un archivo |
| `df -h` | Espacio libre en los discos |
| `lsblk -f` | Lista los discos y su formato |
| `sudo orden` | Hace la orden como administrador (pide contraseña; no se ve al escribirla) |
| `nano archivo` | Editor de texto dentro de la Terminal (guardar: Ctrl+O, Enter; salir: Ctrl+X) |

### Qué significa la contraseña invisible
Cuando `sudo` pide la contraseña, **no aparece nada mientras escribes**. Es normal. Escríbela y presiona Enter.

<!-- EN -->
## The basics

The **Terminal** is where you give the computer written orders. The language is called **Bash**. Open it with **Ctrl + Alt + T**.

### The 7 golden rules

1. **One box = one line.** Even if it wraps onto two lines on screen, type all of it and press **Enter once**.
2. **Capital letters matter.** `Library` and `library` are different things.
3. **Lowercase L is not the number 1.** `systemctl`, `wc -l`, `logind` use the letter **l**.
4. **`$USER` fills itself in** with your username. `~` means your Home folder.
5. **What you change** always looks like this: `<laptop number>`, `YOUR-USERNAME`, `192.168.x.x`. Everything else is typed exactly.
6. **If `>` appears at the start**, the Terminal is waiting for you to finish the command. Finish it, or press **Ctrl + C** to cancel.
7. **Ctrl + C** stops whatever is running in that window. The **↑** arrow repeats the last command.

### The commands we use most

| Command | What it does |
|---|---|
| `ls` | Lists what's in a folder |
| `cd folder` | Goes into a folder (`cd ~` = go Home) |
| `pwd` | Tells you which folder you're in |
| `mkdir name` | Creates a folder |
| `mv source destination` | Moves or renames |
| `cat file` | Shows what a file says |
| `df -h` | Free space on the drives |
| `lsblk -f` | Lists the drives and their format |
| `sudo command` | Runs the command as administrator (asks for your password; it doesn't show as you type) |
| `nano file` | Text editor inside the Terminal (save: Ctrl+O, Enter; quit: Ctrl+X) |

### About the invisible password
When `sudo` asks for your password, **nothing appears while you type**. That's normal. Type it and press Enter.
