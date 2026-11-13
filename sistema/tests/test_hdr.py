"""Un video en HDR (iPhone: HLG / Dolby Vision) entra convertido de verdad a Rec.709, no solo con la matriz cambiada (11-nov: salía
lavado, con la piel pálida y verdosa), y siempre se convierte aunque ya venga vertical a 30 fps."""
import json
import subprocess

import numpy as np
import pytest

from estudio import color, config, ingesta


@pytest.fixture
def hlg(tmp_path):
    """1 s vertical 1080×1920 a 30 fps marcado como HLG, todo en el blanco de referencia del HLG (señal 0,75) + un tono."""
    try:
        ffmpeg, ffprobe = config.ffmpeg()
    except Exception:   # noqa: BLE001 — sin ffmpeg en esta máquina: se salta, nunca falla por eso
        pytest.skip("sin ffmpeg")
    v = tmp_path / "iphone.mov"
    subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=0xBFBFBF:s=1080x1920:r=30:d=1", "-f", "lavfi", "-i", "sine=f=440:d=1",
                    "-vf", "format=yuv420p10le,setparams=color_trc=arib-std-b67:color_primaries=bt2020:colorspace=bt2020nc",
                    "-c:v", "libx264", "-c:a", "aac", "-shortest", str(v)], check=True)
    assert ingesta._probar(v)["hdr"]
    return v, ffmpeg, ffprobe


def _gris(ffmpeg, video) -> float:
    crudo = subprocess.run([ffmpeg, "-v", "error", "-i", str(video), "-frames:v", "1", "-vf", "scale=16:16,format=gray", "-f", "rawvideo", "-"],
                           capture_output=True, check=True).stdout
    return float(np.frombuffer(crudo, np.uint8).mean())


def test_un_hdr_ya_vertical_tambien_se_convierte_y_queda_marcado_rec709(hlg, tmp_path):
    v, ffmpeg, ffprobe = hlg
    c = tmp_path / "proy"
    c.mkdir()
    meta = ingesta.sondear(v, c, lambda *_: None)
    assert meta["video"] == str((c / "fuente.mp4").resolve()) and meta["hdr"] is False   # convertido: el motor ya no le hace nada
    s = json.loads(subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=color_transfer,color_primaries,color_space,pix_fmt", "-of", "json", meta["video"]],
                                  capture_output=True, text=True, check=True).stdout)["streams"][0]
    assert (s["color_transfer"], s["color_primaries"], s["color_space"], s["pix_fmt"]) == ("bt709", "bt709", "bt709", "yuv420p")
    # el blanco de referencia del HLG (señal 0,75) queda donde macOS lo muestra en un iPhone (0,35 de luz → ~150 de 255), no quemado
    # (con 0,9 de luz daba ~243: IMG_4955 e IMG_4965 salían 1,4 pasos más claros que en el teléfono)
    despues = _gris(ffmpeg, meta["video"])
    assert 138 < despues < 162, despues


def test_la_cadena_es_la_aprobada_y_no_depende_de_zscale():
    for trc in color.HDR:
        cadena = color.hdr_a_sdr(trc)
        assert "zscale" not in cadena and "tonemap" not in cadena and cadena.count("lutrgb=") == 2 and "colorchannelmixer" in cadena
    assert "0.35/0.2646" in color.hdr_a_sdr("arib-std-b67") and "0.9/203*10000" in color.hdr_a_sdr("smpte2084")
