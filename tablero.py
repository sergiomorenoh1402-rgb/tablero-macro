# tablero.py - reune los numeros del tablero macro y los deja en tablero.json
#
# Uso:  python "C:\Users\sergi\Desktop\Trading\Tablero Macro\tablero.py"
#
# No pinta nada y no manda nada. Solo escribe tablero.json al lado de este
# fichero. Quien lo pinta es la pagina publicada; quien lo sube es Claude con
# un write_db, o el agente programado.
#
# Sin dependencias: urllib y json de la libreria estandar.
#
# Lo que trae:
#   1. RANGO   - ATR(20) del NQ en dolares por 1 MNQ, y donde cae ese rango
#                dentro de los ultimos 3 anos. Es el numero que toca la cuenta.
#   2. EVENTO  - si hoy hay dato que mueve la sesion (lista de abajo).
#   3. TABLERO - crudo, bono 10 anos, oro, VIX, dolar: nivel, dia y 200 sesiones.
#   4. INDICE  - donde esta el NQ respecto a su maximo y a su media de 200.
#   5. COT     - neto de los fondos apalancados en el Nasdaq (semanal, viernes).
#   6. DIRECCION - probabilidad medida de que el dia cierre al alza, en DOS
#                lecturas: contra el cierre de ayer y contra la apertura.

import json, urllib.request, urllib.parse, datetime, statistics, os, sys, zoneinfo

AQUI = os.path.dirname(os.path.abspath(__file__))
MLL_TOPSTEP = 2000.0      # perdida maxima de Topstep, en tiempo real
DOLAR_POR_PUNTO_MNQ = 2.0

# ---------------------------------------------------------------- calendario
# Eventos que mueven una sesion. Hora en ET. Se amplia a mano segun salgan
# los calendarios oficiales (BLS y Reserva Federal).
EVENTOS = [
    ("2026-09-11", "08:30", "IPC de agosto", "alto"),
    ("2026-09-16", "14:00", "FOMC + proyecciones y diagrama de puntos", "maximo"),
    ("2026-10-02", "08:30", "Informe de empleo de septiembre", "alto"),
    ("2026-10-13", "08:30", "IPC de septiembre", "alto"),
    ("2026-10-28", "14:00", "FOMC", "maximo"),
    ("2026-11-03", "-----", "Elecciones de medio termino", "alto"),
    ("2026-11-06", "08:30", "Informe de empleo de octubre", "alto"),
    ("2026-12-09", "14:00", "FOMC + proyecciones y diagrama de puntos", "maximo"),
]


def bajar(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)


_CACHE = {}


def yahoo_cache(simbolo, rango="2y"):
    """Igual que yahoo() pero sin bajar dos veces la misma serie. El bloque de
    contexto y el tablero de siempre comparten simbolos; sin esto se pedirian
    por duplicado."""
    k = (simbolo, rango)
    if k not in _CACHE:
        _CACHE[k] = yahoo(simbolo, rango)
    return _CACHE[k]


def yahoo(simbolo, rango="3y"):
    """Devuelve [(fecha, o, h, l, c)] ordenado."""
    d = bajar("https://query1.finance.yahoo.com/v8/finance/chart/"
              "%s?range=%s&interval=1d" % (simbolo, rango))["chart"]["result"][0]
    q = d["indicators"]["quote"][0]
    filas = []
    for t, o, h, l, c in zip(d["timestamp"], q["open"], q["high"], q["low"], q["close"]):
        if None in (o, h, l, c):
            continue
        f = datetime.datetime.fromtimestamp(t, datetime.UTC).date()
        filas.append((f, o, h, l, c))
    return filas


def ultimo_cierre_completo():
    """El indice al contado solo imprime sesiones cerradas. Sirve de corte para
    descartar la sesion en curso del futuro, que traia el ATR hacia abajo."""
    return yahoo("%5ENDX", "1mo")[-1][0]


def media(v):
    return sum(v) / len(v)


def pct_en_distribucion(valor, muestra):
    return sum(1 for x in muestra if x <= valor) / len(muestra) * 100


