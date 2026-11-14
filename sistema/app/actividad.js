// Barra de estado: qué está haciendo Pro Studio AHORA y cómo pararlo (Pablo, 11-nov: «poner algo que nos diga absolutamente qué
// está haciendo en cada momento y cómo decirle que no»). La cargan la app y la Edición avanzada. Pregunta cada 2 s a
// /api/actividad; sin nada corriendo no se ve. «Detener» manda /api/detener: el motor corta el paso en curso.
(() => {
  const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const caja = document.body.appendChild(Object.assign(document.createElement("div"), { id: "actividad" }));
  caja.setAttribute("role", "status");
  const tiempo = (s) => (s < 60 ? `${s} s` : `${Math.floor(s / 60)} min${s % 60 >= 10 && s < 600 ? ` ${s % 60} s` : ""}`);
  // el paso, como lo avisa el motor, sin sus etiquetas internas
  const paso = (t) => String(t || "").replace(/^\[video\]\s*/, "").replace(/^(machote|ojo|guion):\s*/, "").replace(/…$/, "").trim();
  let pintado = "";
  async function mirar() {
    let r = null;
    try { r = await (await fetch("/api/actividad")).json(); } catch (e) { /* el estudio no contesta: la barra se queda como está */ }
    const trabajos = (r && r.trabajos) || [];
    // Equipo nuevo: Claude Code sin sesión (o sin instalar) se dice ANTES de que el guion o el editor fallen, con el botón que lo arregla
    const claude = r && r.claude === "sin_sesion"
      ? `<div class="act"><div class="act-t"><b>Falta entrar a Claude</b><small>Sin la sesión de la suscripción no se prepara el guion ni se edita</small></div><button class="act-no" data-entrar>Iniciar sesión</button></div>`
      : r && r.claude === "falta"
        ? `<div class="act"><div class="act-t"><b>Falta Claude Code en este equipo</b><small>Abre otra vez «Instalar Pro Studio» para que lo instale</small></div></div>` : "";
    const html = claude + trabajos.map((t) => `<div class="act"><span class="giro"></span><div class="act-t"><b>${esc(t.que)}</b>${t.proyecto ? ` · ${esc(t.proyecto)}` : ""}` +
      `<small>${esc(t.deteniendo ? "Deteniendo: termina el paso en curso y para" : paso(t.paso) || "empezando")} · ${tiempo(t.segundos)}</small></div>` +
      `<button class="act-no" data-detener="${esc(t.id)}"${t.deteniendo ? " disabled" : ""}>Detener</button></div>`).join("");
    if (html !== pintado) { caja.innerHTML = pintado = html; }
    caja.classList.toggle("on", html !== "");
    // la pantalla le deja su franja: nada queda debajo de la barra (ni Exportar ni ningún otro botón)
    document.documentElement.style.setProperty("--act-h", (html ? caja.offsetHeight : 0) + "px");
  }
  caja.onclick = async (e) => {
    const entrar = e.target.closest("[data-entrar]");
    if (entrar) {   // abre la Terminal con el inicio de sesión oficial; cuando la persona entra, el aviso se quita solo
      entrar.disabled = true;
      setTimeout(() => (entrar.disabled = false), 6000);
      const r = await fetch("/api/claude-entrar", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).then((x) => x.json()).catch(() => null);
      if (!r || !r.ok) alert((r && r.error) || "No pude abrir el inicio de sesión. Abre la Terminal y escribe: claude");
      return;
    }
    const b = e.target.closest("[data-detener]");
    if (!b || !confirm("¿Detener esto? Lo que ya estaba hecho se conserva; lo que iba a la mitad se pierde.")) return;
    b.disabled = true;
    await fetch("/api/detener", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ trabajo: b.dataset.detener }) }).catch(() => {});
    mirar();
  };
  mirar();
  setInterval(mirar, 2000);
})();
