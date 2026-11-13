"""Dónde está Lemo en cada máquina. Caso real (Pablo, 11-nov: «no veo las miniaturas de Lemo»): en su Mac los estilos estaban en
`ESTUDIO BETA/referencias` y la app solo buscaba `laboratorio-estilos`: Estilos Pro salía vacío y sin decir por qué."""
import json

from estudio import config, pro_catalogo


def _lab(raiz, n=2):
    for k in range(n):
        d = raiz / "lemo-opuscar" / "styles" / f"estilo-{k}"
        d.mkdir(parents=True)
    return raiz


def test_la_copia_de_referencia_del_estudio_beta_tambien_cuenta(tmp_path, monkeypatch):
    monkeypatch.delenv("ESTUDIO_LABORATORIO", raising=False)
    monkeypatch.delenv("ESTUDIO_LEMO", raising=False)
    monkeypatch.setattr(config, "RAIZ", tmp_path / "repo")
    monkeypatch.setattr(config.Path, "home", classmethod(lambda cls: tmp_path))
    assert config.laboratorio() is None
    ref = _lab(tmp_path / "Desktop" / "CLAUDE CODE" / "ESTUDIO BETA" / "referencias")
    assert config.laboratorio() == ref
    assert config.lemo() == tmp_path / "laboratorio-estilos" / "lemo-opuscar"   # el motor para EDITAR no es la copia de referencia
    propio = _lab(tmp_path / "laboratorio-estilos")          # el laboratorio de verdad, junto al repo, gana a la copia
    assert config.laboratorio() == propio and pro_catalogo.laboratorio() == propio


def test_sin_lemo_la_pantalla_lo_dice():
    assert "necesitan la carpeta de Lemo" in (config.RAIZ / "app" / "pro.js").read_text()


def test_el_costo_de_un_estilo_pro_se_dice_antes_de_elegirlo():
    """Pablo, 12-nov: «un aviso en la parte derecha que diga ojo, estos estilos son muy costosos, en tiempo y en uso de la IA», con aproximados."""
    a = pro_catalogo.aviso()
    assert a["minutos"] >= 1 and a["consumo"] and a["origen"]
    js, html = (config.RAIZ / "app" / "pro.js").read_text(), (config.RAIZ / "app" / "index.html").read_text()
    assert "muy costosos" in js and "r.aviso.minutos" in js and "r.aviso.consumo" in js and 'id="proCosto"' in html


def test_catalogo_dice_si_aqui_se_puede_editar(monkeypatch, tmp_path):
    """Sin el motor de Lemo el catálogo se ve pero no se edita: la pantalla lo sabe por `motor` y no deja elegir (Pablo, 12-nov:
    «elegí un estilo pro y no pasó nada»)."""
    from estudio import pro, servidor
    monkeypatch.setattr(pro, "LEMO", tmp_path / "no-esta")
    assert servidor._pro_catalogo()["motor"] is False
    (tmp_path / "si-esta").mkdir()
    monkeypatch.setattr(pro, "LEMO", tmp_path / "si-esta")
    assert servidor._pro_catalogo()["motor"] is True


def test_estilo_de_lemo_sin_ficha_propia_no_rompe_el_catalogo(monkeypatch, tmp_path):
    """Lemo saca estilos nuevos seguido; uno que todavía no tiene nombre y temas aquí no se ofrece, y el catálogo sigue saliendo
    (12-nov: con el Lemo del día, 100 estilos, el catálogo entero daba error)."""
    from estudio import pro_catalogo
    conocido = next(iter(json.loads(pro_catalogo.DATOS.read_text(encoding="utf-8"))["estilos"]))
    for slug in (conocido, "estilo-recien-salido"):
        d = tmp_path / "lemo-opuscar" / "styles" / slug
        d.mkdir(parents=True)
        (d / "style.json").write_text("{}")
    monkeypatch.setattr(pro_catalogo, "laboratorio", lambda: tmp_path)
    assert [e["slug"] for e in pro_catalogo.catalogo()] == [conocido]