# ------------------------------------------------------------------- 1. RANGO
def bloque_rango(corte):
    nq = [x for x in yahoo("NQ%3DF", "5y") if x[0] <= corte]
    tr = []
    for i in range(1, len(nq)):
        _, _, h, l, _ = nq[i]
        cprev = nq[i - 1][4]
        tr.append(max(h - l, abs(h - cprev), abs(l - cprev)))
    atr20 = media(tr[-20:])
    atr20_d = atr20 * DOLAR_POR_PUNTO_MNQ

    # serie de ATR(20) de los ultimos 3 anos, para situar el de hoy
    serie = [media(tr[i - 20:i]) for i in range(20, len(tr) + 1)]
    ref = serie[-756:] if len(serie) >= 756 else serie
    pct = pct_en_distribucion(atr20, ref)

    if pct < 33:    etiqueta, nota = "BAJO", "rango comprimido"
    elif pct < 66:  etiqueta, nota = "NORMAL", "rango corriente"
    elif pct < 90:  etiqueta, nota = "ALTO", "rango ancho, el stop de siempre se queda corto"
    else:           etiqueta, nota = "EXTREMO", "rango de los peores dias de los ultimos 3 anos"

    # cuantos de los ultimos 60 dias tuvieron rango mayor que el MLL de Topstep
    rangos_d = [(h - l) * DOLAR_POR_PUNTO_MNQ for _, _, h, l, _ in nq[-60:]]
    supera = sum(1 for x in rangos_d if x > MLL_TOPSTEP) / len(rangos_d) * 100

    return {
        "atr20_puntos": round(atr20, 1),
        "atr20_dolares_mnq": round(atr20_d),
        "pct_historico": round(pct),
        "etiqueta": etiqueta,
        "nota": nota,
        "pct_del_mll": round(atr20_d / MLL_TOPSTEP * 100),
        "dias60_rango_mayor_que_mll": round(supera, 1),
        "rango_medio_60d": round(media(rangos_d)),
    }


# ------------------------------------------------------------------ 2. EVENTO
# 23-sep-2026: el PMI preliminar de las 09:45 ET disparo el bono a 10 anos al
# 5,09% y el NQ cayo 366 puntos desde la apertura. La lista de arriba no lo
# tenia, y la tarjeta dijo "hoy no hay ningun dato". Desde entonces el
# calendario sale del de Forex Factory (semana actual y siguiente). La lista de
# arriba queda de respaldo si la descarga falla, y para lo que FF no pone
# (elecciones).
# Ojo: FF marca el PMI preliminar como impacto BAJO. Por eso, ademas de los de
# impacto alto y medio, entran siempre los de LISTA_FIJA aunque vengan en bajo.
FF_URLS = ["https://nfs.faireconomy.media/ff_calendar_thisweek.json",
           "https://nfs.faireconomy.media/ff_calendar_nextweek.json"]
LISTA_FIJA = ["PMI", "ISM", "GDP", "PCE", "Retail Sales", "PPI", "CPI",
              "Non-Farm", "JOLTS", "FOMC Statement", "Federal Funds Rate",
              "FOMC Press Conference", "FOMC Meeting Minutes"]
TRADUCE = [("Flash Manufacturing PMI", "PMI manufacturero preliminar"),
           ("Flash Services PMI", "PMI de servicios preliminar"),
           ("ISM Manufacturing PMI", "ISM manufacturero"),
           ("ISM Services PMI", "ISM de servicios"),
           ("Unemployment Claims", "Peticiones de subsidio por desempleo"),
           ("Non-Farm Employment Change", "Informe de empleo (NFP)"),
           ("Core PCE Price Index", "PCE subyacente"),
           ("Core CPI", "IPC subyacente"), ("CPI", "IPC"),
           ("Core PPI", "IPP subyacente"), ("PPI", "IPP"),
           ("Advance GDP", "PIB preliminar"), ("GDP", "PIB"),
           ("Core Retail Sales", "Ventas minoristas subyacentes"),
           ("Retail Sales", "Ventas minoristas"),
           ("JOLTS Job Openings", "Vacantes JOLTS"),
           ("Federal Funds Rate", "Decision de tipos de la Fed"),
           ("FOMC Statement", "Comunicado del FOMC"),
           ("FOMC Press Conference", "Rueda de prensa de la Fed"),
           ("FOMC Meeting Minutes", "Actas del FOMC"),
           ("UoM Consumer Sentiment", "Confianza del consumidor (Michigan)"),
           ("UoM Inflation Expectations", "Expectativas de inflacion (Michigan)"),
           ("President Trump Speaks", "Habla Trump")]


def traducir(titulo):
    for en, es in TRADUCE:
        if en in titulo:
            return es + (" (revisado)" if titulo.startswith("Revised") else "")
    return titulo


