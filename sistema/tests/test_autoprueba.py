"""Compuerta de «Exportar» en un equipo recién instalado (Pablo, 13-nov: en una Mac nueva «Exportar» dijo dos veces «Algo falló y ya
quedó anotado»). La causa: la pantalla dejaba exportar un video que el editor aún no había diseñado (cualquier trabajo que terminaba
ponía «listo») y el servidor lo intentaba igual, sin `storyboard.json`. Aquí queda para siempre:
1) el recorrido entero de la app por su API (subir → guion → editar → exportar → descargar) sale bien, sin IA ni sesión de Claude;
2) exportar sin haber editado, o con el editor a medias, se niega con su motivo;
3) lo que un equipo nuevo puede tener distinto (Claude sin sesión, disco lleno, una pieza que falta) llega a la pantalla dicho claro;
4) la pantalla ya no decide sola que un video está listo."""
import errno
import json
import threading
import time
from pathlib import Path

import pytest

from estudio import autoprueba, config, errores, ia, servidor, sesion

APP = Path(__file__).resolve().parent.parent / "app"


def _claude_falso(tmp_path, monkeypatch, respuesta: dict, codigo: int = 0) -> None:
    guion = tmp_path / "claude_falso.py"
    guion.write_text(f"import json,sys\nprint(json.dumps({respuesta!r}))\nsys.exit({codigo})\n")
    monkeypatch.setenv("ESTUDIO_CLAUDE_BIN", str(guion))


