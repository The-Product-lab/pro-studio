// The Product Studio 2 · misma interfaz de la app anterior (Material → Estilo → Personalizar → Exportar) sobre el motor nuevo.
const $ = (s) => document.querySelector(s), $$ = (s) => [...document.querySelectorAll(s)];
const api = (ruta, cuerpo) => fetch(ruta, cuerpo ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(cuerpo) } : {})
  .then((r) => r.json()).catch(() => ({ ok: false, estado: "error", log: ["No pude hablar con el estudio. Revisa que siga abierto."], error: "No pude hablar con el estudio. Revisa que siga abierto." }));

let lib = { estilos: {}, fuentes: {}, tope_imagenes: { defecto: 0, paso: 0 } };
let proyecto = null;                 // id del proyecto en curso
let listo = false;                   // ¿el director ya terminó? Lo dice SIEMPRE el servidor (/api/proyecto), nunca un trabajo que acabó
let noExporta = null;                // por qué este video no se puede exportar ahora (texto del servidor); null = se puede
let fallo = null;                    // {proyecto, texto}: lo último que falló en este video; queda a la vista hasta que algo salga bien
let guionOk = false;                 // ¿el guion está aprobado? (habilita Estilos Pro, que parte del machote y no del director)
let subido = null;                   // {video, nombre}: para la vista rápida mientras el editor prepara
let estilo = { acento: "#FFE800", papel: "#E2D6BE", tinta: "#181614", persona: "bn", fuente: "Playfair" };
let cambios = {}, cambiosDe = null;                    // SOLO lo que la persona tocó en Personalizar: es lo único que se guarda (nunca el estilo entero)
let estiloId = null, foco = null;   // sin estilo por defecto: lo elige la persona (o viene del proyecto abierto)

// ---------- utilidades de la app anterior ----------
function aviso(t, ms = 2400) { const e = $("#toast"); e.textContent = t; e.classList.add("on"); clearTimeout(aviso.t); aviso.t = setTimeout(() => e.classList.remove("on"), ms); }
function cargando(on, txt) { if (txt) $("#cargandoTxt").textContent = txt; $("#cargando").classList.toggle("on", on); }
// Atrás/adelante del navegador = pantalla anterior/siguiente DENTRO de la app; el proyecto en curso y la pantalla se recuerdan
// (almacenamiento local, con try/catch) para reabrirlo solo al recargar o volver. Nada de esto toca el disco del estudio.
const MEMORIA = "tps2.enCurso";
const recordar = () => { try { localStorage.setItem(MEMORIA, JSON.stringify({ proyecto, pantalla: pantallaActual, estiloId })); } catch (e) { /* sin almacenamiento: no se recuerda */ } };
const recordado = () => { try { return JSON.parse(localStorage.getItem(MEMORIA) || "null") || {}; } catch (e) { return {}; } };
let pantallaActual = "mat";
function ir(v, deHistorial) {
  pantallaActual = v;
  if (!deHistorial && history.state?.v !== v) history.pushState({ v }, "", "#" + v);
  recordar();
  $$("#nav button").forEach((b) => b.classList.toggle("on", b.dataset.v === v));
  $$("main section").forEach((s) => s.classList.toggle("on", s.id === "s-" + v));
  if (v === "mat" && typeof biblioteca === "function") biblioteca();
  if (v === "gui") pintarGuion();
  if (v === "per") pintarPer();
  if (v === "exp") pintarExp();
}
$$("#nav button").forEach((b) => (b.onclick = () => ir(b.dataset.v)));
async function seguir(tid, cadaVez) {
  for (;;) {
    const t = await api(`/api/trabajo/${tid}`);
    cadaVez && cadaVez(t);
    if (t.estado !== "corriendo") return t;
    await new Promise((r) => setTimeout(r, 1200));
  }
}
const ultimo = (t) => (t.log || []).filter((l) => !l.startsWith("Traceback")).at(-1) || "";

// ---------- material ----------
$("#elegir").onclick = () => $("#file").click();
$("#file").onchange = (e) => { elegidos(e.target.files); e.target.value = ""; };   // se vacía: elegir otra vez el mismo archivo vuelve a avisar
const drop = $("#drop");
drop.ondragover = (e) => { e.preventDefault(); drop.classList.add("sobre"); };
drop.ondragleave = () => drop.classList.remove("sobre");
drop.ondrop = (e) => { e.preventDefault(); drop.classList.remove("sobre"); elegidos(e.dataTransfer.files); };

const nombreDe = (archivo) => archivo.replace(/\.[^.]+$/, "").toLowerCase().replace(/[^a-z0-9]+/g, "-") || "video";
const esVideo = (f) => (f.type || "").startsWith("video/") || /\.(mp4|mov|m4v|mkv|avi|webm|mxf|mts|3gp)$/i.test(f.name);
// Un archivo → ruta del video ya en el estudio. `avance(0..1)` mientras sube. Rechaza con la frase para la persona.
function subirArchivo(f, avance) {
  return new Promise((ok, mal) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `/api/subir?nombre=${encodeURIComponent(f.name)}`);
    xhr.upload.onprogress = (e) => e.total && avance && avance(e.loaded / e.total);
    xhr.onerror = () => mal(new Error("No pude hablar con el estudio. Revisa que siga abierto."));
    xhr.onload = () => {
      let r = null;
      try { r = JSON.parse(xhr.responseText); } catch (e) { /* respuesta rota: se dice abajo */ }
      if (r && r.ok && r.video) ok(r.video); else mal(new Error((r && r.error) || "La subida se cortó. Súbelo otra vez."));
    };
    xhr.send(f);
  });
}
async function subir(f) {
  $("#lista").innerHTML = `<div class="item"><img alt=""><div class="n">${escP(f.name)}<small id="lEst">Subiendo…</small><div class="barra"><i id="lPb"></i></div></div></div>`;
  let video;
  try { video = await subirArchivo(f, (p) => ($("#lPb").style.width = 100 * p + "%")); }
  catch (e) { $("#lEst").textContent = e.message; return aviso(e.message, 9000); }
  $("#lEst").textContent = "Subido";
  await preparar(video, nombreDe(f.name), false);
  biblioteca();
}