def bajar_ff(url):
    """FF corta con 429 si se le pide seguido: una sola bajada por pasada y un
    reintento a los 20 s."""
    if url not in _CACHE:
        try:
            _CACHE[url] = bajar(url)
        except Exception:
            import time
            time.sleep(20)
            _CACHE[url] = bajar(url)
    return _CACHE[url]


def calendario_ff():
    """Eventos de EE.UU. de las dos semanas de FF, o None si no se pudo bajar."""
    out = []
    try:
        for url in FF_URLS:
            try:
                datos = bajar_ff(url)
            except Exception:
                if url == FF_URLS[0]:
                    raise          # sin la semana actual no vale nada
                continue           # la siguiente a veces no esta publicada
            for e in datos:
                if e.get("country") != "USD":
                    continue
                t = e.get("title", "")
                imp = e.get("impact", "")
                fijo = any(k in t for k in LISTA_FIJA)
                if imp not in ("High", "Medium") and not fijo:
                    continue
                if "Speaks" in t and "Trump" not in t and imp != "High":
                    continue       # los discursos de miembros de la Fed, fuera
                f = e["date"][:10]
                hora = e["date"][11:16]    # FF da la hora ya en ET
                peso = "alto" if imp == "High" or fijo else "medio"
                out.append((f, hora, traducir(t), peso))
    except Exception as err:
        print("calendario FF no disponible: %s" % err, file=sys.stderr)
        return None
    return out


def bloque_evento(hoy):
    ff = calendario_ff()
    if ff is None:
        lista = list(EVENTOS)
    else:
        # FF solo cubre dos semanas: mas alla (y lo que FF no pone, como las
        # elecciones) sigue saliendo de la lista a mano.
        horizonte = max((x[0] for x in ff), default=hoy.isoformat())
        lista = ff + [x for x in EVENTOS if x[0] > horizonte or x[1] == "-----"]
    vistos, prox = set(), []
    for f, hora, que, peso in lista:
        d = datetime.date.fromisoformat(f)
        if d < hoy or (f, hora, que) in vistos:
            continue
        vistos.add((f, hora, que))
        prox.append({"fecha": f, "hora": hora, "que": que, "peso": peso,
                     "dias": (d - hoy).days})
    prox.sort(key=lambda x: (x["fecha"], x["hora"]))
    hoy_hay = [p for p in prox if p["dias"] == 0]
    return {"hoy": hoy_hay, "proximos": prox[:5],
            "fuente": "manual" if ff is None else "forexfactory"}


# ----------------------------------------------------------------- 3. TABLERO
MERCADOS = [
    ("CL%3DF",      "Crudo WTI",      "$",   2),
    ("%5ETNX",      "Bono 10 anos",   "%",   2),
    ("GC%3DF",      "Oro",            "$",   0),
    ("%5EVIX",      "VIX",            "",    2),
    ("DX-Y.NYB",    "Dolar (DXY)",    "",    2),
]


def bloque_tablero():
    out = []
    for sim, nombre, unidad, dec in MERCADOS:
        try:
            v = yahoo_cache(sim, "2y")
        except Exception as e:
            out.append({"nombre": nombre, "error": str(e)})
            continue
        cierres = [c for _, _, _, _, c in v]
        ult, prev = cierres[-1], cierres[-2]
        ma200 = media(cierres[-200:]) if len(cierres) >= 200 else media(cierres)
        max1a = max(cierres[-252:])
        out.append({
            "nombre": nombre,
            "unidad": unidad,
            "nivel": round(ult, dec),
            "dia_pct": round((ult / prev - 1) * 100, 2),
            "vs_ma200_pct": round((ult / ma200 - 1) * 100, 1),
            "desde_max1a_pct": round((ult / max1a - 1) * 100, 1),
        })
    return out