@pytest.mark.skipif(not config.CARAS_ONNX.exists(), reason="esta copia no tiene los modelos instalados (corre `estudio doctor --arreglar`)")
def test_la_app_entera_hasta_el_video_exportado(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    monkeypatch.setenv("ESTUDIO_CLAUDE_BIN", str(tmp_path / "no-hay-claude"))   # un equipo sin Claude: el recorrido no lo necesita
    pasos = []
    final = autoprueba.recorrer(conservar=True, avance=pasos.append)
    assert final.is_file() and final.stat().st_size > 50_000
    assert any("se niega con su motivo" in p for p in pasos) and any("Descargar" in p for p in pasos)
    assert any("las dos partes quedan en un solo video" in p for p in pasos)                 # un video grabado en partes
    assert any("lote: de 4 archivos se proponen 2 videos" in p for p in pasos) and any("lote: su guion trae" in p for p in pasos)   # una grabación → videos
    assert not (tmp_path / "_errores.log").exists()   # nada falló por debajo


def test_la_autoprueba_falla_diciendo_el_paso_y_lo_que_veria_la_persona(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)

    def roto(*a, **k):
        raise OSError(errno.ENOSPC, "No space left on device")
    monkeypatch.setattr(servidor, "_preparar", roto)
    assert autoprueba.main() == 1
    salida = capsys.readouterr().out
    assert "preparar el material" in salida and "El disco está lleno" in salida and "No space left" in salida   # frase + detalle del registro
    assert not list(tmp_path.glob("autoprueba*"))   # no deja el proyecto de prueba tirado


def _trabajo_terminado(tid: str) -> dict:
    for _ in range(200):
        if servidor.TRABAJOS[tid]["estado"] != "corriendo":
            return servidor.TRABAJOS[tid]
        time.sleep(.02)
    raise AssertionError("el trabajo no terminó")


def test_exportar_sin_editar_dice_el_motivo_y_no_algo_fallo(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    (tmp_path / "v").mkdir()
    (tmp_path / "v" / "fuente.json").write_text("{}")
    assert servidor._impide_exportar(tmp_path / "v") == servidor.SIN_EDITAR
    info = servidor._info("v")
    assert info["listo"] is False and info["no_exporta"] == servidor.SIN_EDITAR
    t = _trabajo_terminado(servidor._trabajo("render", servidor._render, "v", proyecto="v"))   # aunque alguien lo lance directo
    assert t["estado"] == "error" and t["log"][-1] == servidor.SIN_EDITAR != errores.GENERICA


def test_con_el_editor_trabajando_no_se_exporta_y_una_vista_previa_no_lo_impide(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    monkeypatch.setattr(servidor, "TRABAJOS", {})
    (tmp_path / "v").mkdir()
    (tmp_path / "v" / "storyboard.json").write_text(json.dumps({"estilo": {"id": "glass"}}))
    assert servidor._impide_exportar(tmp_path / "v") is None
    servidor.TRABAJOS["p"] = {"id": "p", "tipo": "previa", "proyecto": "v", "estado": "corriendo", "log": []}
    assert servidor._impide_exportar(tmp_path / "v") is None and servidor._info("v")["listo"] is True
    servidor.TRABAJOS["d"] = {"id": "d", "tipo": "dirigir", "proyecto": "v", "estado": "corriendo", "log": []}
    assert servidor._impide_exportar(tmp_path / "v") == servidor.EDITANDO and servidor._info("v")["listo"] is False
    servidor.TRABAJOS["d"]["estado"] = "listo"
    servidor.TRABAJOS["r"] = {"id": "r", "tipo": "render", "proyecto": "v", "estado": "corriendo", "log": []}
    assert servidor._impide_exportar(tmp_path / "v") == servidor.EXPORTANDO
    assert servidor._impide_exportar(tmp_path / "v", salvo="r") is None   # el propio render no se impide a sí mismo


def test_la_compuerta_que_no_deja_exportar_se_dice_claro(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    monkeypatch.setattr(servidor, "TRABAJOS", {})
    (tmp_path / "v").mkdir()
    (tmp_path / "v" / "storyboard.json").write_text("{}")

    def no_pasa(*a, **k):
        raise ValueError(servidor.motor.COMPUERTA_NO_DEJA + ":\n- textos: 'x' se sale de la zona segura")
    monkeypatch.setattr(servidor.motor, "render", no_pasa)
    with pytest.raises(errores.Aviso, match="revisión de calidad"):
        servidor._render("v", print)
    assert "zona segura" in (tmp_path / "_errores.log").read_text()   # la lista completa queda en el registro


def test_guion_parado_dice_por_que_en_vez_de_preparando_para_siempre(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    monkeypatch.setattr(servidor, "TRABAJOS", {})
    assert servidor._guion_parado("v") == servidor.GUION_PARADO   # la app se cerró a la mitad: nadie lo prepara
    servidor.TRABAJOS["a"] = {"id": "a", "tipo": "preparar", "proyecto": "v", "estado": "corriendo", "log": []}
    assert servidor._guion_parado("v") is None
    servidor.TRABAJOS["a"].update(estado="error", log=["transcribiendo…", errores.SIN_SESION])
    assert servidor._guion_parado("v") == errores.SIN_SESION


def test_claude_sin_sesion_o_sin_instalar_se_dice_claro(tmp_path, monkeypatch):
    _claude_falso(tmp_path, monkeypatch, {"is_error": True, "result": "Not logged in · Please run /login"})
    with pytest.raises(errores.Aviso) as e:
        ia.llamar("hola", "opus", tmp_path, paso="machote-cortes")
    assert errores.frase(e.value) == errores.SIN_SESION
    monkeypatch.setenv("ESTUDIO_CLAUDE_BIN", str(tmp_path / "no-existe"))
    with pytest.raises(errores.Aviso) as e:
        ia.llamar("hola", "opus", tmp_path, paso="machote-cortes")
    assert errores.frase(e.value) == errores.SIN_CLAUDE


def test_la_app_sabe_si_claude_tiene_sesion(tmp_path, monkeypatch):
    _claude_falso(tmp_path, monkeypatch, {"loggedIn": False}, codigo=1)
    assert sesion.medir() == sesion.SIN_SESION
    _claude_falso(tmp_path, monkeypatch, {"loggedIn": True})
    assert sesion.medir() == sesion.OK
    monkeypatch.setenv("ESTUDIO_CLAUDE_BIN", str(tmp_path / "no-existe"))
    assert sesion.medir() == sesion.FALTA and sesion.orden_entrar() is None


def test_la_orden_de_entrar_a_claude_en_mac_y_windows(tmp_path, monkeypatch):
    _claude_falso(tmp_path, monkeypatch, {"loggedIn": False}, codigo=1)
    monkeypatch.setattr(config, "TPS", tmp_path / ".tps")
    mac = sesion.orden_entrar("darwin")
    assert mac[0] == "open" and "auth login" in Path(mac[1]).read_text() and Path(mac[1]).stat().st_mode & 0o100
    win = sesion.orden_entrar("win32")
    assert win[-2:] == ["auth", "login"] and "start" not in win
    assert sesion.orden_entrar("linux") is None


@pytest.mark.parametrize("e,dice", [
    (errores.Aviso("Esto ya viene dicho para la persona."), "Esto ya viene dicho para la persona."),
    (OSError(errno.ENOSPC, "No space left on device"), "El disco está lleno"),
    (PermissionError(errno.EACCES, "Permission denied"), "No tengo permiso"),
    (MemoryError(), "sin memoria"),
    (ModuleNotFoundError("No module named 'cv2'"), "le falta una pieza"),
    (ia.LimiteAgotado("You've hit your limit"), "límite de uso"),
])
def test_lo_que_puede_pasar_en_un_equipo_nuevo_tiene_su_frase(e, dice):
    assert dice in errores.frase(e) and errores.frase(e) != errores.GENERICA


def test_estilo_sin_director_no_llama_al_ojo(tmp_path, monkeypatch):
    """El Básico promete «no usa IA»: la app llamaba igual al ojo (Opus) dos veces, y sin sesión de Claude fallaba."""
    from estudio import director, imagenes, ingesta, lemo_apoyos, validar
    monkeypatch.setattr(config, "PROYECTOS", tmp_path)
    (tmp_path / "v").mkdir()
    (tmp_path / "v" / "fuente.json").write_text(json.dumps({"original": "x.mp4"}))
    llamadas = []
    monkeypatch.setattr(servidor.machote, "guion_aprobado", lambda c: True)
    monkeypatch.setattr(ingesta, "preparar_media", lambda *a, **k: None)
    monkeypatch.setattr(ingesta, "limpiar_intento", lambda *a, **k: None)
    monkeypatch.setattr(validar, "fijar_densidad", lambda *a, **k: None)
    monkeypatch.setattr(lemo_apoyos, "elegir", lambda c, e: e)
    monkeypatch.setattr(imagenes, "disponibles", lambda *a, **k: False)
    monkeypatch.setattr(imagenes, "arte_del_video", lambda *a, **k: None)
    monkeypatch.setattr(director, "dirigir", lambda *a, **k: llamadas.append("dirigir"))
    monkeypatch.setattr(director, "mirar", lambda *a, **k: llamadas.append("ojo") or {"veredicto": "aprobar"})
    servidor._PEDIDO["v"] = 1
    servidor._dirigir("v", "basico", False, "normal", 1, lambda m: None)
    assert llamadas == ["dirigir"]
    servidor._dirigir("v", "glass", False, "normal", 1, lambda m: None)
    assert llamadas == ["dirigir", "dirigir", "ojo"]


def test_la_pantalla_no_decide_sola_que_el_video_esta_listo():
    """`listo` y el botón Exportar salen de /api/proyecto. Antes `vigilar` ponía `listo = true` al terminar CUALQUIER trabajo."""
    js = (APP / "app.js").read_text(encoding="utf-8") + (APP / "pro.js").read_text(encoding="utf-8")
    assert "listo = true" not in js
    assert "no_exporta" in js and 'api("/api/render"' in js
    html = (APP / "index.html").read_text(encoding="utf-8")
    assert html.count('id="exportar"') == 1 and 'id="exportar" disabled' in html   # un solo botón, apagado hasta que el servidor diga
