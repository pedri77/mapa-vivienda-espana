#!/usr/bin/env python3
"""Recolecta noticias sobre vivienda desde RSS públicos y genera:

- data/noticias.json   histórico de noticias (ventana de RETENTION_DAYS)
- data/medios.json     volumen y tendencia de cobertura por medio
- data/senales.json    menciones de acampadas agrupadas por ciudad

Solo usa la librería estándar para que el workflow de GitHub Actions
no necesite instalar nada.
"""
from __future__ import annotations

import email.utils
import hashlib
import html
import json
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CONFIG = json.loads((ROOT / "scripts" / "config.json").read_text(encoding="utf-8"))

RETENTION_DAYS = CONFIG.get("retention_days", 120)
MAX_ITEMS = CONFIG.get("max_items", 5000)
TIMEOUT = 20
UA = "Mozilla/5.0 (compatible; mapa-vivienda-espana/1.0; +https://github.com/pedri77/mapa-vivienda-espana)"

GNEWS = "https://news.google.com/rss/search?q={q}&hl=es&gl=ES&ceid=ES:es"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def fetch(url: str) -> bytes | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read()
    except Exception as e:  # red caída o feed roto: se sigue con el resto
        print(f"WARN {url}: {e}", file=sys.stderr)
        return None


def parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        d = email.utils.parsedate_to_datetime(s)
        return d.astimezone(timezone.utc) if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", s or "")).strip()


