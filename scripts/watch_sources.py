#!/usr/bin/env python3
"""Vigila las fuentes oficiales y registra cuándo publican un periodo nuevo.

Genera:
- data/actualizaciones.json  estado de cada fuente + historial de avisos
- data/actualizaciones.xml   feed Atom con los avisos (para suscribirse)

Si hay avisos nuevos escribe un resumen en $GITHUB_OUTPUT (clave "events")
para que el workflow abra un issue y, opcionalmente, avise por Telegram.
Además recuerda las fechas previstas de data/calendario.json cuando llegan.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CHECKS = json.loads((ROOT / "scripts" / "watch.json").read_text(encoding="utf-8"))["checks"]
STATE_PATH = DATA / "actualizaciones.json"
FEED_PATH = DATA / "actualizaciones.xml"
SITE = "https://pedri77.github.io/mapa-vivienda-espana/"
UA = "Mozilla/5.0 (compatible; mapa-vivienda-espana/1.0; +https://github.com/pedri77/mapa-vivienda-espana)"
MAX_EVENTS = 200

# FK_Periodo del INE: 1-12 meses, 19-22 trimestres, 28 anual
MONTHS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
QUARTER_WORDS = {"primer": 1, "segundo": 2, "tercer": 3, "cuarto": 4}


def get(url: str, method: str = "GET"):
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method=method)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read() if method == "GET" else r.headers


def ine_period(check):
    """Último periodo de una tabla INE como (clave ordenable, etiqueta)."""
    data = json.loads(get(f"https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/{check['table']}?nult=1"))
    best = None
    for serie in data:
        for x in serie.get("Data", []):
            y, p = x.get("Anyo"), x.get("FK_Periodo")
            if y is None or p is None:
                continue
            key = y * 100 + p
            if best is None or key > best[0]:
                best = (key, y, p)
    if not best:
        return None
    _, y, p = best
    if check.get("label_fmt"):
        label = check["label_fmt"].format(y=y, p=p)
    elif 1 <= p <= 12:
        label = f"{MONTHS[p - 1]} {y}"
    elif 19 <= p <= 22:
        label = f"{p - 18}T {y}"
    else:
        label = str(y)
    return f"{best[0]}", label


def page_period(check):
    """Trimestre o año más reciente enlazado en la página (CGPJ)."""
    html = get(check["url"]).decode("utf-8", "replace")
    found = []
    for word, year in re.findall(r"(Primer|Segundo|Tercer|Cuarto) Trimestre (20\d\d)", html, re.I):
        found.append((int(year) * 10 + QUARTER_WORDS[word.lower()], f"{QUARTER_WORDS[word.lower()]}T {year}"))
    for year in re.findall(r"Anual (20\d\d)", html):
        found.append((int(year) * 10 + 5, f"anual {year}"))
    if not found:
        return None
    key, label = max(found)
    return str(key), label


def http_modified(check):
    """Fecha (día) de última modificación del fichero.

    Se compara solo el día: el servidor del Ministerio responde desde varios
    nodos cuya hora de modificación difiere en segundos o minutos.
    """
    h = get(check["url"], method="HEAD")
    lm = h.get("Last-Modified")
    if lm:
        d = datetime.strptime(lm, "%a, %d %b %Y %H:%M:%S %Z")
        return d.strftime("%Y%m%d"), d.strftime("fichero actualizado el %d-%m-%Y")
    digest = hashlib.sha256(get(check["url"])).hexdigest()[:16]
    return digest, f"contenido {digest[:8]}"


HANDLERS = {"ine_table": ine_period, "page_period": page_period, "http_modified": http_modified}


def main() -> int:
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    today = now.strftime("%Y-%m-%d")
    state = json.loads(STATE_PATH.read_text(encoding="utf-8")) if STATE_PATH.exists() else {}
    first_run = not state
    state.setdefault("since", today)
    sources = state.setdefault("sources", {})
    events = state.setdefault("events", [])
    reminded = set(state.setdefault("reminded", []))
    new = []

    for c in CHECKS:
        s = sources.setdefault(c["id"], {"dato": c["dato"], "fuente": c["fuente"], "url": c["url"]})
        s.update({"dato": c["dato"], "fuente": c["fuente"], "url": c["url"]})
        try:
            res = HANDLERS[c["type"]](c)
        except Exception as e:  # una fuente caída no debe tumbar el resto
            s["error"] = f"{type(e).__name__}: {e}"[:200]
            s["checked_at"] = stamp
            print(f"WARN {c['id']}: {s['error']}", file=sys.stderr)
            continue
        s.pop("error", None)
        s["checked_at"] = stamp
        if not res:
            continue
        key, label = res
        prev = s.get("key")
        s["label"] = label
        if prev is None:
            s["key"], s["since"] = key, today
            continue
        if key > prev:
            s["key"], s["since"] = key, today
            new.append({"id": f"{c['id']}-{key}", "source": c["id"], "kind": "nuevo", "date": stamp,
                        "title": f"Nuevo dato: {c['dato']} ({label})", "fuente": c["fuente"], "url": c["url"],
                        "files": c.get("files", []),
                        "text": f"{c['fuente']} ha publicado {label}. Hay que actualizar {', '.join(c.get('files', []))}."})

    # Recordatorios del calendario cuando llega la fecha prevista
    cal_path = DATA / "calendario.json"
    if cal_path.exists():
        for it in json.loads(cal_path.read_text(encoding="utf-8")).get("items", []):
            m = re.match(r"\d{4}-\d{2}-\d{2}", it.get("proxima_publicacion") or "")
            d = m.group(0) if m else ""
            rid = f"cal-{it.get('id')}-{d}"
            if not d or rid in reminded:
                continue
            if d <= today:
                reminded.add(rid)
                # En la primera ejecución solo se marcan las fechas ya pasadas
                if not first_run and d >= state["since"]:
                    new.append({"id": rid, "source": it.get("id"), "kind": "previsto", "date": stamp,
                                "title": f"Publicación prevista hoy: {it.get('dato')} ({it.get('proximo_periodo', '')})",
                                "fuente": it.get("fuente"), "url": it.get("fuente_url") or it.get("calendario_url"),
                                "text": "Fecha prevista en el calendario. Comprobar si ya está publicado y actualizar la web."})

    events[:0] = sorted(new, key=lambda e: e["date"], reverse=True)
    del events[MAX_EVENTS:]
    state["reminded"] = sorted(reminded)
    state["checked_at"] = stamp
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    FEED_PATH.write_text(atom(events, stamp), encoding="utf-8")

    print(f"checks={len(CHECKS)} nuevos={len(new)}")
    out = os.environ.get("GITHUB_OUTPUT")
    if out and new:
        body = "\n".join(f"- **{e['title']}**: {e['text']} {e.get('url') or ''}" for e in new)
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"count={len(new)}\n")
            f.write(f"title={new[0]['title'] if len(new) == 1 else f'{len(new)} datos nuevos en las fuentes'}\n")
            f.write("body<<EOF_BODY\n" + body + "\nEOF_BODY\n")
    return 0


def atom(events, stamp):
    entries = "".join(
        f"""<entry><id>tag:pedri77.github.io,2026:{escape(e['id'])}</id><title>{escape(e['title'])}</title>
<updated>{e['date']}</updated><link href="{escape(e.get('url') or SITE)}"/><summary>{escape(e['text'])}</summary></entry>
""" for e in events[:50])
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Techo · Datos nuevos de vivienda</title>
<subtitle>Avisos cuando CGPJ, INE o el Ministerio de Vivienda publican datos nuevos</subtitle>
<link href="{SITE}"/><link rel="self" href="{SITE}data/actualizaciones.xml"/>
<id>{SITE}</id><updated>{stamp}</updated>
{entries}</feed>
"""


if __name__ == "__main__":
    sys.exit(main())
