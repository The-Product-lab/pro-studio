// Estilos Pro (docs/PLANO-LEMO-APOYOS.md): en Estilo, el selector «Estilos | Estilos Pro». Editar con un estilo Pro es el MISMO flujo
// que cualquier estilo (`/api/dirigir` con «lemo:<slug>»: nuestro director arma el reel y Lemo hace lo gráfico), y sigue en Personalizar
// y Exportar. La película entera de antes (`estudio pro`) quedó solo en la terminal.
// Se apoya en lo global de app.js ($, api, proyecto, ir, vigilar, abrir, previsualizar, escP, aviso) y solo lo envuelve.
let proCat = null, proAvisoTxt = "", proSel = null, proMotor = true;
try { proSel = localStorage.getItem("tps-pro-estilo") || null; } catch (e) { /* sin almacenamiento: la elección vale hasta cerrar */ }
const proEstilo = (slug) => proCat?.find((e) => e.slug === slug);
const proNombre = () => proSel && proEstilo(proSel) ? `Pro · ${proEstilo(proSel).nombre}` : null;   // para el resumen de Exportar

async function proCargar() {
  if (proCat) return true;
  const r = await api("/api/pro/catalogo");
  if (!r.ok) { aviso(r.error || "No pude cargar los Estilos Pro"); return false; }
  proCat = r.estilos;
  proAvisoTxt = r.aviso?.texto || "";
  proMotor = !!r.motor;
  if (!proMotor) {   // sin el motor de Lemo se ven pero no se editan: se dice ANTES de elegir, y no queda uno elegido que tape «Exportar»
    proOlvidar();
    if (proCat.length) {
      $("#proCosto").innerHTML = `<b>En esta máquina los Estilos Pro son solo para ver</b>
        <p>Para editar con ellos hace falta el motor de Lemo, que está en el PC de la oficina.</p>
        <small>Aquí podés mirar el catálogo y elegir cuál pedir. Para editar en esta máquina, usá la pestaña «Estilos».</small>`;
      $("#proCosto").hidden = false;
    }
  } else if (r.aviso && proCat.length) {   // a la derecha y siempre a la vista: lo que cuesta un estilo Pro, antes de elegirlo (Pablo, 12-nov)
    $("#proCosto").innerHTML = `<b>Ojo: estos estilos son muy costosos</b>
      <p><span>Tiempo</span>unos ${r.aviso.minutos} minutos por video</p>
      <p><span>Uso de IA</span>${escP(r.aviso.consumo)}</p>
      <small>Aproximado: ${escP(r.aviso.origen)}. Se hace un video Pro a la vez.</small>`;
    $("#proCosto").hidden = false;
  }
  const fam = [...new Set(proCat.map((e) => e.familia))].sort();
  $("#proFamilia").insertAdjacentHTML("beforeend", fam.map((f) => `<option>${escP(f)}</option>`).join(""));
  return true;
}
function proModo(pro) {
  $$("#proSel button").forEach((b) => b.classList.toggle("on", (b.dataset.m === "p") === pro));
  $("#pro").classList.toggle("oculto", !pro);
  $("#est-sc").classList.toggle("oculto", pro);
  if (pro) proCargar().then((ok) => ok && proPintar());
}
$$("#proSel button").forEach((b) => (b.onclick = () => proModo(b.dataset.m === "p")));

function proPintar() {
  const q = $("#proBuscar").value.trim().toLowerCase(), fam = $("#proFamilia").value;
  const vistos = proCat.filter((e) => (!fam || e.familia === fam) && (!q || `${e.nombre} ${e.familia} ${e.temas.join(" ")}`.toLowerCase().includes(q)));
  $("#proGrilla").innerHTML = vistos.map((e) => `<button class="pro-t${e.slug === proSel ? " sel" : ""}" data-s="${escP(e.slug)}"><b>${escP(e.nombre)}</b><span class="pv-img"><img src="${escP(e.poster)}" alt="" decoding="async"></span><small>${escP(e.temas.slice(0, 2).join(" · "))}</small></button>`).join("")
    || `<p class="pro-vacio">${proCat.length ? "Ningún estilo coincide." : "Los Estilos Pro necesitan la carpeta de Lemo y esta máquina no la tiene."}</p>`;
  $$("#proGrilla .pro-t").forEach((b) => (b.onclick = () => proDetalle(b.dataset.s)));
  const el = proEstilo(proSel);
  $("#proElegido").classList.toggle("oculto", !el);
  if (el) {
    $("#proElegido").innerHTML = `<span>Elegido: <b>${escP(el.nombre)}</b></span>${proMotor ? `<button class="btn chico" id="proSeguir">Editar con este estilo</button>` : ""}`;
    if (proMotor) $("#proSeguir").onclick = () => proEditar(el.slug);
  }
}
$("#proBuscar").oninput = () => proCat && proPintar();
$("#proFamilia").onchange = () => proCat && proPintar();

