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
#
# 🔴 CORREGIDO (14-sep-2026). La primera version media la noche como
#    futuro(09:00 ET) / contado(cierre de ayer). ⛔ MAL: el futuro y el contado
#    NO cotizan al mismo nivel. Hoy NQ=F 29.549,8 contra ^NDX 29.212,0, o sea
#    un +1,16% de BASE que no es movimiento de nada. Eso metia un sesgo
#    positivo en todos los dias y amontonaba 279 de 499 sesiones en el cubo
#    "subiendo fuerte". Misma familia de fallo que la barra de las 18:00.
#    ✅ Ahora la noche se mide FUTURO CONTRA FUTURO: el precio a las 09:00 ET
#    contra el cierre de la barra de las 15:00 ET de ayer (o sea, las 16:00 ET,
#    el cierre del contado). La base se cancela sola.
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
fut_0900, fut_1600 = {}, {}
for t, o, c in zip(h["timestamp"], qh["open"], qh["close"]):
    dt = datetime.datetime.fromtimestamp(t, datetime.UTC).astimezone(ET)
    if dt.hour == 9 and o is not None:
        fut_0900[dt.date()] = o          # precio a las 09:00 ET
    if dt.hour == 15 and c is not None:
        fut_1600[dt.date()] = c          # cierre de la barra 15:00-16:00 = 16:00 ET

fechas = sorted(ndx)
filas = []
for i in range(1, len(fechas)):
    f, fp = fechas[i], fechas[i - 1]
    if f not in fut_0900 or fp not in fut_1600:
        continue
    o, c = ndx[f]
    filas.append({
        "noche": (fut_0900[f] / fut_1600[fp] - 1) * 100,   # futuro contra futuro
        "A": c > ndx[fp][1],
        "B": c > o,
    })

A = np.array([r["A"] for r in filas], dtype=float)
B = np.array([r["B"] for r in filas], dtype=float)
n = np.array([r["noche"] for r in filas])

print("muestra: %d sesiones" % len(filas))
print("la noche, ahora que la base esta fuera: media %+.3f%%  mediana %+.3f%%\n"
      % (n.mean(), np.median(n)))
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
        print("  %-24s %5d  (muestra corta)" % (e, m.sum()))
        continue
    print("  %-24s %5d  %13.1f%%  %13.1f%%" % (e, m.sum(), A[m].mean() * 100, B[m].mean() * 100))
