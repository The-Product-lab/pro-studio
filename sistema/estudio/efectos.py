"""Efectos de imagen para los estilos de «pantalla completa» (HUD, Maestro…): filtros por escena, textura CRT y transiciones.

Todo trabaja con arrays numpy RGB uint8 de 1080×1920 y es determinista (mismo cuadro → mismo resultado).
"""
import numpy as np
from PIL import Image, ImageFilter, ImageOps

# Rampa térmica: negro → violeta → rojo → naranja → amarillo → blanco
_TERMICA = np.array([[0, 0, 0], [40, 0, 90], [150, 0, 140], [230, 30, 50], [255, 122, 0], [255, 220, 40], [255, 255, 255]], np.float32)


def _rampa(colores: np.ndarray) -> np.ndarray:
    """Tabla 256×3 que interpola linealmente entre los colores dados."""
    x = np.linspace(0, 1, len(colores))
    t = np.linspace(0, 1, 256)
    return np.stack([np.interp(t, x, colores[:, c]) for c in range(3)], 1).astype(np.uint8)


_LUT_TERMICA = _rampa(_TERMICA)


def bn(rgb: np.ndarray) -> np.ndarray:
    g = np.asarray(ImageOps.autocontrast(Image.fromarray(rgb).convert("L"), cutoff=(2, 1)), np.float32) / 255
    g = np.clip((g - .5) * 1.25 + .5, 0, 1) ** 1.1
    return np.repeat((g * 255).astype(np.uint8)[..., None], 3, 2)


def termico(rgb: np.ndarray) -> np.ndarray:
    g = np.asarray(ImageOps.autocontrast(Image.fromarray(rgb).convert("L"), cutoff=1).filter(ImageFilter.GaussianBlur(3)))
    return _LUT_TERMICA[g]


def rayosx(rgb: np.ndarray, tinte=(0, 229, 255)) -> np.ndarray:
    """Negativo azulado con bordes brillantes, como placa de rayos X."""
    im = ImageOps.autocontrast(Image.fromarray(rgb).convert("L"), cutoff=1)
    inv = 1 - np.asarray(im, np.float32) / 255
    bordes = np.asarray(im.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(1.5)), np.float32) / 255
    v = np.clip(inv ** 1.6 * .85 + bordes * 1.4, 0, 1)
    t = np.array(tinte, np.float32) / 255
    out = v[..., None] * (t * .75 + .25) + (v[..., None] ** 3) * .35
    return (np.clip(out, 0, 1) * 255).astype(np.uint8)


def duotono(rgb: np.ndarray, oscuro, claro) -> np.ndarray:
    g = np.asarray(ImageOps.autocontrast(Image.fromarray(rgb).convert("L"), cutoff=1), np.float32)[..., None] / 255
    return (np.array(oscuro, np.float32) * (1 - g) + np.array(claro, np.float32) * g).astype(np.uint8)


def halftone(rgb: np.ndarray, celda=10, tinta=(14, 14, 16), papel=(236, 232, 222)) -> np.ndarray:
    """Semitono de imprenta a 45°: puntos de tinta cuyo tamaño sigue la sombra de la imagen (B/N de archivo, pop)."""
    g = np.asarray(ImageOps.autocontrast(Image.fromarray(rgb).convert("L"), cutoff=(2, 1)), np.float32) / 255
    h, w = g.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = (xx + yy) * .7071, (xx - yy) * .7071
    pantalla = (np.cos(2 * np.pi * u / celda) + np.cos(2 * np.pi * v / celda)) / 4 + .5
    tinta_m = (g < pantalla).astype(np.float32)
    tinta_m = np.asarray(Image.fromarray((tinta_m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(.6)), np.float32)[..., None] / 255
    return (np.array(papel, np.float32) * (1 - tinta_m) + np.array(tinta, np.float32) * tinta_m).astype(np.uint8)


def blueprint(rgb: np.ndarray, oscuro=(10, 26, 52), claro=(77, 238, 234)) -> np.ndarray:
    """Plano técnico / ecografía: azul profundo, luces cian y una retícula isométrica fina encima."""
    out = duotono(rgb, oscuro, claro).astype(np.float32)
    h, w = out.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    reticula = ((xx + yy) % 60 < 2) | ((xx - yy) % 60 < 2) | (yy % 60 < 1)
    out[reticula] = out[reticula] * .55 + np.array(claro, np.float32) * .45
    return np.clip(out, 0, 255).astype(np.uint8)


def penumbra(rgb: np.ndarray, tinte=(6, 9, 7)) -> np.ndarray:
    """Toma real en penumbra (luminoso/cine): −1 paso de luz, poca saturación, negros levantados hacia un tono y viñeta fuerte."""
    f = rgb.astype(np.float32) / 255
    g = f @ np.array([.299, .587, .114], np.float32)
    f = g[..., None] + (f - g[..., None]) * .55                       # desatura
    f = f ** 1.35 * .78                                               # baja la luz (más en sombras)
    h, w = g.shape
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w * .55)) ** 2 + ((yy - h * .42) / (h * .55)) ** 2)
    f *= np.clip(1.25 - r * .85, .12, 1)[..., None]
    f = f + np.array(tinte, np.float32) / 255 * (1 - f)               # negros levantados al tono del fondo
    return (np.clip(f, 0, 1) * 255).astype(np.uint8)


