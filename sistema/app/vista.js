// Vista en vivo, compartida por Personalizar y Edición avanzada. UNA sola regla (Pablo, 11-nov: «crea una forma de mostrar las
// previews fácil»): a la izquierda, un pantallazo de SU video con los textos del estilo encima; a la derecha, el apoyo del estilo
// (solo fondo y texto, sin persona). Siempre así, haya o no storyboard: antes, con el video ya dirigido, las dos vistas pasaban a
// ser cuadros del montaje y la misma pantalla mostraba cosas distintas según el estado del proyecto.
// Con video: pide al servidor las dos vistas con el estilo elegido (espera 250 ms; solo se pinta el último pedido; la primera
// vista se pinta apenas está). Un panel nunca queda vacío: o su cuadro o una nota que dice qué pasa.
// Sin video: la muestra del estilo con los textos dibujados en HTML/CSS (tipografía, color, caja), que cambian al instante.
// El hook (caja y color) NO se dibuja en ninguna vista: el motor aún no lo dibuja y la vista solo muestra lo que sale en el video.
const Vista = (() => {
  const ESPERA = 250;
  const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  // Qué formas de subtítulo llevan caja de serie: sale del código (/api/catalogo › subtitulo.tipos[t].caja), no se repite aquí.
  let tiposSub = null, subCargado = false;
  const alCargarSub = [];
  fetch("/api/catalogo").then((r) => r.json()).then((r) => { tiposSub = r.subtitulo?.tipos || null; }).catch(() => {})
    .finally(() => { subCargado = true; alCargarSub.forEach((f) => f()); });
  const fam = (f) => (f ? `'tps-${f}'` : "inherit");

  async function esperar(api, tid, cadaVez, ms = 1200) {
    for (;;) {
      const t = await api(`/api/trabajo/${tid}`);
      cadaVez && cadaVez(t);
      if (t.estado !== "corriendo") return t;
      await new Promise((r) => setTimeout(r, ms));
    }
  }
  const ultimo = (t) => (t.log || []).filter((l) => !l.startsWith("Traceback")).at(-1) || "";

  // Sin video: la 1.ª miniatura con la persona de la portada del estilo (x 22, y 867, 210x373 de 720x1280) y encima los textos.
  function muestra(a, b, { estiloId, estilo }) {
    const url = `/app/muestras/${estiloId}.jpg`;
    const acento = estilo.acento || "#FFE800", tinta = estilo.tinta || "#181614", papel = estilo.papel || "#fff";
    const tipo = estilo.subtitulo || "tira";   // la muestra dibuja las mismas sub_* que el motor (caja sí/no, colores, tipografía)
    const caja = estilo.sub_caja ?? !!tiposSub?.[tipo]?.caja;
    const borde = estilo.sub_caja_color || estilo.borde || acento;
    const colTexto = estilo.sub_color || "#fff", colClave = estilo.sub_clave || acento, famSub = estilo.sub_fuente || estilo.fuente;
    const sub = `<div class="vs${caja ? " caja" : ""}" style="font-family:${fam(famSub)};color:${colTexto};${caja ? `border-color:${borde}` : ""}">Así se ven <em style="font-family:${fam(estilo.sub_fuente || estilo.fuente_script || estilo.fuente)};color:${colClave}">tus palabras</em></div>`;
    a.innerHTML = `<div class="vf" style="background:url('${url}') ${(22 / 510) * 100}% ${(867 / 907) * 100}%/${(720 / 210) * 100}% auto no-repeat"></div>${sub}`;
    a.style.setProperty("--papel", papel);
    if (b) b.innerHTML = `<img src="${url}" alt="">`;
  }

  // crear({a, b, api, leer}): leer() → {proyecto, subido, listo, estiloId, estilo, hook}
  function crear({ a, b, api, leer }) {
    let t = null, viva = false, pendiente = false, ver = 0, espera = false;
    const carga = (on) => [a, b].forEach((c) => c && c.classList.toggle("carga", on));

    // Un panel nunca queda vacío: o su cuadro, o una nota que dice qué pasa.
    function poner(c, url, nota) {
      if (!c) return;
      const im = c.querySelector("img");
      if (url && im?.getAttribute("src") !== url) c.innerHTML = `<img src="${url}" alt="">`;
      else if (!url && !im) c.innerHTML = "";
      c.querySelector(".nota")?.remove();
      if (nota) c.insertAdjacentHTML("beforeend", `<div class="nota">${esc(nota)}</div>`);
    }

    async function una(e, mia) {
      const nombre = (e.subido && e.subido.nombre) || e.proyecto;
      const vigente = () => !pendiente && ver === mia;   // ya pidieron otra cosa: este cuadro quedó viejo, no se pinta
      [a, b].forEach((c) => c && !c.querySelector("img") && poner(c, null, "Preparando la vista…"));
      const estilo = e.estiloId ? { ...e.estilo, id: e.estiloId } : e.estilo;   // el id del estilo viaja SIEMPRE: el motor reconoce el preset solo por él
      // con el video ya dirigido, lo que la persona tocó (SOLO eso: `e.cambios`) queda guardado en su storyboard; Edición avanzada mira sin guardar
      if (e.listo && e.guardar !== false && e.cambios && Object.keys(e.cambios).length) api("/api/estilo-guardar", { proyecto: e.proyecto, estilo: e.cambios });
      const r = await api("/api/previa-rapida", { nombre, video: e.subido && e.subido.video, proyecto: e.proyecto, estilo });
      if (!r.ok) return [a, b].forEach((c) => poner(c, null, r.error || "No pude preparar la vista."));
      const hechas = new Set();
      const tr = await esperar(api, r.trabajo, (t) => {   // la primera vista se pinta apenas está, sin esperar a la segunda
        if (!vigente()) return;
        for (const l of t.log || []) {
          if (!l.startsWith("/") || hechas.has(l)) continue;
          hechas.add(l);
          if (l.includes("previa-a.jpg")) poner(a, l); else if (l.includes("previa-b.jpg")) poner(b, l);
        }
      }, 250);
      if (!vigente()) return;
      if (tr.estado !== "listo") return [a, b].forEach((c) => poner(c, null, ultimo(tr) || "No pude preparar la vista."));
      if (tr.resultado.cancelada) return;
      poner(a, tr.resultado.a, tr.resultado.nota_a);
      poner(b, tr.resultado.b, tr.resultado.nota_b);
    }

    async function montar() {
      if (viva) { pendiente = true; return; }
      viva = true;
      try {
        do {
          pendiente = false;
          espera = false;   // en CADA vuelta: un cambio hecho mientras se dibujaba la vista anterior dejaba `espera` encendida y el
                            // círculo de «cargando» no se apagaba nunca, aunque la vista ya estuviera pintada (11-nov: «se queda pensando»)
          const e = leer(), mia = ver;
          if (!e.proyecto && !e.subido) { muestra(a, b, e); continue; }
          carga(true);
          await una(e, mia);
        } while (pendiente);
      } finally { viva = false; if (!espera) carga(false); }
    }

    const ctl = {
      // ya=true: sin espera. Sin video no hay servidor: se redibuja al instante.
      pedir(ya) {
        clearTimeout(t);
        const e = leer();
        if (!e.proyecto && !e.subido) return muestra(a, b, e);
        ver++;   // la que esté en marcha ya no es la última: su cuadro se descarta
        espera = true;
        carga(true);
        t = setTimeout(montar, ya ? 0 : ESPERA);
      },
      hayCuadro: () => !!a.querySelector("img"),
    };
    subCargado ? 0 : alCargarSub.push(() => ctl.pedir(true));   // cuando llega el catálogo, la muestra sin video se redibuja con la caja de serie correcta
    return ctl;
  }

  return { crear, muestra, esperar, ultimo, esc };
})();
