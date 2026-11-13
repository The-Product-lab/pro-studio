"""El paquete trae su propio ffmpeg (`config.ffmpeg()`): nada del motor llama al de la máquina, que en un equipo nuevo no existe
o es otra versión (10-nov: en una Mac sin ffmpeg, Estilos Pro reventaba con «No such file or directory: 'ffprobe'»)."""
import re
from pathlib import Path

from estudio import config

A_SECAS = re.compile(r"""\[\s*["']ff(mpeg|probe)["']\s*,""")   # ["ffmpeg", …]: el nombre a secas como primer elemento de un comando


def test_nadie_llama_al_ffmpeg_de_la_maquina():
    raiz = Path(config.__file__).parent
    malos = [f"{f.relative_to(raiz.parent)}:{n}" for f in sorted(raiz.rglob("*.py"))
             for n, linea in enumerate(f.read_text().splitlines(), 1) if A_SECAS.search(linea)]
    assert malos == [], f"usa config.ffmpeg() en: {malos}"
