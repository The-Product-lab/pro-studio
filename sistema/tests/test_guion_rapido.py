"""docs/PLANO-GUION-RAPIDO.md: el guion sale primero, el director solo después de la orden (guion aprobado + estilo elegido),
un solo Whisper (GPU si arranca, CPU si no) y un estilo nuevo parte de su preset completo."""
import json
import threading
from pathlib import Path

import pytest

from estudio import asr, config, director, ingesta, servidor, validar


# ---------- motores: un solo Whisper, GPU con caída a CPU ----------

class _Modelo:
    def __init__(self, dispositivo, falla_al_transcribir=False):
        self.dispositivo, self.falla = dispositivo, falla_al_transcribir

    def transcribe(self, audio, **kw):
        if self.falla:
            raise RuntimeError("CUDA out of memory")
        return iter([f"segmento-{self.dispositivo}"]), None


@pytest.fixture
def whisper(monkeypatch):
    creados = []
    monkeypatch.setattr(asr, "_estado", {"modelo": None, "dispositivo": None, "sin_gpu": False})
    monkeypatch.setattr(asr, "AVISOS", [])
    monkeypatch.delenv("ESTUDIO_WHISPER", raising=False)
    monkeypatch.setattr(asr, "_cuda_servible", lambda: not asr._estado["sin_gpu"])
    return creados


def _fabrica(creados, falla_cuda_al_crear=False, falla_cuda_al_transcribir=False):
    def crear(dispositivo):
        creados.append(dispositivo)
        if dispositivo == "cuda" and falla_cuda_al_crear:
            raise OSError("libcublas.so.12 not found")
        return _Modelo(dispositivo, falla_cuda_al_transcribir and dispositivo == "cuda")
    return crear


def test_un_solo_modelo_para_todos(whisper, monkeypatch):
    monkeypatch.setattr(asr, "_crear", _fabrica(whisper))
    assert asr.transcribir([0.0]) == ["segmento-cuda"] == asr.transcribir([0.0])
    assert whisper == ["cuda"]


def test_sin_gpu_usable_cae_a_cpu_con_aviso(whisper, monkeypatch):
    monkeypatch.setattr(asr, "_crear", _fabrica(whisper, falla_cuda_al_crear=True))
    assert asr.transcribir([0.0]) == ["segmento-cpu"]
    assert whisper == ["cuda", "cpu"] and "se usa la CPU" in asr.AVISOS[0]


def test_la_gpu_falla_a_mitad_de_transcripcion_y_sigue_en_cpu(whisper, monkeypatch):
    monkeypatch.setattr(asr, "_crear", _fabrica(whisper, falla_cuda_al_transcribir=True))
    assert asr.transcribir([0.0]) == ["segmento-cpu"]
    assert asr.dispositivo() == "cpu" and "se sigue en CPU" in asr.AVISOS[-1]
    assert asr.transcribir([0.0]) == ["segmento-cpu"] and whisper == ["cuda", "cpu"]   # no vuelve a probar la GPU


def test_cpu_forzada_no_toca_la_gpu(whisper, monkeypatch):
    monkeypatch.setattr(asr, "_crear", _fabrica(whisper))
    monkeypatch.undo()   # _cuda_servible real: respeta ESTUDIO_WHISPER
    monkeypatch.setenv("ESTUDIO_WHISPER", "cpu")
    assert asr._cuda_servible() is False


def test_nadie_mas_crea_whisper_por_su_cuenta():
    for f in (Path(servidor.__file__).parent).glob("*.py"):
        if f.name != "asr.py":
            assert "WhisperModel(" not in f.read_text(), f.name


# ---------- el flujo: guion primero, director después de la orden ----------

