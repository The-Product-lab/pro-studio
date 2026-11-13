"""Que el paquete corra igual en Windows, Mac y Linux: UTF-8, proceso vivo, candado, Git for Windows, reinstalar sin pisar lo del usuario."""
import json
import os
import subprocess
import sys
import threading

import pytest

from estudio import agente, config, escritorio, instalar, portable


def test_windows_relanza_con_utf8_y_el_resto_no():
    orden = portable.relanzar_utf8(["doctor", "--json"], windows=True, utf8_activo=False)
    assert orden[:3] == [sys.executable, "-X", "utf8"] and orden[-2:] == ["doctor", "--json"] and "estudio.cli" in orden
    assert portable.relanzar_utf8(["doctor"], windows=True, utf8_activo=True) is None   # ya está en UTF-8: no se relanza otra vez
    assert portable.relanzar_utf8(["doctor"], windows=False, utf8_activo=False) is None   # Mac y Linux: comportamiento de siempre


def test_cli_main_relanza_en_windows_simulado(monkeypatch):
    from estudio import cli
    llamadas = []
    monkeypatch.setattr(portable, "relanzar_utf8", lambda argv, **k: [sys.executable, "-X", "utf8", "-m", "estudio.cli", *argv])
    monkeypatch.setattr(subprocess, "run", lambda orden, env=None, **k: llamadas.append((orden, env)) or subprocess.CompletedProcess(orden, 7))
    assert cli.main(["doctor"]) == 7
    orden, env = llamadas[0]
    assert "utf8" in orden and env["PYTHONUTF8"] == "1"   # y los hijos que lancen Python lo heredan


def test_proceso_vivo():
    assert portable.proceso_vivo(os.getpid())
    assert not portable.proceso_vivo(None) and not portable.proceso_vivo("x") and not portable.proceso_vivo(0)
    hijo = subprocess.Popen([sys.executable, "-c", "pass"])
    hijo.wait()
    assert not portable.proceso_vivo(hijo.pid)


def test_candado_serializa_la_escritura(tmp_path):
    f = tmp_path / "datos.json"
    f.write_text("0")
    def sumar():
        for _ in range(20):
            with open(f, "r+", encoding="utf-8") as h, portable.candado(h):
                n = int(h.read())
                h.seek(0)
                h.truncate()
                h.write(str(n + 1))
    hilos = [threading.Thread(target=sumar) for _ in range(4)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert f.read_text() == "80"


def test_git_for_windows_pone_su_sh_en_el_path(tmp_path, monkeypatch):
    usr = tmp_path / "Git" / "usr" / "bin"
    usr.mkdir(parents=True)
    (usr / "sh.exe").write_text("")
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    assert config.git_usr_bin(windows=True) == usr and config.git_usr_bin(windows=False) is None
    env = config.herramientas_en_path({"PATH": "C:\\Windows"}, windows=True)
    assert str(usr) in env["PATH"].split(os.pathsep) and env["PATH"].startswith("C:\\Windows")   # al final: no tapa find ni sort de Windows
    assert config.herramientas_en_path({"PATH": "x"}, windows=False)["PATH"] == "x"


def test_lemo_listo_en_windows_exige_sh(monkeypatch):
    monkeypatch.setattr(instalar.os, "name", "nt")
    monkeypatch.setattr(instalar.shutil, "which", lambda n, **k: None if n == "sh" else "/usr/bin/" + n)
    assert instalar.lemo_listo() is False


def test_el_agente_sin_git_dice_que_falta_git(monkeypatch):
    def sin_git(*a, **k):
        raise FileNotFoundError(2, "No such file", "git")
    monkeypatch.setattr(agente.subprocess, "run", sin_git)
    with pytest.raises(FileNotFoundError, match="necesita Git"):
        agente._git("rev-parse", "HEAD")
    monkeypatch.setattr(agente, "_registros", lambda: [{"id": "C-0001", "commit": "abc"}])
    r = agente.deshacer("C-0001")
    assert r["ok"] is False and "Git" in r["error"]


def test_reinstalar_fusiona_los_presets_y_conserva_los_del_usuario(tmp_path):
    usuario, paquete = tmp_path / "presets.json", tmp_path / "presets-paquete.json"
    usuario.write_text(json.dumps({"pop": {"acento": "#111111", "extra": 1}, "mio": {"acento": "#222222"}}))
    paquete.write_text(json.dumps({"pop": {"acento": "#FFFFFF", "grano": 3}, "nuevo": {"acento": "#333333"}}))
    assert instalar.fusionar_presets(usuario, paquete) == ["nuevo"]
    fusion = json.loads(usuario.read_text())
    assert fusion["pop"] == {"acento": "#111111", "grano": 3, "extra": 1}   # lo del usuario manda; falta lo nuevo del paquete
    assert fusion["mio"] == {"acento": "#222222"} and fusion["nuevo"] == {"acento": "#333333"}
    assert not paquete.exists()
    assert instalar.fusionar_presets(usuario, paquete) == []   # idempotente: sin semilla no hace nada


def test_el_acceso_directo_resuelve_el_escritorio_dentro_del_script_y_escapa_apostrofos():
    ps = escritorio.guion_lnk("wscript.exe", '"C:\\Users\\O\'Brien\\Pro Studio\\herramientas\\abrir.vbs"', "C:\\O'Brien\\app.ico", "C:\\O'Brien")
    assert "GetFolderPath('Desktop')" in ps and "O''Brien" in ps and "O'Brien" not in ps.replace("O''Brien", "")


def test_el_servidor_toma_el_puerto_en_exclusiva_en_windows():
    from estudio import servidor
    assert servidor.Servidor.allow_reuse_address is (os.name != "nt")
