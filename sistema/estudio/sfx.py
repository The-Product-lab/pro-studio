"""Banco de efectos de sonido GRABADOS: Openverse (api.openverse.org, gratis y sin llave), solo licencia CC0.

    estudio sfx traer [--por-tipo 3]   → llena librerias/sonido/sfx/<tipo>_ov<n>.wav (48 kHz, sin silencio inicial, ≤ 2,5 s)

Si la máquina ya tiene un banco (en el PC es un enlace al banco de captions/assets-lib/sfx), no baja lo que ya existe.
Cada archivo queda anotado en CREDITOS-openverse.csv con su página original.
"""
import csv
import json
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from . import config, sonido

API = "https://api.openverse.org/v1/audio/"
TIPOS = {"whoosh": "whoosh", "swish": "swish", "impact": "impact hit", "boom": "sub boom", "pop": "pop", "click": "ui click",
         "tick": "tick", "slide": "paper slide", "glitch": "glitch", "zap": "zap", "riser": "riser"}
UA = {"User-Agent": "the-product-studio"}


def _buscar(q: str, n: int) -> list:
    url = API + "?" + urllib.parse.urlencode({"q": q, "license": "cc0", "page_size": 20})
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        res = json.loads(r.read())["results"]
    return [x for x in res if x.get("url") and (x.get("duration") or 9e9) <= 2500][:n]


def _bajar_a_wav(ffmpeg: str, url: str, destino: Path) -> None:
    """Baja el audio a una carpeta temporal y lo convierte a wav (48 kHz mono, sin silencio inicial, ≤ 2,5 s). El temporal queda CERRADO
    antes de que ffmpeg lo lea: en Windows un archivo temporal abierto no se puede abrir otra vez."""
    with tempfile.TemporaryDirectory() as tmp:
        origen = Path(tmp) / ("descarga" + (Path(urllib.parse.urlparse(url).path).suffix or ".mp3"))
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
            origen.write_bytes(r.read())
        subprocess.run([ffmpeg, "-v", "error", "-y", "-i", str(origen), "-af",
                        "silenceremove=start_periods=1:start_threshold=-45dB,atrim=0:2.5", "-ar", str(sonido.SR),
                        "-ac", "1", "-sample_fmt", "s16", str(destino)], check=True)


def traer(por_tipo=3, avance=print) -> int:
    banco = sonido.BANCO
    banco.mkdir(parents=True, exist_ok=True)
    ffmpeg, _ = config.ffmpeg()
    creditos = banco / "CREDITOS-openverse.csv"
    nuevos = 0
    with open(creditos, "a", newline="") as fc:
        w = csv.writer(fc)
        for tipo, q in TIPOS.items():
            ya = len(list(banco.glob(f"{tipo}_*.wav")))
            if ya >= por_tipo:
                continue
            for k, x in enumerate(_buscar(q, por_tipo - ya), start=ya + 1):
                destino = banco / f"{tipo}_ov{k}.wav"
                _bajar_a_wav(ffmpeg, x["url"], destino)
                w.writerow([destino.name, x.get("title", ""), x.get("creator", ""), x.get("foreign_landing_url", ""), "CC0"])
                nuevos += 1
                avance(f"{destino.name}: {x.get('title', '')[:50]}")
    return nuevos


