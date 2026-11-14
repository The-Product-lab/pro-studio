"""Unir varias partes en UN video antes de preparar (Pablo, 13-nov: «un video puede venir grabado en 2 o 3 partes»).

Las partes pueden venir distintas (otro tamaño, otros cuadros por segundo, una sin sonido, el celular girado): todas se llevan a lo de
la PRIMERA (su tamaño ya derecho y sus cuadros por segundo; la que no llena el cuadro se centra con franjas, no se deforma) y a un
sonido común (48 kHz estéreo; la parte muda entra en silencio), y se pegan en el orden recibido. Sale un solo `.mp4` que el resto
del flujo trata como cualquier video subido. El color no se toca: si las partes son HDR (iPhone) el resultado conserva 10 bits y sus
marcas, y la ingesta lo convierte como siempre. No se mezclan partes HDR con partes que no lo son: se dice claro.
ffmpeg corre sin intérprete de órdenes y con rutas como argumentos: igual en Mac, Windows y Linux."""
import json
import subprocess
from pathlib import Path

from . import color, config, errores, trabajo

MAX_PARTES = 20
MEZCLA_HDR = ("Unas partes están grabadas en HDR y otras no, y no se pueden unir sin dañar el color. Graba todas con el mismo ajuste "
              "de cámara, o súbelas por separado.")


def _sonda(video: Path) -> dict:
    """Lo que hace falta saber de una parte: tamaño ya derecho, cuadros por segundo, duración, si trae sonido y su color."""
    _, ffprobe = config.ffmpeg()
    try:
        info = json.loads(subprocess.run(
            [ffprobe, "-v", "error", "-show_entries",
             "stream=codec_type,width,height,r_frame_rate,pix_fmt,color_transfer,color_primaries,color_space:stream_side_data=rotation"
             ":format=duration", "-of", "json", str(video)], capture_output=True, text=True, check=True).stdout)
        v = next(s for s in info["streams"] if s.get("codec_type") == "video")
        num, den = (int(x) for x in v["r_frame_rate"].split("/"))
        ancho, alto, duracion = int(v["width"]), int(v["height"]), float(info["format"]["duration"])
    except (subprocess.CalledProcessError, StopIteration, KeyError, ValueError, ZeroDivisionError):
        raise errores.Aviso(f"No pude leer «{video.name}» como video. Quítalo de la lista o vuelve a exportarlo desde la cámara.") from None
    rotacion = next((abs(int(d["rotation"])) for d in v.get("side_data_list", []) if "rotation" in d), 0)
    if rotacion in (90, 270):   # ffmpeg entrega los cuadros ya girados
        ancho, alto = alto, ancho
    return {"ancho": ancho, "alto": alto, "fps": num / den if den else 30.0, "duracion": duracion,
            "audio": any(s.get("codec_type") == "audio" for s in info["streams"]),
            "trc": v.get("color_transfer") or "", "primarias": v.get("color_primaries") or "", "matriz": v.get("color_space") or "",
            "hdr": v.get("color_transfer") in color.HDR, "diez_bits": "10" in (v.get("pix_fmt") or "")}


