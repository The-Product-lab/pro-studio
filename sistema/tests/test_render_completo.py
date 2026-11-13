"""El render nunca entrega un final con cuadros de menos y la memoria de tramos sí se reusa (09-nov: una corrección re-exportaba
todo — `_cuadro_guardado` devolvía otra forma y ningún tramo calzaba — y con el PC cargado un tramo salió con 26 de 90 cuadros
y el final con 423 de 511, sin aviso)."""
import subprocess

import numpy as np
import pytest

from estudio import config, motor, tramos


def _video(path, cuadros):
    subprocess.run([config.ffmpeg()[0], "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size=1080x1920:rate=30:d={cuadros / 30}",
                    "-pix_fmt", "yuv420p", str(path)], check=True)


def test_cuadro_guardado_tiene_la_forma_del_nuevo(tmp_path):
    f = tmp_path / "t.mp4"
    _video(f, 30)
    assert tramos._cuadro_guardado(f, 10).shape == (480, 270)


def test_tramo_guardado_roto_no_se_reusa(tmp_path):
    f = tmp_path / "roto.mp4"
    f.write_bytes(b"no es un video")
    with pytest.raises(ValueError):
        tramos._cuadro_guardado(f, 10)


def test_cuenta_cuadros(tmp_path):
    f = tmp_path / "t.mp4"
    _video(f, 45)
    assert motor._cuadros(f) == 45


def test_trozo_seguro_devuelve_el_error_en_vez_de_romper(monkeypatch):
    def falla(args):
        raise RuntimeError("tramo 0–90: salieron 26 de 90 cuadros")
    monkeypatch.setattr(motor, "_trozo", falla)
    assert motor._trozo_seguro(("x", 0, 90, "y")) == (0, "tramo 0–90: salieron 26 de 90 cuadros")
