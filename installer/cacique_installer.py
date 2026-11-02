#!/usr/bin/env python3
"""
El Cacique Home Lab - Setup (the installer window)

  python3 ~/elcaciquedeck/installer/cacique_installer.py            (or "El Cacique Setup" in the apps menu)
  python3 ~/elcaciquedeck/installer/cacique_installer.py --dry-run  (practice: shows every step, changes nothing)

A simple gray step-by-step window, like the installers of the Windows XP days:
Welcome -> Your computer -> Level -> Apps -> Drives -> Accounts -> Options -> Summary -> Installing -> Done.
All the real work is in engine.py. Only needs python3-tk (install.sh adds it).
"""
import os, queue, re, subprocess, sys, threading, webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine  # noqa: E402

DRY = "--dry-run" in sys.argv
GRAY, DARK, ACCENT, WHITE = "#d4d0c8", "#0b1322", "#f6a744", "#ffffff"

T = {  # every text, Spanish + English
    "title": ("El Cacique Home Lab - Instalación", "El Cacique Home Lab - Setup"),
    "back": ("< Atrás", "< Back"), "next": ("Siguiente >", "Next >"), "cancel": ("Cancelar", "Cancel"),
    "install": ("Instalar", "Install"), "finish": ("Terminar", "Finish"),
    "w_h": ("Bienvenido a El Cacique Home Lab", "Welcome to El Cacique Home Lab"),
    "w_s": ("Este asistente convierte esta computadora en el servidor de la familia.",
            "This wizard turns this computer into the family's home server."),
    "w_body": ("Vamos a:\n\n  1. Mirar qué tiene esta computadora.\n  2. Escoger el nivel: Laptop, Deck o Lab.\n"
               "  3. Escoger las aplicaciones: películas, fotos, documentos, casa inteligente, juegos,\n"
               "     contraseñas, calendario, Dropbox propia, cámaras e IA local.\n  4. Crear el administrador y las cuentas de la familia.\n"
               "  5. Instalar todo. Usted solo mira.\n\n"
               "Hecho en Puerto Rico. Proyecto para aprender. Solo contenido legal (sus películas, juegos gratis o propios).\n"
               "Necesita internet durante la instalación. Después, casi todo funciona sin internet.",
               "We will:\n\n  1. Look at what this computer has.\n  2. Choose the level: Laptop, Deck or Lab.\n"
               "  3. Choose the apps: movies, photos, documents, smart home, games,\n"
               "     passwords, calendar, our own Dropbox, cameras and local AI.\n  4. Create the administrator and the family accounts.\n"
               "  5. Install everything. You just watch.\n\n"
               "Made in Puerto Rico. A learning project. Legal content only (your own movies, free or owned games).\n"
               "Needs internet during the install. Afterwards, almost everything works without internet."),
    "lang": ("Idioma / Language:", "Idioma / Language:"),
    "s_h": ("Su computadora", "Your computer"), "s_s": ("Esto es lo que encontramos.", "This is what we found."),
    "scanning": ("Mirando la computadora...", "Looking at the computer..."),
    "os": ("Sistema", "System"), "cpu": ("Procesador", "Processor"), "threads": ("hilos", "threads"),
    "ram": ("Memoria", "Memory"), "disk": ("Espacio libre en el disco", "Free disk space"),
    "drives": ("Discos extra", "Extra drives"), "none": ("ninguno", "none"), "net": ("Red", "Network"),
    "internet": ("internet", "internet"), "yes": ("sí", "yes"), "no": ("no", "no"),
    "existing": ("Ya instalado aquí", "Already installed here"),
    "fits": ("Niveles que esta computadora cumple:", "Levels this computer meets:"),
    "recommended": ("Recomendado", "Recommended"),
    "notmounted": ("no conectado - ábralo en Archivos", "not mounted - open it in Files"),
    "l_h": ("Nivel", "Level"), "l_s": ("¿Qué tan grande será El Cacique en esta computadora?",
                                        "How big will El Cacique be on this computer?"),
    "force": ("Permitir un nivel que no cumple (avanzado)", "Allow a level it doesn't meet (advanced)"),
    "lab_check": ("El Lab también necesita (marque lo que ya tiene):", "The Lab also needs (tick what you have):"),
    "lab_items": (["Router con VLANs y firewall (Omada ER707-M2 o similar)", "Switch administrable (VLANs)",
                   "UPS (batería de respaldo)", "Closet con ventilación"],
                  ["Router with VLANs and firewall (Omada ER707-M2 or similar)", "Managed switch (VLANs)",
                   "UPS (battery backup)", "Ventilated closet"]),
    "lab_note": ("El instalador prepara los programas. Las VLANs se configuran en el equipo Omada siguiendo\n"
                 "docs/network-plan.md (el asistente le recuerda al final).",
                 "The installer sets up the programs. VLANs are configured on the Omada gear following\n"
                 "docs/network-plan.md (the wizard reminds you at the end)."),
    "a_h": ("Aplicaciones", "Apps"), "a_s": ("Marque lo que quiere instalar. Puede añadir más después.",
                                              "Tick what to install. You can add more later."),
    "gb": ("descarga ~%s GB", "download ~%s GB"), "needs2": ("(necesita Nivel 2)", "(needs Level 2)"),
    "slow": ("(lento con poca memoria)", "(slow with little memory)"),
    "d_h": ("Discos", "Drives"), "d_s": ("Dónde se guarda cada cosa.", "Where everything is kept."),
    "d_l1": ("Nivel Laptop: todo va en el disco de esta computadora (solo programas, sin películas):",
             "Laptop level: everything goes on this computer's own disk (programs only, no movies):"),
    "lib": ("Library - películas, juegos, enciclopedia, cámaras (se puede reemplazar):",
            "Library - movies, games, encyclopedia, cameras (replaceable):"),
    "vault": ("Vault - documentos, fotos, contraseñas, calendario (¡no se puede perder!):",
              "Vault - documents, photos, passwords, calendar (must not be lost!):"),
    "vault_folder": ("Carpeta 'Vault' dentro del disco Library", "A 'Vault' folder inside the Library drive"),
    "vault_warn": ("Mejor en un disco aparte: si Library se daña, no pierde los documentos.",
                   "Better on its own drive: if Library breaks, the documents survive."),
    "c_h": ("Cuentas", "Accounts"), "c_s": ("El administrador del Lab y las personas de la casa.",
                                            "The Lab's administrator and the people in the house."),
    "admin": ("Administrador (para quien maneje el Lab):", "Administrator (for whoever runs the Lab):"),
    "pw": ("Contraseña:", "Password:"), "pw2": ("Repetir:", "Repeat:"),
    "adults": ("Adultos (cada uno con su cuenta privada):", "Adults (each with a private account):"),
    "login": ("usuario (ej. maria)", "login (e.g. maria)"), "nick": ("apodo (ej. Mari)", "nickname (e.g. Mari)"),
    "add": ("Añadir", "Add"), "remove": ("Quitar", "Remove"),
    "family": ("Familia: entra sin contraseña, películas hasta PG", "Familia: no password, movies up to PG"),
    "guest": ("Invitado: películas hasta PG-13, fotos Familia Abierta, juegos", "Invitado: movies up to PG-13, Familia Abierta photos, games"),
    "o_h": ("Opciones", "Options"), "o_s": ("Últimos detalles.", "Last details."),
    "auto": ("Prender los servidores solos cuando se encienda la computadora", "Start the servers by themselves when the computer turns on"),
    "auto_note": ("Apagado = como hasta ahora: usted los prende con start-all.sh.", "Off = as before: you start them with start-all.sh."),
    "sudo": ("Contraseña de esta computadora (la de Ubuntu, para instalar):", "This computer's password (Ubuntu's, to install):"),
    "sum_h": ("Resumen", "Summary"), "sum_s": ("Revise y presione Instalar.", "Check and press Install."),
    "sum_time": ("La primera vez tarda entre 30 minutos y 2 horas (descarga varios GB). No apague la computadora.",
                 "The first time takes 30 minutes to 2 hours (several GB download). Don't turn the computer off."),
    "p_h": ("Instalando", "Installing"), "p_s": ("Puede mirar los detalles abajo.", "You can watch the details below."),
    "f_h": ("¡Listo!", "Done!"), "f_s": ("El Cacique está instalado.", "El Cacique is installed."),
    "f_bad": ("Terminó con problemas", "Finished with problems"),
    "f_open": ("Abrir la página de la familia", "Open the family page"),
    "f_body": ("Página de la familia (desde cualquier equipo de la casa):  http://%s\n\n"
               "Sus contraseñas iniciales y tarjetas: ~/elcaciquedeck-data/accounts/cards/\n"
               "Para cambiar algo más tarde: 'El Cacique Setup' en el menú de aplicaciones.",
               "Family page (from any device in the house):  http://%s\n\n"
               "Starter passwords and cards: ~/elcaciquedeck-data/accounts/cards/\n"
               "To change something later: 'El Cacique Setup' in the apps menu."),
    "f_lab": ("\nLab: ahora configure las VLANs y el firewall en el equipo Omada siguiendo docs/network-plan.md.",
              "\nLab: now set up the VLANs and firewall on the Omada gear following docs/network-plan.md."),
    "e_pw": ("La contraseña debe tener 8 caracteres o más, y las dos deben ser iguales.",
             "The password must have 8 characters or more, and both must match."),
    "e_admin": ("Nombre del administrador: solo letras y números (ej. ElCaciqueAdmin).", "Admin name: letters and numbers only (e.g. ElCaciqueAdmin)."),
    "e_login": ("Usuario: letras y números, sin espacios ni acentos (ej. maria).", "Login: letters and numbers, no spaces or accents (e.g. maria)."),
    "e_sudo": ("La contraseña de la computadora no es correcta.", "The computer password is not correct."),
    "e_lab": ("Para el Nivel Lab marque todo lo de la lista (o use la opción avanzada).",
              "For the Lab level tick everything on the list (or use the advanced option)."),
    "e_drive": ("Escoja el disco Library.", "Choose the Library drive."),
    "q_cancel": ("¿Salir de la instalación?", "Quit the setup?"),
    "q_stop": ("¿Detener la instalación? Lo que ya se instaló se queda.", "Stop the install? What's already installed stays."),
    "dry": ("PRÁCTICA · PRACTICE: no se cambia nada · nothing changes", "PRÁCTICA · PRACTICE: no se cambia nada · nothing changes"),
}


