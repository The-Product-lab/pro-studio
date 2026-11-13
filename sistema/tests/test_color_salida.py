"""El final dice en el archivo qué color lleva (BT.709 completo). Caso real (Pablo, 11-nov: «en original no sale original»): salía
sin marcas y cada reproductor adivinaba; después, con las marcas como opción de salida, ffmpeg dejaba primarios y curva en «desconocido»."""
import subprocess

import numpy as np

from estudio import config, motor


def test_el_final_declara_bt709_completo(tmp_path):
    destino = tmp_path / "v.mp4"
    enc = motor._codificador(destino)
    cuadro = np.full((motor.H, motor.W, 3), (200, 120, 60), np.uint8).tobytes()
    for _ in range(3):
        enc.stdin.write(cuadro)
    enc.stdin.close()
    assert enc.wait() == 0
    _, ffprobe = config.ffmpeg()
    dicho = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=color_space,color_transfer,color_primaries,color_range", "-of", "default=nw=1:nk=1", str(destino)],
                           capture_output=True, text=True).stdout.split()
    assert sorted(dicho) == ["bt709", "bt709", "bt709", "tv"]


def test_el_color_vuelve_igual_al_decodificar(tmp_path):
    """Un color liso entra y sale igual (±3 de 255) leyéndolo como BT.709: la matriz con que se escribe es la que se declara."""
    destino = tmp_path / "v.mp4"
    enc = motor._codificador(destino)
    color = (200, 120, 60)
    for _ in range(3):
        enc.stdin.write(np.full((motor.H, motor.W, 3), color, np.uint8).tobytes())
    enc.stdin.close()
    enc.wait()
    ffmpeg, _ = config.ffmpeg()
    b = subprocess.run([ffmpeg, "-v", "error", "-i", str(destino), "-frames:v", "1", "-vf", "scale=in_color_matrix=bt709:in_range=tv,format=rgb24",
                        "-f", "rawvideo", "-"], capture_output=True).stdout
    visto = np.frombuffer(b[:motor.W * motor.H * 3], np.uint8).reshape(motor.H, motor.W, 3)[900:1000, 500:600].mean((0, 1))
    assert np.abs(visto - np.array(color)).max() <= 3, visto
