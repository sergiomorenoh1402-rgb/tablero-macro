# tarjeta.py - convierte tablero.json en el mensaje corto de Telegram.
#
# Uso:   python tarjeta.py            -> lo imprime
#        python tarjeta.py --enviar   -> lo imprime y lo manda
#
# El token y el destino salen de entorno para no dejarlos escritos aqui:
#   TG_TOKEN, TG_CHAT
#
# REGLA DE ESTA TARJETA (10-sep-2026, decision suya):
#   Solo DIRECCION y EVENTO. Nada de ATR, percentiles ni margenes de error:
#   el margen se traduce a "Fiabilidad: ALTA / MEDIA / BAJA". El bloque de
#   rango se reduce a una linea, "Maximo hoy: N contratos".
#   Todo lo demas vive en la pagina, no en el movil.

import json, os, sys, urllib.request, urllib.parse, datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
PAGINA = "https://claude.ai/code/artifact/5dbc9f8c-7446-4a4e-b142-8f54590e2f77"
MLL = 2000.0

DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun",
         "jul", "ago", "sep", "oct", "nov", "dic"]


def fecha_larga(iso):
    d = datetime.date.fromisoformat(iso)
    return "%s %d-%s" % (DIAS[d.weekday()], d.day, MESES[d.month - 1])


def fiabilidad(n, ic):
    """El margen de error, dicho en palabras."""
    if n >= 250 and ic <= 6:   return "ALTA", ""
    if n >= 80 and ic <= 11:   return "MEDIA", ""
    return "BAJA", "  (solo %d casos parecidos)" % n


def tope_contratos(atr_dolares):
    """Cuantos MNQ antes de que un dia medio valga mas de la mitad del MLL.
    Devuelve (tope, % del MLL que se comeria uno mas)."""
    n = max(1, int(MLL * 0.5 // atr_dolares))
    siguiente = (n + 1) * atr_dolares / MLL * 100
    return n, round(siguiente)


def coma(x, dec=2):
    """Los decimales con coma, que es como se leen aqui."""
    return ("%%+.%df" % dec % x).replace(".", ",")


def construir(d):
    L = []
    L.append("TABLERO - " + fecha_larga(d["fecha"]))
    L.append("")

    dr = d.get("direccion") or {}
    act = dr.get("actual")
    hueco = dr.get("hueco_ahora_pct")

    if hueco is None or not act:
        L.append("Todavia no hay hueco que medir.")
        L.append("Sin lectura de direccion para hoy.")
    else:
        L.append("EL DIA VIENE %s%% DESDE EL CIERRE DE AYER" % coma(hueco))
        L.append("")
        p = act["p_vs_ayer"]
        fi, extra = fiabilidad(act["n"], act["ic_vs_ayer"])
        sesgo = "ALCISTA" if p > 55 else ("BAJISTA" if p < 45 else "SIN SESGO CLARO")
        L.append("Dias que empezaron asi:")
        L.append("   %d de cada 100 acabaron en verde" % round(p))
        L.append("   -> se inclina a %s" % sesgo)
        L.append("   Fiabilidad: %s%s" % (fi, extra))
        L.append("")
        L.append("De aqui al cierre, venga como venga:")
        L.append("   %d de cada 100 acaban en verde." % round(act["p_vs_apertura"]))
        L.append("   Es lo normal de cualquier dia.")

    ev = (d.get("evento") or {}).get("hoy") or []
    L.append("")
    if ev:
        L.append("!! HOY a las %s ET sale %s" % (ev[0]["hora"], ev[0]["que"]))
        L.append("   Es de los datos que parten la sesion.")
    else:
        prox = [x for x in (d.get("evento") or {}).get("proximos", []) if x["dias"] > 0]
        L.append("Hoy no hay ningun dato programado.")
        if prox:
            L.append("   El siguiente: %s, el %s."
                     % (prox[0]["que"], fecha_larga(prox[0]["fecha"])))

    r = d.get("rango")
    if r:
        L.append("")
        tope, sig = tope_contratos(r["atr20_dolares_mnq"])
        L.append("Maximo hoy: %d contrato%s MNQ." % (tope, "" if tope == 1 else "s"))
        L.append("   Con %d, un dia corriente se come el %d%% de tu" % (tope + 1, sig))
        L.append("   perdida maxima. Con %d se queda en la mitad." % tope)

    L.append("")
    L.append("Tablero completo: " + PAGINA)
    return "\n".join(L)


def enviar(texto):
    token, chat = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHAT")
    if not token or not chat:
        print("faltan TG_TOKEN o TG_CHAT en el entorno", file=sys.stderr)
        return False
    datos = urllib.parse.urlencode({
        "chat_id": chat, "text": texto, "disable_web_page_preview": "true"
    }).encode()
    r = urllib.request.urlopen(
        urllib.request.Request("https://api.telegram.org/bot%s/sendMessage" % token, datos),
        timeout=30)
    return json.load(r).get("ok", False)


if __name__ == "__main__":
    with open(os.path.join(AQUI, "tablero.json"), encoding="utf-8") as f:
        d = json.load(f)
    texto = construir(d)
    print(texto)
    if "--enviar" in sys.argv:
        print("\nenviado:", enviar(texto), file=sys.stderr)