class Wizard:
    def __init__(self, root):
        self.root = root
        self.lang = "es"
        self.plan = engine.Plan()
        self.scan = None
        self.levels = None
        self.adults = []
        self.q = queue.Queue()
        self.ins = None
        self.done = None
        self.page = 0
        self.pages = [self.p_welcome, self.p_scan, self.p_level, self.p_apps, self.p_drives,
                      self.p_accounts, self.p_options, self.p_summary, self.p_progress, self.p_finish]
        # variables kept between pages
        self.v_lang = tk.StringVar(value="es")
        self.v_level = tk.IntVar(value=1)
        self.v_force = tk.BooleanVar(value=False)
        self.v_lab = [tk.BooleanVar(value=False) for _ in range(4)]
        self.v_apps = {k: tk.BooleanVar(value=False) for k in engine.APP_KEYS}
        self.v_lib = tk.StringVar()
        self.v_vault = tk.StringVar()
        self.v_admin = tk.StringVar(value="ElCaciqueAdmin")
        self.v_pw = tk.StringVar()
        self.v_pw2 = tk.StringVar()
        self.v_login = tk.StringVar()
        self.v_nick = tk.StringVar()
        self.v_family = tk.BooleanVar(value=True)
        self.v_guest = tk.BooleanVar(value=True)
        self.v_auto = tk.BooleanVar(value=False)
        self.v_sudo = tk.StringVar()
        self.apps_defaulted = False
        self.build_frame()
        self.show()

    # ---------------------------------------------------------------- frame
    def t(self, key):
        v = T[key]
        return v[0] if self.lang == "es" else v[1]

    def build_frame(self):
        r = self.root
        r.configure(bg=GRAY)
        self.side = tk.Canvas(r, width=170, bg=DARK, highlightthickness=0)
        self.side.grid(row=0, column=0, rowspan=2, sticky="ns")
        self.draw_side()
        right = tk.Frame(r, bg=GRAY)
        right.grid(row=0, column=1, sticky="nsew")
        r.grid_columnconfigure(1, weight=1)
        r.grid_rowconfigure(0, weight=1)
        head = tk.Frame(right, bg=WHITE)
        head.pack(fill="x")
        self.h1 = tk.Label(head, bg=WHITE, font=("DejaVu Sans", 13, "bold"), anchor="w")
        self.h1.pack(fill="x", padx=14, pady=(10, 0))
        self.h2 = tk.Label(head, bg=WHITE, font=("DejaVu Sans", 9), anchor="w", fg="#333")
        self.h2.pack(fill="x", padx=26, pady=(0, 10))
        tk.Frame(right, bg="#808080", height=1).pack(fill="x")
        self.body = tk.Frame(right, bg=GRAY)
        self.body.pack(fill="both", expand=True, padx=16, pady=12)
        bottom = tk.Frame(r, bg=GRAY)
        bottom.grid(row=1, column=1, sticky="ew")
        tk.Frame(bottom, bg="#808080", height=1).pack(fill="x")
        tk.Frame(bottom, bg=WHITE, height=1).pack(fill="x")
        bar = tk.Frame(bottom, bg=GRAY)
        bar.pack(fill="x", padx=10, pady=8)
        if DRY:
            tk.Label(bar, text=self.t("dry"), bg=GRAY, fg="#a00", font=("DejaVu Sans", 8, "bold")).pack(side="left")
        self.b_cancel = ttk.Button(bar, command=self.cancel, width=11)
        self.b_cancel.pack(side="right")
        self.b_next = ttk.Button(bar, command=self.next, width=13)
        self.b_next.pack(side="right", padx=(0, 10))
        self.b_back = ttk.Button(bar, command=self.back, width=11)
        self.b_back.pack(side="right")
        r.protocol("WM_DELETE_WINDOW", self.cancel)

    def draw_side(self):
        c = self.side
        c.delete("all")
        for i in range(60):          # dusk gradient
            r, g, b = 11 + i * 2, 19 + i, 34 + i // 2
            c.create_rectangle(0, i * 10, 170, i * 10 + 10, fill="#%02x%02x%02x" % (min(r, 160), min(g, 70), min(b, 60)), width=0)
        cx, cy = 85, 90             # Taíno-style sun
        c.create_oval(cx - 22, cy - 22, cx + 22, cy + 22, outline=ACCENT, width=3)
        c.create_arc(cx - 12, cy - 12, cx + 12, cy + 12, start=0, extent=300, style="arc", outline=ACCENT, width=3)
        for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0), (.7, .7), (-.7, .7), (.7, -.7), (-.7, -.7)]:
            c.create_line(cx + dx * 30, cy + dy * 30, cx + dx * 44, cy + dy * 44, fill=ACCENT, width=3, capstyle="round")
        c.create_text(85, 160, text="El Cacique", fill=WHITE, font=("DejaVu Serif", 17, "bold"))
        c.create_text(85, 184, text="HOME LAB", fill="#b6c3d5", font=("DejaVu Sans", 9))
        c.create_polygon(0, 520, 40, 470, 80, 500, 120, 455, 170, 495, 170, 600, 0, 600, fill="#141526", outline="")
        c.create_text(85, 515, text="Puerto Rico", fill="#b6c3d5", font=("DejaVu Sans", 8))

    def clear(self):
        for w in self.body.winfo_children():
            w.destroy()

    def show(self):
        self.clear()
        self.root.title(self.t("title"))
        self.b_back.configure(text=self.t("back"), state="normal" if 0 < self.page < 8 else "disabled")
        self.b_cancel.configure(text=self.t("cancel"), state="normal" if self.page < 9 else "disabled")
        nxt = self.t("install") if self.page == 7 else self.t("finish") if self.page == 9 else self.t("next")
        self.b_next.configure(text=nxt, state="normal")
        self.pages[self.page]()

    def head(self, h, s):
        self.h1.configure(text=self.t(h))
        self.h2.configure(text=self.t(s))

    def label(self, parent, text, **kw):
        kw.setdefault("bg", GRAY)
        kw.setdefault("anchor", "w")
        kw.setdefault("justify", "left")
        return tk.Label(parent, text=text, **kw)

    # ---------------------------------------------------------------- navigation
    def next(self):
        check = getattr(self, "ok_%d" % self.page, None)
        if check and not check():
            return
        if self.page == 7:
            self.page = 8
            self.show()
            self.start_install()
            return
        if self.page == 9:
            self.root.destroy()
            return
        self.page += 1
        self.show()

    def back(self):
        if self.page > 0:
            self.page -= 1
            self.show()

    def cancel(self):
        if self.page == 8 and self.ins and self.done is None:
            if messagebox.askyesno(self.t("title"), self.t("q_stop")):
                self.ins.cancelled.set()
            return
        if self.page == 9 or messagebox.askyesno(self.t("title"), self.t("q_cancel")):
            self.root.destroy()

    # ---------------------------------------------------------------- pages
    def p_welcome(self):
        self.head("w_h", "w_s")
        f = tk.Frame(self.body, bg=GRAY)
        f.pack(fill="x", pady=(0, 10))
        self.label(f, self.t("lang")).pack(side="left")
        for val, txt in (("es", "Español"), ("en", "English")):
            tk.Radiobutton(f, text=txt, value=val, variable=self.v_lang, bg=GRAY, activebackground=GRAY,
                           command=self.set_lang).pack(side="left", padx=8)
        self.label(self.body, self.t("w_body"), wraplength=580).pack(fill="x")

    def set_lang(self):
        self.lang = self.v_lang.get()
        self.plan.lang = self.lang
        self.show()

    def p_scan(self):
        self.head("s_h", "s_s")
        if self.scan is None:
            self.label(self.body, self.t("scanning")).pack(anchor="w")
            self.b_next.configure(state="disabled")

            def work():
                s = engine.scan()
                self.q.put(("scan", s))
            threading.Thread(target=work, daemon=True).start()
            self.root.after(100, self.poll)
            return
        s, yes, no = self.scan, self.t("yes"), self.t("no")
        box = tk.Frame(self.body, bg=WHITE, bd=1, relief="sunken")
        box.pack(fill="x")
        drives = ["%s  %s  %s GB  %s" % (d["dev"], d["label"] or "-", d["size_gb"], d["mount"] or self.t("notmounted"))
                  for d in s["drives"]] or [self.t("none")]
        rows = [(self.t("os"), s["os"]), (self.t("cpu"), "%s (%d %s)" % (s["cpu"][:48], s["threads"], self.t("threads"))),
                (self.t("ram"), "%.1f GB" % s["ram_gb"]), (self.t("disk"), "%.0f GB" % s["home_free_gb"]),
                (self.t("drives"), "\n".join(drives)),
                (self.t("net"), "%s  (%s: %s)" % (s["ip"] or "?", self.t("internet"), yes if s["internet"] else no))]
        if s["existing"]:
            rows.append((self.t("existing"), ", ".join(a[1] for a in engine.APPS if a[0] in s["existing"])))
        for i, (k, v) in enumerate(rows):
            tk.Label(box, text=k, bg=WHITE, anchor="nw", font=("DejaVu Sans", 9, "bold")).grid(row=i, column=0, sticky="nw", padx=8, pady=2)
            tk.Label(box, text=v, bg=WHITE, anchor="w", justify="left", wraplength=400).grid(row=i, column=1, sticky="w", padx=8, pady=2)
        self.label(self.body, self.t("fits"), font=("DejaVu Sans", 9, "bold")).pack(anchor="w", pady=(10, 2))
        rec = engine.recommend(self.levels)
        for lv in (1, 2, 3):
            ok, why = self.levels[lv]
            line = ("✔  " if ok else "✘  ") + engine.LEVELS[lv]["name"][self.lang]
            if lv == rec and ok:
                line += "   ← " + self.t("recommended")
            self.label(self.body, line, fg="#060" if ok else "#900").pack(anchor="w")
            for w in why[:2]:
                self.label(self.body, "      " + (w[0] if self.lang == "es" else w[1]), fg="#555").pack(anchor="w")

    def poll(self):
        try:
            while True:
                kind, data = self.q.get_nowait()
                if kind == "scan":
                    self.scan = data
                    self.levels = engine.check_levels(data)
                    self.v_level.set(engine.recommend(self.levels))
                    self.prefill_drives()
                    if self.page == 1:
                        self.show()
                elif kind == "log":
                    if getattr(self, "logbox", None):
                        self.logbox.configure(state="normal")
                        self.logbox.insert("end", data + "\n")
                        self.logbox.see("end")
                        self.logbox.configure(state="disabled")
                elif kind == "progress":
                    i, n, title = data
                    if getattr(self, "bar", None):
                        self.bar.configure(maximum=n, value=i)
                        self.stepl.configure(text=title)
                elif kind == "done":
                    self.done = data
                    self.page = 9
                    self.show()
        except queue.Empty:
            pass
        if self.scan is None or (self.ins and self.done is None):
            self.root.after(100, self.poll)

    def p_level(self):
        self.head("l_h", "l_s")
        for lv in (1, 2, 3):
            ok = self.levels[lv][0] or self.v_force.get()
            f = tk.Frame(self.body, bg=GRAY)
            f.pack(fill="x", pady=4)
            tk.Radiobutton(f, text=engine.LEVELS[lv]["name"][self.lang], value=lv, variable=self.v_level, bg=GRAY,
                           activebackground=GRAY, font=("DejaVu Sans", 10, "bold"), state="normal" if ok else "disabled",
                           command=self.show).pack(anchor="w")
            self.label(f, "      " + engine.LEVELS[lv]["desc"][self.lang], fg="#333" if ok else "#888").pack(anchor="w")
        tk.Checkbutton(self.body, text=self.t("force"), variable=self.v_force, bg=GRAY, activebackground=GRAY,
                       command=self.show).pack(anchor="w", pady=(8, 0))
        if self.v_level.get() == 3:
            self.label(self.body, self.t("lab_check"), font=("DejaVu Sans", 9, "bold")).pack(anchor="w", pady=(8, 0))
            for v, txt in zip(self.v_lab, T["lab_items"][0 if self.lang == "es" else 1]):
                tk.Checkbutton(self.body, text=txt, variable=v, bg=GRAY, activebackground=GRAY).pack(anchor="w", padx=16)
            self.label(self.body, self.t("lab_note"), fg="#333").pack(anchor="w", pady=(4, 0))

    def ok_2(self):
        lv = self.v_level.get()
        if lv == 3 and not all(v.get() for v in self.v_lab) and not self.v_force.get():
            messagebox.showwarning(self.t("title"), self.t("e_lab"))
            return False
        if self.plan.level != lv or not self.apps_defaulted:
            defaults = engine.default_apps(lv, self.scan) | set(self.scan["existing"])
            for k, v in self.v_apps.items():
                v.set(k in defaults)
            self.apps_defaulted = True
        self.plan.level = lv
        return True

    def p_apps(self):
        self.head("a_h", "a_s")
        existing = set(self.scan["existing"])
        for key, name, es, en, minlv, gb in engine.APPS:
            allowed = self.plan.level >= minlv or self.v_force.get()
            if not allowed:
                self.v_apps[key].set(False)
            f = tk.Frame(self.body, bg=GRAY)
            f.pack(fill="x")
            extra = "" if allowed else "  " + self.t("needs2")
            if key == "guide" and self.scan["ram_gb"] < 11.5:
                extra += "  " + self.t("slow")
            if key in existing:
                extra += "  ✔ " + self.t("existing").lower()
            tk.Checkbutton(f, text="%-16s" % name, variable=self.v_apps[key], bg=GRAY, activebackground=GRAY,
                           font=("DejaVu Sans Mono", 9, "bold"), state="normal" if allowed else "disabled").pack(side="left")
            self.label(f, (es if self.lang == "es" else en) + "  ·  " + self.t("gb") % gb + extra,
                       fg="#222" if allowed else "#888", font=("DejaVu Sans", 8), wraplength=410).pack(side="left")

    def ok_3(self):
        self.plan.apps = {k for k, v in self.v_apps.items() if v.get()}
        return True

    def prefill_drives(self):
        usable = engine.usable_drives(self.scan, 1)
        if usable and not self.v_lib.get():
            lib = next((d for d in usable if d["label"].lower() == "library"), usable[0])
            self.v_lib.set(lib["mount"])
            vault = next((d for d in usable if d["label"].lower() == "vault" and d is not lib),
                         next((d for d in usable if d is not lib), None))
            self.v_vault.set(vault["mount"] if vault else self.t("vault_folder"))

    def p_drives(self):
        self.head("d_h", "d_s")
        if self.plan.level == 1:
            self.label(self.body, self.t("d_l1"), wraplength=540).pack(anchor="w")
            for p in (self.plan_l1_paths()):
                self.label(self.body, "    " + p, font=("DejaVu Sans Mono", 9)).pack(anchor="w")
            return
        mounts = [d["mount"] for d in engine.usable_drives(self.scan, 1)]
        self.label(self.body, self.t("lib")).pack(anchor="w")
        ttk.Combobox(self.body, textvariable=self.v_lib, values=mounts, state="readonly", width=50).pack(anchor="w", pady=(2, 10))
        self.label(self.body, self.t("vault")).pack(anchor="w")
        ttk.Combobox(self.body, textvariable=self.v_vault, values=mounts + [self.t("vault_folder")], state="readonly",
                     width=50).pack(anchor="w", pady=2)
        if self.v_vault.get() in (self.t("vault_folder"), T["vault_folder"][0], T["vault_folder"][1]) or \
                self.v_vault.get() == self.v_lib.get():
            self.label(self.body, "⚠  " + self.t("vault_warn"), fg="#a60").pack(anchor="w", pady=(6, 0))
        unmounted = [d for d in self.scan["drives"] if not d["mount"]]
        if unmounted:
            self.label(self.body, "\n" + "\n".join("%s %s: %s" % (d["dev"], d["label"], self.t("notmounted")) for d in unmounted),
                       fg="#555").pack(anchor="w")

    def plan_l1_paths(self):
        return [engine.os.path.join(engine.DATA, "library"), engine.os.path.join(engine.DATA, "vault")]

    def ok_4(self):
        p = self.plan
        if p.level == 1:
            p.library, p.vault = self.plan_l1_paths()
            p.vault_is_folder = True
            return True
        if not self.v_lib.get():
            messagebox.showwarning(self.t("title"), self.t("e_drive"))
            return False
        p.library = self.v_lib.get()
        v = self.v_vault.get()
        if not v or v in T["vault_folder"] or v == p.library:
            p.vault, p.vault_is_folder = os.path.join(p.library, "Vault"), True
        else:
            p.vault, p.vault_is_folder = v, False
        return True

    def p_accounts(self):
        self.head("c_h", "c_s")
        g = tk.Frame(self.body, bg=GRAY)
        g.pack(fill="x")
        self.label(g, self.t("admin")).grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Entry(g, textvariable=self.v_admin, width=20).grid(row=1, column=0, sticky="w", pady=2)
        self.label(g, "  " + self.t("pw")).grid(row=1, column=1, sticky="e")
        ttk.Entry(g, textvariable=self.v_pw, show="•", width=16).grid(row=1, column=2, sticky="w")
        self.label(g, "  " + self.t("pw2")).grid(row=1, column=3, sticky="e")
        ttk.Entry(g, textvariable=self.v_pw2, show="•", width=16).grid(row=1, column=4, sticky="w")
        self.label(self.body, self.t("adults")).pack(anchor="w", pady=(12, 2))
        a = tk.Frame(self.body, bg=GRAY)
        a.pack(fill="x")
        e1 = ttk.Entry(a, textvariable=self.v_login, width=18)
        e1.pack(side="left")
        e2 = ttk.Entry(a, textvariable=self.v_nick, width=18)
        e2.pack(side="left", padx=6)
        ttk.Button(a, text=self.t("add"), command=self.add_adult).pack(side="left")
        ttk.Button(a, text=self.t("remove"), command=self.remove_adult).pack(side="left", padx=6)
        self.label(self.body, "      %s          %s" % (self.t("login"), self.t("nick")), fg="#666",
                   font=("DejaVu Sans", 8)).pack(anchor="w")
        self.lb = tk.Listbox(self.body, height=6, width=50)
        self.lb.pack(anchor="w", pady=2)
        for l, n in self.adults:
            self.lb.insert("end", "%-14s %s" % (l, n))
        e2.bind("<Return>", lambda e: self.add_adult())
        tk.Checkbutton(self.body, text=self.t("family"), variable=self.v_family, bg=GRAY, activebackground=GRAY).pack(anchor="w", pady=(8, 0))
        tk.Checkbutton(self.body, text=self.t("guest"), variable=self.v_guest, bg=GRAY, activebackground=GRAY).pack(anchor="w")

    def add_adult(self):
        login = self.v_login.get().strip().lower()
        if not re.match(r"^[a-z][a-z0-9]{1,30}$", login):
            messagebox.showwarning(self.t("title"), self.t("e_login"))
            return
        nick = self.v_nick.get().strip() or login.capitalize()
        if login not in [l for l, _ in self.adults] and login != self.v_admin.get().lower():
            self.adults.append((login, nick))
            self.lb.insert("end", "%-14s %s" % (login, nick))
        self.v_login.set("")
        self.v_nick.set("")

    def remove_adult(self):
        sel = self.lb.curselection()
        if sel:
            self.adults.pop(sel[0])
            self.lb.delete(sel[0])

    def ok_5(self):
        if not re.match(r"^[A-Za-z][A-Za-z0-9]{2,30}$", self.v_admin.get()):
            messagebox.showwarning(self.t("title"), self.t("e_admin"))
            return False
        if len(self.v_pw.get()) < 8 or self.v_pw.get() != self.v_pw2.get():
            messagebox.showwarning(self.t("title"), self.t("e_pw"))
            return False
        p = self.plan
        p.admin, p.admin_pw, p.adults = self.v_admin.get(), self.v_pw.get(), list(self.adults)
        p.family, p.guest = self.v_family.get(), self.v_guest.get()
        return True

    def p_options(self):
        self.head("o_h", "o_s")
        tk.Checkbutton(self.body, text=self.t("auto"), variable=self.v_auto, bg=GRAY, activebackground=GRAY).pack(anchor="w")
        self.label(self.body, "      " + self.t("auto_note"), fg="#555").pack(anchor="w")
        self.label(self.body, "\n" + self.t("sudo")).pack(anchor="w")
        e = ttk.Entry(self.body, textvariable=self.v_sudo, show="•", width=30)
        e.pack(anchor="w", pady=2)
        e.focus_set()

    def ok_6(self):
        self.plan.autostart = self.v_auto.get()
        pw = self.v_sudo.get()
        if not DRY:
            r = subprocess.run(["sudo", "-S", "-k", "-v"], input=pw + "\n", capture_output=True, text=True)
            if r.returncode != 0:
                messagebox.showwarning(self.t("title"), self.t("e_sudo"))
                return False
        self.plan.sudo_pw = pw
        return True

    def p_summary(self):
        self.head("sum_h", "sum_s")
        box = tk.Frame(self.body, bg=WHITE, bd=1, relief="sunken")
        box.pack(fill="x")
        for i, (k, v) in enumerate(self.plan.summary(self.lang)):
            tk.Label(box, text=k, bg=WHITE, anchor="nw", font=("DejaVu Sans", 9, "bold")).grid(row=i, column=0, sticky="nw", padx=8, pady=2)
            tk.Label(box, text=v, bg=WHITE, anchor="w", justify="left", wraplength=300).grid(row=i, column=1, sticky="w", padx=8, pady=2)
        self.label(self.body, "\n" + self.t("sum_time"), wraplength=540, fg="#333").pack(anchor="w")

    def p_progress(self):
        self.head("p_h", "p_s")
        self.b_next.configure(state="disabled")
        self.stepl = self.label(self.body, "", font=("DejaVu Sans", 9, "bold"))
        self.stepl.pack(anchor="w")
        self.bar = ttk.Progressbar(self.body, mode="determinate", length=540)
        self.bar.pack(fill="x", pady=6)
        frame = tk.Frame(self.body)
        frame.pack(fill="both", expand=True)
        self.logbox = tk.Text(frame, height=14, font=("DejaVu Sans Mono", 8), bg="#111", fg="#d6d6d6", wrap="char",
                              state="disabled")
        sb = ttk.Scrollbar(frame, command=self.logbox.yview)
        self.logbox.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.logbox.pack(side="left", fill="both", expand=True)

    def start_install(self):
        self.plan.lang = self.lang
        self.ins = engine.Installer(self.plan, log=lambda l: self.q.put(("log", l)),
                                    progress=lambda i, n, t: self.q.put(("progress", (i, n, t))), dry_run=DRY)

        def work():
            ok = False
            try:
                ok = self.ins.execute()
            except Exception as e:      # never leave the window stuck
                self.q.put(("log", "[FAIL] %s" % e))
            self.q.put(("done", ok))
        threading.Thread(target=work, daemon=True).start()
        self.root.after(100, self.poll)

    def p_finish(self):
        ok = bool(self.done)
        self.h1.configure(text=self.t("f_h") if ok else self.t("f_bad"))
        self.h2.configure(text=self.t("f_s") if ok else "")
        ip = engine.laptop_ip() or "<laptop>"
        text = self.t("f_body") % ip
        if self.plan.level == 3:
            text += self.t("f_lab")
        if self.ins and self.ins.failed:
            text = "✘ " + "\n✘ ".join("%s: %s" % f for f in self.ins.failed) + "\n\n" + text
        self.label(self.body, text, wraplength=540).pack(anchor="w")
        ttk.Button(self.body, text=self.t("f_open"), command=lambda: webbrowser.open("http://%s" % ip)).pack(anchor="w", pady=10)


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("default")
    except Exception:
        pass
    root.geometry("780x560")
    root.minsize(720, 520)
    Wizard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
