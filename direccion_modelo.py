# direccion_modelo.py - investigacion, NO produccion.
#
# Objetivo de Sergio, textual: "nunca se va a estar 100 seguro de la direccion,
# solo quiero q se haga un analisis macro para saber x porcentaje la direccion
# del dia, NO para buscar trades en base a eso, sino para conocer".
#
# Eso cambia la vara de medir. Si no se opera con el numero, da igual que gane
# dinero: lo unico que importa es que el numero SEA VERDAD. Es decir,
# CALIBRACION: que de los dias en los que diga 60%, acaben verdes ~60.
# La metrica principal aqui es el Brier score, no el acierto ni el beneficio.
#
# ---------------------------------------------------------------------------
# OBJETIVO: ^NDX cierra hoy por encima del cierre de ayer.
#   Se usa ^NDX (contado) y no NQ=F a proposito: la barra diaria del futuro
#   ABRE A LAS 18:00 ET DEL DIA ANTERIOR, asi que cualquier señal nocturna cae
#   DENTRO de su ventana y aparenta predecir lo que en realidad ya esta viendo.
#
# MOMENTO DE LA LECTURA: la tarjeta sale a las 06:23 de Las Vegas = 09:23 ET,
#   siete minutos antes de que abra el contado. Todo lo que entra tiene que
#   conocerse a esa hora:
#     - hueco      : apertura de ^NDX contra el cierre de ayer. En vivo se lee
#                    con el futuro a las 09:23; en historico se aproxima con la
#                    apertura del contado, siete minutos despues. ⚠️ Es una
#                    aproximacion, y es el supuesto mas discutible del fichero.
#     - Asia       : cierre de HOY (cierran entre las 02:00 y las 04:00 ET).
#     - Europa     : HUECO de apertura de hoy (abren a las 03:00 ET). Su cierre
#                    es a las 11:30 ET y NO se puede usar.
#     - VIX, dolar : cierre de AYER.
#     - dia semana : gratis.
#
# VALIDACION: corte temporal. Se ajusta con los primeros 70% de las sesiones y
# se mide en el 30% final, que el modelo no ha visto nunca.
import json, urllib.request, urllib.parse, datetime, time, math

import numpy as np

ASIA = {"^N225", "^HSI", "000001.SS", "^KS11"}
EUROPA = {"^GDAXI", "^STOXX50E"}
AYER = {"^VIX", "DX-Y.NYB"}
AUX = sorted(ASIA | EUROPA | AYER)


