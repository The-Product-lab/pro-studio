"""Director (Opus): mira el video y escribe el storyboard. Ojo (Opus): mira el render y lo corrige."""
import json
import shutil
from pathlib import Path


from .. import color, config, ia, machote, montaje, motor, persona, repeticiones, subtitulo_basico, validar

AQUI = Path(__file__).resolve().parent
ESTILOS = config.RAIZ / "librerias" / "estilos"


def _cuadro_fuente(carpeta, meta, t):
    """Un cuadro de la fuente como lo verá el video: con el LUT que la persona haya elegido (mismo `color.cubo` que el render), o tal cual."""
    pref = Path(carpeta) / "preferencias.json"
    try:
        cfg = (json.loads(pref.read_text()).get("estilo") or {}).get("color") if pref.exists() else None
    except ValueError:
        cfg = None
    p = type("P", (), {"meta": meta, "dir": Path(carpeta), "cubo": color.cubo(carpeta, cfg)})()
    return motor._un_cuadro(p, round(t * config.FPS))


def _obsoletos() -> set:
    f = AQUI / "ejemplo" / "OBSOLETOS.txt"
    return {l.strip() for l in f.read_text().splitlines() if l.strip() and not l.startswith("#")} if f.exists() else set()


def _ejemplo(estilo: str) -> Path:
    """El ejemplo PROPIO del estilo. Nunca se presta el de otro estilo (Básico no tiene director ni ejemplo)."""
    f = AQUI / "ejemplo" / f"{estilo}.json"
    if not f.exists() or f.name in _obsoletos():
        raise ValueError(f"el estilo «{estilo}» no tiene ejemplo propio vigente (estudio/director/ejemplo/{estilo}.json)")
    return f


# El ejemplo de «lemo» se armó sobre el guion del ejemplo de Maestro calma: esas palabras viven una sola vez
# (`estudio verificar` › copias idénticas), y este es el único lugar que lo sabe.
GUION_DE_EJEMPLO = {"lemo": "maestro-calma"}


def _palabras_del_ejemplo(estilo: str) -> Path:
    """El guion (palabras con tiempo) sobre el que se armó el ejemplo del estilo: el suyo, el que comparte, o el común de los viejos."""
    for nombre in (estilo, GUION_DE_EJEMPLO.get(estilo)):
        if nombre and (f := AQUI / "ejemplo" / f"{nombre}.palabras.json").exists():
            return f
    return AQUI / "ejemplo" / "palabras.json"


def contexto(carpeta: Path, estilo: str) -> None:
    """Deja en la carpeta lo que el director necesita ver: contacto.jpg, cara.json y palabras_numeradas.txt."""
    meta = json.loads((carpeta / "fuente.json").read_text())
    palabras = json.loads((carpeta / "palabras.json").read_text())
    dur = meta["cuadros"] / config.FPS
    paso = max(1.0, dur / 36)
    tiempos = [round(k * paso, 2) for k in range(int(dur / paso) + 1) if k * paso < dur]
    motor.hoja([(f"{t:.1f}s", _cuadro_fuente(carpeta, meta, t)) for t in tiempos], carpeta / "contacto.jpg", ancho=180)
    tabla, caras = persona.Tabla(carpeta), []
    for seg in range(int(dur) + 1):
        cara = tabla.cara(min(meta["cuadros"] - 1, seg * config.FPS))
        if cara:
            caras.append({"t": seg, "x0": int(cara[0]), "x1": int(cara[2]), "y0": int(cara[1]), "y1": int(cara[3])})
    (carpeta / "cara.json").write_text(json.dumps(caras))
    guia = carpeta / "_guia"
    guia.mkdir(exist_ok=True)
    shutil.copy(AQUI / "GRAMATICA.md", guia / "GRAMATICA.md")
    shutil.copy(_ejemplo(estilo), guia / "ejemplo-storyboard.json")
    shutil.copy(_palabras_del_ejemplo(estilo), guia / "ejemplo-palabras.json")
    from .. import referentes
    familia = estilo if referentes.codigos(estilo) else estilo.split("-")[0]   # variante (p. ej. julian-alborna-3d): el look de su familia
    _referentes_en_imagen(guia / "ref", familia)
    (carpeta / "repeticiones.txt").write_text(repeticiones.texto_para_director(palabras))
    (carpeta / "palabras_numeradas.txt").write_text(
        "\n".join(f"{i}\t{p['s']:.2f}-{p['e']:.2f}\t{p['w']}" for i, p in enumerate(palabras)))


