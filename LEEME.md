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

## La DIRECCION: que mide exactamente, y que NO mide

Pregunta suya, 14-sep: *"cuando dices q cierre verde, q significa, q NY puede subir?"*.
La respuesta es **NO**, y por eso el titular cambio.

Hay **dos preguntas distintas** que se pueden llamar "cierra verde", y solo una tiene respuesta:

| | pregunta | ¿se puede saber? |
|---|---|---|
| **A** | ¿cierra por encima del **cierre de ayer**? (incluye la noche) | **si**, de 21% a 82% |
| **B** | ¿sube la **sesion de NY**, de 09:30 a 16:00? | **no**, plana en ~54% |

```
la noche viene...          n     A: sobre ayer    B: NY sube
  bajando fuerte          450         20.9%         53.1%
  bajando poco            371         39.6%         56.1%
  plana                   555         54.8%         53.9%
  subiendo poco           552         70.8%         54.2%
  subiendo fuerte         584         82.0%         55.7%
```
⭐ **A va de 21 a 82. B no se entera de nada.** Y el **11,4%** de los dias cierran por encima de
ayer **habiendo caido toda la sesion de Nueva York**. Por eso la tarjeta dice literalmente
"ACABA POR ENCIMA DE AYER" y nunca "hoy apunta alcista".

### Los tres fallos que hubo que arreglar (todos la misma familia)
🔴 **1. La tabla se calculaba sobre `NQ=F`**, cuya barra diaria abre a las **18:00 ET del dia
anterior**. El "hueco" que salia era el reabrir de las 18:00: el **70%** de las sesiones caian en
"sin hueco". ✅ Ahora la tabla va sobre **`^NDX`**, que solo imprime sesion regular.

🔴 **2. En vivo se comparaba el FUTURO contra el CONTADO.** No cotizan al mismo nivel: hoy NQ=F
29.549,8 contra ^NDX 29.212,0, **337 puntos = +1,16% de base** que entraba como si fuera
movimiento. Amontonaba 279 de 499 dias en "subiendo fuerte". ✅ Ahora la noche se mide **futuro
contra futuro**: precio de ahora contra el cierre del futuro a las 16:00 ET de ayer.

🔴 **3. La señal en vivo y la tabla eran variables distintas** (lo canto Codex). ✅ Medido: el
movimiento del futuro a las 09:00 y el hueco del contado a las 09:30 tienen **correlacion 0,9705**,
misma media (+0,065% contra +0,062%), misma desviacion y **92% de coincidencia de signo**. Son la
misma variable, asi que vale usar la tabla de 10 años con lectura en vivo del futuro.

⭐ **La pista que delata a los tres: un cubo que se traga la mayoria de la muestra.** 70% en "sin
hueco", 56% en "subiendo fuerte". Si pasa eso, la variable esta mal definida. Ahora reparten
450/371/555/552/584.

## El bloque CONTEXTO: 25 series gratis

`tablero.json` lleva una clave **`contexto`** con todo lo gratis y sin clave que se puede mirar
antes de operar, de la misma API de Yahoo que ya se usaba: bolsas de fuera (Nikkei, Hang Seng,
Shanghai, Corea, DAX, FTSE, Stoxx), futuros de EEUU (ES, YM, RTY), volatilidad (VIX, VIX9D,
VIX3M, VVIX, SKEW), tipos (bono 10a, letra 3m, futuro del bono), divisas (DXY, euro, yen),
materias primas (oro, crudo, cobre) y bitcoin. De cada una: nivel, cambio del dia, percentil
dentro de su propio rango de 52 semanas y distancia a su media de 200.

Ni secretos, ni facturas, ni dependencias. La pasada entera sigue en **~12 s** porque
`yahoo_cache()` evita bajar dos veces los simbolos que el bloque comparte con `tablero`.

⛔ **Ninguna de esas casillas dice hacia donde va el dia, y es a proposito.** Medido el
14-sep-2026 sobre 2.512 sesiones con el objetivo limpio: de 21 senales solo 2 cruzaron su banda
de confianza, cuando por azar se esperaria 1,1. Es ruido. Estan ahi como contexto, no como
prediccion.

