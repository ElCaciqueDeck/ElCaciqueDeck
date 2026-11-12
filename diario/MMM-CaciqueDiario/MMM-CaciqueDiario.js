/* Cacique Diario for MagicMirror² - shows the home's message of the day on the smart mirror.
 * Copy this folder to ~/MagicMirror/modules/ and add to ~/MagicMirror/config/config.js:
 *   { module: "MMM-CaciqueDiario", position: "lower_third",
 *     config: { url: "http://<server>:8097", para: "familia" } },     // para: a person's name from the adults' page
 */
Module.register("MMM-CaciqueDiario", {
  defaults: { url: "http://SERVIDOR:8097", para: "familia", segundos: 20, actualizar: 600, idioma: "es+en" },

  start() {
    this.msgs = []; this.i = 0;
    this.load();
    setInterval(() => this.load(), this.config.actualizar * 1000);
    setInterval(() => { this.i++; this.updateDom(800); }, this.config.segundos * 1000);
  },

  async load() {
    try {
      const r = await fetch(this.config.url + "/api/hoy?para=" + encodeURIComponent(this.config.para), { cache: "no-store" });
      const d = await r.json();
      this.msgs = d.mensajes || [];
      this.updateDom(800);
    } catch (e) { /* server asleep: keep the last messages */ }
  },

  getDom() {
    const w = document.createElement("div");
    w.style.textAlign = "center"; w.style.maxWidth = "900px"; w.style.margin = "0 auto";
    if (!this.msgs.length) return w;
    const m = this.msgs[this.i % this.msgs.length];
    if (this.config.idioma !== "en") {
      const es = document.createElement("div"); es.className = "bright medium"; es.textContent = m.es; w.appendChild(es);
    }
    if (this.config.idioma !== "es" && m.en) {
      const en = document.createElement("div"); en.className = this.config.idioma === "en" ? "bright medium" : "dimmed small";
      en.style.fontStyle = this.config.idioma === "en" ? "normal" : "italic"; en.textContent = m.en; w.appendChild(en);
    }
    if (m.fuente && m.fuente !== "Cacique" && !m.recordatorio) {
      const s = document.createElement("div"); s.className = "dimmed xsmall"; s.textContent = m.fuente; w.appendChild(s);
    }
    return w;
  }
});
