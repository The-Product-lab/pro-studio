"""Un video grabado en vertical se lee como vertical aunque la rotación no sea el primer dato del archivo (11-nov: iPhone 4K en HDR
Dolby Vision; `ffprobe` devuelve antes el registro de Dolby y la app lo trató como horizontal: recortó una tajada de la esquina)."""
import json
import subprocess
from pathlib import Path

import pytest

from estudio import config, ingesta


def _ffprobe(monkeypatch, datos_laterales):
    video = {"streams": [{"width": 3840, "height": 2160, "color_transfer": "arib-std-b67", "r_frame_rate": "30/1",
                          **({"side_data_list": datos_laterales} if datos_laterales is not None else {})}],
             "format": {"duration": "68.351700"}}

    def correr(cmd, **_):
        return subprocess.CompletedProcess(cmd, 0, stdout="1" if "a" in cmd else json.dumps(video), stderr="")
    monkeypatch.setattr(config, "ffmpeg", lambda: ("ffmpeg", "ffprobe"))
    monkeypatch.setattr(ingesta.subprocess, "run", correr)


@pytest.mark.parametrize("datos, vertical", [
    ([{}, {"rotation": -90}, {}], True),      # iPhone HDR: lo que devuelve ffprobe de verdad con el IMG_5339
    ([{"rotation": 90}], True),               # iPhone sin HDR
    ([{"rotation": -270}], True),
    ([{}, {"rotation": 180}], False),         # de cabeza sigue siendo horizontal
    ([{}], False), (None, False),             # cámara: sin rotación
])
def test_la_rotacion_se_lee_aunque_no_sea_el_primer_dato(monkeypatch, datos, vertical):
    _ffprobe(monkeypatch, datos)
    p = ingesta._probar(Path("x.mov"))
    assert (p["ancho"], p["alto"]) == ((2160, 3840) if vertical else (3840, 2160)) and p["hdr"]
