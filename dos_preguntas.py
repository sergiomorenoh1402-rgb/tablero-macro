# Las DOS preguntas que se pueden llamar "cierra verde", y por que solo una
# tiene respuesta.
#
#   A) "cierra por encima de AYER"      ^NDX cierre(hoy) > cierre(ayer)
#      Incluye el movimiento de la NOCHE. Es lo que mide la tarjeta.
#
#   B) "la SESION DE NUEVA YORK sube"   ^NDX cierre(hoy) > apertura(hoy)
#      Solo de 09:30 a 16:00. La noche queda fuera.
#
# Un dia puede ser A verde y B rojo: abre arriba por la noche y luego cae toda
# la sesion, pero sigue por encima del cierre de ayer.
import json, urllib.request, urllib.parse, datetime
from zoneinfo import ZoneInfo

import numpy as np

ET = ZoneInfo("America/New_York")


def bajar(u):
    r = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    return json.load(urllib.request.urlopen(r, timeout=60))


d = bajar("https://query1.finance.yahoo.com/v8/finance/chart/%s?range=2y&interval=1d"
          % urllib.parse.quote("^NDX", safe=""))["chart"]["result"][0]
q = d["indicators"]["quote"][0]
ndx = {}
for t, o, c in zip(d["timestamp"], q["open"], q["close"]):
    if o is None or c is None:
        continue
    ndx[datetime.datetime.fromtimestamp(t, datetime.UTC).astimezone(ET).date()] = (o, c)

h = bajar("https://query1.finance.yahoo.com/v8/finance/chart/%s?range=2y&interval=1h"
          % urllib.parse.quote("NQ=F", safe=""))["chart"]["result"][0]
qh = h["indicators"]["quote"][0]
px0900 = {}
for t, o in zip(h["timestamp"], qh["open"]):
    if o is None:
        continue
    dt = datetime.datetime.fromtimestamp(t, datetime.UTC).astimezone(ET)
    if dt.hour == 9:
        px0900[dt.date()] = o

fechas = sorted(ndx)
filas = []
for i in range(1, len(fechas)):
    f, fp = fechas[i], fechas[i - 1]
    if f not in px0900:
        continue
    cp = ndx[fp][1]
    o, c = ndx[f]
    filas.append({
        "noche": (px0900[f] / cp - 1) * 100,      # lo que se ve a las 09:00 ET
        "A": c > cp,                               # por encima de ayer
        "B": c > o,                                # la sesion de NY sube
    })

A = np.array([r["A"] for r in filas], dtype=float)
B = np.array([r["B"] for r in filas], dtype=float)
n = np.array([r["noche"] for r in filas])

print("muestra: %d sesiones\n" % len(filas))
print("A) cierra por encima de AYER  : %.1f%% de los dias" % (A.mean() * 100))
print("B) la SESION DE NY sube       : %.1f%% de los dias" % (B.mean() * 100))
print("\nlos dos a la vez: %.1f%%   |   A verde pero B rojo: %.1f%% de los dias"
      % (np.mean(A * B) * 100, np.mean(A * (1 - B)) * 100))

print("\n=== segun lo que lleve movido la NOCHE (leido a las 09:00 ET) ===")
print("  %-24s %5s  %14s  %14s" % ("la noche viene...", "n", "A: sobre ayer", "B: NY sube"))
cortes = [(-99, -0.5), (-0.5, -0.15), (-0.15, 0.15), (0.15, 0.5), (0.5, 99)]
etiq = ["bajando fuerte", "bajando poco", "plana", "subiendo poco", "subiendo fuerte"]
for (lo, hi), e in zip(cortes, etiq):
    m = (n >= lo) & (n < hi)
    if m.sum() < 15:
        continue
    print("  %-24s %5d  %13.1f%%  %13.1f%%" % (e, m.sum(), A[m].mean() * 100, B[m].mean() * 100))

print("\nA = se mueve con la noche.  B = no se entera de nada.")
