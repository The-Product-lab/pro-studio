"""El color de los textos lo decide la persona, también el de los pequeños (Pablo, 11-nov: «no me está dejando editar el color de los
textos pequeños… ojo que eso es muy importante»). El director los escribe en blanco fijo, o con el #hex de la paleta en vez de su
nombre: ningún control de la pantalla los alcanzaba."""
from estudio import catalogo, motor

SWISS = catalogo.presets()["swiss"]   # acento #002FA7 · acento2 #B9C0D2 · tinta #111111


def _estilo(**cambios):
    return motor.Estilo({**{k: v for k, v in SWISS.items() if k != "nombre"}, "id": "swiss", **cambios})


def test_los_textos_pequenos_en_blanco_toman_el_color_elegido_y_los_grandes_no():
    est = _estilo(texto="#FFE600")
    assert est.color_linea({"texto": "para", "tam": 60, "color": "blanco"}) == (255, 230, 0)
    assert est.color_linea({"texto": "para", "tam": 60}) == (255, 230, 0)                       # sin color = blanco
    assert est.color_linea({"texto": "PUBLICARLO", "tam": 150, "color": "blanco"}) == (255, 255, 255)   # el grande no es «pequeño»
    assert est.color_linea({"texto": "dato", "tam": 60, "color": "#111111"}) == (17, 17, 17)    # el que va en tinta sobre papel, intacto


def test_sin_elegir_nada_todo_queda_como_estaba():
    est = _estilo()
    assert est.color_linea({"texto": "para", "tam": 60, "color": "blanco"}) == (255, 255, 255)
    assert est.color("#002FA7") == (0, 47, 167) and est.color("acento") == (0, 47, 167)


def test_una_linea_escrita_con_el_hex_de_la_paleta_sigue_al_color_que_la_persona_cambio():
    est = _estilo(acento="#E3141E")
    assert est.color("acento") == (227, 20, 30)
    assert est.color("#002FA7") == (227, 20, 30) and est.color("#002fa7") == (227, 20, 30)      # el director escribió el hex del preset
    assert est.color("#B9C0D2") == motor._hex("#B9C0D2") and est.color("#123456") == (18, 52, 86)   # lo demás no se toca


def test_la_pantalla_ofrece_el_color_de_los_textos_pequenos_y_el_catalogo_lo_valida():
    cat = {c["id"]: c for c in catalogo.catalogo()["categorias"]}
    assert cat["texto"]["nombre"] == "Color de los textos pequeños" and cat["texto"]["opciones"][0]["id"] == "#FFFFFF"
    js = (catalogo.config.RAIZ / "app" / "app.js").read_text()
    assert 'bloque("Color de los textos pequeños", puntos("texto"))' in js and 'puntos("acento")' in js
    err = []
    catalogo._valor_estilo("texto", "no-es-color", err)
    assert err and "texto" in err[0]
