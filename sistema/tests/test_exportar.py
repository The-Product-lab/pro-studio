"""`estudio exportar`: el paquete es de LISTA BLANCA y nunca lleva proyectos, privadas, secretos ni datos personales (orden de Pablo)."""
import zipfile
from pathlib import Path

import pytest

from estudio import exportar

USUARIO, CORREO, CHAT = "deal" + "c", "pabl" + "oat", "169217" + "1320"


@pytest.fixture
def arbol(tmp_path, monkeypatch):
    r = tmp_path / "repo"
    def f(rel, texto="x" * 10, binario=None):
        p = r / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(binario if binario is not None else texto.encode())
    f("herramientas/paquete/Instalar Pro Studio (Windows).bat", "@echo off\ngoto :x\n"); f("herramientas/paquete/LEEME.txt", "uno\n")
    f("herramientas/paquete/Instalar Pro Studio (Mac).command", "#!/bin/bash\n"); f("herramientas/pesado.sh", "#!/bin/bash\n")
    f("README.md"); f("CLAUDE.md"); f("pyproject.toml"); f("instalar.sh"); f("estudio/motor.py", f"RUTA = '/home/{USUARIO}/claude-code/x'  # {CHAT}\n")
    f("estudio/__pycache__/a.pyc", binario=b"\0\1"); f("app/muestras/sel/efecto.mp4", binario=b"\0mp4"); f("app/muestras/sel/efecto.poster.jpg", binario=b"\xff\xd8")
    f("app/video-cliente.mp4", binario=b"\0mp4"); f("librerias/sonido/organico/papel/a.wav", binario=b"RIFF\0")
    f("perfil/gusto.md", "gusto"); f("referencias-estilos/pop/c_1.jpg", binario=b"\xff"); f("referencias-estilos/pop/hoja.jpg", binario=b"\xff")
    f("proyectos/cliente/final.mp4", binario=b"\0"); f("privadas/color/lut.cube", "lut"); f("costos.jsonl", "{}"); f(".env", "TELEGRAM_BOT_TOKEN=abc")
    f("estudio/.env", "A=1"); f("librerias/tokens.json", "{}"); f("banco/LEEME.md", "banco"); f("banco/tierno-24s.mp4", binario=b"\0")
    f(".claude/settings.json", '{"hooks": {}}'); f(".claude/settings.local.json", "{}"); f(".claude/otro.md", "x"); f("docs/HANDOFF-PC.md", "pc"); f("docs/PLANO.md", "plano")
    monkeypatch.setattr(exportar, "RAIZ", r)
    monkeypatch.setattr(exportar.verificar, "_git", lambda *a: [])
    return r


def test_lista_blanca_deja_fuera_lo_privado(arbol, tmp_path):
    zp = exportar.armar(tmp_path / "salida", "2026-01-01")
    with zipfile.ZipFile(zp) as z:
        crudos = z.namelist()
        nombres = {n.split("/sistema/", 1)[1] for n in crudos if "/sistema/" in n}
    assert {"README.md", "estudio/motor.py", "perfil/gusto.md", "librerias/sonido/organico/papel/a.wav", "app/muestras/sel/efecto.mp4",
            "referencias-estilos/pop/hoja.jpg", "banco/LEEME.md", "MANIFIESTO.txt"} <= nombres
    # A la vista, al abrir el zip: una sola carpeta con tres cosas y `sistema/` (Pablo 10-nov)
    afuera = sorted(n.split("/", 1)[1] for n in crudos if n.count("/") == 1 and not n.endswith("/"))
    assert {n.split("/")[0] for n in crudos} == {"Pro Studio"}
    assert afuera == ["Instalar Pro Studio (Mac).command", "Instalar Pro Studio (Windows).bat", "LEEME.txt"]
    assert not any("herramientas/paquete" in n for n in nombres) and "herramientas/pesado.sh" in nombres
    with zipfile.ZipFile(zp) as z2:
        assert b"\r\n" in z2.read("Pro Studio/Instalar Pro Studio (Windows).bat")   # los .bat salen con saltos de Windows
    # La guarda del Agente Editor viaja (solo ella de la carpeta .claude); las notas del PC de la oficina, no
    assert ".claude/settings.json" in nombres and "docs/PLANO.md" in nombres
    assert not any(n.startswith(".claude/") and n != ".claude/settings.json" for n in nombres) and "docs/HANDOFF-PC.md" not in nombres
    prohibido = ("proyectos/", "privadas/", "costos.jsonl", ".env", "__pycache__", "tierno-24s.mp4", "video-cliente.mp4", "c_1.jpg", "tokens.json")
    assert [n for n in nombres if any(x in n for x in prohibido)] == []


def test_el_texto_sale_sin_datos_personales(arbol, tmp_path):
    zp = exportar.armar(tmp_path / "salida", "2026-01-01")
    with zipfile.ZipFile(zp) as z:
        for n in z.namelist():
            d = z.read(n)
            for malo in (USUARIO, CORREO, CHAT):
                assert malo.encode() not in d, f"{n} lleva {malo}"
        assert b"/claude-code/x" in z.read("Pro Studio/sistema/estudio/motor.py")
    assert exportar.revisar_zip(zp) == []


def test_revisar_zip_atrapa_lo_que_no_debe(tmp_path):
    zp = tmp_path / "malo.zip"
    with zipfile.ZipFile(zp, "w") as z:
        z.writestr("P/sistema/proyectos/a.txt", "x"); z.writestr("P/sistema/ok.txt", "TELEGRAM_BOT_TOKEN" + " = " + "1234567890abcdefghijklmnop")
        z.writestr("P/sistema/notas.md", f"mi correo {CORREO}@x.com"); z.writestr("P/sistema/.env", "A=1")
    fallas = " ".join(exportar.revisar_zip(zp))
    for esperado in ("proyectos/a.txt", "ok.txt", "notas.md", ".env"):
        assert esperado in fallas


def test_publicar_en_seco_usa_repo_privado(arbol, tmp_path, capsys):
    zp = exportar.armar(tmp_path / "salida", "2026-01-01")
    assert exportar.publicar(zp, en_seco=True) == 0
    salida = capsys.readouterr().out
    assert "--private" in salida and "gh release create" in salida and "academiaprestiggio/" in salida


@pytest.mark.parametrize("falta, dice", [("app/muestras/sel/efecto.mp4", "muestras del editor avanzado"),
                                         ("librerias/sonido/organico/papel/a.wav", "sonido orgánico")])
def test_una_copia_sin_lo_que_no_vive_en_git_no_arma_el_paquete(arbol, tmp_path, falta, dice):
    """11-nov: desde una copia clonada el zip salía con el editor avanzado vacío y solo un aviso en pantalla."""
    (arbol / falta).unlink()
    with pytest.raises(SystemExit, match=dice):
        exportar.armar(tmp_path / "salida", "2026-01-01")
    assert not list((tmp_path / "salida").glob("*.zip"))