# --------------------------------------------------------------- 3bis. CONTEXTO
# Todo lo gratis y sin clave que se puede mirar antes de operar, en un solo
# sitio. 25 series de la misma API de Yahoo que ya se usa: ni secretos, ni
# facturas, ni dependencias nuevas.
#
# ⛔ NINGUNA DE ESTAS CASILLAS DICE HACIA DONDE VA EL DIA, y no es un descuido.
# Medido el 14-sep-2026 sobre 2.512 sesiones, con el objetivo limpio (^NDX de
# apertura a cierre, que es la unica ventana donde lo nocturno no se puede
# colar dentro): de 21 senales probadas solo 2 cruzaron su banda de confianza,
# y por puro azar se esperaria 1,1. Es ruido.
#
# 🔴 El aviso que costo el susto: la barra diaria de NQ=F ABRE A LAS 18:00 ET
# DEL DIA ANTERIOR. Medir "cierre > apertura" sobre ella mete toda la noche
# dentro de la ventana, y entonces las bolsas asiaticas (que cierran entre las
# 02:00 y las 04:00 ET) parecen predecir con +13 puntos lo que en realidad ya
# estan viendo. Con ^NDX ese mismo Nikkei se queda en -1,9. Para cualquier
# medicion direccional, el objetivo es ^NDX, nunca NQ=F.
CONTEXTO = [
    ("%5EN225",     "Nikkei",          "bolsas fuera de EEUU", 0),
    ("%5EHSI",      "Hang Seng",       "bolsas fuera de EEUU", 0),
    ("000001.SS",   "Shanghai",        "bolsas fuera de EEUU", 0),
    ("%5EKS11",     "Corea (KOSPI)",   "bolsas fuera de EEUU", 0),
    ("%5EGDAXI",    "DAX",             "bolsas fuera de EEUU", 0),
    ("%5EFTSE",     "FTSE 100",        "bolsas fuera de EEUU", 0),
    ("%5ESTOXX50E", "Euro Stoxx 50",   "bolsas fuera de EEUU", 0),
    ("ES%3DF",      "Futuro SP500",    "futuros de EEUU",      0),
    ("YM%3DF",      "Futuro Dow",      "futuros de EEUU",      0),
    ("RTY%3DF",     "Futuro Russell",  "futuros de EEUU",      0),
    ("%5EVIX",      "VIX",             "volatilidad",          2),
    ("%5EVIX9D",    "VIX 9 dias",      "volatilidad",          2),
    ("%5EVIX3M",    "VIX 3 meses",     "volatilidad",          2),
    ("%5EVVIX",     "VVIX",            "volatilidad",          1),
    ("%5ESKEW",     "SKEW",            "volatilidad",          1),
    ("%5ETNX",      "Bono 10 anos",    "tipos",                2),
    ("%5EIRX",      "Letra 3 meses",   "tipos",                2),
    ("ZN%3DF",      "Futuro bono 10a", "tipos",                2),
    ("DX-Y.NYB",    "Dolar (DXY)",     "divisas",              2),
    ("EURUSD%3DX",  "Euro",            "divisas",              4),
    ("JPY%3DX",     "Yen",             "divisas",              2),
    ("GC%3DF",      "Oro",             "materias primas",      0),
    ("CL%3DF",      "Crudo WTI",       "materias primas",      2),
    ("HG%3DF",      "Cobre",           "materias primas",      3),
    ("BTC-USD",     "Bitcoin",         "cripto",               0),
]


def bloque_contexto():
    out = []
    for sim, nombre, familia, dec in CONTEXTO:
        try:
            v = yahoo_cache(sim, "2y")
        except Exception as e:
            out.append({"nombre": nombre, "familia": familia, "error": str(e)})
            continue
        c = [x[4] for x in v]
        if len(c) < 30:
            out.append({"nombre": nombre, "familia": familia, "error": "serie corta"})
            continue
        ult, prev = c[-1], c[-2]
        ma200 = media(c[-200:]) if len(c) >= 200 else media(c)
        ref = c[-252:] if len(c) >= 252 else c
        out.append({
            "nombre": nombre,
            "familia": familia,
            "fecha": v[-1][0].isoformat(),
            "nivel": round(ult, dec),
            "dia_pct": round((ult / prev - 1) * 100, 2),
            "pct_52s": round(pct_en_distribucion(ult, ref)),
            "vs_ma200_pct": round((ult / ma200 - 1) * 100, 1),
        })
    return out


# ------------------------------------------------------------------ 4. INDICE
def bloque_indice():
    v = yahoo("%5ENDX", "2y")
    c = [x[4] for x in v]
    ult, prev = c[-1], c[-2]
    ma200 = media(c[-200:])
    mx = max(c[-252:])
    i_mx = len(c) - 1 - c[::-1].index(mx)
    return {
        "nivel": round(ult),
        "fecha": v[-1][0].isoformat(),
        "dia_pct": round((ult / prev - 1) * 100, 2),
        "ano_pct": round((ult / c[-252] - 1) * 100, 1),
        "vs_ma200_pct": round((ult / ma200 - 1) * 100, 1),
        "desde_max_pct": round((ult / mx - 1) * 100, 1),
        "fecha_max": v[i_mx][0].isoformat(),
    }