def _referentes_en_imagen(destino: Path, estilo: str, maximo=10) -> list:
    """Cuadros REALES de los referentes para que el director y el ojo vean el estilo (no solo lo lean):
    primero lo que Pablo marcó «me gusta» en el taller (con su nota), si no hay, cuadros repartidos de sus referencias."""
    from .. import referentes
    shutil.rmtree(destino, ignore_errors=True)
    destino.mkdir(parents=True)
    elegidos = []
    marcas = sorted(referentes.gustos(estilo), key=lambda g: {"me encanta": 0, "me gusta": 1}.get(g.get("cuanto"), 2))
    for g in marcas:
        f = referentes.RAIZ / estilo / g["ref"] / f"t_{g['t']:06.1f}.jpg"
        if f.exists():
            nota = f"{(g.get('cuanto') or ('me gusta' if g.get('me_gusta') else 'no me gusta')).upper()}"
            nota += f" [{', '.join((g.get('aspectos') or []) + (g.get('terminos') or []))}]" if g.get("aspectos") or g.get("terminos") else ""
            nota += f": {g.get('nota') or ''}" + (" (el recorte _z muestra justo el elemento)" if g.get("caja") else "")
            elegidos.append((f, nota, g.get("caja")))
    if not any(n.startswith(("ME GUSTA", "ME ENCANTA")) for _, n, _ in elegidos):
        d = json.loads((referentes.DB / "referencias.json").read_text()).get(estilo, {})
        principales = d.get("del_duenno") or [r[0] for r in d.get("refs", []) if "tu referencia" in str(r) or "dueño" in str(r)]
        principales = principales or [r[0] for r in d.get("refs", [])][:2]
        for c in principales:
            fotos = sorted((referentes.RAIZ / estilo / c).glob("t_*.jpg"))
            for f in fotos[:: max(1, len(fotos) // 4)][:4]:
                elegidos.append((f, f"referencia de Pablo {c}, segundo {f.stem[2:]}", None))
    from PIL import Image
    notas = []
    for k, (f, nota, caja) in enumerate(elegidos[:maximo]):
        shutil.copy(f, destino / f"{k:02d}.jpg")
        if caja:
            im = Image.open(f)
            w, h = im.size
            im.crop((int(caja[0] * w), int(caja[1] * h), int(caja[2] * w), int(caja[3] * h))).save(destino / f"{k:02d}_z.jpg", quality=92)
        notas.append(f"{k:02d}.jpg — {nota}")
    generales = referentes.notas_reel(estilo)
    if generales:
        notas += ["", "Lo que Pablo dice de cada reel en general:"] + [f"- {r}: {n}" for r, n in generales.items() if n]
    (destino / "LEEME.txt").write_text("\n".join(notas))
    return notas


def _guia(estilo: str) -> str:
    """La guía del estilo + el gusto que el Agente Editor aprendió de las correcciones de Pablo (manda sobre la guía)."""
    f = ESTILOS / f"{estilo}.md"
    if not f.exists():
        raise FileNotFoundError(f"el estilo {estilo!r} no tiene guía en {ESTILOS}: no hay estilo por defecto")
    guia = f.read_text()
    gusto = config.RAIZ / "perfil" / "gusto.md"
    lineas = [l for l in gusto.read_text().splitlines()[1:] if l.strip()] if gusto.exists() else []
    if lineas:
        guia += "\n\n## Gusto de Pablo (aprendido de sus correcciones; manda sobre todo lo anterior)\n" + "\n".join(lineas)
    from .. import huella
    # Con un ejemplo aprobado por Pablo, su guía manda: la huella de los referentes (que a veces contradice lo aprobado, p. ej.
    # texto detrás de la persona o whip zooms) ya no se le muestra al director para no confundirlo.
    aprobado = (AQUI / "ejemplo" / f"{estilo}.json").exists() and f"{estilo}.json" not in _obsoletos()
    hu = "" if aprobado else huella.resumen(estilo)
    if hu:
        guia += ("\n\n## Lo que suelen tener sus referentes (inspiración, NO obligación: úsalo si sirve a ESTE guion)\n" + hu)
    r = validar.reglas(estilo)
    if r["nota"] or r["colores_prohibidos"]:
        guia += "\n\n## Correcciones de Pablo para este estilo (límites que la compuerta hace cumplir; dentro de ellos, crea con libertad: perfil/reglas.json)\n" + "\n".join(
            [f"- {n}" for n in r["nota"]] + [f"- Color prohibido: {c}" for c in r["colores_prohibidos"]])
    return guia


COMO_SE_ESCRIBE = {"transiciones": "`entrada` de la escena", "entradas": "`entra` de cada texto y etiqueta",
                   "tratamientos": "en cada foto, recorte o clip", "fondos": "`persona.fondo`",
                   "filtros": "`filtro` de la escena o de una franja, siempre como golpe corto", "trazos": "`tipo` de cada trazo",
                   "recursos": "elementos que no son texto ni apoyo, y `cajas`", "textos": "cómo se dibuja cada texto o etiqueta",
                   "hooks": "cómo abren los primeros segundos"}


def _clave_apoyo(tid: str) -> str:
    k, _, v = tid.partition(":")
    return f'"{k}": "{v}"' if v else f'"{k}"'


def guia_seleccion(carpeta: Path) -> str:
    """Lo que Pablo eligió en el seleccionador para ESTE video (preferencias.json › repertorio). Vacío = nada que decir."""
    from .. import catalogo
    rep = validar.repertorio(carpeta)
    hook = catalogo.leer(carpeta).get("hook_texto")
    if not rep and not hook:
        return ""
    out = ["", "", "## Pablo eligió para ESTE video (seleccionador; la compuerta lo hace cumplir)",
           "En cada categoría de abajo usa SOLO lo que él eligió. Elegir no es una receta: no tienes que usarlo todo, usa lo que "
           "sirva a este guion. Lo que no aparece aquí es libertad total, como siempre."]
    if hook:
        out.append(f"- Hook del inicio: el hook dice textualmente «{hook}» (escríbelo tal cual en los primeros segundos, sin cambiarle palabras) y márcalo con `gancho: true`.")
    explica = {"textos": validar.ESTILOS_TEXTO, "recursos": validar.RECURSOS,
               "hooks": {h: f"{n}: {q}" for h, (n, q) in catalogo.HOOKS.items()}}
    for cat, ids in rep.items():
        if cat == "hooks":   # el hook no se mide: se le muestra al director cuál copia aprobada abre así
            ej = catalogo.hooks_aprobados()
            lista = "; ".join(f'«{explica["hooks"].get(i, i)}»' + (f" (como abre el ejemplo de {', '.join(ej[i][:2])})" if ej.get(i) else "")
                              for i in sorted(ids))
            out.append(f"- Tipo de hook ({COMO_SE_ESCRIBE[cat]}): arma el hook con uno de estos: {lista}")
            continue
        lista = ", ".join(_clave_apoyo(i) if cat == "tratamientos" else f'"{i}"' + (f" ({explica[cat][i]})" if i in explica.get(cat, {}) else "")
                          for i in sorted(ids))
        extra = {"transiciones": " (el corte seco siempre se puede)", "tratamientos": " (una foto sin tratamiento siempre se puede)",
                 "entradas": " (sin `entra` cuenta como \"pop\")", "textos": " (el texto lleno y recto siempre se puede)",
                 "filtros": " (sin filtro siempre se puede)"}.get(cat, "")
        out.append(f"- {validar.REPERTORIO_NOMBRES[cat].capitalize()} ({COMO_SE_ESCRIBE.get(cat, cat)}): {lista}{extra}")
    return "\n".join(out)


def _densidad_del_ejemplo(estilo: str, densidad: str = "normal") -> str:
    """Las piezas que usa el EJEMPLO APROBADO del estilo, como INSPIRACIÓN (Pablo 10-nov: el director crea con libertad; el ejemplo no es una
    cuenta que igualar). No pasa cantidades: ni de elementos ni de imágenes."""
    ej = ESTILOS.parent.parent / "estudio" / "director" / "ejemplo" / f"{estilo}.json"
    ej = ej if ej.exists() else AQUI / "ejemplo" / f"{estilo}.json"
    if not ej.exists():
        return ""
    sb = json.loads(ej.read_text())
    from .. import camara
    pal = _palabras_del_ejemplo(estilo)
    try:
        palabras = json.loads(pal.read_text())
        dur = camara.salida(sb, palabras[-1]["e"] + .6)
    except Exception:  # noqa: BLE001
        return ""
    if dur <= 0:
        return ""
    from collections import Counter
    tipos = Counter(e.get("tipo") for e in sb.get("elementos", []))
    por_min = len(sb.get("elementos", [])) * 60 / dur
    meta = {"poco": "POCO: calmado, que respire, cada cosa con razón",
            "normal": "NORMAL: la riqueza propia del estilo, sin amontonar",
            "mucho": "MUCHO: más lleno, siempre una cosa a la vez"}[densidad]
    solo_ideas = [k for k, _ in tipos.most_common() if k not in ("foto", "recorte", "clip")]
    return (f"\n\n## DENSIDAD ELEGIDA POR PABLO: {meta}\nEl ejemplo aprobado de este estilo es INSPIRACIÓN, no una cuenta que igualar. "
            "Piezas que usa (úsalas, mézclalas o inventa otras): " + ", ".join(solo_ideas) +
            ". Pablo prefiere menos imágenes y más elementos tipográficos y animaciones. "
            "\n\n## CÁMARA (regla única, perfil/reglas.json)\n" + _regla_camara())


def _regla_camara() -> str:
    """El texto de la regla de cámara, tal cual está en perfil/reglas.json (un solo lugar)."""
    return next((n for n in validar.reglas(None).get("nota", []) if n.startswith("Cámara")), "")


def sin_director(estilo: str) -> bool:
    """Estilos que no necesitan director (Básico): su storyboard sale de palabras.json, sin Opus."""
    return bool(json.loads((ESTILOS / "presets.json").read_text()).get(estilo, {}).get("sin_director"))


def _tope_elegido(carpeta: Path):
    """El tope de imágenes que la persona dejó en Personalizar («cantidad de edición») en el storyboard anterior, si lo hay."""
    f = carpeta / "storyboard.json"
    try:
        return json.loads(f.read_text()).get("estilo", {}).get("tope_imagenes") if f.exists() else None
    except ValueError:
        return None


def dirigir(carpeta: Path, estilo: str, con_imagenes=True, avance=print) -> None:
    carpeta = Path(carpeta)
    preset = json.loads((ESTILOS / "presets.json").read_text()).get(estilo, {})
    if preset.get("sin_director"):   # estilo Básico: no hay nada que decidir; el storyboard sale de palabras.json, sin Opus
        avance("estilo sin director: subtítulo palabra por palabra armado desde las palabras…")
        subtitulo_basico.armar(carpeta)
        machote.imponer(carpeta)
        _fijar_estilo(carpeta, estilo)
        _validar(carpeta, "director", imagenes_pendientes=False)
        return
    if preset.get("base") == "pantalla" and not preset.get("imagenes"):   # salvo que el estilo pida arte (p. ej. ráfagas)
        con_imagenes = False
    contexto(carpeta, estilo)
    avance("el director (Opus) está diseñando las escenas…")
    from .. import lemo_apoyos
    lemo = lemo_apoyos.slug_de(carpeta) if estilo == lemo_apoyos.ESTILO else None   # el arte lo hace Lemo: otra sección de arte
    tope = min(config.TOPE_IMAGENES_MAX, int(_tope_elegido(carpeta) or preset.get("tope_imagenes", config.TOPE_IMAGENES)))
    if lemo:
        arte = (AQUI / "arte_lemo.md").read_text().format()   # sin tope: el director marca tramos y Lemo decide (PLANO-LEMO-APOYOS §0)
    else:
        arte = (AQUI / "arte_imagenes.md").read_text().format(tope=tope, imagenes=(
            "SÍ: pide el arte en arte.json" if con_imagenes else "NO: no hay generación de imágenes; usa solo etiquetas y trazos")
            + (f". YA HAY ARTE en este proyecto (úsalo primero, ábrelo para ver qué es; cuenta para el tope): "
               f"{', '.join('arte/' + x.name for x in sorted((carpeta / 'arte').glob('*.png')))}" if any((carpeta / "arte").glob("*.png")) else ""))
    prompt = (AQUI / "director.md").read_text().format(
        gramatica="_guia/GRAMATICA.md", limite_s=machote.LIMITE_S, ejemplo="_guia/ejemplo-storyboard.json",
        ejemplo_palabras="_guia/ejemplo-palabras.json", arte=arte.rstrip("\n"),
        guia=_guia(estilo) + (lemo_apoyos.nota_del_estilo(lemo) if lemo else "") + guia_seleccion(carpeta) + machote.nota_para_director(carpeta)
        + _densidad_del_ejemplo(estilo, validar.densidad_de(carpeta)))
    ia.llamar(prompt, "opus", carpeta, tope_usd=3.0, paso="director")
    machote.imponer(carpeta)      # los cortes del machote entran siempre, los haya copiado el director o no
    _fijar_estilo(carpeta, estilo)
    _validar(carpeta, "director", imagenes_pendientes=True)


def _fijar_estilo(carpeta: Path, estilo: str) -> None:
    """El bloque `estilo` (base, paleta, tipografías, subtítulos) lo pone el código desde el preset, no el director."""
    presets = json.loads((ESTILOS / "presets.json").read_text())
    if estilo not in presets:
        return
    sb = json.loads((carpeta / "storyboard.json").read_text())
    sb["estilo"] = {"id": estilo, **{k: v for k, v in presets[estilo].items() if k != "nombre"}}
    prefs = carpeta / "preferencias.json"   # lo que Pablo eligió para este video (p. ej. el color) manda sobre el preset
    if prefs.exists():
        sb["estilo"].update(json.loads(prefs.read_text()).get("estilo", {}))
    (carpeta / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=1))


def _anotar_avisos(carpeta: Path, avisos: list, residuales: set) -> None:
    """Lo que el código no pudo dejar perfecto queda a la vista (segundo y motivo) en `avisos-montaje.json`; sin avisos, no hay archivo."""
    destino = carpeta / "avisos-montaje.json"
    todo = [*avisos, *({"tipo": "residual", "motivo": r} for r in sorted(residuales))]
    if todo:
        destino.write_text(json.dumps(todo, ensure_ascii=False, indent=1))
    elif destino.exists():
        destino.unlink()


class GuionCambiado(RuntimeError):
    """El montaje quiso cambiar los cortes del guion aprobado: se para y se avisa, no se corta."""


def _parar_si_son_de_cortes(carpeta: Path, problemas: list) -> None:
    """Con el guion congelado, una queja sobre los CORTES no la puede arreglar Opus (imponer la deshace): se para y se avisa, sin gastar."""
    de_cortes = [x for x in problemas if x.startswith(("montaje:", "cortes ", "REGLA DE PABLO (queda la ÚLTIMA"))]
    if de_cortes and machote.cargar(carpeta):
        raise GuionCambiado("el guion aprobado tiene problemas de cortes que el director no puede cambiar: se detuvo sin gastar. "
                            "Corrige el guion y vuelve a aprobarlo.\n- " + "\n- ".join(de_cortes[:5]))


def _validar(carpeta: Path, paso: str, imagenes_pendientes=False) -> None:
    """Carga el storyboard con el motor; si falla, Opus lo arregla una vez con el error exacto."""
    INTENTOS = 5   # lote del workshop (04-nov): con 3 se rendía a 1–3 errores de corte del final
    for intento in range(INTENTOS):
        try:
            sb = json.loads((carpeta / "storyboard.json").read_text())
            # Lo medible del montaje (voz fuera de cámara, bordes en silencio real, silencios largos) lo repara el CÓDIGO antes
            # de pedirle nada a Opus (T-0193): lo que no se pueda queda como aviso con su segundo, nunca como motivo para tirar el video.
            avisos = []
            try:
                reparado = montaje.reparar(sb, carpeta, avisos)
            except Exception as x:  # noqa: BLE001 — un fallo de la reparación no tira el video: queda a la vista y sigue la compuerta
                reparado = sb
                avisos.append({"tipo": "reparar_fallo", "t": 0, "motivo": f"montaje.reparar falló ({type(x).__name__}: {x}); se dejaron los cortes del director"})
            if machote.cargar(carpeta) and [list(x) for x in reparado.get("cortes", [])] != [list(x) for x in sb.get("cortes", [])]:
                # mover un borde dentro de un silencio (mismas palabras) NO cambia el guion: el machote se actualiza y sigue; si cambiaran las palabras, se para
                if not machote.actualizar_cortes(carpeta, reparado["cortes"], avance=lambda m: None):
                    if machote.cambia_palabras(carpeta, reparado["cortes"]):   # red de seguridad: `machote.estabilizar` ya corrió antes de gastar
                        raise GuionCambiado("red de seguridad (no debería ocurrir): el montaje quiere cambiar las palabras del guion aprobado; se detuvo sin cortar.")
                    reparado = {**reparado, "cortes": sb["cortes"]}   # solo traería errores nuevos: se queda el corte aprobado
            ajustado = validar.acomodar(validar.limpiar_inicio(reparado), carpeta)
            if ajustado != sb:
                sb = ajustado
                (carpeta / "storyboard.json").write_text(json.dumps(sb, ensure_ascii=False, indent=1))
            try:
                residuales = set(montaje.medibles(sb, carpeta))
            except Exception as x:  # noqa: BLE001 — datos de montaje dañados: aviso, no una pregunta a la IA
                residuales = set()
                avisos.append({"tipo": "montaje_fallo", "t": 0, "motivo": f"no se pudo medir el montaje ({type(x).__name__}: {x})"})
            avisos += [{"tipo": "consejo", "t": 0, "motivo": m} for m in validar.consejos(sb, carpeta)]   # registro a la vista; a Opus le llegan en la ronda del ojo
            _anotar_avisos(carpeta, avisos, residuales)
            # Solo bloquean las reglas de Pablo y lo que rompe el motor. La huella del estilo es INSPIRACIÓN, no obligación
            # (Pablo, 04-nov: «el anterior editor no tenía libertad creativa, siempre hacía lo mismo, las guías bloqueaban»).
            problemas = [x for x in validar.errores(sb, carpeta, imagenes_pendientes)
                         if not x.startswith("huella") and x not in residuales]
            _parar_si_son_de_cortes(carpeta, problemas)
            if problemas:
                raise ValueError("la compuerta encontró estos problemas (arréglalos todos):\n- " + "\n- ".join(problemas))
            if imagenes_pendientes:
                faltan = [e for e in sb.get("elementos", []) if e.get("src") and not (carpeta / e["src"]).exists()]
                ids = {a["id"] for a in json.loads((carpeta / "arte.json").read_text())} if (carpeta / "arte.json").exists() else set()
                malos = [e["src"] for e in faltan if Path(e["src"]).stem not in ids]
                if malos:
                    raise ValueError(f"estas imágenes no existen ni están pedidas en arte.json: {malos}")
            else:
                faltan = montaje.repetidas_sin_cortar(montaje.contexto(carpeta), sb.get("cortes", []))
                if faltan:
                    _parar_si_son_de_cortes(carpeta, ["REGLA DE PABLO (queda la ÚLTIMA versión): " + "; ".join(faltan)])
                    raise ValueError("REGLA DE PABLO (queda la ÚLTIMA versión): estas versiones anteriores siguen sin cortar:\n- "
                                     + "\n- ".join(faltan))
                dur = len(motor.Proyecto(carpeta).mapa) / config.FPS
                if dur > machote.LIMITE_S + machote.TOLERANCIA_S:
                    if machote.cargar(carpeta):   # con guion congelado el director no corta: se avisa a la persona
                        raise GuionCambiado(f"el reel dura {dur:.0f} s y el máximo es {machote.LIMITE_S} s: los cortes del guion aprobado no se tocan; vuelve al guion, quita frases y apruébalo de nuevo")
                    raise ValueError(f"el reel dura {dur:.0f} s y el máximo es {machote.LIMITE_S} s: quita más en `cortes` (deja lo mejor)")
            return
        except GuionCambiado:
            raise
        except Exception as e:  # noqa: BLE001 — cualquier error del storyboard se le devuelve al director
            if intento == INTENTOS - 1:
                raise
            ia.llamar(f"El storyboard.json de esta carpeta no carga en el motor. Error exacto:\n{e}\n"
                      "Corrígelo editando storyboard.json (lee _guia/GRAMATICA.md). No cambies nada más.",
                      "opus", carpeta, tope_usd=1.0, paso=f"{paso}-arreglo")
            machote.imponer(carpeta)   # el arreglo de Opus tampoco toca los cortes aprobados


def tiempos_revision(carpeta: Path) -> list:
    sb = json.loads((carpeta / "storyboard.json").read_text())
    esc = sorted(e["t0"] for e in sb["escenas"])
    meta = json.loads((carpeta / "fuente.json").read_text())
    fin = meta["cuadros"] / config.FPS
    ts = []
    for a, b in zip(esc, esc[1:] + [fin]):
        ts += [a + min(.6, (b - a) / 3), a + (b - a) * .75]
    return [round(t, 2) for t in ts if t < fin - .05][:18]


def mirar(carpeta: Path, ronda: int, avance=print) -> dict:
    carpeta = Path(carpeta)
    _validar(carpeta, "ojo")
    previa = carpeta / f"revision-{ronda}.jpg"
    motor.vista_previa(carpeta, tiempos_revision(carpeta), previa)
    avance(f"el ojo (Opus) revisa el resultado, ronda {ronda}…")
    notas = validar.consejos(json.loads((carpeta / "storyboard.json").read_text()), carpeta)   # guía (hueco, texto siempre, variedad, ritmo): llega a Opus, no lo obliga
    prompt = (AQUI / "ojo.md").read_text().format(previa=previa.name, gramatica="_guia/GRAMATICA.md",
                                                  consejos="\n".join(f"- {n}" for n in notas) or "- (ninguna)")
    out = ia.llamar(prompt, "opus", carpeta, tope_usd=1.5, paso=f"ojo-{ronda}")
    _validar(carpeta, "ojo")
    return ia.json_de(out.get("result", "")) or {"veredicto": "corregido"}
