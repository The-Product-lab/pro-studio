"""12-nov (video-3217): Lemo rehízo `arte/a1.mp4` con el mismo nombre y el render siguió mostrando los cuadros viejos, porque la
caché de cuadros de un clip iba solo por la ruta. Ahora va por la ruta y el archivo, y la versión vieja se borra."""
import os
import subprocess

import numpy as np
from PIL import Image

from estudio import config, motor


def _clip(f, color):
    ffmpeg, _ = config.ffmpeg()
    subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=108x192:d=0.2:r=30", "-pix_fmt", "yuv420p", str(f)],
                   check=True)


def test_un_clip_rehecho_con_el_mismo_nombre_no_reusa_los_cuadros_viejos(tmp_path):
    f = tmp_path / "arte" / "a1.mp4"
    f.parent.mkdir()
    _clip(f, "black")
    viejos = motor._cuadros_clip(f, tmp_path)
    assert int(np.asarray(Image.open(viejos[0]).convert("L")).max()) < 30
    _clip(f, "white")
    os.utime(f, ns=(f.stat().st_atime_ns, f.stat().st_mtime_ns + 10**9))   # el mismo segundo no basta para distinguirlos en todo disco
    nuevos = motor._cuadros_clip(f, tmp_path)
    assert int(np.asarray(Image.open(nuevos[0]).convert("L")).min()) > 200
    assert len(list((tmp_path / ".clips").iterdir())) == 1                  # la versión vieja no queda tirada
