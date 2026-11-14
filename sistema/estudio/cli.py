"""Puerta única del motor: `estudio <herramienta>`. La usan la app, el Agente Editor y las pruebas."""
import argparse
import json
import sys
import time
import shutil
from pathlib import Path

from . import doctor, recursos


def editar(video, estilo, con_imagenes, rondas, nombre=None, desde=None, biblioteca=None, densidad=None) -> Path:
    from . import director, imagenes, ingesta, machote, motor
    t0 = time.time()

    def avance(msg):
        print(f"[{time.time() - t0:5.0f}s] {msg}", flush=True)
    carpeta = ingesta.derivar(desde, nombre or f"{desde}-{estilo}") if desde else ingesta.preparar(video, nombre, avance)
    if not (carpeta / "machote.json").exists():   # etapa fija: los cortes se deciden una vez (0 IA o una llamada corta) y el director parte de ellos
        machote.preparar(carpeta, con_video=False, avance=avance)
    if (problema := machote.impedimento(carpeta)):   # antes de gastar director e imágenes
        raise SystemExit(problema)
    if densidad:
        from . import validar
        validar.fijar_densidad(carpeta, densidad)
    if biblioteca:   # arte ya hecho (p. ej. los renders 3D aprobados): el director lo ve como «YA HAY ARTE» y lo usa primero
        n = _traer_biblioteca(Path(biblioteca), carpeta)
        avance(f"biblioteca: {n} imágenes de {biblioteca}")
    from . import lemo_apoyos
    estilo = lemo_apoyos.elegir(carpeta, estilo)   # `--estilo lemo:<slug>`: el reel con los apoyos de Lemo
    if director.sin_director(estilo):   # estilo Básico: sin arte y sin ojo de Opus; todo sale determinista de las palabras
        con_imagenes, rondas = False, 0
    if estilo != lemo_apoyos.ESTILO:
        con_imagenes = imagenes.disponibles(con_imagenes, avance)
    director.dirigir(carpeta, estilo, con_imagenes, avance)
    imagenes.arte_del_video(carpeta, con_imagenes, avance)   # nada llega al ojo ni al render dibujando una imagen que no existe
    for ronda in range(1, rondas + 1):
        veredicto = director.mirar(carpeta, ronda, avance)
        avance(f"ojo: {veredicto.get('veredicto')} · " + " | ".join(veredicto.get("cambios", []))[:400])
        if veredicto.get("veredicto") == "aprobar":
            break
    avance("renderizando…")
    final = motor.render(carpeta, avance=avance)
    costos = [json.loads(l) for l in (carpeta / "costos.jsonl").read_text().splitlines()] if (carpeta / "costos.jsonl").exists() else []   # Básico: 0 llamadas
    avance(f"listo: {final}  ·  IA {sum(c['usd_equivalente'] or 0 for c in costos):.2f} USD eq. en {len(costos)} llamadas")
    return final


def _traer_biblioteca(origen: Path, carpeta: Path) -> int:
    """Copia las imágenes de una biblioteca al arte del proyecto (png para que el director las liste; jpg se convierte)."""
    from PIL import Image
    from . import archivo
    arte = carpeta / "arte"
    arte.mkdir(exist_ok=True)
    n = 0
    for f in sorted(origen.glob("*")):
        if f.suffix.lower() not in (".png", ".jpg", ".jpeg") or (arte / f"{f.stem}.png").exists():
            continue
        if f.stem.startswith("arch_") and archivo.tiene_persona(Image.open(f)):   # foto de archivo con una persona: no entra (regla 4)
            continue
        if f.suffix.lower() == ".png":
            shutil.copy2(f, arte / f.name)
        else:
            Image.open(f).convert("RGB").save(arte / f"{f.stem}.png")
        n += 1
    return n


