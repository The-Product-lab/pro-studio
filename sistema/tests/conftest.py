"""Banco de pruebas del montaje: casos reales (palabras, storyboard del director y mapa de energía) de los videos del lote del
07-nov. Cada caso es una carpeta de proyecto en miniatura (sin video ni audio crudo); `banco(nombre)` la copia a un temporal."""
import json
import shutil
from pathlib import Path

import pytest

BANCO = Path(__file__).parent / "banco"
CASOS = sorted(p.name for p in BANCO.iterdir() if p.is_dir()) if BANCO.exists() else []


@pytest.fixture
def banco(tmp_path):
    def _copiar(nombre: str) -> Path:
        destino = tmp_path / nombre
        shutil.copytree(BANCO / nombre, destino)
        return destino
    return _copiar


@pytest.fixture
def pagina_lemo():
    """Escribe `index.html` mínimo con el contrato de Lemo (`DUR`, `EV`, `render`, `TEXTS`, `READY`) que muestra esos textos:
    [(id, texto, t0, t1)]. Sirve para probar `textos_lemo` sin una película de verdad."""
    def _escribir(carpeta: Path, textos: list, dur: float) -> Path:
        lista = [{"id": i, "text": t, "t0": a, "t1": b} for i, t, a, b in textos]
        (carpeta / "index.html").write_text(
            "<!doctype html><meta charset=utf-8><body><script>\n"
            f"window.DUR={dur};window.EV=[];const T={json.dumps(lista, ensure_ascii=False)};\n"
            "window.render=t=>{};\n"
            "window.TEXTS=t=>T.filter(x=>t>=x.t0&&t<=x.t1).map(x=>({id:x.id,text:x.text,x0:100,y0:300,x1:900,y1:420}));\n"
            "window.READY=true;</script>\n")
        return carpeta / "index.html"
    return _escribir


@pytest.fixture
def camara_movil(monkeypatch):
    """Desde el 11-nov la cámara es FIJA por regla de Pablo (perfil/reglas.json › camara_fija). La maquinaria que la movía sigue en
    el código, apagada por esa regla; las pruebas que la ejercitan la encienden con esta fixture."""
    from estudio import camara
    monkeypatch.setattr(camara, "fija", lambda: False)
