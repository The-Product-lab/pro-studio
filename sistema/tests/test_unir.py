"""Un video grabado en 2 o 3 partes se sube junto y se une en uno antes de preparar (Pablo, 13-nov: «hoy la app no deja seleccionar
ni subir varios archivos a la vez»). Las partes pueden venir distintas: se igualan al tamaño y los cuadros por segundo de la primera
y a un sonido común; la que no trae sonido entra en silencio; el orden es el que dejó la persona."""
import subprocess
from pathlib import Path

import pytest

from estudio import config, errores, servidor, unir

APP = Path(__file__).resolve().parent.parent / "app"


def _parte(ruta: Path, color: str, tam: str, fps: int, seg: float, audio: bool = True) -> Path:
    ffmpeg, _ = config.ffmpeg()
    sonido = ["-f", "lavfi", "-i", f"sine=frequency=330:duration={seg}"] if audio else []
    subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:size={tam}:rate={fps}:d={seg}", *sonido,
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", *(["-c:a", "aac", "-ac", "1", "-shortest"] if audio else ["-an"]), str(ruta)],
                   check=True)
    return ruta


def _color_en(video: Path, t: float) -> tuple:
    """El color (r, g, b) del centro del cuadro en el segundo `t`."""
    ffmpeg, _ = config.ffmpeg()
    b = subprocess.run([ffmpeg, "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", "-vf", "crop=2:2,scale=1:1",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return tuple(b[:3])


def test_tres_partes_distintas_quedan_en_un_solo_video_en_el_orden_dado(tmp_path):
    a = _parte(tmp_path / "IMG_0002.mp4", "red", "1280x720", 25, 1.0)
    b = _parte(tmp_path / "IMG_0010.mp4", "blue", "540x960", 30, 1.0, audio=False)   # vertical, más chica y sin sonido
    c = _parte(tmp_path / "IMG_0003.mov", "green", "640x360", 60, 1.0)
    avisos = []
    final = unir.unir([a, c, b], tmp_path / "junto.mp4", avisos.append)
    s = unir._sonda(final)
    assert (s["ancho"], s["alto"]) == (1280, 720) and s["fps"] == pytest.approx(25) and s["audio"]   # todo a lo de la PRIMERA
    assert s["duracion"] == pytest.approx(3.0, abs=.15)
    rojo, verde, centro_azul = _color_en(final, .5), _color_en(final, 1.5), _color_en(final, 2.5)
    assert rojo[0] > 180 and rojo[2] < 80 and verde[1] > 90 and verde[0] < 80 and centro_azul[2] > 180 and centro_azul[0] < 80   # orden a, c, b
    assert any("uniendo 3 partes" in x for x in avisos) and not list(tmp_path.glob(".*uniendo*"))   # sin restos a medias


def test_la_parte_vertical_no_se_deforma_se_centra_con_franjas(tmp_path):
    a = _parte(tmp_path / "a.mp4", "red", "1280x720", 30, .6)
    b = _parte(tmp_path / "b.mp4", "blue", "540x960", 30, .6)
    final = unir.unir([a, b], tmp_path / "junto.mp4", lambda m: None)
    ffmpeg, _ = config.ffmpeg()
    px = subprocess.run([ffmpeg, "-v", "error", "-ss", "0.9", "-i", str(final), "-frames:v", "1", "-vf", "crop=2:2:20:360,scale=1:1",
                         "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout[:3]
    assert max(px) < 40                                  # el borde izquierdo de la segunda parte es franja negra, no azul estirado
    assert _color_en(final, .9)[2] > 180                 # y su centro sí es la toma


def test_la_orden_es_igual_en_cualquier_sistema_y_la_muda_entra_en_silencio():
    base = {"ancho": 1081, "alto": 1920, "fps": 59.94, "duracion": 2.5, "audio": True, "trc": "bt709", "primarias": "bt709", "matriz": "bt709",
            "hdr": False, "diez_bits": False}
    muda = {**base, "ancho": 640, "alto": 360, "audio": False, "duracion": 1.25}
    cmd = unir.orden([Path("C:/Users/Ana María/Videos/parte 1.mov"), Path("parte 2.mp4")], [base, muda], Path("sale.mp4"))
    filtro = cmd[cmd.index("-filter_complex") + 1]
    assert "scale=1080:1920" in filtro and "pad=1080:1920" in filtro and "fps=59.94" in filtro   # tamaño par, cuadros de la primera
    assert "anullsrc=r=48000:cl=stereo,atrim=duration=1.250" in filtro and "[1:a:0]" not in filtro
    assert "concat=n=2:v=1:a=1" in filtro and "format=yuv420p," in filtro
    assert cmd.count("-i") == 2 and "C:/Users/Ana María/Videos/parte 1.mov" in [c.replace("\\", "/") for c in cmd]   # rutas como argumentos, sin comillas ni intérprete
    hdr = {**base, "hdr": True, "diez_bits": True, "trc": "arib-std-b67", "primarias": "bt2020", "matriz": "bt2020nc"}
    cmd = unir.orden([Path("a.mov"), Path("b.mov")], [hdr, hdr], Path("sale.mp4"))
    assert "format=yuv420p10le" in cmd[cmd.index("-filter_complex") + 1] and cmd[cmd.index("-color_trc") + 1] == "arib-std-b67"


def test_lo_que_no_se_puede_unir_se_dice_claro(tmp_path, monkeypatch):
    a = _parte(tmp_path / "a.mp4", "red", "320x180", 30, .4)
    with pytest.raises(errores.Aviso, match="al menos dos partes"):
        unir.unir([a], tmp_path / "x.mp4")
    with pytest.raises(errores.Aviso, match="Ya no encuentro «falta.mp4»"):
        unir.unir([a, tmp_path / "falta.mp4"], tmp_path / "x.mp4")
    roto = tmp_path / "roto.mp4"
    roto.write_bytes(b"esto no es un video")
    with pytest.raises(errores.Aviso, match="No pude leer «roto.mp4»"):
        unir.unir([a, roto], tmp_path / "x.mp4")
    with pytest.raises(errores.Aviso, match="demasiadas partes"):
        unir.unir([a] * (unir.MAX_PARTES + 1), tmp_path / "x.mp4")
    real = unir._sonda
    monkeypatch.setattr(unir, "_sonda", lambda v: {**real(v), "hdr": Path(v).name == "a.mp4"})
    b = _parte(tmp_path / "b.mp4", "blue", "320x180", 30, .4)
    with pytest.raises(errores.Aviso, match="HDR"):
        unir.unir([a, b], tmp_path / "x.mp4")
    assert not (tmp_path / "x.mp4").exists()


def test_la_app_une_solo_lo_que_ella_subio_borra_las_partes_y_no_pisa_otro_video(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    subidas = tmp_path / "_subidas"
    subidas.mkdir()
    a = _parte(subidas / "Toma 1.mp4", "red", "320x180", 30, .5)
    b = _parte(subidas / "Toma 2.mp4", "blue", "320x180", 30, .5)
    (subidas / "Toma 1-unido.mp4").write_bytes(b"otro video que ya estaba")
    fuera = _parte(tmp_path / "fuera.mp4", "green", "320x180", 30, .5)
    with pytest.raises(errores.Aviso, match="subidos desde esta pantalla"):
        servidor._unir([str(a), str(fuera)], lambda m: None)
    assert a.exists() and fuera.exists()
    final = Path(servidor._unir([str(a), str(b)], lambda m: None))
    assert final == (subidas / "Toma 1-unido-2.mp4").resolve() and unir._sonda(final)["duracion"] == pytest.approx(1.0, abs=.12)
    assert not a.exists() and not b.exists()                                           # las partes ya están dentro del video unido
    assert (subidas / "Toma 1-unido.mp4").read_bytes() == b"otro video que ya estaba"   # el que ya estaba no se pisó


def test_la_pantalla_deja_elegir_y_soltar_varios_archivos():
    html = (APP / "index.html").read_text(encoding="utf-8")
    assert 'id="file" accept="video/*" multiple' in html
    js = (APP / "app.js").read_text(encoding="utf-8")
    assert "elegidos(e.dataTransfer.files)" in js and "elegidos(e.target.files)" in js   # arrastrar y elegir: todos los archivos, no solo el primero
    assert "files[0]" not in js
    assert '"/api/unir"' in js and "numeric: true" in js and "lastModified" in js       # se unen; orden por nombre («2» antes que «10») o por fecha
    assert "data-sube" in js and "data-baja" in js and "data-quita" in js              # y se puede reordenar o quitar a mano
