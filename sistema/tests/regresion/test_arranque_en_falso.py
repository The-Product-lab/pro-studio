"""C8868 (Pablo, 04-nov): «el segundo video deja pasar un error del hablante, quita eso… corta lo que va atrás y deja solo
y todo completamente». El tramo arrancaba en 49,64 s con «grabas.», un pedazo de otra toma, pegado a la toma que queda
(«lo montas en una carpeta…», 50,40 s). La compuerta del montaje lo detecta; empezando en la toma buena pasa."""
from estudio import montaje

PALABRAS = [{"w": "Ya,", "s": 28.24, "e": 28.8}, {"w": "lo", "s": 28.86, "e": 30.0}, {"w": "grabas,", "s": 30.0, "e": 30.56}, {"w": "subes", "s": 30.56, "e": 31.46}, {"w": "a", "s": 31.46, "e": 31.5}, {"w": "una", "s": 31.5, "e": 31.68}, {"w": "carpeta", "s": 31.68, "e": 32.36}, {"w": "y", "s": 32.36, "e": 32.76}, {"w": "en", "s": 32.76, "e": 32.86}, {"w": "cuestión", "s": 32.86, "e": 33.12}, {"w": "de", "s": 33.12, "e": 33.34}, {"w": "minutos", "s": 33.34, "e": 33.62}, {"w": "te", "s": 33.62, "e": 33.92}, {"w": "entrega", "s": 33.92, "e": 34.26}, {"w": "todo", "s": 34.26, "e": 34.42}, {"w": "listo.", "s": 34.42, "e": 34.94}, {"w": "Ya,", "s": 35.4, "e": 36.0}, {"w": "lo", "s": 36.08, "e": 36.38}, {"w": "grabas,", "s": 36.38, "e": 36.92}, {"w": "ya", "s": 36.92, "e": 37.36}, {"w": "listo.", "s": 37.36, "e": 37.82}, {"w": "Dos,", "s": 37.86, "e": 38.3}, {"w": "tres,", "s": 38.44, "e": 38.82}, {"w": "va.", "s": 38.9, "e": 39.06}, {"w": "Lo", "s": 39.36, "e": 39.96}, {"w": "grabas,", "s": 39.96, "e": 40.42}, {"w": "subes", "s": 40.42, "e": 40.86}, {"w": "en", "s": 40.86, "e": 41.0}, {"w": "una", "s": 41.0, "e": 41.14}, {"w": "carpeta", "s": 41.14, "e": 41.82}, {"w": "y", "s": 41.82, "e": 42.08}, {"w": "te", "s": 42.08, "e": 42.26}, {"w": "entrega...", "s": 42.26, "e": 42.82}, {"w": "Lo", "s": 42.82, "e": 43.52}, {"w": "grabas,", "s": 43.52, "e": 43.98}, {"w": "subes", "s": 43.98, "e": 44.34}, {"w": "en", "s": 44.34, "e": 44.44}, {"w": "una", "s": 44.44, "e": 44.6}, {"w": "carpeta", "s": 44.6, "e": 45.26}, {"w": "y", "s": 45.26, "e": 45.66}, {"w": "Cloud", "s": 45.66, "e": 45.94}, {"w": "te", "s": 45.94, "e": 46.14}, {"w": "entrega", "s": 46.14, "e": 46.52}, {"w": "todo", "s": 46.52, "e": 46.76}, {"w": "listo", "s": 46.76, "e": 47.28}, {"w": "en", "s": 47.28, "e": 47.46}, {"w": "minutos.", "s": 47.46, "e": 47.76}, {"w": "Lo", "s": 48.16, "e": 48.64}, {"w": "Lo", "s": 48.59, "e": 49.95}, {"w": "grabas.", "s": 49.95, "e": 50.33}, {"w": "lo", "s": 50.4, "e": 50.56}, {"w": "montas", "s": 50.56, "e": 50.9}, {"w": "en", "s": 50.9, "e": 51.02}, {"w": "una", "s": 51.02, "e": 51.16}, {"w": "carpeta", "s": 51.16, "e": 51.72}, {"w": "y", "s": 51.72, "e": 51.84}, {"w": "Cloud", "s": 51.84, "e": 52.08}, {"w": "te", "s": 52.08, "e": 52.22}, {"w": "entrega", "s": 52.22, "e": 52.58}, {"w": "el", "s": 52.58, "e": 52.64}, {"w": "video", "s": 52.64, "e": 52.82}, {"w": "listo", "s": 52.82, "e": 53.5}, {"w": "para", "s": 53.5, "e": 53.64}, {"w": "publicar.", "s": 53.64, "e": 54.18}]


def test_pedazo_de_otra_toma_pegado_a_la_buena_no_pasa():
    err = montaje.arranques_en_falso(PALABRAS, [(49.64, 54.44)])
    assert err and "grabas" in err[0]


def test_empezando_en_la_toma_buena_pasa():
    assert montaje.arranques_en_falso(PALABRAS, [(50.37, 54.44)]) == []


def test_un_tramo_largo_que_llega_a_la_toma_buena_no_es_pedazo():
    assert montaje.arranques_en_falso(PALABRAS, [(28.0, 54.44)]) == []
