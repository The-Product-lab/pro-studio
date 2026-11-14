"""La compuerta capa 1 (estudio/verificar.py) detecta la basura que Pablo no quiere en el repo."""
from estudio import verificar


def _repo(tmp_path, monkeypatch, archivos):
    monkeypatch.setattr(verificar, "RAIZ", tmp_path)
    monkeypatch.setattr(verificar, "CONOCIDA", tmp_path / "conocida.txt")
    for rel, datos in archivos.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_bytes(datos)
    return list(archivos)


def test_limpio_no_falla(tmp_path, monkeypatch):
    a = _repo(tmp_path, monkeypatch, {"estudio/a.py": b"x = 1\n" * 50, "estudio/b.py": b"y = 2\n" * 50, "estudio/__init__.py": b""})
    assert verificar.sin_basura(a) == []


def test_video_en_mayuscula_falla(tmp_path, monkeypatch):
    a = _repo(tmp_path, monkeypatch, {"banco/workshop-C8866.MP4": b"v"})
    assert any("video versionado" in f for f in verificar.sin_basura(a))


def test_archivo_grande_falla(tmp_path, monkeypatch):
    a = _repo(tmp_path, monkeypatch, {"datos/enorme.bin": b"0" * (verificar.MAX_BYTES + 1)})
    assert any("archivo grande" in f for f in verificar.sin_basura(a))


def test_intentos_y_copias_fallan(tmp_path, monkeypatch):
    a = _repo(tmp_path, monkeypatch, {".intentos/uno.json": b"{}", "estudio/motor.py.bak": b"x"})
    f = verificar.sin_basura(a)
    assert any("intentos" in x for x in f) and any("copia o temporal" in x for x in f)


def test_copias_identicas_fallan_y_la_deuda_conocida_no(tmp_path, monkeypatch):
    dato = b"palabras " * 60
    a = _repo(tmp_path, monkeypatch, {"x/uno.json": dato, "x/dos.json": dato})
    assert any("copias idénticas" in f for f in verificar.sin_basura(a))
    (tmp_path / "conocida.txt").write_text("# deuda\nx/uno.json\nx/dos.json\n")
    assert verificar.sin_basura(a) == []


def test_correccion_de_sistema_sin_prueba_falla(tmp_path, monkeypatch):
    _repo(tmp_path, monkeypatch, {"perfil/correcciones.jsonl": b'{"id": "C-0009", "clase": "sistema"}\n{"id": "C-0010", "clase": "gusto"}\n'})
    assert len(verificar.correcciones_con_prueba()) == 1
    (tmp_path / "tests" / "regresion").mkdir(parents=True)
    (tmp_path / "tests" / "regresion" / "test_C-0009.py").write_text("")
    assert verificar.correcciones_con_prueba() == []