@pytest.fixture
def proyectos(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    monkeypatch.setattr(servidor, "TRABAJOS", {})
    monkeypatch.setattr(servidor, "_PEDIDO", {})
    monkeypatch.setattr(servidor, "_DIRIGIENDO", {})
    return tmp_path


@pytest.fixture
def falsa_ingesta(monkeypatch, proyectos):
    """Ingesta sin video ni modelos: deja las mismas marcas que la real."""
    llamadas = []
    monkeypatch.setattr(ingesta, "_probar", lambda v: {"duracion": 10.0})
    monkeypatch.setattr(ingesta, "_duracion", lambda v: 10.0)
    monkeypatch.setattr(ingesta, "transcribir", lambda v, d: (d.write_text("[]"), [])[1])
    from estudio import machote, montaje
    monkeypatch.setattr(montaje, "voces_fuera", lambda c, p, avance=None: p)

    def machote_falso(carpeta, con_video=True, avance=print, **_):
        llamadas.append(("machote", ingesta.es_provisional(carpeta)))
        (Path(carpeta) / "machote.json").write_text(json.dumps({"cortes": []}))
    monkeypatch.setattr(machote, "preparar", machote_falso)

    def sondear(video, carpeta, avance=print):
        llamadas.append(("sondear",))
        (Path(carpeta) / "fuente.mp4").write_text("normalizado")
        return {"video": str(carpeta / "fuente.mp4"), "original": str(video), "cuadros": 300, "hdr": False}
    monkeypatch.setattr(ingesta, "sondear", sondear)
    monkeypatch.setattr(ingesta.persona, "ubicar", lambda *a, **k: llamadas.append(("ubicar",)))
    return llamadas


def test_el_guion_sale_con_fuente_provisional_y_la_media_la_deja_definitiva(falsa_ingesta, proyectos, tmp_path):
    carpeta = ingesta.preparar_guion(tmp_path / "v.mp4", "p1")
    assert ingesta.es_provisional(carpeta) and (carpeta / "machote.json").exists()
    assert ("machote", True) in falsa_ingesta and ("sondear",) not in falsa_ingesta   # el guion no esperó la normalización
    ingesta.preparar_media(tmp_path / "v.mp4", "p1")
    assert not ingesta.es_provisional(carpeta)
    assert json.loads((carpeta / "fuente.json").read_text())["video"].endswith("fuente.mp4")
    with pytest.raises(FileNotFoundError):   # derivar de un proyecto provisional nunca copia un video falso
        ingesta.preparar_guion(tmp_path / "w.mp4", "p2")
        ingesta.derivar("p2", "p3")


def test_regla_principal_preparar_no_decide_nada(falsa_ingesta, proyectos, tmp_path, monkeypatch):
    """Antes de la orden de la persona solo hay trabajo neutro: sin storyboard, sin arte.json, sin llamadas del director."""
    quien = []
    for nombre in ("dirigir", "mirar"):
        monkeypatch.setattr(director, nombre, lambda *a, _n=nombre, **k: quien.append(_n))
    from estudio import imagenes
    monkeypatch.setattr(imagenes, "generar", lambda *a, **k: quien.append("imagenes"))
    monkeypatch.setattr(imagenes, "conector", lambda: imagenes.HF)   # sin consultar la cuenta real de Claude
    servidor._preparar(str(tmp_path / "v.mp4"), "p1", print)
    c = proyectos / "p1"
    assert not (c / "storyboard.json").exists() and not (c / "arte.json").exists()
    costos = (c / "costos.jsonl").read_text() if (c / "costos.jsonl").exists() else ""
    assert '"director"' not in costos and not quien
    assert (c / "machote.json").exists() and not ingesta.es_provisional(c)
    assert not (c / "preferencias.json").exists()     # ni hook, ni preset, ni color: nada que la persona no haya pedido


def _listo(proyectos, aprobado):
    c = proyectos / "p1"
    c.mkdir()
    (c / "fuente.json").write_text(json.dumps({"video": "x", "original": "x.mp4", "cuadros": 30, "hdr": False}))
    if aprobado:
        (c / "preferencias.json").write_text(json.dumps({"guion_aprobado": True}))
    return c


@pytest.fixture
def director_falso(monkeypatch):
    registro = []
    monkeypatch.setattr(ingesta, "preparar_media", lambda *a, **k: registro.append("media"))
    monkeypatch.setattr(director, "dirigir", lambda c, estilo, imgs, avance=print: registro.append(("dirigir", estilo)))
    monkeypatch.setattr(director, "mirar", lambda c, r, avance=print: registro.append("ojo") or {"veredicto": "aprobar"})
    from estudio import imagenes
    monkeypatch.setattr(imagenes, "generar", lambda *a, **k: registro.append("imagenes"))
    monkeypatch.setattr(imagenes, "conector", lambda: imagenes.HF)   # sin consultar la cuenta real de Claude
    monkeypatch.setattr(validar, "fijar_densidad", lambda *a, **k: registro.append("densidad"))
    return registro


def test_dirigir_sin_guion_aprobado_se_niega(proyectos, director_falso):
    _listo(proyectos, aprobado=False)
    with pytest.raises(ValueError, match="aprueba el guion"):
        servidor._dirigir("p1", "vox", True, "normal", 1, print)
    assert director_falso == []


def test_dirigir_con_el_estilo_elegido_y_otro_estilo_redirige_limpio(proyectos, director_falso, monkeypatch):
    c = _listo(proyectos, aprobado=True)
    borrados = []
    monkeypatch.setattr(ingesta, "limpiar_intento", lambda carpeta: borrados.append(len(director_falso)))
    servidor._PEDIDO["p1"] = 1
    servidor._dirigir("p1", "vox", True, "normal", 1, print)
    servidor._PEDIDO["p1"] = 2
    servidor._dirigir("p1", "pop", True, "normal", 2, print)
    assert [x for x in director_falso if isinstance(x, tuple)] == [("dirigir", "vox"), ("dirigir", "pop")]
    assert len(borrados) == 2 and borrados[1] > borrados[0]    # cada intento parte limpio, antes del director


def test_un_pedido_viejo_que_esperaba_no_corre(proyectos, director_falso):
    _listo(proyectos, aprobado=True)
    servidor._PEDIDO["p1"] = 2      # ya llegó uno más nuevo
    assert "reemplazado" in servidor._dirigir("p1", "vox", True, "normal", 1, print)
    assert director_falso == []


def test_dirigir_espera_a_que_termine_preparar(proyectos, director_falso):
    _listo(proyectos, aprobado=True)
    servidor.TRABAJOS["x"] = {"id": "x", "tipo": "preparar", "proyecto": "p1", "estado": "corriendo", "log": []}
    servidor._PEDIDO["p1"] = 1
    hilo = threading.Thread(target=servidor._dirigir, args=("p1", "vox", False, "normal", 1, lambda m: None))
    hilo.start()
    hilo.join(.5)
    assert hilo.is_alive() and director_falso == []
    servidor.TRABAJOS["x"]["estado"] = "listo"
    hilo.join(10)
    assert ("dirigir", "vox") in director_falso


# ---------- un estilo nuevo parte de su preset completo ----------

def test_elegir_a_y_luego_b_deja_exactamente_el_preset_de_b(tmp_path):
    presets = json.loads((servidor.LIB / "estilos" / "presets.json").read_text())
    (tmp_path / "storyboard.json").write_text(json.dumps({"cortes": [], "estilo": {"id": "viejo", "resto": "de-otro-estilo"}}))
    for a in presets:
        for b in ("glass", "vox", "pop"):
            if a == b:
                continue
            director._fijar_estilo(tmp_path, a)
            director._fijar_estilo(tmp_path, b)
            est = json.loads((tmp_path / "storyboard.json").read_text())["estilo"]
            assert est == {"id": b, **{k: v for k, v in presets[b].items() if k != "nombre"}}, (a, b)


def test_la_app_no_mezcla_el_estilo_nuevo_con_el_anterior():
    js = (config.RAIZ / "app" / "app.js").read_text()
    assert "estilo = { ...estilo, ...e }" not in js
    assert "estilo = { ...e }" in js
    llamada = js[js.index('"/api/preparar"'):].split("}", 1)[0]
    assert "estilo" not in llamada and "imagenes" not in llamada    # subir no manda estilo: el director no corre


def test_normalizar_no_entrega_un_video_cortado(tmp_path, monkeypatch):
    """ffmpeg salió «bien» pero dejó 43 s de 109 s (memoria justa): se repite una vez y, si sigue corto, no hay fuente.mp4."""
    (tmp_path / "x.mp4").write_bytes(b"")
    corridas, duraciones = [], iter([43.5, 43.5])

    def ffmpeg_falso(cmd, **kw):
        corridas.append(cmd)
        Path(cmd[-1]).write_bytes(b"v")
    monkeypatch.setattr(ingesta.trabajo, "correr", ffmpeg_falso)   # normalizar lanza ffmpeg por `trabajo.correr` (se puede detener)
    monkeypatch.setattr(ingesta, "_duracion", lambda v: next(duraciones))
    p = {"hdr": False, "ancho": 1080, "alto": 1920, "duracion": 109.0}
    with pytest.raises(RuntimeError, match="más corta"):
        ingesta.normalizar(tmp_path / "x.mp4", p, tmp_path)
    assert len(corridas) == 2 and not (tmp_path / "fuente.mp4").exists() and not (tmp_path / "fuente.part.mp4").exists()


@pytest.mark.parametrize("en_cpu", [True, False])
def test_sin_gpu_el_guion_va_primero_y_con_gpu_van_a_la_vez(proyectos, monkeypatch, en_cpu):
    """11-nov, Mac sin GPU: el guion de un 4K de 68 s tardaba más de 7 min porque Whisper y la conversión se peleaban el procesador."""
    orden, guion_corriendo, video_arranco = [], threading.Event(), threading.Event()
    monkeypatch.setattr(asr, "en_cpu", lambda: en_cpu)

    def guion(video, nombre, avance):
        guion_corriendo.set()
        if not en_cpu:
            assert video_arranco.wait(5)      # con GPU el video arranca sin esperar al guion
        orden.append("guion")

    def video(video, nombre, avance):
        assert guion_corriendo.wait(5)
        video_arranco.set()
        orden.append("video")
    monkeypatch.setattr(ingesta, "preparar_guion", guion)
    monkeypatch.setattr(ingesta, "preparar_media", video)
    servidor._preparar("v.mp4", "p1", lambda m: None)
    assert orden == (["guion", "video"] if en_cpu else ["video", "guion"])