FILTROS = {"ninguno": lambda rgb, est: rgb, "penumbra": lambda rgb, est: penumbra(rgb), "bn": lambda rgb, est: bn(rgb), "termico": lambda rgb, est: termico(rgb),
           "rayosx": lambda rgb, est: rayosx(rgb, est.acento2), "duotono": lambda rgb, est: duotono(rgb, est.tinta, est.acento),
           "halftone": lambda rgb, est: halftone(rgb, tinta=est.tinta if sum(est.tinta) < 240 else (14, 14, 16)),
           "blueprint": lambda rgb, est: blueprint(rgb, claro=est.acento2)}


ZOOM_ENTRADA_DUR, ZOOM_ENTRADA_AMP = .7, .04  # C-0002: era 0,22 s y 20 % (brusco, se veía como zoom in + zoom out juntos)


def zoom_entrada_k(p: float) -> float:
    """Cuánto zoom de entrada queda (1 → 0) con curva que acelera y desacelera (smootherstep, velocidad 0 en los dos extremos)."""
    p = min(max(p, 0.), 1.)
    return 1 - p * p * p * (p * (6 * p - 15) + 10)


ACERCAR_MAX = .15  # C-0003: el apoyo se acerca solo (Ken Burns de cine) hasta +15 %, nunca más rápido que la cámara


def acercar_k(p: float) -> float:
    """Avance del acercamiento lento de un apoyo (0 → 1) a lo largo de su vida: arranca y llega suave (smoothstep)."""
    p = min(max(p, 0.), 1.)
    return p * p * (3 - 2 * p)


def zoom_radial(arr: np.ndarray, p: float) -> np.ndarray:
    """Zoom de entrada (0 ≤ p ≤ 1): llega desde 104 % con un leve desenfoque radial y se asienta en 100 %, con calma."""
    k = zoom_entrada_k(p)
    if k <= .01:
        return arr
    im = Image.fromarray(arr)
    h, w = arr.shape[:2]
    acum = np.zeros(arr.shape, np.float32)
    n = 8
    for i in range(n):
        z = 1 + ZOOM_ENTRADA_AMP * k * (1 + i / n * .3)
        cw, ch = int(w / z), int(h / z)
        x0, y0 = (w - cw) // 2, (h - ch) // 2
        acum += np.asarray(im.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h), Image.BILINEAR), np.float32)
    return np.clip(acum / n, 0, 255).astype(np.uint8)