# --------------------------------------------------------------------- 5. COT
def bloque_cot():
    url = ("https://publicreporting.cftc.gov/resource/gpe5-46if.json"
           "?$where=contract_market_name='NASDAQ-100 Consolidated'"
           "&$select=report_date_as_yyyy_mm_dd,lev_money_positions_long,"
           "lev_money_positions_short,open_interest_all"
           "&$order=report_date_as_yyyy_mm_dd DESC&$limit=160")
    d = bajar(urllib.parse.quote(url, safe=":/?&=$',"))
    filas = [{
        "fecha": r["report_date_as_yyyy_mm_dd"][:10],
        "neto": int(r["lev_money_positions_long"]) - int(r["lev_money_positions_short"]),
        "largo": int(r["lev_money_positions_long"]),
        "corto": int(r["lev_money_positions_short"]),
    } for r in d]
    hist = [f["neto"] for f in filas]
    return {
        "fecha": filas[0]["fecha"],
        "neto": filas[0]["neto"],
        "largo": filas[0]["largo"],
        "corto": filas[0]["corto"],
        "cambio_semana": filas[0]["neto"] - filas[1]["neto"],
        "pct_3anos": round(pct_en_distribucion(filas[0]["neto"], hist)),
        "min_3anos": min(hist),
        "max_3anos": max(hist),
    }



# --------------------------------------------------------------- 6. DIRECCION
# Probabilidad direccional del dia, medida, no opinada.
#
# 🔴🔴 REESCRITO EL 14-SEP-2026. La version anterior tenia DOS fallos, los dos
# de la misma familia: medir sin mirar que ventana abarca cada dato.
#
#   1. Se calculaba sobre NQ=F, cuya barra DIARIA ABRE A LAS 18:00 ET DEL DIA
#      ANTERIOR. El "hueco" que salia de ahi era el reabrir de las 18:00, que
#      dura un minuto y casi siempre es cero: el 70% de las sesiones caian en
#      "sin hueco". No era el hueco de nada.
#   2. En vivo se leia el movimiento real de la noche y se puntuaba contra esa
#      tabla. Se comparaban dos cosas distintas.
#
# ✅ Ahora:
#   - La TABLA se construye sobre ^NDX (contado), que solo imprime la sesion
#     regular: hueco = apertura(hoy) / cierre(ayer). 10 anos.
#   - EN VIVO se lee el movimiento de la noche del futuro, futuro contra futuro
#     (precio de ahora / cierre del futuro a las 16:00 ET de ayer). ⛔ NUNCA
#     futuro contra contado: hoy NQ=F va 337 puntos (+1,16%) por encima de
#     ^NDX, y esa base se colaria como si fuera movimiento.
#   - Comprobado que las dos son la misma variable: correlacion 0,9705, misma
#     media (+0,065% contra +0,062%), misma desviacion, y coinciden de signo el
#     92% de las veces. Por eso vale usar 10 anos de tabla con lectura en vivo.
#
# 🔴 LA TRAMPA, y por eso van los DOS numeros:
#   "cierra por encima del cierre de ayer" con la noche subiendo fuerte sale
#   altisimo (81%), pero es casi mecanico: la subida YA esta puesta, solo hace
#   falta no devolverla. "cierra por encima de la APERTURA" es la sesion de
#   Nueva York de verdad, y ahi la noche no separa NADA: medido sobre los mismos
#   cubos sale 54,1 / 61,5 / 52,9 / 57,3 / 47,8 — sin patron.
#   El 11,4% de los dias cierran por encima de ayer HABIENDO CAIDO toda la
#   sesion. Dar solo el primer numero seria vender una ventaja que no existe.

# Los cubos describen LA NOCHE, no un "hueco" de apertura. Se renombraron el
# 14-sep-2026 junto con el arreglo: con la tabla vieja (barra de NQ=F que abria
# a las 18:00) el 70% de las sesiones caia en "sin hueco", que era la pista de
# que la variable estaba mal definida. Ahora reparten 450/371/555/552/584.
BUCKETS = [
    ("la noche viene bajando fuerte", -99.0, -0.5),
    ("la noche viene bajando poco",   -0.5,  -0.15),
    ("la noche viene plana",          -0.15,  0.15),
    ("la noche viene subiendo poco",   0.15,  0.5),
    ("la noche viene subiendo fuerte", 0.5,  99.0),
]