function proDetalle(slug) {
  const e = proEstilo(slug);
  const v = document.createElement("div");
  v.className = "pro-velo";
  v.innerHTML = `<div class="pro-det" role="dialog" aria-label="${escP(e.nombre)}">
    ${e.muestra ? `<video src="${escP(e.muestra)}" poster="${escP(e.poster)}" controls autoplay muted loop playsinline></video>` : `<img src="${escP(e.poster)}" alt="">`}
    <h2>${escP(e.nombre)}</h2>
    <small class="aviso" style="margin:0">${escP(e.familia)} · sirve para: ${escP(e.temas.join(", "))}${e.muestra ? "" : " · sin muestra todavía"}</small>
    ${e.riesgo ? `<small class="aviso" style="margin:0;color:var(--fg)">Ojo: ${escP(e.riesgo)}</small>` : ""}
    ${proMotor ? "" : `<small class="aviso" style="margin:0;color:var(--fg)">Solo para ver: en esta máquina no está el motor de Lemo. Se edita en el PC de la oficina.</small>`}
    <div class="pie"><button class="btn g" data-c>Cerrar</button>${proMotor ? `<button class="btn" data-e>Editar con este estilo</button>` : ""}</div></div>`;
  const cerrar = () => v.parentNode && v.parentNode.removeChild(v);
  v.onclick = (ev) => ev.target === v && cerrar();
  v.querySelector("[data-c]").onclick = cerrar;
  const elegirBtn = v.querySelector("[data-e]");
  if (elegirBtn) elegirBtn.onclick = () => { cerrar(); proEditar(slug); };
  document.body.append(v);
}
function proElegir(slug) {
  proSel = slug;
  try { localStorage.setItem("tps-pro-estilo", slug); } catch (e) { /* ver arriba */ }
  proPintar();
  aviso(`Estilo Pro: ${proEstilo(slug).nombre}`);
}

function proOlvidar() {
  proSel = null;
  try { localStorage.removeItem("tps-pro-estilo"); } catch (e) { /* ver arriba */ }
}
// Elegir un estilo normal deja atrás el Pro
const proElegirNormal = elegir;
elegir = function (id) {
  proOlvidar();
  proElegirNormal(id);
};

// ---------- Editar: el flujo de siempre, con «lemo:<slug>» ----------
async function proEditar(slug) {
  if (!proyecto) return aviso("Primero sube un video.");
  if (!guionOk) return aviso("Primero aprueba el guion.");
  const e = proEstilo(slug);
  if (!confirm(`${proAvisoTxt}\n\nEdición completa: nuestro editor arma el reel y Lemo hace lo gráfico con el estilo «${e.nombre}». ¿Editar con este estilo?`)) return;
  proElegir(slug);
  const r = await api("/api/dirigir", { proyecto, estilo: `lemo:${slug}`, imagenes: true, confirmado: true });
  if (!r.ok) return aviso(r.error || "No se pudo empezar el diseño");
  listo = false;
  estiloId = null;   // «lemo» no es una tarjeta: Personalizar toma el estilo del storyboard cuando el director termina
  cambios = {};
  ir("per");
  previsualizar(true);
  await vigilar(r.trabajo);
  if (listo && proyecto) {   // el estilo que dejó el flujo (preset «lemo» con el acento y la letra de Lemo) pasa a la pantalla
    await abrir(proyecto);
    if ($("#s-per").classList.contains("on")) pintarPer();
    previsualizar(true);
  }
}
