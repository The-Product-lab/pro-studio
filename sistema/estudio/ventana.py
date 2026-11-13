"""La ventana de Pro Studio en Mac: una app de verdad (ventana propia, nombre e icono en el Dock), no una ventana de Chrome.
Pablo, 11-nov: «me desespera que no tenga un icono en el Dock, o algo que me permita entenderla como app».
Solo Mac: en Windows y Linux la ventana la sigue abriendo `servidor.orden_ventana`."""
import sys

from . import config

MEMORIA = config.TPS / "ventana"   # lo que la pantalla recuerda (video abierto, estilo): sobrevive al cerrar la app
TAMANO = (1600, 1000)


def disponible() -> bool:
    if sys.platform != "darwin":
        return False
    try:
        import webview  # noqa: F401
    except ImportError:
        return False
    return True


def pregunta_cierre(trabajando: list[str]) -> str | None:
    """Lo que se le pregunta a la persona al cerrar; None = no hay nada corriendo y se cierra sin preguntar."""
    if not trabajando:
        return None
    return "Pro Studio está trabajando: " + ", ".join(trabajando) + ". Si cierras, eso se detiene."


def _confirmar(texto: str) -> bool:
    from AppKit import NSAlert, NSAlertFirstButtonReturn
    a = NSAlert.alloc().init()
    a.setMessageText_("¿Cerrar Pro Studio?")
    a.setInformativeText_(texto)
    a.addButtonWithTitle_("Seguir trabajando")
    a.addButtonWithTitle_("Cerrar y detener")
    return a.runModal() != NSAlertFirstButtonReturn


def avisar(texto: str) -> None:
    """Un aviso con un solo botón, para lo que la persona tiene que saber antes de que la app se cierre."""
    from AppKit import NSAlert, NSApplication
    NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
    a = NSAlert.alloc().init()
    a.setMessageText_(config.NOMBRE_APP)
    a.setInformativeText_(texto)
    a.addButtonWithTitle_("Entendido")
    a.runModal()


def abrir(url: str, trabajando) -> None:
    """Abre la ventana y NO vuelve hasta que la persona la cierra. `trabajando()` → nombres de lo que está corriendo."""
    import webview
    webview.settings["ALLOW_DOWNLOADS"] = True                   # «Descargar» el video final
    webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = False   # las páginas de la app que abren aparte siguen dentro de la app
    w = webview.create_window(config.NOMBRE_APP, url, width=TAMANO[0], height=TAMANO[1], min_size=(1100, 700), text_select=True)
    w.events.closing += lambda: (p := pregunta_cierre(trabajando())) is None or _confirmar(p)
    MEMORIA.mkdir(parents=True, exist_ok=True)
    webview.start(private_mode=False, storage_path=str(MEMORIA))