def movimiento_de_la_noche():
    """Cuanto lleva movido el futuro desde el cierre de ayer, FUTURO CONTRA
    FUTURO: precio de ahora contra el cierre de la barra de las 15:00 ET de
    ayer (es decir, las 16:00 ET, cuando cierra el contado).

    ⛔ No vale comparar el futuro con el cierre del CONTADO: no cotizan al
    mismo nivel (hoy 337 puntos de diferencia) y esa base entraria como si
    fuera movimiento."""
    d = bajar("https://query1.finance.yahoo.com/v8/finance/chart/"
              "NQ%3DF?range=5d&interval=1h")["chart"]["result"][0]
    ahora = d["meta"].get("regularMarketPrice")
    q = d["indicators"]["quote"][0]
    cierres = []
    for t, c in zip(d["timestamp"], q["close"]):
        if c is None:
            continue
        dt = datetime.datetime.fromtimestamp(t, datetime.UTC).astimezone(
            zoneinfo.ZoneInfo("America/New_York"))
        if dt.hour == 15:
            cierres.append((dt.date(), c))
    if not ahora or not cierres:
        return None, None
    hoy = datetime.datetime.now(zoneinfo.ZoneInfo("America/New_York")).date()
    previos = [c for f, c in cierres if f < hoy]
    if not previos:
        return None, None
    return ahora, previos[-1]


def bloque_direccion(corte):
    # La tabla, sobre el CONTADO: solo imprime la sesion regular, asi que la
    # noche no puede colarse dentro de la ventana que se intenta explicar.
    ndx = [x for x in yahoo("%5ENDX", "10y") if x[0] <= corte]
    cl = [x[4] for x in ndx]
    casos = []
    for i in range(1, len(ndx)):
        f, o, h, l, c = ndx[i]
        cp = cl[i - 1]
        casos.append(((o / cp - 1) * 100, c > cp, c > o))

    base_ayer = sum(1 for _, a, _ in casos if a) / len(casos) * 100
    base_apert = sum(1 for _, _, b in casos if b) / len(casos) * 100

    def banda(k, m):
        p = k / m
        return 1.96 * (p * (1 - p) / m) ** 0.5 * 100

    tabla = []
    for nombre, lo, hi in BUCKETS:
        s = [c for c in casos if lo <= c[0] < hi]
        if not s:
            continue
        ka = sum(1 for _, a, _ in s if a)
        kb = sum(1 for _, _, b in s if b)
        tabla.append({
            "bucket": nombre, "n": len(s),
            "p_vs_ayer": round(ka / len(s) * 100, 1),
            "ic_vs_ayer": round(banda(ka, len(s)), 1),
            "p_vs_apertura": round(kb / len(s) * 100, 1),
            "ic_vs_apertura": round(banda(kb, len(s)), 1),
        })

    # donde estamos AHORA
    hueco = None
    actual = None
    try:
        px, prev = movimiento_de_la_noche()
        if px and prev:
            hueco = round((px / prev - 1) * 100, 2)
            for i, (nombre, lo, hi) in enumerate(BUCKETS):
                if lo <= hueco < hi:
                    actual = tabla[i]
                    break
    except Exception:
        pass

    return {
        "muestra": len(casos),
        "desde": ndx[0][0].isoformat(),
        "base_vs_ayer": round(base_ayer, 1),
        "base_vs_apertura": round(base_apert, 1),
        "hueco_ahora_pct": hueco,
        "actual": actual,
        "tabla": tabla,
        "aviso": ("El primero cuenta el movimiento de la noche, que ya esta "
                  "puesto. El segundo es la sesion de Nueva York y no se mueve "
                  "del ~54% haga lo que haga la noche."),
    }


def main():
    hoy = datetime.date.today()
    corte = ultimo_cierre_completo()
    datos = {
        "actualizado": datetime.datetime.now().isoformat(timespec="minutes"),
        "fecha": hoy.isoformat(),
        "ultimo_cierre": corte.isoformat(),
        "rango": bloque_rango(corte),
        "evento": bloque_evento(hoy),
        "tablero": bloque_tablero(),
        "contexto": bloque_contexto(),
        "indice": bloque_indice(),
        "cot": bloque_cot(),
        "direccion": bloque_direccion(corte),
    }
    destino = os.path.join(AQUI, "tablero.json")
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    print(json.dumps(datos, ensure_ascii=False))
    print("\n-> escrito en %s" % destino, file=sys.stderr)


if __name__ == "__main__":
    main()