### 🔴 La trampa que casi cuela: NQ=F no vale para medir direccion
La barra **diaria** de `NQ=F` en Yahoo **abre a las 18:00 ET del dia anterior** (verificado
contra las barras horarias). Medir "cierre > apertura" sobre ella mete **toda la noche** dentro
de la ventana objetivo. Con eso, las bolsas asiaticas —que cierran entre las 02:00 y las 04:00
ET, o sea **dentro**— parecian predecir el dia con **+13 puntos**. No predecian: estaban viendo
el resultado.

Con el objetivo bueno, **`^NDX` de apertura a cierre** (el indice al contado solo imprime la
sesion regular, asi que nada nocturno se puede colar), ese mismo Nikkei se queda en **-1,9**.

➡️ **Para cualquier medicion direccional el objetivo es `^NDX`, nunca `NQ=F`.** Y por lo mismo,
el "hueco" calculado como `apertura(NQ=F) / cierre anterior` es el reabrir de las 18:00, que es
casi cero: no es el hueco de contado y no sirve.

⚠️ El efecto **lunes** tambien encoge al medirlo limpio: de 61,6% baja a **58,3% +-4,5** contra
una base de 54,6%. Identico en las dos mitades de la muestra, pero su banda toca la base. Es un
indicio, no un hallazgo.

## El porcentaje de direccion: que lo mueve de verdad

`direccion_modelo.py` y `direccion_0923.py` son **investigacion, no produccion**. Miden si un
analisis macro puede dar un porcentaje honesto de la direccion del dia.

**La vara de medir es la CALIBRACION, no el beneficio.** El numero no se usa para operar, asi
que lo unico que importa es que cuando diga 62% acaben verdes ~62 de cada 100. Metrica: Brier.

### Lo que salio (2.467 sesiones, corte temporal 70/30)
```
Brier del modelo            0.1918
Brier de decir siempre 55.6% 0.2444      <- el modelo aporta de verdad
acierto                     72.2% vs 57.8%
```
🔴 **Pero el reparto de meritos mata la idea del "analisis macro":** quitando cada variable y
mirando cuanto empeora el Brier fuera de muestra,

```
sin hueco       +0.0430      <- se lo lleva TODO
sin dolar       +0.0011
sin lunes       +0.0007
sin Asia        +0.0000
sin Europa      -0.0000
sin VIX         +0.0001
```
➡️ **Asia, Europa, el VIX y el dolar no aportan nada.** El porcentaje sale del **movimiento que
ya lleva la noche**, no de la macro.

### La auditoria de Codex y lo que corrigio
Codex canto dos cosas CIERTAS: (1) el `hueco` usaba la apertura del contado de las **09:30**
cuando la tarjeta sale a las **09:23** — siete minutos de informacion futura; y (2) que el 72%
no es prediccion, porque el hueco ya es el primer tramo del propio movimiento que se predice.

`direccion_0923.py` responde a la primera con datos: usa el futuro NQ a las **09:00 ET**, que son
23 minutos ANTES de la tarjeta, o sea con MENOS informacion de la que habria en vivo.
```
correlacion entre la señal de 09:00 y la de 09:30   0.923
señal 09:00 (limpia)    Brier 0.1988 (base 0.2526)  acierto 68.7%
señal 09:30 (con fuga)  Brier 0.1825 (base 0.2526)  acierto 74.0%
```
⭐ La fuga inflaba, pero **el efecto sobrevive**: 68.7% contra una base de 56.7%.
⚠️ Precio: las horarias de Yahoo solo dan 2 años, asi que ahi la muestra baja a 499 sesiones
(150 de prueba) y la calibracion por cubos va justa.

⛔ Lo que NO se puede decir de este numero: que anticipe nada. Dice cuanto empuja lo que **ya
ha pasado de noche**. Es exactamente el aviso que la tarjeta ya lleva impreso.

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
