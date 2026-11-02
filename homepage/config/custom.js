// El Cacique - redesign helpers for the Homepage front page (loaded by Homepage as /api/config/custom.js).
//
// What this file does (looks only; it never changes a link, a server or a health check):
//   * Adds the left menu (computer), the bottom menu (phone) and the "Estado · Status" button (phone).
//   * Reads the live status dots that Homepage already shows and adds words for them
//     ("En línea · Online", "Con problemas · Down", "Revisando · Checking"), so status is not color-only.
//   * Labels the six live server numbers (CPU, free RAM, temperature, uptime, Library free, Vault free).
// Everything it reads comes from Homepage itself (services.yaml + widgets.yaml). No internet, no new servers.
// To undo the redesign: put the old custom.css / custom.js back (see git history) and reload the page.
(function () {
  "use strict";
  if (window.__elCacique) return;
  window.__elCacique = true;

  var GROUPS = [
    { id: "familia", match: /^Familia/i, label: "Familia", en: "Family", icon: "family" },
    { id: "aprender", match: /^Aprender/i, label: "Aprender", en: "Learn", icon: "learn" },
    { id: "hogar", match: /^Hogar/i, label: "Hogar", en: "Home", icon: "home" },
    { id: "servidor", match: /^Servidor/i, label: "Servidor", en: "Server", icon: "server" },
  ];
  var NAV = [{ id: "inicio", label: "Inicio", en: "Start", icon: "start" }].concat(GROUPS);

  // Which live number is which (same order as widgets.yaml / Homepage's resources widget)
  var DECK_METRICS = [
    { id: "cpu", caption: "Procesador · CPU use" },
    { id: "ram", caption: "Memoria libre · Free RAM" },
    { id: "temp", caption: "Temperatura · Temperature" },
    { id: "uptime", caption: "Encendido · Uptime" },
  ];
  var STATUS = {
    up: "En línea · Online",
    down: "Con problemas · Down",
    unknown: "Revisando · Checking",
  };

  var ICONS = {
    start: '<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10v9.5h13V10"/><path d="M10 19.5v-5h4v5"/>',
    family: '<circle cx="9" cy="8" r="3.2"/><path d="M3 19.5c.6-3.4 3-5.3 6-5.3s5.4 1.9 6 5.3"/><circle cx="17" cy="9" r="2.5"/><path d="M16.5 14.2c2.4.2 4 1.8 4.5 4.6"/>',
    learn: '<path d="M2.5 9 12 4.5 21.5 9 12 13.5Z"/><path d="M6.5 11v4.6c1.4 1.6 3.3 2.4 5.5 2.4s4.1-.8 5.5-2.4V11"/><path d="M21.5 9v5"/>',
    home: '<path d="M4 10.5 12 4l8 6.5V20H4Z"/><path d="M9.5 20v-5.5h5V20"/>',
    server: '<rect x="4" y="4" width="16" height="6.5" rx="2"/><rect x="4" y="13.5" width="16" height="6.5" rx="2"/><path d="M8 7.25h.01M8 16.75h.01M12 7.25h4M12 16.75h4"/>',
    status: '<path d="M3 12h4l2.5-6 4 12 2.5-6H21"/>',
  };
  function svg(name) {
    return '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">' + ICONS[name] + "</svg>";
  }
  function el(tag, attrs, html) {
    var n = document.createElement(tag);
    for (var k in attrs) n.setAttribute(k, attrs[k]);
    if (html != null) n.innerHTML = html;
    return n;
  }
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var scroller = function () { return document.getElementById("inner_wrapper") || document.scrollingElement; };

  // ---------------------------------------------------------------- page chrome
  function navButtons(where) {
    return NAV.map(function (g) {
      return '<li><button type="button" class="cq-nav-btn" data-cq-target="' + g.id + '" data-cq-where="' + where + '">' +
        '<span class="cq-nav-ico">' + svg(g.icon) + "</span>" +
        '<span class="cq-nav-txt"><span class="cq-es">' + g.label + '</span><span class="cq-en" lang="en">' + g.en + "</span></span></button></li>";
    }).join("");
  }

  function buildChrome() {
    if (document.getElementById("cq-rail")) return;
    document.body.classList.add("cq");
    try {
      if (localStorage.getItem("cq-solid") === "1") document.body.classList.add("cq-solid");
    } catch (e) { /* private mode: fine */ }

    // safe areas on phones with a notch
    var vp = document.querySelector('meta[name="viewport"]');
    if (vp && vp.content.indexOf("viewport-fit") < 0) vp.content += ", viewport-fit=cover";

    var emblem = '<img class="cq-emblem" src="/icons/cacique-emblem.svg" alt="" width="44" height="44">';

    // computer + tablet: left menu
    var rail = el("aside", { id: "cq-rail", "aria-label": "El Cacique" },
      '<a class="cq-brand" href="#" data-cq-target="inicio">' + emblem +
        '<span class="cq-brand-txt"><span class="cq-brand-name">El Cacique</span>' +
        '<span class="cq-brand-sub">Home Lab</span><span class="cq-brand-deck">ElCaciqueDeck</span></span></a>' +
      '<nav aria-label="Secciones · Sections"><ul class="cq-nav">' + navButtons("rail") + "</ul></nav>" +
      '<div class="cq-summary" role="status" aria-live="polite"><span class="cq-sum-dot" aria-hidden="true"></span>' +
        '<span class="cq-sum-txt"><b>Lab</b><span class="cq-sum-line">Revisando… · Checking…</span></span></div>');

    // phone: top bar with the status button
    var top = el("header", { id: "cq-mtop" },
      '<a class="cq-brand" href="#" data-cq-target="inicio">' + emblem.replace('width="44" height="44"', 'width="32" height="32"') +
        '<span class="cq-brand-name">El Cacique</span></a>' +
      '<button type="button" id="cq-status-btn" aria-expanded="false" aria-controls="information-widgets">' +
        '<span class="cq-sum-dot" aria-hidden="true"></span>' + svg("status") +
        '<span>Estado <span class="cq-en" lang="en">· Status</span></span></button>');

    // phone: bottom menu
    var tab = el("nav", { id: "cq-tabbar", "aria-label": "Secciones · Sections" }, '<ul class="cq-nav">' + navButtons("tab") + "</ul>");

    // first in the page, so the keyboard reaches the menu before the cards
    document.body.insertBefore(tab, document.body.firstChild);
    document.body.insertBefore(top, document.body.firstChild);
    document.body.insertBefore(rail, document.body.firstChild);

    document.addEventListener("click", function (e) {
      var t = e.target.closest && e.target.closest("[data-cq-target]");
      if (t) { e.preventDefault(); goTo(t.getAttribute("data-cq-target")); return; }
      if (e.target.closest && e.target.closest("#cq-status-btn")) toggleStatus();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && document.body.classList.contains("cq-status-open")) toggleStatus(false);
    });
  }

  function goTo(id) {
    var behavior = reduceMotion ? "auto" : "smooth";
    if (id === "inicio") {
      var s = scroller();
      if (s && s.scrollTo) s.scrollTo({ top: 0, behavior: behavior });
      window.scrollTo({ top: 0, behavior: behavior });
      lockUntil = Date.now() + 1200;
      setActive("inicio", true);
      return;
    }
    var g = document.querySelector('.services-group[data-cq-group="' + id + '"]');
    if (!g) return;
    g.scrollIntoView({ behavior: behavior, block: "start" });
    var btn = g.querySelector("button");
    if (btn && btn.focus) btn.focus({ preventScroll: true });
    lockUntil = Date.now() + 1200;   // keep the chosen section highlighted while the page scrolls
    setActive(id, true);
  }

  function toggleStatus(force) {
    var open = typeof force === "boolean" ? force : !document.body.classList.contains("cq-status-open");
    document.body.classList.toggle("cq-status-open", open);
    var b = document.getElementById("cq-status-btn");
    if (b) b.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) goTo("inicio");
  }

  var activeId = null, lockUntil = 0;
  function setActive(id, force) {
    if (!force && Date.now() < lockUntil) return;
    if (id === activeId) return;
    activeId = id;
    document.querySelectorAll(".cq-nav-btn").forEach(function (b) {
      if (b.getAttribute("data-cq-target") === id) b.setAttribute("aria-current", "true");
      else b.removeAttribute("aria-current");
    });
  }

  // ---------------------------------------------------------------- tagging what Homepage draws
  function tagGroups() {
    document.querySelectorAll("#layout-groups > .services-group, #services > .services-group").forEach(function (g) {
      var h = g.querySelector("h2.service-group-name");
      if (!h) return;
      var name = h.textContent.trim();
      for (var i = 0; i < GROUPS.length; i++) {
        if (GROUPS[i].match.test(name)) {
          if (g.getAttribute("data-cq-group") !== GROUPS[i].id) {
            g.setAttribute("data-cq-group", GROUPS[i].id);
            g.setAttribute("role", "region");
            h.id = "cq-h-" + GROUPS[i].id;
            g.setAttribute("aria-labelledby", h.id);
            observeSection(g);
          }
          break;
        }
      }
    });
  }

  function statusOf(li) {
    var dot = li.querySelector(".site-monitor-status > div");
    if (!dot) return "unknown";
    var c = dot.className;
    if (c.indexOf("bg-emerald") >= 0) return "up";
    if (c.indexOf("bg-rose") >= 0) return "down";
    return "unknown";
  }

  function tagServices() {
    var counts = { up: 0, down: 0, unknown: 0 }, total = 0;
    document.querySelectorAll("#layout-groups li.service, #services li.service").forEach(function (li) {
      var st = statusOf(li);
      counts[st]++; total++;
      if (li.getAttribute("data-cq-status") !== st) li.setAttribute("data-cq-status", st);
      var link = li.querySelector("a.service-title-text");
      var nameEl = li.querySelector(".service-name");
      var descEl = li.querySelector(".service-description");
      if (link && nameEl) {
        var name = li.getAttribute("data-name") || "";
        var desc = descEl ? descEl.textContent.trim() : "";
        var label = name + ". " + desc + ". Estado · Status: " + STATUS[st];
        if (link.getAttribute("aria-label") !== label) link.setAttribute("aria-label", label);
      }
      // the icon repeats the same link: keep one tab stop per card
      var iconLink = li.querySelector("a.service-icon");
      if (iconLink && iconLink.getAttribute("tabindex") !== "-1") {
        iconLink.setAttribute("tabindex", "-1");
        iconLink.setAttribute("aria-hidden", "true");
      }
    });
    updateSummary(counts, total);
  }

  function updateSummary(c, total) {
    var state = c.down ? "down" : c.unknown ? "unknown" : "up";
    var line;
    if (!total) line = "Revisando… · Checking…";
    else if (c.down) line = c.up + " de " + total + " en línea · " + c.down + " con problemas";
    else if (c.unknown) line = c.up + " de " + total + " en línea · revisando " + c.unknown;
    else line = "Todo en línea · All " + total + " online";
    document.querySelectorAll(".cq-summary, #cq-status-btn").forEach(function (n) {
      if (n.getAttribute("data-cq-state") !== state) n.setAttribute("data-cq-state", state);
    });
    var t = document.querySelector(".cq-sum-line");
    if (t && t.textContent !== line) t.textContent = line;
    var b = document.getElementById("cq-status-btn");
    if (b) {
      var bl = "Estado del servidor · Server status. " + line;
      if (b.getAttribute("aria-label") !== bl) b.setAttribute("aria-label", bl);
    }
  }

  function tagWidgets() {
    var wrap = document.getElementById("widgets-wrap");
    if (!wrap) return;
    var info = document.getElementById("information-widgets");
    if (info && !info.getAttribute("aria-label")) info.setAttribute("aria-label", "Estado del servidor · Server status");
    wrap.querySelectorAll(".widget-container").forEach(function (w) {
      var kind = null;
      if (w.classList.contains("information-widget-greeting")) kind = "greeting";
      else if (w.classList.contains("information-widget-datetime")) kind = "datetime";
      else {
        var txt = w.textContent || "";
        if (/Library/.test(txt)) kind = "media";
        else if (/Vault/.test(txt)) kind = "vault";
        else if (/ElCaciqueDeck/.test(txt) || w.querySelector(".information-widget-resource")) kind = "deck";
      }
      if (!kind) return;
      if (w.getAttribute("data-cq-w") !== kind) w.setAttribute("data-cq-w", kind);
      if (kind === "deck" || kind === "media" || kind === "vault") {
        var row = w.querySelector(".flex-wrap");
        if (!row) return;
        var kids = row.children;
        for (var i = 0; i < kids.length; i++) {
          var m = kind === "deck" ? DECK_METRICS[i] : { id: kind, caption: kind === "media" ? "Espacio libre · Free space" : "Espacio libre · Free space" };
          if (!m) continue;
          if (kids[i].getAttribute("data-cq-m") !== m.id) {
            kids[i].setAttribute("data-cq-m", m.id);
            kids[i].setAttribute("role", "group");
            kids[i].setAttribute("aria-label", m.caption);
          }
        }
      }
    });
  }

  // ---------------------------------------------------------------- which section is on screen
  var io = null;
  var visible = {};
  function observeSection(g) {
    if (!("IntersectionObserver" in window)) return;
    if (!io) {
      io = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) { visible[en.target.getAttribute("data-cq-group")] = en.isIntersecting; });
        var s = scroller();
        if (s && s.scrollTop < 40) { setActive("inicio"); return; }
        var atBottom = s && s.scrollTop + s.clientHeight >= s.scrollHeight - 4;
        var order = atBottom ? GROUPS.slice().reverse() : GROUPS;   // at the very end, the last section wins
        for (var i = 0; i < order.length; i++) if (visible[order[i].id]) { setActive(order[i].id); return; }
      }, { rootMargin: "-25% 0px -55% 0px" });
    }
    io.observe(g);
  }

  // ---------------------------------------------------------------- keep up with Homepage's live updates
  var queued = false;
  function refresh() {
    queued = false;
    buildChrome();
    tagGroups();
    tagWidgets();
    tagServices();
  }
  function queue() {
    if (queued) return;
    queued = true;
    (window.requestAnimationFrame || setTimeout)(refresh);
  }

  function start() {
    refresh();
    new MutationObserver(queue).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ["class"] });
    var s = scroller();
    if (s) s.addEventListener("scroll", function () { if (s.scrollTop < 40) setActive("inicio"); }, { passive: true });
    setActive("inicio");
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