def orden(videos: list, sondas: list, destino: Path, tramos: list | None = None) -> list[str]:
    """La orden de ffmpeg que une las partes (pura: se prueba sin correr nada). `tramos`: por parte, (desde, hasta) en segundos para
    tomar solo ese pedazo del archivo, o None para tomarlo entero (lo usa el reparto de una grabación en videos)."""
    tramos = tramos or [None] * len(videos)
    ffmpeg, _ = config.ffmpeg()
    base = sondas[0]
    ancho, alto = base["ancho"] // 2 * 2, base["alto"] // 2 * 2
    fps = min(60.0, max(1.0, base["fps"]))
    formato = "yuv420p10le" if base["hdr"] and base["diez_bits"] else "yuv420p"
    cmd, filtros, pares = [ffmpeg, "-v", "error", "-y"], [], ""
    for v, t in zip(videos, tramos):
        if t:   # el pedazo se pide al abrir el archivo: al volver a codificar, el corte cae en el cuadro exacto
            cmd += ["-ss", f"{t[0]:.3f}", "-t", f"{t[1] - t[0]:.3f}"]
        cmd += ["-i", str(v)]
    for i, s in enumerate(sondas):
        dura = tramos[i][1] - tramos[i][0] if tramos[i] else s["duracion"]
        filtros.append(f"[{i}:v:0]scale={ancho}:{alto}:force_original_aspect_ratio=decrease:flags=lanczos,"
                       f"pad={ancho}:{alto}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps:.6g},format={formato},setpts=PTS-STARTPTS[v{i}]")
        if s["audio"]:
            filtros.append(f"[{i}:a:0]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS[a{i}]")
        else:   # parte sin sonido: su mismo tiempo en silencio, para que las demás no se corran
            filtros.append(f"anullsrc=r=48000:cl=stereo,atrim=duration={dura:.3f},asetpts=PTS-STARTPTS[a{i}]")
        pares += f"[v{i}][a{i}]"
    filtros.append(f"{pares}concat=n={len(videos)}:v=1:a=1[v][a]")
    cmd += ["-filter_complex", ";".join(filtros), "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", "fast", "-crf", "14",
            "-c:a", "aac", "-b:a", "256k"]
    for opcion, valor in (("-color_trc", base["trc"]), ("-color_primaries", base["primarias"]), ("-colorspace", base["matriz"])):
        if valor and valor != "unknown":   # el color de las tomas viaja marcado como venía
            cmd += [opcion, valor]
    return cmd + ["-movflags", "+faststart", str(destino)]


def unir(videos: list, destino: Path, avance=print, tramos: list | None = None) -> Path:
    """`videos` en el orden en que deben quedar → `destino` (un solo .mp4). Lanza `errores.Aviso` con lo que la persona debe hacer.
    Con `tramos` (uno por video: (desde, hasta) o None) toma solo ese pedazo de cada archivo; ahí vale también un solo pedazo."""
    videos = [Path(v) for v in videos]
    if tramos is not None and len(tramos) != len(videos):
        raise ValueError("unir: un tramo por video")
    if len(videos) < (1 if tramos else 2):
        raise errores.Aviso("Para unir hacen falta al menos dos partes.")
    if len(videos) > MAX_PARTES:
        raise errores.Aviso(f"Son demasiadas partes ({len(videos)}): se unen hasta {MAX_PARTES} a la vez.")
    falta = next((v for v in videos if not v.is_file()), None)
    if falta:
        raise errores.Aviso(f"Ya no encuentro «{falta.name}». Sube las partes otra vez.")
    sondas = [_sonda(v) for v in videos]
    if len({s["hdr"] for s in sondas}) > 1:
        raise errores.Aviso(MEZCLA_HDR)
    if tramos:   # ningún pedazo se sale de su archivo
        tramos = [None if t is None else (max(0.0, float(t[0])), min(s["duracion"], float(t[1]))) for t, s in zip(tramos, sondas)]
        if any(t is not None and t[1] - t[0] < .05 for t in tramos):
            raise errores.Aviso("Uno de los pedazos quedó vacío. Revisa el reparto y prueba de nuevo.")
    total = sum(t[1] - t[0] if t else s["duracion"] for t, s in zip(tramos or [None] * len(videos), sondas))
    avance(f"uniendo {len(videos)} partes ({total:.0f} s en total)…")
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_name(f".{destino.stem}.uniendo.mp4")
    try:
        trabajo.correr(orden(videos, sondas, parcial, tramos), check=True)   # se puede detener desde la app
        hecho = _sonda(parcial)
        if not hecho["audio"] or abs(hecho["duracion"] - total) > .5 + .1 * len(videos):
            raise errores.Aviso("La unión salió incompleta. Prueba de nuevo; si se repite, sube las partes por separado.")
        parcial.replace(destino)
    finally:
        parcial.unlink(missing_ok=True)
    avance(f"partes unidas: {destino.name}")
    return destino
