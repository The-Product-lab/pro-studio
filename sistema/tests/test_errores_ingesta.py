"""Punto 1 de la tanda 1 (Pablo, 07-nov): al preparar un video salió en pantalla «ValueError: invalid literal for int() with base 10: ''».
1) Contar cuadros no revienta aunque ffprobe no entregue el dato (S-Log de la Sony): cae a duración × fps.
2) La app nunca muestra trazas: frase clara en español; el detalle técnico va solo al registro."""
import subprocess

import pytest

from estudio import config, errores, ingesta


def _video(tmp_path, seg=2):
    ffmpeg, _ = config.ffmpeg()
    v = tmp_path / "v.mp4"
    subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size=160x284:rate=30:duration={seg}",
                    "-f", "lavfi", "-i", f"sine=duration={seg}", "-pix_fmt", "yuv420p", "-shortest", str(v)], check=True)
    return v


def test_cuadros_de_un_video_real(tmp_path):
    assert ingesta._cuadros(_video(tmp_path)) == 60


def test_ffprobe_vacio_no_revienta(tmp_path, monkeypatch):
    v = _video(tmp_path)
    real = subprocess.run

    def vacio(cmd, *a, **k):
        if "-count_packets" in cmd or "stream=nb_frames" in cmd or "-count_frames" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="\n", stderr="")
        return real(cmd, *a, **k)
    monkeypatch.setattr(ingesta.subprocess, "run", vacio)
    assert ingesta._cuadros(v) == 60            # duración × fps


@pytest.mark.parametrize("texto,esperado", [("", None), ("N/A", None), ("0", None), ("1832\n", 1832), ("1832,", 1832)])
def test_entero_tolerante(texto, esperado):
    assert ingesta._entero(texto) == esperado


@pytest.mark.parametrize("e", [ValueError("invalid literal for int() with base 10: ''"),
                               subprocess.CalledProcessError(1, ["ffprobe", "-v", "error"]),
                               KeyError("streams"), RuntimeError("boom"), FileNotFoundError("/x/y.py line 3")])
def test_la_pantalla_nunca_ve_trazas(e, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    f = errores.amable("preparar", e)
    for malo in ("Traceback", "invalid literal", "ffprobe", ".py", "int()", "KeyError", "RuntimeError"):
        assert malo not in f
    assert type(e).__name__ in (tmp_path / "_errores.log").read_text()      # el detalle queda en el registro


def test_frase_nuestra_se_conserva():
    assert errores.frase(ValueError("el video no tiene audio")) == "el video no tiene audio"
