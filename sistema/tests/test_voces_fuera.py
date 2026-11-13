"""`montaje.voces_fuera`: re-escuchar las pausas agrega SOLO lo que no estaba. La misma palabra del talento, oída otra vez con el
inicio estirado hacia la pausa, no es una voz de fuera (10-nov, IMG_0653 en una Mac: frenaba el guion del video de ejemplo)."""
from types import SimpleNamespace

import numpy as np

from estudio import asr, montaje

TALENTO = [{"w": "Latinoamérica.", "s": 4.04, "e": 4.78, "p": .98}, {"w": "Y", "s": 5.40, "e": 5.72, "p": .97},
           {"w": "hoy", "s": 5.72, "e": 5.90, "p": 1.0}]


def _whisper(monkeypatch, oido: list):
    """Re-escucha de mentira: en la pausa entre «Latinoamérica.» y «Y» se oye `oido` = [(palabra, inicio, fin, p)] en tiempos del
    video; en los demás trozos, nada."""
    pausa = (round(4.78 - .15, 2), round(5.40 + .6, 2))

    def reescuchar(x, trozos, avance=None):
        return [list(oido) if (round(t0, 2), round(t1, 2)) == pausa else [] for t0, t1 in trozos]
    monkeypatch.setattr(montaje, "reescuchar", reescuchar)
    monkeypatch.setattr(montaje, "audio", lambda carpeta: np.full(montaje.SR * 8, .1, np.float32))


def test_la_misma_palabra_estirada_hacia_la_pausa_no_es_voz_de_fuera(monkeypatch, tmp_path):
    _whisper(monkeypatch, [(" y", 4.63, 5.73, .36)])
    assert montaje.voces_fuera(tmp_path, [dict(p) for p in TALENTO]) == TALENTO   # ni palabra nueva ni el «Y» corrido


def test_una_voz_distinta_en_la_pausa_si_se_agrega(monkeypatch, tmp_path):
    _whisper(monkeypatch, [(" acción", 4.90, 5.25, .80)])
    todas = montaje.voces_fuera(tmp_path, [dict(p) for p in TALENTO])
    assert [(p["w"], p.get("fuera")) for p in todas] == [("Latinoamérica.", None), ("acción", True), ("Y", None), ("hoy", None)]


def _mapa(*trozos, fin=10.0):
    m = np.zeros(int(fin / montaje.voz.HOP), bool)
    for a, b in trozos:
        m[int(a / montaje.voz.HOP):int(b / montaje.voz.HOP)] = True
    return m


def test_una_palabra_estirada_sobre_una_pausa_se_cine_a_donde_suena():
    """IMG_4965 (11-nov): «vas» ocupaba 8 s; adentro hablaba el apuntador y el «vas» real sonaba pegado al «a» que sigue."""
    ps = [{"w": "y", "s": 1.0, "e": 1.2}, {"w": "vas", "s": 1.4, "e": 8.6}, {"w": "a", "s": 8.6, "e": 8.7}]
    ceñidas = montaje.cenir_estiradas(ps, _mapa((1.0, 1.2), (2.0, 5.5), (8.3, 8.7)))
    assert (ceñidas[1]["s"], ceñidas[1]["e"]) == (8.3, 8.6)          # el trozo pegado a la palabra siguiente
    assert ceñidas[0] == ps[0] and ceñidas[2] == ps[2] and ps[1]["s"] == 1.4   # las demás intactas; la lista original no se toca


def test_la_estirada_hacia_adelante_se_cine_al_trozo_pegado_a_la_anterior():
    ps = [{"w": "no", "s": 1.0, "e": 1.3}, {"w": "sé", "s": 1.3, "e": 4.0}, {"w": "Suena", "s": 6.0, "e": 6.4}]
    assert (lambda p: (p["s"], p["e"]))(montaje.cenir_estiradas(ps, _mapa((1.0, 1.6), (3.0, 3.8), (6.0, 6.4)))[1]) == (1.3, 1.6)


def test_una_palabra_larga_sin_pausa_por_dentro_no_se_toca():
    ps = [{"w": "extraordinariamente", "s": 1.0, "e": 2.4}]
    assert montaje.cenir_estiradas(ps, _mapa((1.0, 1.7), (1.8, 2.4))) == ps   # 0,1 s de hueco no es una pausa
    fuera = [{"w": "acción", "s": 1.0, "e": 4.0, "fuera": True}]
    assert montaje.cenir_estiradas(fuera, _mapa((1.0, 1.2), (3.5, 4.0))) == fuera   # lo de fuera se corta entero: no importa


# ---------- la re-escucha avisa por cuál va (Pablo, 11-nov: «lleva casi 15 min en los guiones… es muy lento») ----------
def test_la_reescucha_es_una_por_trozo_dice_por_cual_va_y_da_tiempos_del_video(monkeypatch):
    oidos = []

    def transcribir(trozo, **_):
        oidos.append(len(trozo) / montaje.SR)
        return [SimpleNamespace(words=[SimpleNamespace(word=" acción", start=.2, end=.6, probability=.9)])]
    monkeypatch.setattr(asr, "transcribir", transcribir)
    avisos = []
    oido = montaje.reescuchar(np.zeros(montaje.SR * 60, np.float32), [(10.0, 11.0), (50.0, 52.0)], avisos.append)
    assert oidos == [1.0, 2.0]                                             # cada trozo se oye solo, como siempre
    assert [(w.strip(), round(a, 2), round(b, 2)) for w, a, b, _ in oido[1]] == [("acción", 50.2, 50.6)]
    assert avisos == ["re-escuchando las pausas: 1 de 2…", "re-escuchando las pausas: 2 de 2…"]


def test_el_guion_recibe_el_avance_de_la_reescucha():
    from estudio import config
    assert "montaje.voces_fuera(carpeta, palabras, avance)" in (config.RAIZ / "estudio" / "ingesta.py").read_text()
