"""Fase 0 del plano T-0193: el banco carga y documenta POR QUÉ falla el montaje de cada caso real (no cambia comportamiento)."""
import json

import numpy as np
import pytest

from conftest import CASOS


@pytest.mark.parametrize("caso", CASOS)
def test_el_caso_carga_completo(banco, caso):
    c = banco(caso)
    fuente = json.loads((c / "fuente.json").read_text())
    sb = json.loads((c / "storyboard.json").read_text())
    palabras = json.loads((c / "palabras.json").read_text())
    db = np.load(c / ".energia.npy")
    assert abs(len(db) / 100 - fuente["cuadros"] / 30) < .1          # un cuadro de energía por cada 10 ms del video
    assert sb["cortes"] and palabras
    assert all(0 <= a < b <= fuente["cuadros"] / 30 + .01 for a, b in sb["cortes"])


def test_cine_el_dictado_del_apuntador_no_esta_marcado_y_suena_mas_bajo(banco):
    """Causa raíz de Cine (7-nov): 8,54–17,1 s es alguien fuera de cámara dictando; `voces_fuera` solo mira pausas ≥ 0,3 s,
    así que Whisper lo dejó como palabras del talento y suena ~15–20 dB bajo el talento."""
    c = banco("cine-c8867")
    palabras = json.loads((c / "palabras.json").read_text())
    assert not any(p.get("fuera") for p in palabras if 7.3 < p["s"] < 41)
    db = np.load(c / ".energia.npy").astype(np.float32)
    zona, talento = np.percentile(db[854:1710], 90), np.percentile(db[2470:3600], 90)
    assert talento - zona > 12
