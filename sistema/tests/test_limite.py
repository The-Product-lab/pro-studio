"""F5 (T-0193): «hit your limit» no es un fallo del video: se espera a la hora indicada y se repite el mismo paso."""
import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from estudio import config, ia

MENSAJE = "You've hit your 5-hour limit · resets 4:10pm (America/Bogota)"
BOGOTA = ZoneInfo("America/Bogota")


def _a(hora, minuto=0):
    return datetime(2026, 11, 4, hora, minuto, tzinfo=BOGOTA)


def test_parsea_la_hora_pm_con_zona():
    lim = ia.parsear_limite(MENSAJE, _a(13, 0))
    assert lim.reanuda_en == _a(16, 10)


def test_parsea_am_otra_zona_y_pasa_al_dia_siguiente():
    lim = ia.parsear_limite("You've hit your limit · resets 9am (America/New_York)", _a(10, 0))
    assert lim.reanuda_en.astimezone(ZoneInfo("America/New_York")).hour == 9
    assert lim.reanuda_en > _a(10, 0)
    assert ia.parsear_limite("hit your limit · resets 12:30am (America/Bogota)", _a(23, 0)).reanuda_en == datetime(2026, 11, 5, 0, 30, tzinfo=BOGOTA)


def test_sin_hora_devuelve_limite_sin_reanudacion_y_un_error_normal_no_es_limite():
    assert ia.parsear_limite("You've hit your usage limit").reanuda_en is None
    assert ia.parsear_limite("claude falló: timeout") is None


def _claude_falso(tmp_path, monkeypatch, respuestas):
    """Un `claude` falso que devuelve las respuestas en orden y cuenta las llamadas."""
    cuenta = tmp_path / "cuenta"
    cuenta.write_text("0")
    guion = tmp_path / "claude_falso.py"
    guion.write_text(
        "import json,sys,pathlib\n"
        f"c=pathlib.Path({str(cuenta)!r});n=int(c.read_text());c.write_text(str(n+1))\n"
        f"r={respuestas!r}\n"
        "print(json.dumps(r[min(n,len(r)-1)]))\n")
    monkeypatch.setenv("ESTUDIO_CLAUDE_BIN", str(guion))
    return cuenta


def test_espera_y_repite_el_mismo_paso_sin_fallar(tmp_path, monkeypatch):
    cuenta = _claude_falso(tmp_path, monkeypatch, [{"is_error": True, "result": MENSAJE}, {"is_error": False, "result": "ok"}])
    dormidos = []
    monkeypatch.setattr(ia, "_ahora", lambda tz=None: _a(16, 0) if tz is None else _a(16, 0).astimezone(tz))
    monkeypatch.setattr(ia, "_dormir", dormidos.append)
    estado = tmp_path / "limite.json"
    monkeypatch.setenv("ESTUDIO_ESTADO_LIMITE", str(estado))
    out = ia.llamar("hola", "opus", tmp_path, paso="director")
    assert out["result"] == "ok" and cuenta.read_text() == "2"                  # exactamente 1 reanudación
    assert sum(dormidos) == 10 * 60 + ia.LIMITE_MARGEN_S and max(dormidos) <= ia.LIMITE_TROZO_S
    assert json.loads(estado.read_text()) == {"esperando": False}
    assert [json.loads(l)["ok"] for l in (tmp_path / "costos.jsonl").read_text().splitlines()] == [False, True]


def test_no_esperar_y_el_tope_levantan_el_limite(tmp_path, monkeypatch):
    _claude_falso(tmp_path, monkeypatch, [{"is_error": True, "result": MENSAJE}])
    monkeypatch.setattr(ia, "_ahora", lambda tz=None: _a(10, 0) if tz is None else _a(10, 0).astimezone(tz))
    monkeypatch.setattr(ia, "_dormir", lambda s: None)
    monkeypatch.setenv("ESTUDIO_NO_ESPERAR", "1")
    with pytest.raises(ia.LimiteAgotado):
        ia.llamar("hola", "opus", tmp_path)
    monkeypatch.delenv("ESTUDIO_NO_ESPERAR")
    monkeypatch.setenv("ESTUDIO_LIMITE_TOPE_H", "1")                            # faltan 6 h: pasa del tope
    with pytest.raises(ia.LimiteAgotado):
        ia.llamar("hola", "opus", tmp_path)


def test_claude_corre_sin_lo_personal_de_la_maquina_salvo_con_conectores_o_si_se_pide(tmp_path, monkeypatch):
    """10-nov: cada llamada cargaba el CLAUDE.md, la memoria y las skills de quien instaló (56 mil tokens por llamada y un director
    distinto en cada equipo). Aislado por defecto; los conectores (Higgsfield) y quien trabaja sobre el sistema, no."""
    guion = tmp_path / "claude_eco.py"
    guion.write_text("import json,os\nprint(json.dumps({'is_error': False, 'result': os.environ.get('CLAUDE_CODE_SAFE_MODE', 'no')}))\n")
    monkeypatch.setenv("ESTUDIO_CLAUDE_BIN", str(guion))
    monkeypatch.delenv("CLAUDE_CODE_SAFE_MODE", raising=False)
    assert ia.llamar("p", "opus", tmp_path, paso="x")["result"] == "1"
    assert ia.llamar("p", "opus", tmp_path, paso="x", mcp=True)["result"] == "no"
    assert ia.llamar("p", "opus", tmp_path, paso="x", aislado=False)["result"] == "no"


def test_con_conectores_claude_puede_cargar_sus_herramientas_diferidas(tmp_path, monkeypatch):
    """11-nov: Claude Code entrega las herramientas de los conectores «diferidas»; sin permiso para ToolSearch no las carga y la
    llamada de imágenes volvía vacía en 5 s (ningún video recibía su arte). Sin conectores no se agrega nada."""
    guion = tmp_path / "claude_args.py"
    guion.write_text("import json,sys\nprint(json.dumps({'is_error': False, 'result': sys.argv[sys.argv.index('--allowedTools') + 1]}))\n")
    monkeypatch.setenv("ESTUDIO_CLAUDE_BIN", str(guion))
    assert ia.llamar("p", "opus", tmp_path, herramientas="mcp__x__y,mcp__x__z", paso="x", mcp=True)["result"] == "ToolSearch,mcp__x__y,mcp__x__z"
    assert ia.llamar("p", "opus", tmp_path, herramientas="ToolSearch,mcp__x__y", paso="x", mcp=True)["result"] == "ToolSearch,mcp__x__y"
    assert ia.llamar("p", "opus", tmp_path, herramientas="Read,Write", paso="x")["result"] == "Read,Write"
