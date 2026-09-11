# Tablero Macro — qué es y cómo se toca

**No es una estrategia.** Es un tablero para mirar antes de operar. Responde a tres cosas:
en qué **régimen de rango** estás, si **hoy hay un dato** que parte la sesión, y si algo del
contexto macro está estirado. **No dice hacia dónde va el precio y no debe hacerlo nunca.**

Nació el 10-sep-2026, después de medir que el posicionamiento de los fondos apalancados explica
el **0,04%** de lo que hace el Nasdaq la semana siguiente (743 informes de la CFTC, 2012-2026).
Esa medición es la razón de que aquí no haya ninguna casilla direccional.

## La página

https://claude.ai/code/artifact/5dbc9f8c-7446-4a4e-b142-8f54590e2f77

## Las tres piezas

```
tablero.py              trae los numeros y escribe tablero.json
tablero.json            los numeros de la ultima pasada
pagina.plantilla.html   la pagina, con __DATOS__ sin rellenar
pagina.html             la pagina ya rellenada (esto es lo que se publica)
```

## Actualizar

Lo normal es pedírmelo: **«actualiza el tablero»**. Yo corro esto y subo el resultado:

```
python "C:\Users\sergi\Desktop\Trading\Tablero Macro\tablero.py"
```

Eso escribe `tablero.json`, y yo lo empujo a la base de datos de la página con un `write_db`
sobre `tablero/hoy`. **La página no hay que republicarla**: se actualiza sola en cuanto cambia
el documento, aunque la tengas abierta en el móvil.

Solo hay que volver a publicar `pagina.html` si se cambia el **diseño** o se añaden campos
nuevos. En ese caso: rellenar la plantilla con el json y publicar sobre la misma URL.

## El número que importa

**ATR(20) del NQ traducido a dólares sobre 1 MNQ.** Es lo único de todo el tablero que toca
la cuenta directamente: te dice cuánto recorre un día medio con un solo contrato, y qué
porcentaje del MLL de Topstep (2.000 $, en tiempo real) se come ese recorrido.

La etiqueta sale del percentil frente a los últimos 3 años:
`<33 BAJO` · `33-66 NORMAL` · `66-90 ALTO` · `>90 EXTREMO`.

⚠️ La barra de 5 años del NQ de Yahoo es de contrato continuo: los saltos de vencimiento
inflan algún true range suelto. No afecta a la media de 20, pero no leer un día aislado.

⚠️ Se descarta siempre la **sesión en curso**: el corte es el último cierre del índice al
contado (`ultimo_cierre` en el json). Sin ese corte, la barra a medias metía el ATR hacia abajo.

## El calendario de eventos es a mano

La lista `EVENTOS` de `tablero.py` está escrita a mano y hay que ampliarla cuando salgan los
calendarios del BLS y de la Reserva Federal. Si se queda corta, el tablero dirá «sin dato
programado» un día que sí lo había. Es la parte frágil.

## Lo que se descartó a propósito

- **Cualquier casilla direccional.** Medido y descartado, ver arriba.
- **Que la página busque los datos ella sola.** Una página publicada no puede salir a internet
  (lo bloquea la política de seguridad del visor). Por eso el reparto: el script trae, la base
  guarda, la página pinta.
