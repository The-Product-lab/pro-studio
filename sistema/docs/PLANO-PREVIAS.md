# Plano: las dos vistas previas de Personalizar — 2026-11-10

Pedido de Pablo (literal): «la app es muy lenta en mostrar las previas en el módulo de personalizar; la preview de la persona hablando
a cámara debe poder hacer dos cosas: mostrar la persona mirando a la cámara y dos, ojo con la pantalla de B-roll completa, es muy
lenta, aún no muestra nada para escoger nada».

## Contrato
- **Entra:** un proyecto (director terminado, con o sin todo su arte) o, mientras el director trabaja, la toma que Pablo subió; más el
  estilo que está eligiendo (cada clic cambia uno).
- **Sale:** siempre dos cuadros 540×960: «con la persona» y «apoyo a pantalla completa», más una nota en español cuando algo falta.
- **Nunca:** un panel vacío ni un fallo mudo; una vista vieja pisando a la nueva; reconstruir el video entero para dibujar dos cuadros.

## Dónde se iba el tiempo (medido en `c8866-glass`, 7147 cuadros, 158 elementos)
| Causa | Costo | Arreglo |
|---|---|---|
| `Proyecto` armaba los 158 elementos (decodifica imágenes, mide textos) para dibujar 2 cuadros | 0,7 s por cambio | `Proyecto(solo_en=…)`: solo los que se ven en ese cuadro |
| `cara_de` lee la máscara de TODOS los cuadros para la caja estable de la cara si no hay caché (cada cambio de cortes la invalida) | ~7000 PNG, decenas de segundos en un video nuevo | `caras_estables(cerca=…)`: solo la ventana del cuadro pedido, mismas cajas |
| Las dos vistas se dibujaban una tras otra | suma | un hilo y un proyecto por vista; la primera se pinta apenas está |
| Pantalla esperaba 600 ms + sondeo cada 1,2 s | ~1 s muerto | espera 250 ms y sondeo cada 250 ms |
| Petición vieja seguía dibujando | trabajo inútil | solo la última por carpeta dibuja (`servidor._pedir_previa`) |
| Vista rápida: preparaba 274 máscaras PNG optimizadas (~10 s) y partía del crudo 4K | 8–17 s | 2 máscaras; parte del `fuente.mp4` ya normalizado si la ingesta lo dejó |

## Por qué el B-roll quedaba vacío (dos causas)
1. `motor.Proyecto` fallaba con `FileNotFoundError` si UNA foto del storyboard aún no tenía su arte (aunque no se viera en el cuadro):
   el trabajo moría, la pantalla ignoraba el error y las dos vistas quedaban como estaban (vacías). Ahora la vista omite esa foto y lo dice.
2. Con el director sin terminar, la vista rápida devolvía UN solo cuadro: el panel de apoyo se vaciaba. Ahora dibuja también una muestra
   del estilo a pantalla completa, con la nota «tu apoyo real aparece cuando el editor termine».
Además, si el video no tiene ninguna escena de apoyo, se dice («aún no tiene apoyo a pantalla completa») en vez de repetir la persona sin aviso.

## Un solo camino
`estudio/previas.py` (`con_director`, `con_toma`, `pintar`) es el único que genera las vistas; `servidor` solo pide y numera;
`rapida.py` solo prepara el trozo; `app/vista.js` solo pinta y avisa. El motor (`mapa_de`, `Proyecto(solo_en)`, `precargar`,
`caras_estables(cerca)`) no sabe de vistas.

## Criterios (CUANDO… EL SISTEMA DEBE…) y su verificador
Verificador de todos: `uv run pytest tests/test_previas.py tests/test_cara_estable.py -q` (sale 0) y `uv run estudio verificar`.
1. CUANDO cambia una opción de estilo con el proyecto ya visto, EL SISTEMA DEBE entregar las dos vistas en menos de 2 s (`test_dos_vistas_distintas_y_rapidas`).
2. CUANDO falta el arte de una foto, EL SISTEMA DEBE dibujar igual las dos vistas y decir cuántas imágenes faltan; el render completo sigue exigiendo todo su arte (`test_el_arte_que_falta_no_deja_el_panel_vacio`).
3. CUANDO se dibuja con solo los elementos visibles, EL SISTEMA DEBE dar exactamente los mismos píxeles que con el proyecto completo (`test_vista_parcial_es_identica_a_la_completa`).
4. CUANDO el video no tiene apoyo a pantalla completa, EL SISTEMA DEBE decirlo (`test_sin_apoyo_se_dice_en_vez_de_dejar_un_cuadro_mudo`).
5. CUANDO el director aún no termina, EL SISTEMA DEBE traer las dos vistas, la segunda marcada como muestra (`test_la_vista_rapida_trae_las_dos_vistas`).
6. CUANDO llega una petición nueva, EL SISTEMA DEBE descartar la vieja y que no escriba en el storyboard (`test_la_peticion_nueva_descarta_a_la_vieja`, `test_guardar_solo_si_sigue_vigente`).
7. CUANDO se repite el mismo pedido, EL SISTEMA DEBE reusar las vistas (`test_mismo_pedido_no_se_vuelve_a_dibujar`).
8. CUANDO no hay caché de caras, EL SISTEMA DEBE medir solo la ventana del cuadro con las mismas cajas (`test_vista_previa_mide_solo_su_ventana_con_las_mismas_cajas`).

## Abogado del diablo
- «El proyecto parcial dibuja distinto» → la prueba 3 compara píxeles; `Proyecto` sigue guardando el storyboard completo para la cámara.
- «Omitir una foto esconde un error real» → solo en vistas (`solo_en`); la nota lo dice; render y `Proyecto` normal siguen fallando.
- «Dos hilos pisan estado compartido» → cada vista tiene su `Proyecto`; la caché de cuadros es por archivo y cada hilo decodifica uno distinto.
- Límite que queda: la PRIMERA vista tras abrir un video decodifica sus cuadros del disco (depende del disco, no del código).
