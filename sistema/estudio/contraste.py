"""Contraste de color (WCAG): UNA fórmula y UN umbral para todo el estudio (texto de película y portadas).
`MINIMO` es el contraste mínimo de texto grande; el nombre de las portadas pide más (`portadas.LEGIBLE_MIN`, AAA) y usa la misma fórmula."""

MINIMO = 3.0


def luz(c) -> float:
    """Luminancia relativa de un color RGB (0-255)."""
    v = [((x / 255) / 12.92 if x / 255 <= .03928 else (((x / 255) + .055) / 1.055) ** 2.4) for x in c[:3]]
    return .2126 * v[0] + .7152 * v[1] + .0722 * v[2]


def razon(a, b) -> float:
    """Razón de contraste entre dos colores (1 a 21)."""
    la, lb = sorted((luz(a), luz(b)), reverse=True)
    return (la + .05) / (lb + .05)
