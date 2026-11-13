"""Un render deja en el proyecto solo lo que sirve: `final.mp4` y la memoria de tramos `.tramos/` (se reusa en las
correcciones; los tramos viejos los quita memoria.limpiar). Nada de intermedios que se acumulen y se degraden."""
import types

import numpy as np

from estudio import motor, sonido


def test_limpiar_render_quita_el_video_mudo_y_conserva_la_memoria_de_tramos(tmp_path):
    (tmp_path / ".tramos").mkdir()
    (tmp_path / ".tramos" / "t000.mp4").write_bytes(b"x")
    (tmp_path / "video_mudo.mp4").write_bytes(b"x")
    (tmp_path / "final.mp4").write_bytes(b"x")
    motor.limpiar_render(tmp_path)
    motor.limpiar_render(tmp_path)                       # sin nada que limpiar tampoco falla
    assert sorted(p.name for p in tmp_path.iterdir()) == [".tramos", "final.mp4"]
    assert (tmp_path / ".tramos" / "t000.mp4").exists()


def test_mezclar_no_deja_el_wav_de_efectos_ni_si_ffmpeg_falla(tmp_path, monkeypatch):
    p = types.SimpleNamespace(dir=tmp_path, mapa=list(range(30)), meta={"video": "v.mp4"})
    monkeypatch.setattr(sonido, "efectos", lambda *a, **k: np.zeros(sonido.SR))
    monkeypatch.setattr(sonido, "_tramos", lambda *_: [(0.0, 1.0)])
    llamadas = []

    def falso(cmd, check):
        llamadas.append((tmp_path / "sfx.wav").exists())          # existe mientras ffmpeg lo lee
        if len(llamadas) == 2:
            raise RuntimeError("ffmpeg")
    monkeypatch.setattr(sonido.subprocess, "run", falso)
    sonido.mezclar(p, tmp_path / "m.mp4", tmp_path / "f.mp4")
    assert llamadas == [True] and not (tmp_path / "sfx.wav").exists()
    try:
        sonido.mezclar(p, tmp_path / "m.mp4", tmp_path / "f.mp4")
    except RuntimeError:
        pass
    assert not (tmp_path / "sfx.wav").exists()