// ---------- varias partes: un video grabado en 2 o 3 archivos se une en uno antes de preparar (Pablo, 13-nov) ----------
// Se eligen o se sueltan juntas (o se van sumando), quedan en una lista ordenada por nombre (o por fecha) que se puede reordenar,
// y «Unir y preparar» las sube en ese orden y pide al estudio que las una (/api/unir); desde ahí sigue como un video cualquiera.
let partes = [], partesOrden = "nombre", uniendo = false;
function elegidos(lista) {
  const fs = [...(lista || [])].filter(esVideo);
  if (!fs.length) return lista && lista.length ? aviso("Eso no es un video.") : null;
  if (uniendo) return aviso("Espera a que termine de subir los archivos.");
  if (tanda && tanda.estado !== "lista") return aviso("Primero aprueba o descarta la revisión de archivos que tienes abierta.", 6000);
  if (tanda) { tandaVivo++; tanda = null; tandaRecordar(null); }
  if (fs.length === 1 && !partes.length) return subir(fs[0]);
  partes = partes.concat(fs.filter((f) => !partes.some((p) => p.name === f.name && p.size === f.size && p.lastModified === f.lastModified)));
  ordenarPartes(partesOrden === "mano" ? "nombre" : partesOrden);
}
function ordenarPartes(como) {
  partesOrden = como;
  if (como === "nombre") partes.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: "base" }));   // «parte 2» antes que «parte 10»
  if (como === "fecha") partes.sort((a, b) => a.lastModified - b.lastModified || a.name.localeCompare(b.name, undefined, { numeric: true }));
  pintarPartes();
}
function pintarPartes(estado) {
  if (!partes.length) { $("#lista").innerHTML = ""; return; }
  const peso = (n) => (n > 1e9 ? (n / 1e9).toFixed(1) + " GB" : Math.max(1, Math.round(n / 1e6)) + " MB");
  const fecha = (t) => new Date(t).toLocaleString("es", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  $("#lista").innerHTML = `<div class="partes${uniendo ? " ocupado" : ""}">
    <div class="pcabz"><b>${partes.length} ${partes.length === 1 ? "archivo" : "archivos"} de una grabación</b>
      <span class="seg" id="parOrden"><button data-o="nombre" class="${partesOrden === "nombre" ? "on" : ""}">Por nombre</button><button data-o="fecha" class="${partesOrden === "fecha" ? "on" : ""}">Por fecha</button></span></div>
    ${partes.map((f, i) => `<div class="item parte"><span class="num">${i + 1}</span><div class="n">${escP(f.name)}<small>${peso(f.size)} · ${fecha(f.lastModified)}</small></div>
      <button class="b" data-sube="${i}" title="Subir un puesto" aria-label="Subir un puesto"${i === 0 ? " disabled" : ""}>↑</button>
      <button class="b" data-baja="${i}" title="Bajar un puesto" aria-label="Bajar un puesto"${i === partes.length - 1 ? " disabled" : ""}>↓</button>
      <button class="b" data-quita="${i}" title="Quitar de la lista" aria-label="Quitar de la lista">×</button></div>`).join("")}
    <div id="parEstado" class="${estado && estado.error ? "err" : "aviso"}"${estado ? "" : " hidden"}>${estado ? escP(estado.texto) : ""}</div>
    <div class="barra${uniendo ? "" : " oculto"}"><i id="parPb"></i></div>
    <small class="aviso">«Ver cuántos videos salen» lee lo que se dice en cada archivo y propone qué archivos forman cada video (tú lo apruebas). «Unir todo» los pega en este orden en un solo video.</small>
    <div class="pie" style="justify-content:flex-end;flex-wrap:wrap"><button class="btn g chico" id="parCancelar">Cancelar</button><button class="btn g" id="parUnir"${partes.length < 2 ? " disabled" : ""}>Unir todo en un solo video</button><button class="btn" id="parRepartir">Ver cuántos videos salen</button></div></div>`;
  $("#parCancelar").onclick = () => { partes = []; pintarPartes(); };
  $("#parUnir").onclick = unirPartes;
  $("#parRepartir").onclick = repartirPartes;
  $$("#parOrden button").forEach((b) => (b.onclick = () => ordenarPartes(b.dataset.o)));
}
$("#lista").addEventListener("click", (e) => {
  const b = e.target.closest("button[data-sube],button[data-baja],button[data-quita]");
  if (!b || uniendo) return;
  const i = +(b.dataset.sube ?? b.dataset.baja ?? b.dataset.quita);
  if (b.dataset.quita !== undefined) partes.splice(i, 1);
  else { const j = b.dataset.sube !== undefined ? i - 1 : i + 1; [partes[i], partes[j]] = [partes[j], partes[i]]; partesOrden = "mano"; }   // orden a mano: ya no es por nombre ni por fecha
  pintarPartes();
});
async function unirPartes() {
  if (uniendo || partes.length < 2) return;
  uniendo = true;
  const lista = [...partes], total = lista.reduce((s, f) => s + f.size, 0) || 1, decir = (texto, error) => pintarPartes({ texto, error });
  try {
    const videos = [];
    let subido = 0;
    for (const [i, f] of lista.entries()) {
      decir(`Subiendo la parte ${i + 1} de ${lista.length}…`);
      $("#parPb").style.width = (90 * subido) / total + "%";
      videos.push(await subirArchivo(f, (p) => ($("#parPb").style.width = (90 * (subido + p * f.size)) / total + "%")));
      subido += f.size;
    }
    decir("Uniendo las partes en un solo video…");
    $("#parPb").style.width = "92%";
    const r = await api("/api/unir", { videos });
    if (!r.ok || !r.trabajo) throw new Error(r.error || "No se pudieron unir las partes.");
    const t = await seguir(r.trabajo);
    if (t.estado !== "listo") throw new Error(t.estado === "detenido" ? "Lo detuviste: las partes no se unieron." : ultimo(t) || "No se pudieron unir las partes.");
    uniendo = false;
    partes = [];
    const unido = String(t.resultado), archivo = unido.split(/[\\/]/).pop();   // la ruta puede venir de Windows
    $("#lista").innerHTML = `<div class="item"><img alt=""><div class="n">${escP(archivo)}<small>Partes unidas</small></div></div>`;
    await preparar(unido, nombreDe(archivo), false);
    biblioteca();
  } catch (e) {
    uniendo = false;
    decir(e.message, true);
  }
}

// ---------- una grabación en muchos archivos: cuántos videos salen (docs/PLANO-LOTE.md; Pablo, 13-nov) ----------
// Los archivos se suben, el estudio los transcribe uno por uno y propone los videos (qué archivos forman cada uno, en qué orden y
// qué tomas sobran). Aquí la persona aprueba, mueve tramos entre videos, junta o separa; cada cambio lo revisa el estudio (nada se
// pierde) y devuelve la propuesta ya corregida. Al aprobar, los videos se preparan uno tras otro y quedan como proyectos.
const TANDA_MEM = "tps2.tanda";
let tanda = null, tandaVivo = 0;
const tandaRecordar = (id) => { try { id ? localStorage.setItem(TANDA_MEM, id) : localStorage.removeItem(TANDA_MEM); } catch (e) { /* sin almacenamiento */ } };
async function repartirPartes() {
  if (uniendo || !partes.length) return;
  uniendo = true;
  const lista = [...partes], total = lista.reduce((s, f) => s + f.size, 0) || 1, decir = (texto, error) => pintarPartes({ texto, error });
  try {
    const videos = [];
    let subido = 0;
    for (const [i, f] of lista.entries()) {
      decir(`Subiendo el archivo ${i + 1} de ${lista.length}…`);
      $("#parPb").style.width = (100 * subido) / total + "%";
      videos.push(await subirArchivo(f, (p) => ($("#parPb").style.width = (100 * (subido + p * f.size)) / total + "%")));
      subido += f.size;
    }
    const r = await api("/api/tanda", { videos });
    if (!r.ok || !r.tanda) throw new Error(r.error || "No se pudo empezar a revisar los archivos.");
    uniendo = false;
    partes = [];
    tandaRecordar(r.tanda);
    seguirTanda(r.tanda);
  } catch (e) {
    uniendo = false;
    decir(e.message, true);
  }
}
async function seguirTanda(id) {   // pregunta hasta que haya algo que decidir (la propuesta) o todo esté preparado
  const mio = ++tandaVivo;
  for (;;) {
    const r = await api(`/api/tanda/${encodeURIComponent(id)}`);
    if (mio !== tandaVivo) return;
    if (!r.ok || !r.tanda) { tanda = null; tandaRecordar(null); $("#lista").innerHTML = `<p class="err">${escP(r.error || "Ya no encuentro esa tanda de archivos.")}</p>`; return; }
    tanda = r.tanda;
    pintarTanda(r);
    if (!r.trabajo) { if (tanda.estado === "lista") biblioteca(); return; }   // nada corriendo: ya se ve la propuesta, el resultado o el botón para seguir
    await new Promise((x) => setTimeout(x, 1500));
  }
}
const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
function pintarTanda(r) {
  const t = tanda, p = t.propuesta, corriendo = !!r.trabajo;
  const cerrar = `<button class="btn g chico" id="tanCerrar">${t.estado === "lista" ? "Cerrar" : "Descartar"}</button>`;
  let html = "";
  if (t.estado === "transcribiendo") {
    const hechos = t.archivos.filter((a) => a.estado !== "pendiente").length;
    html = `<div class="pcabz"><b>Revisando ${t.archivos.length} archivos: ${hechos} listos</b></div>
      ${corriendo ? `<p class="aviso"><span class="giro"></span> ${escP((r.paso || "empezando").replace(/…$/, ""))}…</p>` : `<p class="err">Esto se detuvo antes de terminar. Lo ya revisado se conserva.</p>`}
      ${t.archivos.map((a) => `<div class="item parte"><div class="n">${escP(a.nombre)}<small>${a.estado === "pendiente" ? "en fila" : a.estado === "sin_voz" ? "sin voz" : a.estado === "error" ? escP(a.motivo || "no se pudo leer") : escP(a.texto || "")}</small></div></div>`).join("")}
      <div class="pie" style="justify-content:flex-end">${cerrar}${corriendo ? "" : `<button class="btn" id="tanSeguir">Seguir</button>`}</div>`;
  } else if (t.estado === "propuesta" && p) {
    const destinos = (vi) => p.videos.map((v, k) => (k === vi ? "" : `<option value="v${k}">Video ${k + 1}</option>`)).join("") + `<option value="nuevo">Un video nuevo</option>${vi >= 0 ? `<option value="sobran">Sobran</option>` : ""}`;
    const rango = (x) => (x.entero ? "entero" : `${mmss(x.desde)}–${mmss(x.hasta)}`);
    html = `<div class="pcabz"><b>De ${t.archivos.length} ${t.archivos.length === 1 ? "archivo sale" : "archivos salen"} ${p.videos.length} ${p.videos.length === 1 ? "video" : "videos"}</b><small class="aviso">Revisa, mueve lo que haga falta y aprueba. Nada se prepara sin tu sí.</small></div>
      ${(t.avisos || []).map((a) => `<p class="err">${escP(a)}</p>`).join("")}
      ${p.videos.map((v, vi) => `<div class="tvideo"><div class="tcab"><span class="num">${vi + 1}</span><input class="ttit" data-tit="${vi}" value="${escP(v.titulo)}" maxlength="80" aria-label="Título del video ${vi + 1}">
          ${vi ? `<button class="btn g chico" data-junta="${vi}">Juntar con el anterior</button>` : ""}</div>
        ${v.idea ? `<small class="aviso">${escP(v.idea)}</small>` : ""}
        ${v.tramos.map((x, xi) => `<div class="item parte"><div class="n">${escP(x.nombre)} · ${rango(x)}<small>${escP(x.texto || "sin voz")}</small></div>
          <button class="b" data-tsube="${vi},${xi}" title="Subir un puesto"${xi ? "" : " disabled"}>↑</button><button class="b" data-tbaja="${vi},${xi}" title="Bajar un puesto"${xi < v.tramos.length - 1 ? "" : " disabled"}>↓</button>
          ${xi ? `<button class="btn g chico" data-separa="${vi},${xi}" title="Desde aquí empieza otro video">Separar aquí</button>` : ""}
          <select data-mueve="${vi},${xi}" aria-label="Mover a"><option value="">Mover a…</option>${destinos(vi)}</select></div>`).join("")}</div>`).join("")}
      ${p.sobran.length ? `<div class="tvideo sobra"><div class="tcab"><b>Sobran</b><small class="aviso">No entran a ningún video. Si alguno sí va, muévelo.</small></div>
        ${p.sobran.map((x, xi) => `<div class="item parte"><div class="n">${escP(x.nombre)} · ${rango(x)} · ${escP(x.motivo)}<small>${escP(x.texto || "sin voz")}</small></div>
          <select data-mueve="-1,${xi}" aria-label="Poner en"><option value="">Poner en…</option>${destinos(-1)}</select></div>`).join("")}</div>` : ""}
      <div class="pie" style="justify-content:flex-end">${cerrar}<button class="btn" id="tanAprobar">Aprobar y preparar ${p.videos.length === 1 ? "el video" : `los ${p.videos.length} videos`}</button></div>`;
  } else if (p) {   // preparando o lista: cada video con su estado; el que ya está se abre
    const listos = p.videos.filter((v) => v.estado === "listo").length;
    html = `<div class="pcabz"><b>${t.estado === "lista" ? `${listos} de ${p.videos.length} videos preparados` : `Preparando los videos, uno tras otro: ${listos} de ${p.videos.length}`}</b></div>
      ${corriendo ? `<p class="aviso"><span class="giro"></span> ${escP((r.paso || "").replace(/…$/, ""))}…</p>` : t.estado === "lista" ? "" : `<p class="err">Esto se detuvo antes de terminar. Lo ya preparado se conserva.</p>`}
      ${p.videos.map((v, vi) => `<div class="item parte"><span class="num">${vi + 1}</span><div class="n">${escP(v.titulo)}<small>${v.estado === "listo" ? "Listo: su guion te espera" : v.estado === "error" ? escP(v.error || "No se pudo preparar") : v.estado === "preparando" ? "Preparando…" : "En fila"}</small></div>
        ${v.estado === "listo" ? `<button class="btn g chico" data-abre="${escP(v.proyecto)}">Abrir</button>` : ""}</div>`).join("")}
      <div class="pie" style="justify-content:flex-end">${cerrar}${!corriendo && p.videos.some((v) => v.estado !== "listo") ? `<button class="btn" id="tanSeguir">${t.estado === "lista" ? "Reintentar los que faltan" : "Seguir"}</button>` : ""}</div>`;
  }
  $("#lista").innerHTML = `<div class="partes tanda">${html}</div>`;
  $("#tanCerrar").onclick = () => {
    if (t.estado !== "lista" && !confirm("¿Descartar esta revisión? Los archivos subidos no se borran, pero la propuesta se pierde.")) return;
    tandaVivo++; tanda = null; tandaRecordar(null); $("#lista").innerHTML = ""; biblioteca();
  };
  if ($("#tanSeguir")) $("#tanSeguir").onclick = async () => { const x = await api("/api/tanda-seguir", { tanda: t.id }); if (!x.ok) return aviso(x.error || "No se pudo seguir", 9000); seguirTanda(t.id); };
  if ($("#tanAprobar")) $("#tanAprobar").onclick = async () => {
    const n = p.videos.length;
    if (!confirm(`Se ${n === 1 ? "prepara 1 video" : `preparan ${n} videos, uno tras otro`} (guion de cada uno). ¿Aprobar este reparto?`)) return;
    const x = await api("/api/tanda-aprobar", { tanda: t.id });
    if (!x.ok) return aviso(x.error || "No se pudo empezar", 9000);
    seguirTanda(t.id);
  };
}
// Un cambio de la persona: se arma la propuesta nueva, el estudio la revisa y devuelve la que queda (con lo que corrigió, a la vista)
async function tandaCambiar(cambio) {
  const p = JSON.parse(JSON.stringify(tanda.propuesta));
  cambio(p);
  p.videos = p.videos.filter((v) => v.tramos.length);
  const r = await api("/api/tanda-propuesta", { tanda: tanda.id, videos: p.videos, sobran: p.sobran });
  if (!r.ok) return aviso(r.error || "No se pudo mover", 9000);
  tanda = r.tanda;
  pintarTanda({ trabajo: null });
}
$("#lista").addEventListener("click", async (e) => {
  if (!tanda) return;
  const b = e.target.closest("button");
  if (!b) return;
  const par = (s) => s.split(",").map(Number);
  if (b.dataset.abre) { await abrir(b.dataset.abre); return ir("gui"); }
  if (b.dataset.junta) { const vi = +b.dataset.junta; return tandaCambiar((p) => { p.videos[vi - 1].tramos.push(...p.videos[vi].tramos); p.videos.splice(vi, 1); }); }
  if (b.dataset.separa) { const [vi, xi] = par(b.dataset.separa); return tandaCambiar((p) => p.videos.splice(vi + 1, 0, { titulo: "", tramos: p.videos[vi].tramos.splice(xi) })); }
  if (b.dataset.tsube || b.dataset.tbaja) {
    const [vi, xi] = par(b.dataset.tsube || b.dataset.tbaja), j = b.dataset.tsube ? xi - 1 : xi + 1;
    return tandaCambiar((p) => { const ts = p.videos[vi].tramos; [ts[xi], ts[j]] = [ts[j], ts[xi]]; });
  }
});
$("#lista").addEventListener("change", (e) => {
  if (!tanda) return;
  if (e.target.dataset.tit !== undefined) { const vi = +e.target.dataset.tit, v = e.target.value.trim(); return tandaCambiar((p) => { p.videos[vi].titulo = v; }); }
  if (e.target.dataset.mueve === undefined || !e.target.value) return;
  const [vi, xi] = e.target.dataset.mueve.split(",").map(Number), a = e.target.value;
  tandaCambiar((p) => {
    const [x] = vi < 0 ? p.sobran.splice(xi, 1) : p.videos[vi].tramos.splice(xi, 1);
    if (a === "sobran") p.sobran.push({ ...x, motivo: "lo sacaste tú" });
    else if (a === "nuevo") p.videos.push({ titulo: "", tramos: [x] });
    else p.videos[+a.slice(1)].tramos.push(x);
  });
});

// El proyecto lo nombra el servidor, que reconoce el video por su contenido: el mismo video retoma lo hecho (y se dice);
// otro video con el mismo nombre de archivo abre uno nuevo. «Empezar de cero» rehace el mismo video sin tocar lo anterior.
async function preparar(video, nombre, deCero) {
  const r = await api("/api/preparar", { video, nombre, de_cero: deCero });   // solo trabajo neutro (guion, video, recorte): el estilo se decide después
  subido = { video, nombre: r.proyecto };
  await abrir(r.proyecto, r.trabajo);
  $("#guiYa").hidden = !r.ya_estaba;
  $("#guiDeCero").onclick = () => preparar(video, nombre, true);
  ir("gui");
}

// ---------- biblioteca: lo ya hecho, debajo del recuadro de subida ----------
const MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"];
let bibDatos = [], bibFiltro = "todos";
const esc = (t) => String(t ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
async function biblioteca() {
  const r = await api("/api/biblioteca/proyectos");
  if (!r.ok) return;
  bibDatos = r.proyectos;
  pintarBiblioteca();
}
function pintarBiblioteca() {
  const q = $("#bibQ").value.trim().toLowerCase();
  const vis = bibDatos.filter((p) => (bibFiltro === "todos" || (bibFiltro === "fin" ? p.estado === "final" : p.estado === "en proceso"))
    && (!q || `${p.nombre} ${p.id} ${p.estilo}`.toLowerCase().includes(q)));
  $("#bib").hidden = !bibDatos.length && !q;
  const hoy = new Date(), mesHoy = `${hoy.getFullYear()}-${hoy.getMonth()}`;
  const meses = new Map();
  for (const p of vis) {
    const d = new Date(p.t * 1000), k = `${d.getFullYear()}-${d.getMonth()}`;
    if (!meses.has(k)) meses.set(k, { titulo: `${MESES[d.getMonth()]} ${d.getFullYear()}`, ps: [] });
    meses.get(k).ps.push(p);
  }
  const dur = (s) => (s ? ` · ${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}` : "");
  $("#bibLista").innerHTML = !vis.length ? `<div class="bibvacio">${bibDatos.length ? "Nada con ese filtro" : "Todavía no hay videos editados"}</div>`
    : [...meses].map(([k, m]) => `<details ${k === mesHoy || q ? "open" : ""}><summary>${m.titulo}<small>${m.ps.length}</small></summary>${m.ps.map((p) => `
      <div class="bibfila">${p.miniatura ? `<img src="${esc(p.miniatura)}" alt="">` : `<span class="sinmini"></span>`}
        <div class="n">${esc(p.nombre)}<span class="bibchip ${p.estado === "final" ? "fin" : ""}">${esc(p.estado)}</span>
          <small>${p.fecha}${dur(p.duracion)}${p.estilo ? " · " + esc(p.estilo) : ""}</small></div>
        <div class="acc"><button class="btn g chico" data-abrir="${esc(p.id)}">Abrir</button>
          ${p.videos.map((v, i) => `<button class="btn g chico" data-ver="${esc(v.url)}">Ver${p.videos.length > 1 ? " " + esc(v.nombre) : ""}</button>`).join("")}
          ${p.videos.length ? `<button class="btn g chico" data-finder="${esc(p.id)}" data-archivo="${esc(p.videos[0].ruta)}">Mostrar en Finder</button>` : ""}</div>
      </div>`).join("")}</details>`).join("");
}
$("#bibQ").oninput = pintarBiblioteca;
$$("#bibF button").forEach((b) => (b.onclick = () => { bibFiltro = b.dataset.f; $$("#bibF button").forEach((x) => x.classList.toggle("on", x === b)); pintarBiblioteca(); }));
$("#bibLista").onclick = async (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.abrir) { await abrir(b.dataset.abrir); ir("gui"); }
  else if (b.dataset.ver) { const v = $("#bibVer video"); v.src = b.dataset.ver; $("#bibVer").hidden = false; v.play().catch(() => {}); }
  else if (b.dataset.finder) api("/api/finder", { proyecto: b.dataset.finder, archivo: b.dataset.archivo });
};
const cerrarVer = () => { const v = $("#bibVer video"); v.pause(); v.removeAttribute("src"); v.load(); $("#bibVer").hidden = true; };
$("#bibCerrar").onclick = cerrarVer;
$("#bibVer").onclick = (e) => e.target.id === "bibVer" && cerrarVer();

async function abrir(pid, tid) {
  $("#guiYa").hidden = true;
  const antes = recordado();
  proyecto = pid;
  // el estilo elegido se recuerda con el video: al recargar mientras el editor aún trabaja (todavía sin storyboard) la vista previa
  // se dibujaba sin estilo, con la persona en blanco y negro dentro de un marco de papel (11-nov: «¿por qué se ve ese montaje?»)
  recordar();
  const p = await api(`/api/proyecto/${pid}`);
  const elegido = p.estilo_elegido || (antes.proyecto === pid ? antes.estiloId : null);   // lo que sabe el proyecto; si aún no se mandó a editar, lo que se había marcado
  if (lib.estilos[elegido]) { estiloId = elegido; const { nombre, ...e } = lib.estilos[elegido]; estilo = { ...e }; recordar(); }
  estadoDe(p);
  if (p.storyboard.estilo) estilo = { ...estilo, ...p.storyboard.estilo };
  if (pid !== cambiosDe) { cambios = {}; cambiosDe = pid; }
  if (p.storyboard.estilo?.id && lib.estilos[p.storyboard.estilo.id]) estiloId = p.storyboard.estilo.id;
  tid = tid || p.trabajo;
  if (tid) vigilar(tid);
}

// El estado del video (¿ya está editado?, ¿se puede exportar?) sale del servidor. Antes, CUALQUIER trabajo que terminaba bien ponía
// «listo»: al acabar de preparar el material (sin haber editado nada) Exportar quedaba encendido, y el render fallaba con «Algo falló»
// porque no había diseño que exportar (13-nov, Mac nueva).
function estadoDe(p) {
  listo = !!p.listo;
  noExporta = p.no_exporta || null;
  guionOk = !!p.guion_aprobado;
}
async function refrescar() {
  if (!proyecto) return null;
  const pid = proyecto, p = await api(`/api/proyecto/${encodeURIComponent(pid)}`);
  if (p.ok === false || proyecto !== pid) return null;
  estadoDe(p);
  return p;
}
async function vigilar(tid) {
  const pid = proyecto;
  const t = await seguir(tid, (t) => {
    if (proyecto === pid && $("#s-per").classList.contains("on") && !listo) previaSiFalta();
  });
  if (proyecto !== pid) return;   // mientras tanto se abrió otro video: este resultado ya no es de la pantalla
  await refrescar();
  if (t.estado === "error") {     // queda escrito en la pantalla (Guion y Exportar lo muestran), no solo en un aviso que se va
    fallo = { proyecto: pid, texto: ultimo(t) };
    aviso(fallo.texto, 9000);
  } else if (t.estado === "listo") fallo = null;
  if (listo && $("#s-per").classList.contains("on")) pintarPer();
  if ($("#s-exp").classList.contains("on")) pintarExp();
}

// ---------- guion: todo lo que se dijo, la persona decide qué queda y lo aprueba ----------
// La pantalla NO corta nada: manda al motor los índices de las palabras que quedan (POST /api/guion-editar) y vuelve a pintar lo que
// el motor respondió (los cortes ya hechos). Lo que el motor no pudo cumplir llega en `no_se_pudo` y se dice arriba; nunca se calla.
let guiVivo = 0;
let G = null;                         // el guion editable que mandó el motor: {firma, palabras, frases, duracion_s, problemas}
const guiQuiere = new Set();          // índices de las palabras que la persona quiere que queden
let guiBase = new Set();              // …y las que quedan hoy en los cortes del motor
let guiAvisos = [];                   // lo que el motor no pudo cumplir en la última corrección
const GUI_CHECK = '<svg width="11" height="11" viewBox="0 0 14 14"><path d="M2.5 7.4l2.9 2.9 6-6.2" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';
const guiCambios = () => [...guiQuiere].filter((k) => !guiBase.has(k)).length + [...guiBase].filter((k) => !guiQuiere.has(k)).length;

function guiCargar(edicion, avisos = []) {
  G = edicion; guiAvisos = avisos;
  guiBase = new Set(G.palabras.filter((p) => p.queda).map((p) => p.k));
  guiQuiere.clear(); guiBase.forEach((k) => guiQuiere.add(k));
  guiPintar();
}
function guiPintar() {
  const cambios = guiCambios(), porPalabra = new Map(G.problemas.filter((x) => x.k !== null).map((x) => [x.k, x.texto]));
  $("#guiTxt").innerHTML = G.frases.map(([a, b], i) => {
    const ps = G.palabras.slice(a, b), n = ps.filter((p) => guiQuiere.has(p.k)).length;
    const motivo = n === ps.length ? "" : [...new Set(ps.filter((p) => !guiQuiere.has(p.k) && p.motivo).map((p) => p.motivo))][0] || "";
    const tocada = ps.some((p) => guiQuiere.has(p.k) !== guiBase.has(p.k));   // el aviso solo se quita de la frase que se está corrigiendo; los demás siguen a la vista
    const probs = tocada ? [] : ps.filter((p) => porPalabra.has(p.k)).map((p) => porPalabra.get(p.k));
    const baja = ps.filter((p) => p.baja).length * 2 > ps.length;
    return `<div class="fr ${n === ps.length ? "si" : n ? "medio" : "no"}"><button class="todo" data-todo="${i}" title="Dejar o quitar la frase entera" aria-label="Dejar o quitar la frase entera">${GUI_CHECK}</button>
      <div class="tx">${ps.map((p) => `<span data-k="${p.k}" class="${guiQuiere.has(p.k) ? "" : "no"}${guiQuiere.has(p.k) !== guiBase.has(p.k) ? " cambio" : ""}${!tocada && porPalabra.has(p.k) ? " ojo" : ""}">${escP(p.w)}</span>`).join(" ")}</div>
      <div class="nota">${probs.map((t) => `<span class="prob">${escP(t)}</span>`).join("")}${escP(motivo)}${baja ? '<span class="tag">voz baja</span>' : ""}</div></div>`;
  }).join("");
  const generales = G.problemas.filter((x) => x.k === null).map((x) => x.texto), enFrases = G.problemas.length - generales.length;
  const lineas = [...(cambios ? [] : guiAvisos), ...generales, ...(enFrases ? [`<b>${enFrases === 1 ? "Hay 1 detalle señalado" : `Hay ${enFrases} detalles señalados`} en rojo.</b> Puedes corregirlos o aprobar así: tú decides.`] : [])];
  $("#guiProb").innerHTML = lineas.map((t) => `<p>${t.startsWith("<b>") ? t : escP(t)}</p>`).join("");
  $("#guiProb").hidden = !lineas.length;
  $("#guiCuenta").innerHTML = `<b>${guiQuiere.size}</b> palabras quedan de ${G.palabras.length}` + (cambios ? ` · <b>${cambios}</b> ${cambios === 1 ? "cambio" : "cambios"} sin aplicar` : ` · ${Number(G.duracion_s || 0).toFixed(1).replace(".", ",")} s de video`);
  $("#guiAplicar").disabled = $("#guiDeshacer").disabled = !cambios;
  $("#guiOk").disabled = !!cambios || generales.length > 0;   // se aprueba exactamente lo que se va a cortar; los detalles de montaje los decide la persona
  $("#guiOk").textContent = !cambios && enFrases ? "Aprobar así" : "Aprobar";
}
function guiModo(editable) {
  $("#guiCab").classList.toggle("oculto", !editable);
  $("#guiAplicar").classList.toggle("oculto", !editable); $("#guiDeshacer").classList.toggle("oculto", !editable);
  if (!editable) { G = null; $("#guiProb").hidden = true; $("#guiCuenta").textContent = ""; }
}
async function pintarGuion() {
  const mio = ++guiVivo, caja = $("#guiTxt");
  $("#guiOk").disabled = true;
  guiModo(false);
  if (!proyecto) { caja.innerHTML = ""; return; }
  for (;;) {
    const g = await api(`/api/guion/${encodeURIComponent(proyecto)}`);
    if (mio !== guiVivo || !$("#s-gui").classList.contains("on")) return;
    if (g.listo && g.edicion) { guiModo(true); return guiCargar(g.edicion); }
    if (g.listo) {   // proyecto sin audio medido (viejo): solo lectura, como antes
      caja.innerHTML = g.palabras.length ? `<p>${g.palabras.map((p) => `<span${p.fuera ? ' class="tenue"' : ""}>${escP(p.w)}</span>`).join(" ")}</p>` : "";
      $("#guiOk").disabled = false;
      return;
    }
    if (g.parado) {   // nadie lo está preparando (falló o la app se cerró a la mitad): se dice por qué y se puede reintentar
      caja.innerHTML = `<div class="prep parado"><p class="err">${escP(g.parado)}</p><button class="btn" id="guiReintentar">Reintentar</button></div>`;
      $("#guiReintentar").onclick = async () => {
        const r = await api("/api/preparar", { proyecto, reintentar: true });
        if (!r.ok) return aviso(r.error || "No se pudo reintentar", 9000);
        fallo = null;
        vigilar(r.trabajo);
        pintarGuion();
      };
      return;
    }
    caja.innerHTML = '<p class="prep"><span class="giro"></span>Preparando tu guion…</p>';
    await new Promise((r) => setTimeout(r, 2500));
  }
}
$("#guiTxt").onclick = (e) => {
  if (!G) return;
  const s = e.target.closest("[data-k]"), t = e.target.closest("[data-todo]");
  if (s) { const k = +s.dataset.k; if (guiQuiere.has(k)) guiQuiere.delete(k); else guiQuiere.add(k); }
  else if (t) {
    const [a, b] = G.frases[+t.dataset.todo], ks = G.palabras.slice(a, b).map((p) => p.k), todas = ks.every((k) => guiQuiere.has(k));
    ks.forEach((k) => (todas ? guiQuiere.delete(k) : guiQuiere.add(k)));
  } else return;
  const y = $("#guiTxt").scrollTop;
  guiPintar();
  $("#guiTxt").scrollTop = y;
};
$("#guiDeshacer").onclick = () => { guiQuiere.clear(); guiBase.forEach((k) => guiQuiere.add(k)); guiPintar(); };
$("#guiAplicar").onclick = async () => {
  if (!G || !guiCambios()) return;
  if (!guiQuiere.size) return aviso("Deja al menos una frase.");
  const mio = guiVivo, y = $("#guiTxt").scrollTop;
  $(".gui").classList.add("ocupado");
  $("#guiAplicar").disabled = $("#guiDeshacer").disabled = true;
  $("#guiAplicar").textContent = "Aplicando…";
  const r = await api("/api/guion-editar", { proyecto, firma: G.firma, quedan: [...guiQuiere] });
  $("#guiAplicar").textContent = "Aplicar cambios";
  $(".gui").classList.remove("ocupado");
  if (mio !== guiVivo) return;
  if (!r.ok && r.guion_nuevo) { aviso(r.error); return pintarGuion(); }
  if (!r.ok) { aviso(r.error || "No se pudo aplicar"); return guiPintar(); }
  guionOk = false;
  guiCargar(r.edicion, r.edicion.no_se_pudo || []);
  $("#guiTxt").scrollTop = y;
};
$("#guiOk").onclick = async () => {
  $("#guiOk").disabled = true;
  const r = await api("/api/seleccion", { proyecto, guion_aprobado: true, con_detalles: !!G });   // con el editor a la vista, la persona vio los detalles señalados
  if (!r.ok && r.guion_nuevo) { aviso(r.error); return pintarGuion(); }   // el sistema cambió el guion: se vuelve a mostrar y la persona lo aprueba viéndolo
  if (!r.ok) { aviso(r.error || "No se pudo aprobar"); return pintarGuion(); }
  guionOk = true;
  ir("est");
};

// ---------- estilo (carrusel tipo streaming, solo flechas) ----------
function construirEstilos() {
  $("#riel").innerHTML = "";
  const aprobados = (lib.aprobados || []).filter((id) => lib.estilos[id]);
  const orden = aprobados.length ? aprobados : Object.keys(lib.estilos);   // la lista y su orden vienen del motor (catalogo.en_pantalla)
  for (const id of orden) {
    const e = lib.estilos[id];
    const c = document.createElement("div");
    c.className = "card" + (id === estiloId ? " sel" : "");
    c.dataset.id = id;
    c.tabIndex = 0;
    c.innerHTML = `<div class="cv"><img src="/app/muestras/${id}.jpg" alt=""></div><b>${e.nombre}</b><button class="btn bl elegir">Editar con este estilo</button>`;
    c.onfocus = () => ponerFoco(id);
    c.onclick = () => seleccionar(id);   // un clic en la tarjeta SOLO selecciona: no gasta nada
    c.querySelector(".elegir").onclick = (ev) => { ev.stopPropagation(); editarConEstilo(id); };
    $("#riel").append(c);
  }
  ponerFoco(lib.estilos[estiloId] && orden.includes(estiloId) ? estiloId : orden[0]);
}
function ponerFoco(id) {
  foco = id;
  $$("#riel .card").forEach((c) => c.classList.toggle("foco", c.dataset.id === id));
}
const tarjetas = () => [...$$("#riel .card")];
function irA(k, suave = true) {   // la tarjeta k, lo más a la izquierda que el riel permita, y en foco
  const cards = tarjetas();
  if (!cards.length) return;
  k = Math.max(0, Math.min(cards.length - 1, k));
  const riel = $("#riel");
  riel.scrollTo({ left: cards[k].offsetLeft - parseFloat(getComputedStyle(riel).paddingLeft), behavior: suave ? "smooth" : "auto" });
  ponerFoco(cards[k].dataset.id);
  return k;
}
const indiceFoco = () => Math.max(0, tarjetas().findIndex((c) => c.dataset.id === foco));
// paso manual (flechas, teclas): una tarjeta hacia el lado
const pasoEstilo = (dir) => irA(indiceFoco() + dir);
document.addEventListener("keydown", (e) => {
  if ($("#s-est").offsetParent === null) return;
  if (e.key === "ArrowRight" || e.key === "ArrowLeft") { pasoEstilo(e.key === "ArrowRight" ? 1 : -1); }
});
$$(".fl").forEach((b) => (b.onclick = () => pasoEstilo(b.classList.contains("d") ? 1 : -1)));
async function dirigirConEstilo(id) {   // la orden de la persona: recién ahora el director trabaja, con ESTE estilo
  if (!proyecto) return;
  const r = await api("/api/dirigir", { proyecto, estilo: id, imagenes: conImagenes, confirmado: true });
  if (!r.ok) return aviso(r.error || "No se pudo empezar el diseño", 9000);
  listo = false;   // solo si el diseño de verdad arrancó: si el servidor lo rechaza, el video ya diseñado sigue listo para exportar
  fallo = null;
  vigilar(r.trabajo);
}
function seleccionar(id) {   // solo marca la tarjeta; el preset completo queda listo, pero nada se dirige ni se gasta
  estiloId = id;
  recordar();
  const { nombre, ...e } = lib.estilos[id];
  estilo = { ...e };   // el preset COMPLETO del estilo elegido, nunca mezclado con restos del anterior
  cambios = {};        // el director deja el preset en el storyboard; lo que la persona toque después se suma encima
  $$("#riel .card").forEach((c) => c.classList.toggle("sel", c.dataset.id === id));
  ponerFoco(id);
}
// Cada estilo tiene dos variantes: con imágenes (el director pide arte a Higgsfield) o sin imágenes (lo resuelve con textos y trazos).
let conImagenes = true;
$$("#conImg button").forEach((b) => (b.onclick = () => {
  conImagenes = b.dataset.i === "1";
  $$("#conImg button").forEach((x) => x.classList.toggle("on", x === b));
}));
function editarConEstilo(id) {   // el botón explícito: edición completa (director Opus), con aviso
  // el aviso dice lo que ESE estilo va a gastar: uno sin director (Básico) solo pone subtítulos, sin IA ni imágenes
  const aviso_ = lib.estilos[id]?.sin_director
    ? "Este estilo solo pone los subtítulos: no usa IA ni imágenes. ¿Editar con este estilo?"
    : `Esto es una edición completa: usa IA (el director), ${conImagenes ? "con imágenes" : "sin imágenes"}. ¿Editar con este estilo?`;
  if (!window.confirm(aviso_)) return;
  seleccionar(id);
  dirigirConEstilo(id);
  ir("per");
  previsualizar(true);
}

// ---------- personalizar ----------
// ---------- personalizar (Pablo, 07-nov: «hay demasiadas opciones… necesito que sea mucho más simple») ----------
// Tres columnas: a la izquierda cómo se ve CON la persona; en el centro lo esencial para configurar (todo lo demás sale con los
// valores del estilo; lo fino está en «Más ajustes» y en Edición avanzada); a la derecha el APOYO a pantalla completa.
// Las opciones salen del catálogo del código (/api/catalogo): nada a mano.
let catP = null, subCat = null;
const abiertas = new Set(JSON.parse(localStorage.getItem("tps-per-secciones") || '["persona","textos","subtitulos","hook","edicion","sonido"]'));
const catDe = (id) => catP?.find((c) => c.id === id);
const escP = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
function muestraDe(cat, id) {   // imagen fija de una opción (miniatura): la jpg o el póster del video
  const o = catDe(cat)?.opciones.find((x) => x.id === id);
  if (o) return o.poster || (o.muestra && !/\.mp4/.test(o.muestra) ? o.muestra : null);
  return lib.muestras?.[`${cat}:${id}`] || null;
}
function miniatura(img, nombre, on, datos, titulo, video) {
  if (!img) return `<button class="chip${on ? " on" : ""}" ${datos} title="${escP(titulo || "")}">${escP(nombre)}</button>`;
  return `<button class="mq${on ? " on" : ""}" ${datos} title="${escP(titulo || nombre)}"${video ? ` data-vid="${escP(video)}"` : ""}><span class="mqv"><img src="${escP(img)}" alt="" decoding="async"></span><small>${escP(nombre)}</small></button>`;
}
function grilla(botones) { return `<div class="mqs">${botones.join("")}</div>`; }
function bloque(titulo, cuerpo) { return `<div class="bq"><h3 class="sub">${titulo}</h3>${cuerpo}</div>`; }
function seccion(id, titulo, resumen, cuerpo) {
  return `<details class="sec" data-s="${id}"${abiertas.has(id) ? " open" : ""}><summary><b>${titulo}</b><small>${escP(resumen || "")}</small></summary><div class="secb">${cuerpo}</div></details>`;
}
function puntos(clave) {   // colores que ya usan los estilos (sin rosa) + gotero
  const ops = catDe(clave)?.opciones || [];
  const v = (estilo[clave] || "").toUpperCase();
  const propio = v && !ops.some((o) => o.id === v);
  return `<div class="puntos">${ops.map((o) => `<button class="pt${v === o.id ? " on" : ""}" data-k="${clave}" data-v="${o.id}" title="${escP(o.nota)}"><i style="background:${o.id}"></i></button>`).join("")}
    <label class="pt gotero${propio ? " on" : ""}" title="Otro color"><i style="${propio ? `background:${v}` : ""}"></i><input type="color" data-gk="${clave}" value="${propio ? v : "#ffffff"}"></label></div>`;
}
const seg = (botones) => `<div class="seg">${botones.join("")}</div>`;
let hookEst = null, hookDe = null;   // {si, texto, tipo, caja, color} del proyecto en curso (se pide una vez)
const MAX_HOOK = 120;
const PARADAS = ["Sencilla", "Media", "Pro"];
const topeMedio = () => lib.estilos[estiloId]?.tope_imagenes ?? lib.tope_imagenes.defecto;   // los números viven en config.py (/api/librerias)
const edicionDe = (i) => ({ tope_imagenes: [Math.max(1, topeMedio() - lib.tope_imagenes.paso), topeMedio(), topeMedio() + lib.tope_imagenes.paso][i] });
const paradaDe = () => { const t = estilo.tope_imagenes ?? topeMedio(); return t < topeMedio() ? 0 : t > topeMedio() ? 2 : 1; };
const guardarHook = async (c) => { const r = await api("/api/seleccion", { proyecto, ...c }); if (!r.ok) aviso(r.error || "No se pudo guardar el hook"); return r.ok; };
async function guardarHookDelVideo() {   // Seguir guarda todo, también el hook
  if (!proyecto || !hookEst?.si) return;
  await guardarHook({ hook_texto: hookEst.texto.trim() || null, hook_caja: hookEst.caja, hook_color: hookEst.color, repertorio: { hooks: hookEst.tipo ? [hookEst.tipo] : [] } });
}
function pintarHook() {
  const h = hookEst || { si: false, texto: "", tipo: null, caja: true, color: null };
  const tipos = catDe("hooks")?.opciones || [];
  const col = (h.color || "").toUpperCase();
  const ops = catDe("acento")?.opciones || [];
  const propio = col && !ops.some((o) => o.id === col);
  return seg([[true, "Sí"], [false, "No"]].map(([v, n]) => `<button data-hook-si="${v}" class="${h.si === v ? "on" : ""}">${n}</button>`)) +
    (h.si ? `<h3 class="sub" style="margin-top:20px">¿Qué quieres que diga el hook?</h3><textarea id="hookTxt" rows="2" maxlength="${MAX_HOOK}">${escP(h.texto)}</textarea>
      <h3 class="sub" style="margin-top:20px">Caja</h3>${seg([[true, "Con caja"], [false, "Solo texto"]].map(([v, n]) => `<button data-hook-caja="${v}" class="${h.caja === v ? "on" : ""}">${n}</button>`))}
      <h3 class="sub" style="margin-top:20px">Color</h3><div class="puntos">${ops.map((o) => `<button class="pt${col === o.id ? " on" : ""}" data-hook-color="${o.id}" title="${escP(o.nota)}"><i style="background:${o.id}"></i></button>`).join("")}
        <label class="pt gotero${propio ? " on" : ""}" title="Otro color"><i style="${propio ? `background:${col}` : ""}"></i><input type="color" data-hook-gotero value="${propio ? col : "#ffffff"}"></label></div>
      ${tipos.length ? `<div style="margin-top:20px">${grilla(tipos.map((o) => miniatura(o.poster, o.nombre, h.tipo === o.id, `data-hk="${escP(o.id)}"`, o.nota, o.muestra)))}</div>` : ""}` : "");
}
const looksDe = () => catDe("look")?.opciones || [];
function pintarLooks() {
  const c = estilo.color || {};
  const sin = lib.muestras?.["color:sin"];
  return grilla([miniatura(sin, "Original", !c.look, `data-look=""`),
    ...looksDe().map((o) => miniatura(muestraDe("look", o.id), o.nombre, c.look === o.id, `data-look="${escP(o.id)}"`))]);
}
function cambiarLook(id) {
  const o = looksDe().find((x) => x.id === id);
  cambiar({ color: o ? { look: id, fuerza: o.fuerza } : {}, persona: "color" });
}

// Subtítulos (Pablo, 10-nov): las MISMAS opciones para cualquier forma (tira, vidrio, hud, básico); lo que una forma no admite sale apagado con su
// motivo (viene del código: /api/catalogo › subtitulo). Nada elegido = el subtítulo de siempre del estilo.
const subFormas = () => Object.entries(subCat?.tipos || {}).filter(([, t]) => t.forma).map(([id, t]) => [id, t.nombre]);   // las formas salen del código
const subColores = () => ["#FFFFFF", "#111111", ...(catDe("acento")?.opciones || []).map((o) => o.id.toUpperCase())].filter((c, i, a) => a.indexOf(c) === i);
function subPuntos(k) {
  const v = (estilo[k] || "").toUpperCase(), ops = subColores(), propio = v && !ops.includes(v);
  return `<div class="puntos"><button class="chip${v ? "" : " on"}" data-sk="${k}" data-sv="">Del estilo</button>${ops.map((c) => `<button class="pt${v === c ? " on" : ""}" data-sk="${k}" data-sv="${c}"><i style="background:${c}"></i></button>`).join("")}
    <label class="pt gotero${propio ? " on" : ""}" title="Otro color"><i style="${propio ? `background:${v}` : ""}"></i><input type="color" data-sgk="${k}" value="${propio ? v : "#ffffff"}"></label></div>`;
}
const subVal = (k) => estilo[k] ?? lib.estilos[estiloId]?.[k] ?? null;   // lo elegido, y si no (null = «Del estilo»), lo del preset
function pintarSub(fuentes) {
  const tipo = estilo.subtitulo || "tira", t = subCat?.tipos?.[tipo];
  if (!t) return "";
  const caja = subVal("sub_caja") ?? t.caja;
  const fila = (k, titulo, cuerpo, motivo) => {
    const off = t.soporte[k] || motivo;
    const nota = t.notas[k] ? `<p class="aviso">${escP(t.notas[k])}</p>` : "";
    return off ? `<div class="bq apagado"><h3 class="sub">${titulo}</h3><p class="aviso">${escP(off)}</p></div>` : bloque(titulo, cuerpo + nota);
  };
  const efectos = [[null, "Del estilo"], ...subCat.efectos.map((e) => [e.id, e.nombre])];
  return (tipo === "basico" ? "" : bloque("Forma", seg(subFormas().map(([v, n]) => `<button data-sub="${v}" class="${tipo === v ? "on" : ""}">${n}</button>`)))) +
    fila("sub_caja", "Caja", seg([[true, "Sí"], [false, "No"]].map(([v, n]) => `<button data-sc="${v}" class="${caja === v ? "on" : ""}">${n}</button>`))) +
    fila("sub_caja_color", "Color de la caja", subPuntos("sub_caja_color"), caja ? "" : "Sin caja no hay color de caja: pon la caja en Sí.") +
    fila("sub_color", "Color del texto", subPuntos("sub_color")) +
    fila("sub_clave", "Color de la palabra clave", subPuntos("sub_clave")) +
    fila("sub_efecto", "Efecto de entrada", seg(efectos.map(([v, n]) => `<button data-se="${v ?? ""}" class="${(estilo.sub_efecto ?? null) === v ? "on" : ""}">${n}</button>`))) +
    fila("sub_fuente", "Tipografía", `<button class="chip${estilo.sub_fuente ? "" : " on"}" data-sk="sub_fuente" data-sv="">Del estilo</button>` + fuentes("sub_fuente"));
}
// «Del estilo» manda null: el servidor vuelve al valor del preset (no lo borra: Básico trae sus propios sub_*). Pasa por `cambiar`, como todo control.
function fijarSub(k, v) { cambiar({ [k]: v === "" || v === undefined ? null : v }); }

function pintarPer() {
  const pcb = $("#pcb");
  if (!catP) {   // el catálogo se pide una vez (el servidor lo tiene en caché)
    api("/api/catalogo").then((r) => { catP = r.categorias || []; subCat = r.subtitulo || null; pintarPer(); }).catch(() => { catP = []; });
  }
  if (!proyecto && !hookEst) hookEst = { si: false, texto: "", tipo: null, caja: true, color: null };
  if (proyecto && hookDe !== proyecto) {   // el hook que ya dejó la persona, una vez por video
    hookDe = proyecto;
    hookEst = null;
    api(`/api/seleccion/${encodeURIComponent(proyecto)}`).then((r) => {
      const p = r.preferencias || {};
      hookEst = { si: !!p.hook_texto, texto: p.hook_texto || "", tipo: (p.repertorio?.hooks || [])[0] || null, caja: p.hook_caja !== false, color: p.hook_color || null };
      pintarPer();
    });
  }
  const st = scrollY, sc = pcb.scrollTop;
  const fuentes = (r) => `<div class="opc">${Object.entries(lib.fuentes).map(([f, nota]) => `<button class="aa${estilo[r] === f ? " on" : ""}" data-fr="${r}" data-f="${f}" title="${nota}"><span style="font-family:'tps-${f}'">Aa</span><small>${f}</small></button>`).join("")}</div>`;
  pcb.innerHTML = `<div class="pcab"><h1>${escP(lib.estilos[estiloId]?.nombre || "Personalizar")}</h1><button class="btn g chico" id="cambiarEstilo">Cambiar de estilo</button></div>` +
    (looksDe().length ? seccion("persona", "Color de la persona", "", pintarLooks()) : "") +
    seccion("textos", "Textos", "", bloque("Tipografía", fuentes("fuente")) + bloque("Color del texto grande", puntos("acento")) + bloque("Color de los textos pequeños", puntos("texto"))) +
    seccion("subtitulos", "Subtítulos", "", pintarSub(fuentes)) +
    seccion("hook", "Hook al inicio", "", pintarHook()) +
    seccion("edicion", "Cantidad de edición", "", seg(PARADAS.map((n, i) => `<button data-ed="${i}" class="${paradaDe() === i ? "on" : ""}">${n}</button>`))) +
    seccion("sonido", "Sonido", "", `<button class="chip${(estilo.sfx ?? .28) > 0 ? " on" : ""}" id="sfxOn">Integrar efectos de sonido</button>`) +
    seccion("mas", "Más ajustes", "", `
      <h3 class="sub">Otra letra</h3>
      <div class="fila" style="gap:8px"><input id="gfTxt" placeholder="Buscar en Google Fonts" style="flex:1"><button class="btn g chico" id="gfBuscar">Buscar</button></div>
      <div class="chips" id="gfRes" style="margin-top:8px"></div>`) +
    `<a class="btn g chico mas" href="/seleccionador${proyecto ? "?p=" + encodeURIComponent(proyecto) : ""}">Edición avanzada</a>`;
  // Un estilo sin director (Básico) es solo subtítulos: no tiene textos grandes, hook, apoyos, cantidad de edición ni efectos de sonido.
  // Personalizar no los ofrece ni muestra la vista de apoyo (Pablo, 11-nov: «es únicamente subtítulos, abajito, chiquitos y ya»).
  $(".per").classList.toggle("solo-sub", !!lib.estilos[estiloId]?.sin_director);
  pcb.scrollTop = sc; window.scrollTo(0, st);
  pcb.querySelectorAll("details.sec").forEach((d) => (d.ontoggle = () => {
    d.open ? abiertas.add(d.dataset.s) : abiertas.delete(d.dataset.s);
    localStorage.setItem("tps-per-secciones", JSON.stringify([...abiertas]));
  }));
  pcb.querySelectorAll(".pt[data-k]").forEach((b) => (b.onclick = () => cambiar({ [b.dataset.k]: b.dataset.v })));
  pcb.querySelectorAll("[data-gk]").forEach((g) => (g.onchange = () => cambiar({ [g.dataset.gk]: g.value.toUpperCase() })));
  pcb.querySelectorAll("[data-fr]").forEach((b) => (b.onclick = () => cambiar({ [b.dataset.fr]: b.dataset.f })));
  pcb.querySelectorAll("[data-look]").forEach((b) => (b.onclick = () => cambiarLook(b.dataset.look)));
  pcb.querySelectorAll("[data-ed]").forEach((b) => (b.onclick = () => cambiar(edicionDe(+b.dataset.ed))));
  $("#sfxOn").onclick = () => cambiar({ sfx: (estilo.sfx ?? .28) > 0 ? 0 : lib.estilos[estiloId]?.sfx || .28 });
  pcb.querySelectorAll("[data-hook-si]").forEach((b) => (b.onclick = async () => {
    const si = b.dataset.hookSi === "true";
    hookEst = { caja: true, color: null, ...(hookEst || { texto: "", tipo: null }), si };
    if (!si) { hookEst.texto = ""; hookEst.tipo = null; if (proyecto) await guardarHook({ hook_texto: null, hook_caja: null, hook_color: null, repertorio: { hooks: [] } }); }
    pintarPer();
  }));
  pcb.querySelectorAll("[data-hk]").forEach((b) => (b.onclick = () => { hookEst = { ...hookEst, texto: $("#hookTxt").value, tipo: hookEst.tipo === b.dataset.hk ? null : b.dataset.hk }; pintarPer(); }));
  if ($("#hookTxt")) $("#hookTxt").oninput = (e) => { hookEst.texto = e.target.value; };
  pcb.querySelectorAll("[data-hook-caja]").forEach((b) => (b.onclick = () => { hookEst = { ...hookEst, texto: $("#hookTxt").value, caja: b.dataset.hookCaja === "true" }; pintarPer(); }));
  pcb.querySelectorAll("[data-hook-color]").forEach((b) => (b.onclick = () => { hookEst = { ...hookEst, texto: $("#hookTxt").value, color: hookEst.color === b.dataset.hookColor ? null : b.dataset.hookColor }; pintarPer(); }));
  pcb.querySelectorAll("[data-hook-gotero]").forEach((g) => (g.onchange = () => { hookEst = { ...hookEst, texto: $("#hookTxt").value, color: g.value.toUpperCase() }; pintarPer(); }));
  pcb.querySelectorAll("[data-sub]").forEach((b) => (b.onclick = () => cambiar({ subtitulo: b.dataset.sub })));
  pcb.querySelectorAll("[data-sk]").forEach((b) => (b.onclick = () => fijarSub(b.dataset.sk, b.dataset.sv)));
  pcb.querySelectorAll("[data-sgk]").forEach((g) => (g.onchange = () => fijarSub(g.dataset.sgk, g.value.toUpperCase())));
  pcb.querySelectorAll("[data-sc]").forEach((b) => (b.onclick = () => fijarSub("sub_caja", b.dataset.sc === "true")));
  pcb.querySelectorAll("[data-se]").forEach((b) => (b.onclick = () => fijarSub("sub_efecto", b.dataset.se)));
  pcb.querySelectorAll(".mq[data-vid]").forEach((b) => {   // el video de la muestra solo al pasar el mouse
    b.onmouseenter = () => { if (b.querySelector("video")) return b.querySelector("video").play(); b.querySelector(".mqv").insertAdjacentHTML("beforeend", `<video src="${b.dataset.vid}" muted loop playsinline autoplay></video>`); };
    b.onmouseleave = () => b.querySelector("video")?.pause();
  });
  $("#cambiarEstilo").onclick = () => ir("est");
  $("#gfBuscar").onclick = buscarFuentes;
  $("#gfTxt").onkeydown = (e) => e.key === "Enter" && buscarFuentes();
    previaSiFalta();   // vista rápida de su toma mientras el editor trabaja, o la del video ya dirigido
}
async function buscarFuentes() {
  const r = await api("/api/fuentes-buscar", { texto: $("#gfTxt").value });
  $("#gfRes").innerHTML = (r.fuentes || []).map((f) => `<button class="chip" data-gf="${f.familia}" title="${f.categoria}">${f.familia}</button>`).join("") || "<span class='aviso'>Nada con ese nombre</span>";
  $$("#gfRes [data-gf]").forEach((b) => (b.onclick = async () => {
    b.textContent = "Instalando…";
    const res = await api("/api/fuente-instalar", { familia: b.dataset.gf });
    if (!res.ok) return aviso(res.error || "No se pudo instalar");
    lib = await api("/api/librerias");
    $("#letras").textContent = Object.keys(lib.fuentes).map((f) => `@font-face{font-family:'tps-${f}';src:url('/api/fuente/${encodeURIComponent(f)}')}`).join("\n");
    cambiar({ fuente: b.dataset.gf });
  }));
}
function cambiar(c) { Object.assign(estilo, c); Object.assign(cambios, c); pintarPer(); previsualizar(); }
// La vista en vivo (app/vista.js): con video, un cuadro de SU video con el estilo elegido (se pide 600 ms después del último cambio y
// solo se pinta el último); sin video, la muestra del estilo con los textos dibujados encima, que cambian al instante.
const vista = Vista.crear({
  a: $("#cqA"), b: $("#cqB"), api,
  leer: () => ({ proyecto, subido, listo, estiloId, estilo: proyecto || subido ? estilo : { ...estilo, ...Object.fromEntries(Object.keys(estilo).filter((k) => estilo[k] === null && lib.estilos[estiloId]?.[k] != null).map((k) => [k, lib.estilos[estiloId][k]])) }, cambios, hook: hookEst?.si ? { si: true, texto: hookEst.texto, caja: hookEst.caja, color: hookEst.color } : null }),
});
const previsualizar = (ya) => vista.pedir(ya);
const previaSiFalta = () => { if (!proyecto && !subido) vista.pedir(true); else if (!vista.hayCuadro()) vista.pedir(true); };
$("#pSeguir").onclick = async () => { await guardarHookDelVideo(); ir("exp"); };

// ---------- exportar ----------
// El botón solo se enciende cuando el servidor dice que hay un diseño terminado que exportar; si no, debajo queda escrito el motivo
// (sin editar, el editor trabajando, o lo que falló). Avance y errores salen en el mismo renglón fijo: el botón no se mueve.
function estadoExp(texto, error) {
  $("#error").textContent = texto || "";
  $("#error").classList.toggle("oculto", !texto);
  $("#error").classList.toggle("err", !!error);
}
async function pintarExp() {
  const pid = proyecto;
  $("#res").innerHTML = proyecto
    ? [["Video", proyecto], ["Estilo", lib.estilos[estiloId]?.nombre || (typeof proNombre === "function" && proNombre()) || "—"], ["Letra", estilo.fuente]].map(([k, v]) => `<span>${k} <b>${escP(v)}</b></span>`).join("")
    : "<span>Primero sube un video</span>";
  $("#corr").classList.toggle("oculto", !proyecto || !listo);
  if (!proyecto) { $("#exportar").disabled = true; $("#expTit").textContent = "Exportar"; return estadoExp(""); }
  const p = await refrescar();
  if (proyecto !== pid || exportando) return;
  const puede = !!p && !noExporta;
  $("#exportar").disabled = !puede;
  $("#expTit").textContent = puede ? "Todo listo" : "Todavía no se puede exportar";
  $("#corr").classList.toggle("oculto", !listo);
  const falla = fallo && fallo.proyecto === proyecto ? fallo.texto : "";
  estadoExp(puede ? "" : !p ? "No pude hablar con el estudio. Revisa que siga abierto." : falla ? `${falla} ${noExporta || ""}` : noExporta, !p || !!falla);
  if (p && p.final && puede) mostrarFinal(); else $("#final").classList.add("oculto");
}
function mostrarFinal() {
  $("#final").classList.remove("oculto");
  $("#vf").src = `/archivo/${encodeURIComponent(proyecto)}/final.mp4?${Date.now()}`;
  $("#desc").href = `/archivo/${encodeURIComponent(proyecto)}/final.mp4`;
  $("#desc").download = `${proyecto}.mp4`;
}
let exportando = false;
$("#exportar").onclick = async () => {
  if (exportando) return;
  exportando = true;
  $("#exportar").disabled = true;
  $("#final").classList.add("oculto");
  estadoExp("");
  $("#prog").classList.remove("oculto");
  $("#pb").style.width = "0%";
  $("#paso").textContent = "Renderizando…";
  let t;
  try {
    const r = await api("/api/render", { proyecto, estilo: cambios });   // lo elegido mientras el editor trabajaba se guarda aquí, antes del render
    t = r.trabajo ? await seguir(r.trabajo, (t) => {
      const m = ultimo(t).match(/render (\d+)\/(\d+)/);
      if (m) { $("#pb").style.width = (100 * m[1]) / m[2] + "%"; $("#paso").textContent = `Renderizando ${Math.round((100 * m[1]) / m[2])} %`; }
    }) : { estado: "error", log: [r.error || "No se pudo empezar a exportar."] };   // el servidor no lo dejó empezar y dice por qué
  } finally {
    exportando = false;
    $("#prog").classList.add("oculto");
  }
  await pintarExp();   // el botón vuelve según lo que diga el servidor (no a ciegas)
  if (t.estado === "listo") { if ($("#final").classList.contains("oculto")) mostrarFinal(); aviso("Video exportado"); }
  else estadoExp(ultimo(t) || "No se pudo exportar. Prueba de nuevo.", t.estado !== "detenido");
};
$("#finder").onclick = () => api("/api/finder", { proyecto });

// ---------- corregir ----------
$("#cEnviar").onclick = async () => {
  const texto = $("#cTxt").value.trim();
  if (!texto) return;
  $("#cEnviar").disabled = true;
  $("#cRes").innerHTML = '<span class="giro"></span>El editor está aprendiendo…';
  const { trabajo } = await api("/api/corregir", { texto, proyecto });
  const t = await seguir(trabajo, (t) => ($("#cRes").innerHTML = `<span class="giro"></span>${ultimo(t)}`));
  $("#cEnviar").disabled = false;
  if (t.estado === "listo") {
    const r = t.resultado;
    $("#cTxt").value = "";
    $("#cRes").textContent = `${r.id} · ${r.clase}: ${r.resumen}${r.prueba ? " · prueba: " + r.prueba : ""}`;
    await refrescar();
    previsualizar(true);
  } else $("#cRes").textContent = "No se pudo: " + ultimo(t);
};
const cerrarHoja = () => { $("#velo").classList.remove("on"); $("#hojaBib").classList.remove("on"); };
$("#bibCerrar").onclick = cerrarHoja;
// Biblioteca: lo ya exportado, por fecha y con su estilo (lectura simple de proyectos/)
$("#bib").onclick = async () => {
  const { videos } = await api("/api/biblioteca");
  const dias = {};
  for (const v of videos || []) (dias[v.fecha] ||= []).push(v);
  $("#bibLista").innerHTML = Object.keys(dias).length ? Object.entries(dias).map(([f, vs]) => `<h2 style="margin-top:14px">${f}</h2>` + vs.map((v) =>
    `<a class="item" style="text-decoration:none;color:inherit" href="/archivo/${encodeURIComponent(v.id)}/final.mp4" target="_blank"><img src="${v.previa ? `/archivo/${encodeURIComponent(v.id)}/${v.previa}` : ""}" alt=""><div class="n">${escP(v.id)}<small>${escP(v.estilo)}</small></div></a>`).join("")).join("") : '<p class="aviso">Aún no hay videos exportados.</p>';
  $("#velo").classList.add("on");
  $("#hojaBib").classList.add("on");
};
$("#velo").onclick = cerrarHoja;

// ---------- inicio ----------
(async () => {
  lib = await api("/api/librerias");
  $("#letras").textContent = Object.keys(lib.fuentes).map((f) => `@font-face{font-family:'tps-${f}';src:url('/api/fuente/${encodeURIComponent(f)}')}`).join("\n");
  construirEstilos();
})();
history.replaceState({ v: "mat" }, "", location.hash || "#mat");
window.addEventListener("popstate", (e) => ir(e.state?.v || "mat", true));
(async () => {   // al recargar o volver: el proyecto en curso se reabre solo, en la pantalla donde estaba
  const guardado = recordado(), pantalla = location.hash.slice(1) || guardado.pantalla || "mat";
  if (guardado.proyecto) {
    const p = await api(`/api/proyecto/${encodeURIComponent(guardado.proyecto)}`);
    if (p.storyboard) await abrir(guardado.proyecto);
  }
  if (["mat", "gui", "est", "per", "exp"].includes(pantalla) && (proyecto || pantalla === "mat")) setTimeout(() => ir(pantalla, true), 600);
})();

biblioteca();
// una revisión de archivos a medias se retoma sola al volver (o por su dirección: ?tanda=<id>)
try { const pendiente = new URLSearchParams(location.search).get("tanda") || localStorage.getItem(TANDA_MEM); if (pendiente) seguirTanda(pendiente); } catch (e) { /* sin almacenamiento: no hay revisión que retomar */ }
