# Responde al hallazgo 1 y 3 de Codex, con datos en vez de con opinion.
#
# Su objecion: direccion_modelo.py usa como señal la APERTURA del contado
# (09:30), pero la tarjeta se manda a las 09:23. Son siete minutos de
# descubrimiento de precio que en vivo no se tienen. Ademas, en vivo la señal
# seria el FUTURO, no el contado: no es la misma variable.
#
# Aqui se usa la señal que SI se puede leer a las 09:23, sin discusion posible:
# el precio del futuro NQ=F a las 09:00 ET, que es la apertura de la barra
# horaria de las 09:00. Son 23 minutos ANTES de la tarjeta, o sea que el
# modelo va con MENOS informacion de la que tendria en vivo. Si aun asi
# funciona, el resultado es un suelo, no un techo.
#
# ⚠️ Precio a pagar: las horarias de Yahoo solo llegan a 2 anos (~500 sesiones)
# contra las 2.467 del otro fichero. La muestra es mucho mas corta.
import json, urllib.request, urllib.parse, datetime, math
from zoneinfo import ZoneInfo

import numpy as np

ET = ZoneInfo("America/New_York")


def bajar(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return json.load(urllib.request.urlopen(r, timeout=60))


# --- contado: define el objetivo y el cierre de referencia -------------------
d = bajar("https://query1.finance.yahoo.com/v8/finance/chart/%s?range=2y&interval=1d"
          % urllib.parse.quote("^NDX", safe=""))["chart"]["result"][0]
q = d["indicators"]["quote"][0]
ndx = {}
for t, o, c in zip(d["timestamp"], q["open"], q["close"]):
    if o is None or c is None:
        continue
    ndx[datetime.datetime.fromtimestamp(t, datetime.UTC).astimezone(ET).date()] = (o, c)

# --- futuro por horas: la señal de las 09:00 ET ------------------------------
h = bajar("https://query1.finance.yahoo.com/v8/finance/chart/%s?range=2y&interval=1h"
          % urllib.parse.quote("NQ=F", safe=""))["chart"]["result"][0]
qh = h["indicators"]["quote"][0]
px0900 = {}
for t, o in zip(h["timestamp"], qh["open"]):
    if o is None:
        continue
    dt = datetime.datetime.fromtimestamp(t, datetime.UTC).astimezone(ET)
    if dt.hour == 9:                       # apertura de la barra 09:00-10:00 ET
        px0900[dt.date()] = o

fechas = sorted(ndx)
filas = []
for i in range(1, len(fechas)):
    f, fp = fechas[i], fechas[i - 1]
    if f not in px0900:
        continue
    cp = ndx[fp][1]                        # cierre de ayer del contado
    o, c = ndx[f]
    filas.append({
        "f": f,
        "sig_0900": (px0900[f] / cp - 1) * 100,    # lo que SI se ve a las 09:00
        "sig_0930": (o / cp - 1) * 100,            # lo que usaba el otro fichero
        "verde": 1.0 if c > cp else 0.0,
    })

print("muestra: %d sesiones, de %s a %s" % (len(filas), filas[0]["f"], filas[-1]["f"]))
print("base (dias verdes): %.1f%%" % (np.mean([r["verde"] for r in filas]) * 100))

a = np.array([r["sig_0900"] for r in filas])
b = np.array([r["sig_0930"] for r in filas])
print("\ncorrelacion entre la señal de 09:00 y la de 09:30: %.4f" % np.corrcoef(a, b)[0, 1])
print("diferencia media absoluta entre las dos: %.3f puntos porcentuales" % np.mean(np.abs(a - b)))


def evaluar(clave, etiqueta):
    X = np.array([[r[clave]] for r in filas])
    Y = np.array([r["verde"] for r in filas])
    corte = int(len(Y) * 0.70)
    mu, sd = X[:corte].mean(0), X[:corte].std(0)
    sd[sd == 0] = 1.0
    Xs = (X - mu) / sd
    Xtr = np.hstack([np.ones((corte, 1)), Xs[:corte]])
    Xte = np.hstack([np.ones((len(Y) - corte, 1)), Xs[corte:]])
    Ytr, Yte = Y[:corte], Y[corte:]
    w = np.zeros(Xtr.shape[1])
    for _ in range(6000):
        p = 1 / (1 + np.exp(-Xtr @ w))
        g = Xtr.T @ (p - Ytr) / len(Ytr)
        g[1:] += 1.0 * w[1:] / len(Ytr)
        w -= 0.08 * g
    pte = 1 / (1 + np.exp(-Xte @ w))
    br = float(np.mean((pte - Yte) ** 2))
    base = Ytr.mean()
    brb = float(np.mean((np.full_like(Yte, base) - Yte) ** 2))
    ac = float(np.mean((pte > 0.5) == (Yte > 0.5)) * 100)
    print("  %-34s Brier %.4f (base %.4f)  acierto %.1f%%  n_test=%d"
          % (etiqueta, br, brb, ac, len(Yte)))
    return pte, Yte


print("\n=== FUERA DE MUESTRA, las dos señales sobre la MISMA muestra ===")
p09, Yte = evaluar("sig_0900", "señal 09:00 ET (limpia)")
evaluar("sig_0930", "señal 09:30 ET (la que objeta Codex)")

print("\n=== CALIBRACION de la señal limpia de 09:00 ===")
print("  %-14s %6s  %10s  %10s" % ("cubo", "n", "dice", "sale"))
for lo, hi in [(0, .45), (.45, .50), (.50, .55), (.55, .60), (.60, .65), (.65, 1.01)]:
    m = (p09 >= lo) & (p09 < hi)
    if m.sum() < 10:
        continue
    print("  %-14s %6d  %9.1f%%  %9.1f%%"
          % ("%.0f-%.0f%%" % (lo * 100, hi * 100), m.sum(), p09[m].mean() * 100, Yte[m].mean() * 100))
