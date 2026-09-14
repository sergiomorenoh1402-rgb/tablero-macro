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

## Quien lo dispara cada dia: GitHub Actions

`.github/workflows/tablero.yml` — lunes a viernes, **dos pasadas**:

```
23 13 * * 1-5   (UTC)  = 06:23 de Las Vegas   <- la buena
23 15 * * 1-5   (UTC)  = 08:23 de Las Vegas   <- el respaldo
```

Manda la tarjeta **la primera que llegue**; la otra se calla sola. Tambien se puede lanzar a
mano desde la pestana **Actions**, boton *Run workflow*, o con `gh workflow run tablero.yml`.

## 🔴 GitHub NO es un reloj: lo encola horas

Medido en este repo, no es teoria:

| dia | programada | salio | retraso |
|---|---|---|---|
| vie 11-sep | 13:07 UTC | 16:59 UTC | **3 h 52 min** |
| lun 14-sep | 13:07 UTC | 18:30 UTC | **5 h 24 min** |

El minuto **07** caia dentro del pico `:00-:10`, donde programa medio mundo. De ahi las dos
correcciones: el minuto **23**, fuera del pico, y una **segunda pasada de respaldo** dos horas
despues. No hay garantia de hora; lo que si hay es una segunda oportunidad.

⚠️ Con el cambio de hora de noviembre hay que subir **las dos**: `23 14` y `23 16`.

### La guardia: por que no llegan dos tarjetas

Cada pasada que consigue mandar la tarjeta sube un artefacto vacio llamado **`enviado-<fecha>`**.
Lo primero que hace cualquier pasada es preguntar por la API si ese artefacto ya existe:

- **existe** → hoy la tarjeta ya salio, la pasada no hace nada mas y lo dice con un *notice*.
- **no existe** → trae los numeros, manda la tarjeta y deja la marca.

Da igual cual de las dos llegue antes, y cubre el caso raro de que la de las 13:23 se encole
tanto que aterrice despues de la de las 15:23. ⭐ La marca se deja **solo si Telegram acepto el
envio**: si falla, no hay marca y el respaldo reintenta. Caduca a los 3 dias.

⛔ Ojo: un *Run workflow* a mano tambien deja la marca. Si lo lanzas de madrugada para probar,
la pasada de las 06:23 se callara. Es lo que queremos (ya tienes la tarjeta), pero conviene
saberlo.

### Los dos secretos
En **Settings → Secrets and variables → Actions** del repo:
- `TG_TOKEN` — el token del bot `tablero_mnq_bot`
- `TG_CHAT` — `-1004465877423`, el canal privado **Tablero**

⛔ **El token NUNCA va en el repo**, que es publico. Solo como secreto cifrado de Actions, que no
se puede volver a leer. Si falta, el workflow falla a proposito y avisa en vez de callarse.

## ⛔🔴 LO QUE NO FUNCIONA: la rutina en la nube de Claude

Se intento y **no puede funcionar**. La rutina `trig_01EDDGmCxUkayeUYsPeEM1gC` quedo
**desactivada** (no se pueden borrar; se desactivan en https://claude.ai/code/routines).

El entorno de las rutinas sale por un proxy que solo deja pasar Anthropic, los repositorios de
paquetes y GitHub. Medido el 11-sep-2026 desde dentro:

```
query1.finance.yahoo.com  -> BLOQUEADO
publicreporting.cftc.gov  -> BLOQUEADO
api.telegram.org          -> BLOQUEADO
api.github.com            -> 200 OK
example.com               -> BLOQUEADO
```

➡️ No puede bajar precios **ni mandar Telegram**. ⛔ **No volver a intentarlo**: no es cuestion de
permisos ni de configuracion, y el campo `user_declared_urls` de la API no se guarda.

## Por que el repo es publico
La app de Claude en GitHub **no esta instalada** en su cuenta, solo autorizada, y sin instalar,
las rutinas solo alcanzan repos **publicos** — se vio porque en el desplegable solo aparecia
`pulso-latino-generador`, el unico publico de los tres. Decision suya: *"publico, tampoco soy tan
importante como para q me hackeen"*. Aqui dentro no hay credenciales ni nada con ventaja.

## El bot y el canal
- Bot `tablero_mnq_bot`, creado solo para esto. ⛔ **No es el bot de Nimbo ni el del 3D**: si este
  token se cae, no abre nada mas.
- Canal privado **Tablero**, id `-1004465877423`.
