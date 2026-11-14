// El Cacique - "Aero Naturaleza" front page (loaded by Homepage as /api/config/custom.js).
//
// What this file does (LOOKS ONLY - it never changes a link, an account, a server or a health check):
//   * Draws the welcome header ("Bienvenidos a casa"), the date and the three views:
//       Todas las apps · All apps   - the normal directory (every installed app, in its group)
//       Familia                     - only a few extra-large buttons for the kids and the grandparents
//       Invitado · Guest            - only the apps shared with visitors
//   * Copies each button's REAL link, icon and REAL status from what Homepage itself draws
//     (services.yaml + its siteMonitor checks), and shows the status in words:
//       En línea · Online  /  No disponible · Unavailable  /  Revisando · Checking
//   * Shows the "Familia Abierta" panel: a button to the family's shared slideshow (only that shared link).
//
// IMPORTANT: the views are a PRESENTATION choice, not security. Choosing "Familia" does not log anyone in and does
// not block anything. Ratings (Familia = PG, Invitado = PG-13), private photos and documents are protected inside
// each app by its own accounts, exactly as before.
//
// A tablet can open straight into a view:  http://<laptop>/#familia   or   http://<laptop>/#invitado
// No internet, no new servers, no server numbers on this page (those live in CaciqueDash, port 8888).
// To undo: put back the previous custom.css / custom.js / settings.yaml / widgets.yaml from git and reload.
(function () {
  "use strict";
  if (window.__elCaciqueAero) return;
  window.__elCaciqueAero = true;

  // ---------------------------------------------------------------- one language at a time (ES or EN), per device
  var LANG = "es";
  try { LANG = localStorage.getItem("cq-lang") || ((navigator.language || "es").toLowerCase().indexOf("en") === 0 ? "en" : "es"); } catch (e) { /* private mode */ }
  function T(es, en) { return LANG === "en" ? (en || es) : es; }
  function L(es, en) { return '<span data-cq-es="' + esc(es) + '" data-cq-en="' + esc(en || es) + '">' + esc(T(es, en)) + "</span>"; }
  // "Español · English" texts written in services.yaml / settings.yaml: keep one side
  function pickSide(text) {
    var i = text.indexOf(" · ");
    return i < 0 ? text : (LANG === "en" ? text.slice(i + 3) : text.slice(0, i));
  }

  // ---------------------------------------------------------------- what each view shows (edit here)
  // Names are the button names in services.yaml. Apps that aren't installed simply don't appear.
  // CaciqueLibrary / CaciqueAcademy can be added to Familia once their content has been checked for kids.
  var VIEWS = {
    todas: { es: "Todas las apps", en: "All apps", icon: "grid" },
    familia: { es: "Familia", en: "Family", icon: "family", apps: ["CaciqueFlix", "Familia Abierta", "CaciqueArcade", "Cacique Raíces"],
      title: ["Para la familia", "For the family"], sub: ["Toca un botón grande", "Tap a big button"] },
    invitado: { es: "Invitado", en: "Guest", icon: "guest", apps: ["CaciqueFlix", "Familia Abierta", "CaciqueArcade"],
      title: ["Para las visitas", "For our guests"], sub: ["Lo que compartimos contigo", "What we share with you"] },
  };
  // friendlier words for the big buttons (the normal directory keeps services.yaml's descriptions)
  var BIG_WORDS = {
    "CaciqueFlix": ["Películas y series", "Movies & shows"],
    "Familia Abierta": ["Fotos de la familia", "Family photos"],
    "CaciqueArcade": ["Juegos", "Games"],
    "CaciqueLibrary": ["Aprende y lee", "Learn & read"],
    "CaciqueAcademy": ["Aprende jugando", "Learn by playing"],
    "Cacique Raíces": ["Nuestra historia", "Our story"],
  };
  var STATUS = {
    up: ["En línea", "Online"],
    down: ["No disponible", "Unavailable"],
    unknown: ["Revisando", "Checking"],
  };
  var GROUP_ICONS = [[/^Familia/i, "family"], [/^Aprender/i, "learn"], [/^Hogar/i, "home"], [/^Servidor/i, "server"]];

  var ICONS = {
    grid: '<rect x="4" y="4" width="7" height="7" rx="2"/><rect x="13" y="4" width="7" height="7" rx="2"/><rect x="4" y="13" width="7" height="7" rx="2"/><rect x="13" y="13" width="7" height="7" rx="2"/>',
    family: '<circle cx="9" cy="8" r="3.2"/><path d="M3 19.5c.6-3.4 3-5.3 6-5.3s5.4 1.9 6 5.3"/><circle cx="17" cy="9" r="2.5"/><path d="M16.5 14.2c2.4.2 4 1.8 4.5 4.6"/>',
    guest: '<path d="M12 21s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 11c0 5.6-7 10-7 10Z"/>',
    learn: '<path d="M2.5 9 12 4.5 21.5 9 12 13.5Z"/><path d="M6.5 11v4.6c1.4 1.6 3.3 2.4 5.5 2.4s4.1-.8 5.5-2.4V11"/>',
    home: '<path d="M4 10.5 12 4l8 6.5V20H4Z"/><path d="M9.5 20v-5.5h5V20"/>',
    server: '<rect x="4" y="4" width="16" height="6.5" rx="2"/><rect x="4" y="13.5" width="16" height="6.5" rx="2"/><path d="M8 7.25h.01M8 16.75h.01"/>',
    up: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    down: '<path d="M7 7l10 10M17 7 7 17"/>',
    unknown: '<path d="M12 6v6l3.5 2"/><circle cx="12" cy="12" r="8.5"/>',
    play: '<path d="M8 5.5v13l11-6.5Z"/>',
  };
  function svg(name, cls) {
    return '<svg class="' + (cls || "cq-ico") + '" viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" ' +
      'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + ICONS[name] + "</svg>";
  }
  function el(tag, attrs, html) {
    var n = document.createElement(tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (html != null) n.innerHTML = html;
    return n;
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; });
  }
  function pill(st) {
    return '<span class="cq-pill" data-st="' + st + '">' + svg(st, "cq-pill-ico") + "<span>" + T(STATUS[st][0], STATUS[st][1]) + "</span></span>";
  }

  // ---------------------------------------------------------------- the view (hash first, then this device's choice)
  function wantedView() {
    var h = (location.hash || "").replace("#", "").toLowerCase();
    if (VIEWS[h]) return h;
    try { var s = localStorage.getItem("cq-view"); if (VIEWS[s]) return s; } catch (e) { /* private mode */ }
    return "todas";
  }
  var view = wantedView();
  function setView(v, remember) {
    if (!VIEWS[v]) return;
    view = v;
    document.body.setAttribute("data-cq-view", v);
    if (remember) {
      try { localStorage.setItem("cq-view", v); } catch (e) { /* fine */ }
      try { history.replaceState(null, "", v === "todas" ? location.pathname : "#" + v); } catch (e) { /* fine */ }
    }
    document.querySelectorAll(".cq-view-btn").forEach(function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-cq-view") === v ? "true" : "false");
    });
    var info = VIEWS[v];
    var t = document.getElementById("cq-easy-title"), s = document.getElementById("cq-easy-sub");
    if (t && info.title) t.textContent = T(info.title[0], info.title[1]);
    if (s && info.sub) s.textContent = T(info.sub[0], info.sub[1]);
    drawBig();
  }

  // ---------------------------------------------------------------- page chrome (drawn once)
  function buildChrome() {
    if (document.getElementById("cq-top")) return;
    document.body.classList.add("cq-aero");
    var vp = document.querySelector('meta[name="viewport"]');
    if (vp && vp.content.indexOf("viewport-fit") < 0) vp.content += ", viewport-fit=cover";

    var top = el("header", { id: "cq-top" },
      '<div class="cq-brand"><span class="cq-orb" aria-hidden="true"><img src="/icons/cacique-emblem.svg" alt="" width="34" height="34"></span>' +
      '<span><span class="cq-brand-name">El Cacique</span><span class="cq-brand-sub">' + L("Tu hogar digital", "Your digital home") + "</span></span></div>" +
      '<div class="cq-topright"><div class="cq-date" id="cq-date" aria-live="off"></div>' +
      '<div class="cq-lang" role="group" aria-label="Idioma / Language"><button type="button" data-cq-lang="es">ES</button><button type="button" data-cq-lang="en">EN</button></div></div>');

    var buttons = Object.keys(VIEWS).map(function (k) {
      var v = VIEWS[k];
      return '<button type="button" class="cq-view-btn" data-cq-view="' + k + '" aria-pressed="false">' + svg(v.icon) +
        L(v.es, v.en) + "</button>";
    }).join("");
    var hero = el("section", { id: "cq-hero", "aria-labelledby": "cq-hello" },
      '<p class="cq-eyebrow" id="cq-greet"></p>' +
      '<h1 id="cq-hello">' + L("Bienvenidos a casa.", "Welcome home.") + "</h1>" +
      // the home's message of the day (Cacique Diario), part of the page: nothing to open, nothing to sign into
      '<figure class="cq-motd" id="cq-motd" hidden><blockquote id="cq-motd-text"></blockquote><figcaption id="cq-motd-src"></figcaption></figure>' +
      '<p class="cq-subtitle">' + L("Escoge lo que quieres hacer. Todo está a un toque.", "Choose what you'd like to do. Everything is one tap away.") + "</p>" +
      '<div class="cq-views" role="group" aria-label="Vista / View">' + buttons + "</div>" +
      '<p class="cq-note">' + L("Estos botones solo cambian lo que se ve en esta pantalla. No inician sesión ni dan permisos.",
        "These buttons only change what this screen shows. They don't sign anyone in.") + "</p>");

    var easy = el("section", { id: "cq-easy", "aria-labelledby": "cq-easy-title" },
      '<div class="cq-easy-main"><div class="cq-easy-head"><h2 id="cq-easy-title"></h2><p id="cq-easy-sub"></p></div>' +
      '<div class="cq-biggrid" id="cq-biggrid"></div></div>' +
      '<aside class="cq-album" id="cq-album" aria-labelledby="cq-album-title" hidden>' +
        '<div class="cq-album-art" aria-hidden="true"><span class="cq-sun"></span><span class="cq-hill a"></span><span class="cq-hill b"></span>' +
          '<span class="cq-frame f1"></span><span class="cq-frame f2"></span><span class="cq-frame f3"></span></div>' +
        '<h2 id="cq-album-title">Familia Abierta</h2>' +
        "<p>" + L("Las fotos que la familia decidió compartir, en presentación.", "The photos the family chose to share, as a slideshow.") + "</p>" +
        '<a class="cq-album-go" id="cq-album-go" href="#">' + svg("play") + L("Ver las fotos", "View photos") + "</a>" +
        '<p class="cq-album-small">' + L("Solo el álbum compartido. Los álbumes privados se quedan privados.", "Only the shared album. Private albums stay private.") + "</p>" +
      "</aside>");

    var foot = el("footer", { id: "cq-foot" },
      L("Un hogar, muchas aplicaciones", "One home, many apps") + "<br>" +
      L("Hecho en Puerto Rico · Todo se queda en la casa", "Made in Puerto Rico · Everything stays at home"));

    var next = document.getElementById("__next");
    document.body.insertBefore(top, next);
    document.body.insertBefore(hero, next);
    document.body.insertBefore(easy, next);
    document.body.appendChild(foot);

    document.addEventListener("click", function (e) {
      var b = e.target.closest && e.target.closest(".cq-view-btn");
      if (b) setView(b.getAttribute("data-cq-view"), true);
      var lb = e.target.closest && e.target.closest("[data-cq-lang]");
      if (lb) setLang(lb.getAttribute("data-cq-lang"));
    });
    loadMotd();
    setInterval(loadMotd, 600000);
    setInterval(showMotd, 15000);
    window.addEventListener("hashchange", function () { setView(wantedView(), false); });
    tickDate();
    setInterval(tickDate, 30000);
  }

  function tickDate() {
    var d = document.getElementById("cq-date");
    if (!d) return;
    var now = new Date(), txt;
    try {
      var loc = LANG === "en" ? "en-US" : "es-PR";
      txt = now.toLocaleDateString(loc, { weekday: "long", day: "numeric", month: "long" }) + " · " +
        now.toLocaleTimeString(loc, { hour: "numeric", minute: "2-digit" });
    } catch (e) { txt = now.toDateString(); }
    txt = txt.charAt(0).toUpperCase() + txt.slice(1);
    if (d.textContent !== txt) d.textContent = txt;
    var g = document.getElementById("cq-greet"), h = now.getHours();
    var greet = h < 12 ? T("Buenos días", "Good morning") : h < 19 ? T("Buenas tardes", "Good afternoon") : T("Buenas noches", "Good evening");
    if (g && g.textContent !== greet) g.textContent = greet;
  }

  // ---------------------------------------------------------------- the home's message of the day (Cacique Diario)
  var MOTD = [], motdI = 0;
  function loadMotd() {
    if (!window.fetch) return;
    fetch(location.protocol + "//" + location.hostname + ":8097/api/hoy?para=familia", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (d) { MOTD = (d.mensajes || []).filter(function (m) { return m.es; }); showMotd(); })
      .catch(function () { var f = document.getElementById("cq-motd"); if (f) f.hidden = true; });
  }
  function showMotd() {
    var f = document.getElementById("cq-motd");
    if (!f || !MOTD.length) return;
    var m = MOTD[motdI++ % MOTD.length];
    f.classList.add("cq-fade");
    setTimeout(function () {
      document.getElementById("cq-motd-text").textContent = T(m.es, m.en);
      var src = m.recordatorio ? "" : (m.fuente && m.fuente !== "Cacique" ? pickSide(m.fuente) : "");
      document.getElementById("cq-motd-src").textContent = src;
      f.hidden = false;
      f.classList.remove("cq-fade");
    }, f.hidden ? 0 : 450);
  }

  function setLang(l) {
    if (l !== "es" && l !== "en") return;
    LANG = l;
    try { localStorage.setItem("cq-lang", l); } catch (e) { /* fine */ }
    document.documentElement.setAttribute("lang", l);
    document.querySelectorAll("[data-cq-es]").forEach(function (n) { n.textContent = n.getAttribute("data-cq-" + l); });
    document.querySelectorAll("[data-cq-lang]").forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-cq-lang") === l ? "true" : "false"); });
    document.querySelectorAll("[data-cq-orig]").forEach(function (n) { setSide(n, n.getAttribute("data-cq-orig")); });
    if (MOTD.length) { motdI = Math.max(0, motdI - 1); showMotd(); }
    lastBig = "";
    tickDate();
    setView(view, false);
    refresh();
  }
  // keep one side of an "Español · English" text, remembering the original for the language switch
  function setSide(node, orig) {
    var want = pickSide(orig), tn = null;
    node.childNodes.forEach(function (c) { if (c.nodeType === 3 && c.nodeValue.trim()) tn = tn || c; });
    if (tn) { if (tn.nodeValue !== want) tn.nodeValue = want; }
    else if (node.textContent !== want) node.textContent = want;
  }
  function localize(node) {
    var text = (node.textContent || "").trim();
    if (!node.getAttribute("data-cq-orig")) {
      if (text.indexOf(" · ") < 0) return;
      node.setAttribute("data-cq-orig", text);
    } else if (text.indexOf(" · ") >= 0 && text !== node.getAttribute("data-cq-orig")) {
      node.setAttribute("data-cq-orig", text);          // Homepage redrew it with new words
    }
    setSide(node, node.getAttribute("data-cq-orig"));
  }

  // ---------------------------------------------------------------- reading what Homepage draws
  function statusOf(li) {
    var dot = li.querySelector(".site-monitor-status > div");
    if (!dot) return "unknown";
    var c = dot.className || "";
    if (c.indexOf("bg-emerald") >= 0) return "up";
    if (c.indexOf("bg-rose") >= 0) return "down";
    return "unknown";
  }
  function cards() {
    var out = {};
    document.querySelectorAll("#layout-groups li.service, #services li.service").forEach(function (li) {
      var name = li.getAttribute("data-name") || "";
      var link = li.querySelector("a.service-title-text");
      var img = li.querySelector(".service-icon img");
      var desc = li.querySelector(".service-description");
      if (!name || !link) return;
      out[name] = { li: li, href: link.getAttribute("href"), target: link.getAttribute("target") || "_self",
        icon: img ? img.getAttribute("src") : "", desc: desc ? desc.textContent.trim() : "", status: statusOf(li) };
    });
    return out;
  }

  function tagGroups() {
    document.querySelectorAll("#layout-groups > .services-group, #services > .services-group").forEach(function (g) {
      var h = g.querySelector("h2.service-group-name");
      if (!h || h.getAttribute("data-cq-done")) return;
      var name = h.textContent.trim(), ico = "grid";
      GROUP_ICONS.forEach(function (gi) { if (gi[0].test(name)) ico = gi[1]; });
      h.setAttribute("data-cq-done", "1");
      var b = g.querySelector(":scope > button");      // groups stay open: no accidental folding by little hands
      if (b) { b.setAttribute("tabindex", "-1"); b.setAttribute("aria-hidden", "false"); }
      h.insertAdjacentHTML("afterbegin", svg(ico, "cq-gico"));
    });
    document.querySelectorAll("h2.service-group-name, .service-description").forEach(localize);
  }

  function tagServices(all) {
    Object.keys(all).forEach(function (name) {
      var c = all[name], li = c.li;
      if (li.getAttribute("data-cq-status") !== c.status) li.setAttribute("data-cq-status", c.status);
      var link = li.querySelector("a.service-title-text");
      var label = name + ". " + c.desc + ". " + T("Estado", "Status") + ": " + T(STATUS[c.status][0], STATUS[c.status][1]);
      if (link && link.getAttribute("aria-label") !== label) link.setAttribute("aria-label", label);
      // the icon repeats the same link: one tab stop per card
      var iconLink = li.querySelector("a.service-icon");
      if (iconLink && iconLink.getAttribute("tabindex") !== "-1") {
        iconLink.setAttribute("tabindex", "-1");
        iconLink.setAttribute("aria-hidden", "true");
      }
    });
  }

  // ---------------------------------------------------------------- the big buttons (Familia / Invitado)
  var lastBig = "";
  function drawBig() {
    var grid = document.getElementById("cq-biggrid");
    if (!grid) return;
    var info = VIEWS[view], all = cards();
    if (!info.apps) { lastBig = ""; return; }
    var html = info.apps.filter(function (n) { return all[n]; }).map(function (n) {
      var c = all[n], w = BIG_WORDS[n] ? T(BIG_WORDS[n][0], BIG_WORDS[n][1]) : c.desc;
      return '<a class="cq-big" href="' + esc(c.href) + '" target="' + esc(c.target) + '" data-st="' + c.status + '" ' +
        'aria-label="' + esc(n + ". " + w + ". " + T("Estado", "Status") + ": " + T(STATUS[c.status][0], STATUS[c.status][1])) + '">' +
        '<span class="cq-big-icon" aria-hidden="true">' + (c.icon ? '<img src="' + esc(c.icon) + '" alt="">' : "") + "</span>" +
        '<span class="cq-big-text"><span class="cq-big-name">' + esc(n) + "</span>" +
        '<span class="cq-big-desc">' + esc(w) + "</span>" +
        pill(c.status) + "</span></a>";
    }).join("");
    if (!html) html = '<p class="cq-empty">' + esc(T("Todavía no hay aplicaciones para esta vista.", "No apps for this view yet.")) + "</p>";
    if (html !== lastBig) {      // redraw only when something changed (keeps keyboard focus steady)
      var focused = document.activeElement && document.activeElement.closest && document.activeElement.closest(".cq-big");
      var href = focused ? focused.getAttribute("href") : null;
      grid.innerHTML = html;
      lastBig = html;
      if (href) { var again = grid.querySelector('.cq-big[href="' + href.replace(/"/g, '\\"') + '"]'); if (again) again.focus(); }
    }
    // Familia Abierta panel: only when that shared link is installed
    var album = document.getElementById("cq-album"), fa = all["Familia Abierta"];
    if (album) {
      album.hidden = !fa;
      if (fa) {
        var go = document.getElementById("cq-album-go");
        if (go.getAttribute("href") !== fa.href) go.setAttribute("href", fa.href);
      }
    }
  }

  // ---------------------------------------------------------------- keep up with Homepage's live updates
  var queued = false;
  function refresh() {
    queued = false;
    buildChrome();
    tagGroups();
    var all = cards();
    tagServices(all);
    drawBig();
  }
  function queue() {
    if (queued) return;
    queued = true;
    (window.requestAnimationFrame || setTimeout)(refresh);
  }
  function start() {
    refresh();
    setLang(LANG);
    setView(view, false);
    var root = document.getElementById("__next") || document.body;
    new MutationObserver(queue).observe(root, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