# ---------------------------------------------------------------------------------------------------------------------
# Banco ORGÁNICO (Pablo 07-nov: «los efectos suenan sintéticos, inorgánicos, falsos»; «no puede pesar 45 GB»): sonidos GRABADOS
# de Freesound/Openverse (CC0), bajados uno a uno solo por categoría que el editor usa, y escuchados por el oído del Taller de Audio
# (revisar-kit: descarta lo que suena a latigazo, caricatura o juego/UI) antes de entrar. Pesa megas, no gigas.
# ---------------------------------------------------------------------------------------------------------------------
ORGANICO = config.RAIZ / "librerias" / "sonido" / "organico"
# categoría (mismo nombre que en el Taller) → búsqueda
CATEGORIAS = {
    "whoosh-corto": "cinematic whoosh short", "whoosh-largo": "cinematic whoosh transition", "swish": "swoosh air",
    "riser": "cinematic riser", "boom": "cinematic boom", "golpe-corto": "punchy impact hit", "sub-drop": "sub bass drop",
    "obturador": "camera shutter", "papel-mov": "paper slide", "papel-apoya": "paper on table", "periodico-hoja": "page turn",
    "tela": "cloth rustle", "tecleo": "keyboard typing", "caja-kaching": "cash register", "sello": "rubber stamp",
    "film": "film projector", "platillo-reversa": "reverse cymbal", "celular-desliza": "phone slide table",
    "ficha-desliza": "card slide table", "lapiz-check": "pencil check paper", "marcador": "marker writing", "click-maquina": "typewriter key click",
}
TALLER = Path.home() / "claude-code" / "taller-audio"


def traer_organicos(por_cat=4, avance=print) -> dict:
    """Baja hasta `por_cat` sonidos por categoría a una carpeta de paso, los hace escuchar al Taller (revisar-kit) y deja en
    `ORGANICO/<categoría>/` solo los que el oído aprueba. → {categoría: n aprobados}."""
    ffmpeg, _ = config.ffmpeg()
    paso = ORGANICO.parent / "_paso"
    paso.mkdir(parents=True, exist_ok=True)
    indice = []
    for cat, q in CATEGORIAS.items():
        ya = len(list((ORGANICO / cat).glob("*.wav"))) if (ORGANICO / cat).exists() else 0
        if ya >= por_cat:
            continue
        (paso / cat).mkdir(exist_ok=True)
        for k, x in enumerate(_buscar(q, por_cat * 2), start=1):      # el doble: el oído descarta parte
            destino = paso / cat / f"{cat}_{k}.wav"
            try:
                _bajar_a_wav(ffmpeg, x["url"], destino)
            except Exception as e:  # noqa: BLE001 — un archivo roto no frena el banco
                avance(f"{cat}: no se pudo bajar «{x.get('title', '')[:40]}» ({type(e).__name__})")
                continue
            indice.append({"archivo": f"{cat}/{destino.name}", "titulo": x.get("title", ""), "autor": x.get("creator", ""),
                           "url": x.get("foreign_landing_url", ""), "licencia": "CC0"})
    (paso / "indice.json").write_text(json.dumps(indice, ensure_ascii=False, indent=1))
    avance(f"el oído del Taller revisa {len(indice)} sonidos…")
    informe = paso / "_informe"
    subprocess.run([str(TALLER / "taller.sh"), "revisar-kit", str(paso), "--salida", str(informe)], check=True)
    veredicto = {x["archivo"]: x["nivel"] for x in json.loads((informe / "informe-kit.json").read_text())}
    aprobados: dict = {}
    creditos = ORGANICO / "CREDITOS.csv"
    ORGANICO.mkdir(parents=True, exist_ok=True)
    with open(creditos, "a", newline="") as fc:
        w = csv.writer(fc)
        for x in indice:
            cat = x["archivo"].split("/")[0]
            n = len(list((ORGANICO / cat).glob("*.wav"))) if (ORGANICO / cat).exists() else 0
            if veredicto.get(x["archivo"]) != "ok" or n >= por_cat:
                continue
            (ORGANICO / cat).mkdir(exist_ok=True)
            final = ORGANICO / cat / f"{cat}_{n + 1}.wav"
            (paso / x["archivo"]).replace(final)
            w.writerow([f"{cat}/{final.name}", x["titulo"], x["autor"], x["url"], "CC0"])
            aprobados[cat] = aprobados.get(cat, 0) + 1
    import shutil
    shutil.rmtree(paso, ignore_errors=True)     # nada de intermedios (regla de limpieza)
    return aprobados