def bajar(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return json.load(urllib.request.urlopen(r, timeout=45))


def oc(sim, rango="10y"):
    d = bajar("https://query1.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=1d"
              % (urllib.parse.quote(sim, safe=""), rango))["chart"]["result"][0]
    q = d["indicators"]["quote"][0]
    out = {}
    for t, o, c in zip(d["timestamp"], q["open"], q["close"]):
        if o is None or c is None:
            continue
        out[datetime.datetime.fromtimestamp(t, datetime.UTC).date()] = (o, c)
    return out


print("bajando...")
ndx = oc("^NDX")
aux = {}
for s in AUX:
    aux[s] = oc(s)
    time.sleep(0.25)

fechas = sorted(ndx)


def cambio(serie, f, modo):
    ks = sorted(k for k in serie if k <= f)
    if modo == "asia":                      # cierre de hoy / cierre previo
        if len(ks) < 2 or ks[-1] != f:
            return None
        return (serie[ks[-1]][1] / serie[ks[-2]][1] - 1) * 100
    if modo == "europa":                    # hueco de apertura de hoy
        if len(ks) < 2 or ks[-1] != f:
            return None
        return (serie[ks[-1]][0] / serie[ks[-2]][1] - 1) * 100
    ks = [k for k in sorted(serie) if k < f]   # cierre de ayer / anteayer
    if len(ks) < 2:
        return None
    return (serie[ks[-1]][1] / serie[ks[-2]][1] - 1) * 100


def nivel_ayer(serie, f):
    ks = [k for k in sorted(serie) if k < f]
    return serie[ks[-1]][1] if ks else None


NOMBRES = ["hueco", "asia", "europa", "d_vix", "vix_nivel", "d_dolar", "lunes"]
X, Y, F = [], [], []
for i in range(1, len(fechas)):
    f, fp = fechas[i], fechas[i - 1]
    o, c = ndx[f]
    cp = ndx[fp][1]
    hueco = (o / cp - 1) * 100
    asia = [cambio(aux[s], f, "asia") for s in ("^N225", "^HSI", "000001.SS", "^KS11")]
    asia = [a for a in asia if a is not None]
    eur = [cambio(aux[s], f, "europa") for s in ("^GDAXI", "^STOXX50E")]
    eur = [e for e in eur if e is not None]
    dv = cambio(aux["^VIX"], f, "ayer")
    nv = nivel_ayer(aux["^VIX"], f)
    dd = cambio(aux["DX-Y.NYB"], f, "ayer")
    if not asia or not eur or dv is None or nv is None or dd is None:
        continue
    X.append([hueco, sum(asia) / len(asia), sum(eur) / len(eur), dv, nv, dd,
              1.0 if f.weekday() == 0 else 0.0])
    Y.append(1.0 if c > cp else 0.0)
    F.append(f)

X = np.array(X)
Y = np.array(Y)
print("muestra: %d sesiones, de %s a %s" % (len(Y), F[0], F[-1]))
print("base (dias verdes): %.1f%%\n" % (Y.mean() * 100))

corte = int(len(Y) * 0.70)
mu, sd = X[:corte].mean(0), X[:corte].std(0)     # tipificado SOLO con el tramo de ajuste
sd[sd == 0] = 1.0
Xs = (X - mu) / sd
Xtr = np.hstack([np.ones((corte, 1)), Xs[:corte]])
Xte = np.hstack([np.ones((len(Y) - corte, 1)), Xs[corte:]])
Ytr, Yte = Y[:corte], Y[corte:]


def ajustar(Xm, y, l2=1.0, pasos=4000, lr=0.08):
    w = np.zeros(Xm.shape[1])
    for _ in range(pasos):
        p = 1 / (1 + np.exp(-Xm @ w))
        g = Xm.T @ (p - y) / len(y)
        g[1:] += l2 * w[1:] / len(y)
        w -= lr * g
    return w


w = ajustar(Xtr, Ytr)
ptr = 1 / (1 + np.exp(-Xtr @ w))
pte = 1 / (1 + np.exp(-Xte @ w))


def brier(p, y):
    return float(np.mean((p - y) ** 2))


base_te = Ytr.mean()
print("=== FUERA DE MUESTRA (%d sesiones, de %s en adelante) ===" % (len(Yte), F[corte]))
print("  Brier del modelo          : %.4f" % brier(pte, Yte))
print("  Brier de decir siempre %.1f%%: %.4f" % (base_te * 100, brier(np.full_like(Yte, base_te), Yte)))
print("  acierto del modelo        : %.1f%%" % (np.mean((pte > 0.5) == (Yte > 0.5)) * 100))
print("  acierto de decir 'verde'  : %.1f%%" % (Yte.mean() * 100))

print("\n=== CALIBRACION fuera de muestra ===")
print("  %-14s %6s  %10s  %10s" % ("cubo", "n", "dice", "sale"))
bordes = [0, .45, .50, .55, .60, .65, 1.01]
for a, b in zip(bordes[:-1], bordes[1:]):
    m = (pte >= a) & (pte < b)
    if m.sum() < 15:
        continue
    print("  %-14s %6d  %9.1f%%  %9.1f%%"
          % ("%.0f-%.0f%%" % (a * 100, b * 100), m.sum(), pte[m].mean() * 100, Yte[m].mean() * 100))

print("\n=== PESOS (tipificados; signo = hacia donde empuja) ===")
for n, v in zip(NOMBRES, w[1:]):
    print("  %-12s %+.4f" % (n, v))
print("  %-12s %+.4f" % ("(constante)", w[0]))

print("\n=== APORTACION DE CADA UNO (quitarlo y ver el Brier fuera de muestra) ===")
b0 = brier(pte, Yte)
for j, n in enumerate(NOMBRES):
    idx = [0] + [k + 1 for k in range(len(NOMBRES)) if k != j]
    wj = ajustar(Xtr[:, idx], Ytr)
    pj = 1 / (1 + np.exp(-Xte[:, idx] @ wj))
    print("  sin %-12s Brier %.4f  (%+.4f)" % (n, brier(pj, Yte), brier(pj, Yte) - b0))