def pixelar(arr: np.ndarray, p: float) -> np.ndarray:
    """Mosaico de transición (0 ≤ p ≤ 1): bloques de 64 px que se afinan hasta desaparecer."""
    k = 1 - p
    bloque = int(4 + 60 * k)
    if k <= .05 or bloque < 5:
        return arr
    h, w = arr.shape[:2]
    chico = Image.fromarray(arr).resize((max(1, w // bloque), max(1, h // bloque)), Image.BILINEAR)
    return np.asarray(chico.resize((w, h), Image.NEAREST))


def filtrar(rgb: np.ndarray, nombre: str, est) -> np.ndarray:
    if nombre not in FILTROS:
        raise ValueError(f"filtro desconocido {nombre!r} (hay: {', '.join(FILTROS)})")
    return FILTROS[nombre](rgb, est)


def aberracion(arr: np.ndarray, px: int) -> np.ndarray:
    """Desplaza rojo a la izquierda y azul a la derecha (aberración cromática)."""
    if px <= 0:
        return arr
    out = arr.copy()
    out[:, :-px, 0] = arr[:, px:, 0]
    out[:, px:, 2] = arr[:, :-px, 2]
    return out


_VINETA = None


def crt(arr: np.ndarray, fuerza=1.0) -> np.ndarray:
    """Textura de pantalla de tubo: scanlines finas, viñeta y un leve sangrado RGB."""
    global _VINETA
    h, w = arr.shape[:2]
    if _VINETA is None or _VINETA.shape != (h, w):
        yy, xx = np.mgrid[0:h, 0:w]
        r = np.sqrt(((xx - w / 2) / (w * .6)) ** 2 + ((yy - h / 2) / (h * .6)) ** 2)
        _VINETA = (1 - np.clip(r - .55, 0, 1) * 1.1).astype(np.float32)
    f = arr.astype(np.float32)
    f[::3] *= 1 - .16 * fuerza
    f *= _VINETA[..., None] ** fuerza
    return aberracion(np.clip(f, 0, 255).astype(np.uint8), int(2 * fuerza))


def rafaga(arr: np.ndarray, p: float, semilla: int) -> np.ndarray:
    """Transición de interferencia (0 ≤ p ≤ 1): franjas desplazadas, aberración fuerte y destello; se apaga al final."""
    k = 1 - p
    if k <= 0:
        return arr
    rng = np.random.default_rng(semilla)
    out = arr.copy()
    h = arr.shape[0]
    for _ in range(int(14 * k) + 2):
        y = int(rng.integers(0, h - 40))
        alto = int(rng.integers(8, 90))
        out[y:y + alto] = np.roll(arr[y:y + alto], int(rng.integers(-180, 180) * k), axis=1)
    out = aberracion(out, int(22 * k))
    f = out.astype(np.float32)
    f[::2] *= 1 - .45 * k
    f += 70 * k * (rng.random() > .5)
    return np.clip(f, 0, 255).astype(np.uint8)


MUROS = {"muro-luz", "muro-claro"}
_MURO = {}


def muro(tipo: str, est):
    """Fondo de muro con rayas diagonales de luz: «muro-luz» = petróleo oscuro (neón), «muro-claro» = gris blanco (respiro)."""
    clave = (tipo, est.acento2)
    if clave in _MURO:
        return _MURO[clave]
    H, W = 1920, 1080
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    r = np.sqrt(((xx - W / 2) / (W * .75)) ** 2 + ((yy - H * .45) / (H * .6)) ** 2)
    ovalo = np.clip(1.15 - r, 0, 1)
    rayas = .5 + .5 * np.sin((xx * .6 + yy) / 1920 * 2 * np.pi * 3.2)
    rayas = np.asarray(Image.fromarray((rayas * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(40)), np.float32) / 255
    ruido = np.random.default_rng(5).normal(0, 1, (H, W)).astype(np.float32)
    if tipo == "muro-claro":
        base = np.array([214, 218, 216], np.float32)
        img = base * (.72 + .28 * ovalo[..., None]) * (.86 + .14 * rayas[..., None])
    else:
        base = np.array([10, 43, 51], np.float32)
        img = base * (.25 + .95 * ovalo[..., None]) * (.7 + .45 * rayas[..., None]) + np.array([4, 6, 6], np.float32)
    img = img + ruido[..., None] * 4
    out = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).convert("RGBA")
    _MURO[clave] = out
    return out


def bloom(arr: np.ndarray, fuerza=.35, umbral=.95, rodilla=.035) -> np.ndarray:
    """Bloom de verdad (como las luces del referente): SOLO las fuentes de luz (luz > 95 %: lámparas, letras encendidas, pantallas; NO la camiseta blanca ni la piel) suelta un
    halo en tres capas (chica, media, amplia) que se SUMA; los medios tonos, la piel y los negros de la toma no cambian."""
    f = arr.astype(np.float32) / 255
    luz = f.max(-1)
    k = np.clip((luz - umbral + rodilla) / (2 * rodilla), 0, 1) ** 2        # rodilla suave alrededor del umbral
    fuente = f * k[..., None]
    if fuente.max() < .02:
        return arr
    h, w = arr.shape[:2]
    halo = np.zeros_like(f)
    for escala, radio, peso in ((2, 3, .45), (4, 6, .35), (8, 9, .2)):   # mips: 1/2, 1/4, 1/8 de la imagen
        chico = Image.fromarray((fuente * 255).astype(np.uint8)).resize((w // escala, h // escala), Image.BILINEAR)
        chico = chico.filter(ImageFilter.GaussianBlur(radio))
        halo += np.asarray(chico.resize((w, h), Image.BILINEAR), np.float32) / 255 * peso
    return (np.clip(f + halo * fuerza, 0, 1) * 255).astype(np.uint8)


def bloques(arr: np.ndarray, p: float, color, semilla=0) -> np.ndarray:
    """Transición de DRUpn (0 ≤ p ≤ 1, ~0,22 s): destello del color de acento 1–2 cuadros, mosaico que se afina y cuadrados
    del acento que se multiplican en cascada (6 → 40) y se apagan."""
    out = pixelar(arr, min(1, p * 1.4)).astype(np.float32)
    if p < .12:                                   # destello de cuadro completo
        out = out * .25 + np.array(color, np.float32) * .75
    rng = np.random.default_rng(semilla)
    h, w = arr.shape[:2]
    n = int(6 + 34 * min(1, p * 2.5)) if p < .8 else 0
    for _ in range(n):
        lado = int(w * rng.uniform(.03, .06))
        x, y = int(rng.integers(0, w - lado)), int(rng.integers(0, h - lado))
        out[y:y + lado, x:x + lado] = color if rng.random() < .7 else (240, 240, 240)
    return np.clip(out, 0, 255).astype(np.uint8)


def invertir(arr: np.ndarray) -> np.ndarray:
    """Negativo (positivo ↔ negativo) para el cambio de idea."""
    return (255 - arr).astype(np.uint8)