def domain_of(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def outlet_key(domain: str) -> str:
    """Agrupa subdominios (p. ej. cadenaser.com y play.cadenaser.com)."""
    aliases = CONFIG.get("outlet_aliases", {})
    for d, key in aliases.items():
        if domain == d or domain.endswith("." + d):
            return key
    parts = domain.split(".")
    return ".".join(parts[-2:]) if len(parts) > 2 and parts[-2] not in ("com", "co", "org") else domain


def parse_feed(raw: bytes, via_google: bool):
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as e:
        print(f"WARN parse: {e}", file=sys.stderr)
        return
    atom = "{http://www.w3.org/2005/Atom}"
    items = root.findall(".//item") or root.findall(f".//{atom}entry")
    for it in items:
        title = strip_tags(it.findtext("title") or it.findtext(f"{atom}title") or "")
        link = it.findtext("link") or ""
        if not link:
            le = it.find(f"{atom}link")
            link = le.get("href", "") if le is not None else ""
        date = parse_date(it.findtext("pubDate") or it.findtext(f"{atom}updated") or it.findtext(f"{atom}published"))
        desc = strip_tags(it.findtext("description") or it.findtext(f"{atom}summary") or "")
        outlet, odomain = None, None
        if via_google:
            src = it.find("source")
            if src is not None:
                outlet = (src.text or "").strip()
                odomain = domain_of(src.get("url", ""))
            # Google añade " - Medio" al final del titular
            if outlet and title.endswith(" - " + outlet):
                title = title[: -len(outlet) - 3].strip()
            desc = ""  # la descripción de Google repite el titular
        else:
            odomain = domain_of(link)
        if title and link and date:
            yield {"title": title, "url": link.strip(), "date": date, "outlet": outlet,
                   "domain": odomain, "summary": desc[:400]}


def classify(text: str) -> list[str]:
    t = norm(text)
    return [topic for topic, words in CONFIG["topics"].items() if any(norm(w) in t for w in words)]


CITIES = CONFIG["cities"]  # {nombre: [lat, lng, ccaa_code]}
CITY_RE = {c: re.compile(r"\b" + re.escape(norm(c)) + r"\b") for c in CITIES}


def detect_city(text: str) -> str | None:
    t = norm(text)
    hits = [(m.start(), c) for c, rx in CITY_RE.items() if (m := rx.search(t))]
    return min(hits)[1] if hits else None


def relevant(text: str) -> bool:
    t = norm(text)
    return any(norm(w) in t for w in CONFIG["must_match_any"])


def main() -> int:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=RETENTION_DAYS)
    old_path = DATA / "noticias.json"
    store: dict[str, dict] = {}
    history_since = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    if old_path.exists():
        old = json.loads(old_path.read_text(encoding="utf-8"))
        history_since = old.get("history_since", history_since)
        for n in old.get("items", []):
            store[n["id"]] = n

    sources = [(GNEWS.format(q=urllib.parse.quote(q)), True) for q in CONFIG["google_queries"]]
    sources += [(u, False) for u in CONFIG.get("direct_feeds", [])]

    names = CONFIG.get("outlet_names", {})
    fetched = new = 0
    for url, via_google in sources:
        raw = fetch(url)
        if not raw:
            continue
        for it in parse_feed(raw, via_google):
            fetched += 1
            if it["date"] < cutoff:
                continue
            text = f'{it["title"]} {it["summary"]}'
            if not via_google and not relevant(text):
                continue
            key = outlet_key(it["domain"] or "desconocido")
            nid = hashlib.sha1(norm(it["title"]).encode()).hexdigest()[:12]
            if nid in store:
                continue
            store[nid] = {
                "id": nid,
                "title": it["title"],
                "url": it["url"],
                "date": it["date"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "outlet_key": key,
                "outlet": names.get(key) or it["outlet"] or key,
                "topics": classify(text),
                "city": detect_city(text),
            }
            new += 1

    items = [n for n in store.values() if parse_date(n["date"]) >= cutoff]
    items.sort(key=lambda n: n["date"], reverse=True)
    items = items[:MAX_ITEMS]
    stamp = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    write(old_path, {"generated_at": stamp, "history_since": history_since, "count": len(items), "items": items})
    # La tendencia semanal solo es comparable cuando hay 14 días recogidos
    has_history = now - parse_date(history_since) >= timedelta(days=14)
    write(DATA / "medios.json", build_outlets(items, now, stamp, history_since, has_history))
    write(DATA / "senales.json", build_signals(items, now, stamp))
    print(f"fetched={fetched} new={new} stored={len(items)}")
    return 0


def build_outlets(items, now, stamp, history_since, has_history):
    days = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(59, -1, -1)]
    by = defaultdict(list)
    for n in items:
        by[n["outlet_key"]].append(n)
    d7, d14, d30 = (now - timedelta(days=x) for x in (7, 14, 30))
    out = []
    for key, ns in by.items():
        dates = [parse_date(n["date"]) for n in ns]
        daily = Counter(d.strftime("%Y-%m-%d") for d in dates)
        last7 = sum(d >= d7 for d in dates)
        prev7 = sum(d14 <= d < d7 for d in dates)
        topics = Counter(t for n in ns for t in n["topics"])
        out.append({
            "key": key,
            "name": ns[0]["outlet"],
            "total": len(ns),
            "last7": last7,
            "prev7": prev7,
            "last30": sum(d >= d30 for d in dates),
            "trend": trend(last7, prev7) if has_history else None,
            "topics": dict(topics.most_common()),
            "daily": [daily.get(d, 0) for d in days],
            "latest": [{"title": n["title"], "url": n["url"], "date": n["date"]} for n in ns[:3]],
        })
    out.sort(key=lambda o: (o["last30"], o["total"]), reverse=True)
    total_daily = Counter()
    for n in items:
        total_daily[n["date"][:10]] += 1
    return {"generated_at": stamp, "history_since": history_since, "trend_ready": has_history, "days": days, "total_daily": [total_daily.get(d, 0) for d in days],
            "outlets": out}


def trend(cur: int, prev: int) -> str:
    if cur == prev:
        return "estable"
    if prev == 0:
        return "sube"
    ratio = (cur - prev) / prev
    return "sube" if ratio >= 0.25 else "baja" if ratio <= -0.25 else "estable"


def build_signals(items, now, stamp):
    """Menciones de acampadas por ciudad en los últimos 14 días.

    Es una señal automática: indica cobertura, no confirma una acampada.
    """
    since = now - timedelta(days=14)
    by = defaultdict(list)
    for n in items:
        if "acampadas" in n["topics"] and n["city"] and parse_date(n["date"]) >= since:
            by[n["city"]].append(n)
    out = []
    for city, ns in by.items():
        lat, lng, ccaa = CITIES[city]
        out.append({"city": city, "lat": lat, "lng": lng, "ccaa": ccaa, "mentions": len(ns),
                    "outlets": len({n["outlet_key"] for n in ns}),
                    "latest": [{"title": n["title"], "url": n["url"], "date": n["date"],
                                "outlet": n["outlet"]} for n in ns[:5]]})
    out.sort(key=lambda s: s["mentions"], reverse=True)
    return {"generated_at": stamp, "window_days": 14, "cities": out}


def write(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