def main(argv=None) -> int:
    from . import ia, portable
    orden = portable.relanzar_utf8(list(sys.argv[1:] if argv is None else argv))
    if orden:   # Windows: sin modo UTF-8 los textos del sistema (acentos, ñ) revientan en cp1252
        import os
        import subprocess
        return subprocess.run(orden, env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}).returncode
    try:
        return _ejecutar(argv)
    except ia.LimiteAgotado as e:
        print(f"Límite de Claude: {e}", file=sys.stderr)
        return 75      # EX_TEMPFAIL: no es un fallo del video, se reintenta cuando Claude vuelva


def _ejecutar(argv=None) -> int:
    p = argparse.ArgumentParser(prog="estudio", description="Pro Studio: herramientas del motor")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("doctor", help="revisa que todo esté instalado y dice cómo arreglarlo")
    d.add_argument("--json", action="store_true")
    d.add_argument("--arreglar", action="store_true", help="instala lo que falte (Claude Code, ffmpeg, modelos, bancos) y vuelve a revisar")
    sub.add_parser("instalar", help="instala todo lo que falte y revisa (lo que llaman instalar.bat / .command / .sh)")
    ex = sub.add_parser("exportar", help="arma el ZIP del paquete (lista blanca; nunca proyectos, privadas ni secretos)")
    ex.add_argument("--destino", default=".", help="carpeta donde queda el zip del paquete")
    ex.add_argument("--publicar", action="store_true", help="además: repo PRIVADO nuevo con gh + el zip como Release (lo corre quien tiene gh con sesión)")
    ex.add_argument("--en-seco", action="store_true", help="con --publicar: solo muestra los comandos de gh")
    ex.add_argument("--repo", default="", help="dueño/nombre del repo (por defecto el del paquete)")
    sub.add_parser("instalar-recursos", help="baja ffmpeg y los modelos (solo lo que falte)")
    e = sub.add_parser("editar", help="edita un video de punta a punta")
    e.add_argument("video", nargs="?", help="video crudo (o --desde un proyecto ya preparado)")
    e.add_argument("--desde", help="proyecto ya preparado: mismo video, otro estilo, sin volver a transcribir")
    e.add_argument("--estilo", required=True)
    e.add_argument("--sin-imagenes", action="store_true")
    e.add_argument("--rondas", type=int, default=2, help="vueltas del ojo de director")
    e.add_argument("--nombre")
    e.add_argument("--biblioteca", help="carpeta con imágenes ya hechas para reusar como arte (sin gastar créditos)")
    e.add_argument("--densidad", choices=["poco", "normal", "mucho"], help="cuántos elementos: poco, normal (el del ejemplo aprobado) o mucho")
    m = sub.add_parser("machote", help="crudo colorizado + solo los cortes, en un MP4 liviano (machote.json + machote.mp4): la base de cada estilo")
    m.add_argument("objetivo", help="proyecto (nombre o carpeta) o video crudo (se prepara primero)")
    m.add_argument("--sin-ia", action="store_true", help="solo cortes de código (0 llamadas a Claude)")
    m.add_argument("--sin-video", action="store_true", help="solo decide los cortes (machote.json)")
    m.add_argument("--rehacer", action="store_true", help="decide los cortes de nuevo aunque ya existan")
    m.add_argument("--ancho", type=int, default=720, help="ancho del MP4 liviano (alto 16:9 vertical)")
    m.add_argument("--crf", type=int, default=26, help="calidad H.264: más alto = más liviano")
    rc = sub.add_parser("reparar-cortes", help="repara en código los bordes de los cortes de un proyecto ya dirigido (mismas palabras; 0 IA); luego `estudio render`")
    rc.add_argument("proyecto")
    r = sub.add_parser("render", help="renderiza un proyecto ya dirigido")
    r.add_argument("carpeta")
    v = sub.add_parser("previa", help="hoja de contacto del proyecto en esos segundos (tiempo fuente)")
    v.add_argument("carpeta")
    v.add_argument("tiempos", nargs="+", type=float)
    es = sub.add_parser("crear-estilo", help="crea un estilo solo: busca con vidIQ, estudia, implementa y prueba")
    es.add_argument("estilo")
    es.add_argument("links", nargs="*", help="reels de referencia del dueño (pesan más)")
    es.add_argument("--idea", default="", help="el formato de edición en una frase")
    es.add_argument("--sin-buscar", action="store_true", help="no buscar creadores, solo los links dados")
    es.add_argument("--probar", help="clip corto para la prueba final")
    fu = sub.add_parser("fuentes", help="Google Fonts completo: buscar o instalar una familia por nombre")
    fu.add_argument("accion", choices=["buscar", "instalar"])
    fu.add_argument("texto", nargs="?", default="")
    fu.add_argument("--categoria", default="")
    sx = sub.add_parser("sfx", help="banco de efectos de sonido grabados (Openverse, CC0)")
    sx.add_argument("accion", choices=["traer", "organicos"])
    sx.add_argument("--por-tipo", type=int, default=3)
    ar = sub.add_parser("archivo", help="banco de apoyos literales y gratis (fotos de dominio público de Openverse)")
    ar.add_argument("accion", choices=["buscar", "bajar"])
    ar.add_argument("palabra")
    ar.add_argument("--en", help="búsqueda en inglés")
    ar.add_argument("--proyecto")
    ar.add_argument("-n", type=int, default=3)
    lo = sub.add_parser("lote", help="edita todos los videos de una carpeta en varios estilos (se retoma solo, freno de disco)")
    lo.add_argument("carpeta")
    lo.add_argument("--estilos", default="", help="separados por coma (todos a cada video)")
    lo.add_argument("--asignar", action="append", default=[], help="VIDEO=estilo: un estilo por video (se puede repetir)")
    lo.add_argument("--salida", required=True)
    lo.add_argument("--biblioteca", action="append", default=[], help="estilo=carpeta de arte a reusar (se puede repetir)")
    lo.add_argument("--con-imagenes", action="store_true", help="generar imágenes nuevas (gasta créditos)")
    lo.add_argument("--rondas", type=int, default=1)
    lo.add_argument("--trabajo-en", help="carpeta FUERA de Ubuntu (p. ej. en C:, no OneDrive) para lo pesado de cada video nuevo")
    lo.add_argument("--telegram", action="store_true", help="manda cada video terminado por Telegram")
    lo.add_argument("--color-de", help="proyecto cuyo color (preferencias.json) se usa en todo el lote")
    cc = sub.add_parser("corregir-capas", help="corrección por capas (reglas o una llamada chica) y re-exporta solo los tramos tocados")
    cc.add_argument("proyecto")
    cc.add_argument("texto")
    cc.add_argument("--segundo", type=float, help="segundo del video final al que se refiere")
    cc.add_argument("--simular", action="store_true", help="muestra las operaciones sin tocar nada")
    sub.add_parser("portadas", help="portadas del carrusel de estilos desde cada video aprobado")
    ig = sub.add_parser("integrar", help="pasa un estilo APROBADO por Pablo al director (ejemplo + preset), con candados")
    ig.add_argument("estilo")
    ig.add_argument("proyecto")
    ig.add_argument("--nombre")
    mu = sub.add_parser("muestras", help="muestras del seleccionador (motor real sobre el C8866), por la cola pesado.sh")
    mu.add_argument("--forzar", action="store_true", help="rehace todas, aunque no hayan cambiado")
    mu.add_argument("--solo", help="una categoría: transicion, entrada, subtitulo, efecto, look, estilo")
    pr = sub.add_parser("pro", help="Estilos Pro: el reel aprobado como película animada de Lemo (estilo <slug>) con todas las palabras del guion")
    pr.add_argument("proyecto", help="proyecto (nombre o carpeta) con su machote")
    pr.add_argument("estilo", help="slug del estilo de Lemo (p. ej. engraving)")
    pt = sub.add_parser("pro-textos", help="Estilos Pro: solo medir qué mostró Lemo y poner las palabras que faltan sobre un encargo ya rendido (sin Opus)")
    pt.add_argument("encargo", help="carpeta del encargo (index.html de Lemo, película completa, palabras.json)")
    pt.add_argument("--video", help="nombre de la película en esa carpeta (por defecto pelicula.mp4, o limpio.mp4 en encargos viejos)")
    sub.add_parser("verificar", help="compuerta capa 1 (<60 s): sin basura, compila, pruebas; sale 1 si algo falla")
    ap = sub.add_parser("autoprueba", help="recorre la app entera en esta instalación (subir → guion → editar → exportar) y sale 0 si el video final sale bien; sin argumentos no gasta IA")
    ap.add_argument("--video", help="un video tuyo en vez del de prueba (se transcribe de verdad)")
    ap.add_argument("--estilo", default="basico", help="estilo con el que edita (por defecto Básico, sin director)")
    ap.add_argument("--con-ia", action="store_true", help="deja que el guion y el editor llamen a Claude (necesita la sesión)")
    ap.add_argument("--conservar", action="store_true", help="no borra el proyecto de prueba al terminar")
    sv = sub.add_parser("servir", help="abre la app en el navegador")
    sv.add_argument("--sin-abrir", action="store_true")
    a = p.parse_args(argv)

    if a.cmd == "doctor":
        return doctor.main(a.json, a.arreglar)
    if a.cmd == "instalar":
        return doctor.main(False, True)
    if a.cmd == "exportar":
        from . import exportar
        return exportar.main(Path(a.destino), a.publicar, a.en_seco, a.repo)
    if a.cmd == "autoprueba":
        from . import autoprueba
        return autoprueba.main(a.video, a.estilo, a.con_ia, a.conservar)
    if a.cmd == "verificar":
        from . import verificar
        return verificar.main()
    if a.cmd == "instalar-recursos":
        recursos.instalar()
    elif a.cmd == "machote":
        from . import config, ingesta, machote
        destino = Path(a.objetivo)
        carpeta = config.PROYECTOS / a.objetivo if (config.PROYECTOS / a.objetivo).is_dir() else destino
        t0 = time.time()
        avance = lambda msg: print(f"[{time.time() - t0:5.0f}s] {msg}", flush=True)  # noqa: E731
        if not carpeta.is_dir():
            carpeta = ingesta.preparar(destino, None, avance)
        mj = machote.preparar(carpeta, not a.sin_video, not a.sin_ia, a.rehacer, a.ancho, a.crf, avance)
        print(json.dumps({k: mj.get(k) for k in ("duracion_s", "fuente_s", "quitado_s", "ia", "residuales", "revision")}, ensure_ascii=False, indent=1))
        if not a.sin_video and not machote.apto(carpeta):
            sys.exit(3)                     # no apto: la revisión final encontró fallas (quien lo llame no lo entrega)
    elif a.cmd == "pro":
        from . import config, pro
        carpeta = config.PROYECTOS / a.proyecto if (config.PROYECTOS / a.proyecto).is_dir() else Path(a.proyecto)
        r = pro.correr(carpeta, a.estilo)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if r["ok"] else 1
    elif a.cmd == "pro-textos":
        from . import pro
        r = pro.pro_textos(Path(a.encargo), a.video)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0 if r["ok"] else 1
    elif a.cmd == "editar":
        editar(a.video, a.estilo, not a.sin_imagenes, a.rondas, a.nombre, a.desde, a.biblioteca, a.densidad)
    elif a.cmd == "crear-estilo":
        from . import estilista
        print(json.dumps(estilista.crear(a.estilo, a.links, a.idea, not a.sin_buscar, a.probar), ensure_ascii=False))
    elif a.cmd == "fuentes":
        from . import fuentes
        if a.accion == "buscar":
            for f in fuentes.buscar(a.texto, a.categoria):
                print(f"{f['familia']:<28} {f['categoria']:<12} {' '.join(f['clases'])}")
        else:
            print(json.dumps(fuentes.instalar(a.texto), ensure_ascii=False))
    elif a.cmd == "sfx":
        from . import sfx
        if a.accion == "organicos":
            print(json.dumps(sfx.traer_organicos(a.por_tipo), ensure_ascii=False))
        else:
            print(f"{sfx.traer(a.por_tipo)} efectos nuevos en {sfx.sonido.BANCO}")
    elif a.cmd == "archivo":
        from . import archivo
        if a.accion == "buscar":
            for c in archivo.buscar(a.palabra, a.n, a.en):
                print(f"{c['ancho']}x{c['alto']} {c['licencia']} {c['titulo'][:60]}  {c['url']}")
        else:
            print("\n".join(archivo.bajar(Path(a.proyecto), a.palabra, a.n, a.en)))
    elif a.cmd == "lote":
        from . import disco, lote
        bib = dict(b.split("=", 1) for b in a.biblioteca)
        asig = dict(x.split("=", 1) for x in a.asignar)
        try:
            print(json.dumps(lote.lote(Path(a.carpeta), [e for e in a.estilos.split(",") if e], Path(a.salida), bib, a.con_imagenes,
                                       a.rondas, a.color_de, asig or None, a.telegram, Path(a.trabajo_en) if a.trabajo_en else None),
                             ensure_ascii=False, indent=1))
        except disco.DiscoError as e:
            print(f"No arranco: {e}", file=sys.stderr)
            return 2
    elif a.cmd == "portadas":
        from . import portadas
        print("\n".join(portadas.todas()))
    elif a.cmd == "integrar":
        from . import integrar
        print(json.dumps(integrar.integrar(a.estilo, a.proyecto, a.nombre), ensure_ascii=False))
    elif a.cmd == "muestras":
        from . import muestras
        rc = muestras.en_cola(argv if argv is not None else sys.argv[1:])
        if rc is not None:
            return rc
        inf = muestras.generar(a.forzar, a.solo)
        print(f"{len(inf['hechas'])} muestras hechas en {muestras.SEL}" + (f"; fallaron {len(inf['fallas'])}: {inf['fallas']}" if inf["fallas"] else ""))
        return 1 if inf["fallas"] else 0
    elif a.cmd == "servir":
        from . import servidor
        servidor.servir(not a.sin_abrir)
    elif a.cmd == "corregir-capas":
        from . import config, corrector_capas
        carpeta = Path(a.proyecto) if Path(a.proyecto).is_dir() else config.PROYECTOS / a.proyecto
        r = corrector_capas.corregir(carpeta, a.texto, a.segundo, a.simular)
        print(json.dumps(r, ensure_ascii=False, indent=1, default=str))
        if r["estado"] == "aplicado":
            corrector_capas._render(carpeta, print)
        return 0 if r["estado"] in ("aplicado", "simulado") else 3
    elif a.cmd == "reparar-cortes":
        from . import config, machote
        carpeta = Path(a.proyecto) if Path(a.proyecto).is_dir() else config.PROYECTOS / a.proyecto
        r = machote.reparar_cortes(carpeta)
        if r["estado"] == "guion_nuevo":
            print(r["mensaje"] + " (queda pendiente de aprobación en la app; no lances el render hasta aprobarlo)")
            return 3
        print({"estable": "los cortes ya estaban bien", "ajustado": "bordes movidos dentro de un silencio, mismas palabras; ahora `estudio render`",
               "empeora": "reparar traería errores de montaje nuevos: se dejaron los cortes como estaban"}[r["estado"]])
    elif a.cmd == "render":
        from . import motor
        print(motor.render(a.carpeta))
    elif a.cmd == "previa":
        from . import motor
        print(motor.vista_previa(Path(a.carpeta), a.tiempos, Path(a.carpeta) / "previa.jpg"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
