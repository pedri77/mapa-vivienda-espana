#!/usr/bin/env python3
"""Actualiza automáticamente los datos que vienen de la API del INE.

- ETCL (tabla 6061): coste salarial por trabajador y mes, por CCAA   -> data/salarios.json
- EAES (tabla 28191): salario anual medio y mediano, por CCAA       -> data/salarios.json
- ETDP (tabla 6150): compraventas de vivienda, mensual nacional      -> data/precios.json
- IPV  (tabla 80270): variación anual del índice de precios, CCAA    -> data/precios.json

Solo reescribe un fichero si el periodo publicado es más reciente que el
guardado. Imprime una línea por cambio para el resumen del workflow.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
UA = "Mozilla/5.0 (compatible; mapa-vivienda-espana/1.0)"
MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

REGION = {
    "Total Nacional": "ES", "Nacional": "ES",
    "Andalucía": "01", "Aragón": "02", "Asturias, Principado de": "03", "Balears, Illes": "04", "Canarias": "05",
    "Cantabria": "06", "Castilla y León": "07", "Castilla - La Mancha": "08", "Cataluña": "09",
    "Comunitat Valenciana": "10", "Extremadura": "11", "Galicia": "12", "Madrid, Comunidad de": "13",
    "Murcia, Región de": "14", "Navarra, Comunidad Foral de": "15", "País Vasco": "16", "Rioja, La": "17",
    "Ceuta": "18", "Melilla": "19",
}


def ine(table: int, n: int = 1):
    url = f"https://servicios.ine.es/wstempus/js/ES/DATOS_TABLA/{table}?nult={n}"
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
        return json.loads(r.read())


def region_of(name: str, pos: int = 0):
    part = name.split(". ")[pos].strip()
    return REGION.get(part)


def qlabel(y, p):
    return f"{p - 18}T {y}" if 19 <= p <= 22 else str(y)


def load(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def save(name, obj):
    (DATA / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def update_etcl(sal) -> list[str]:
    rows = {}
    for s in ine(6061, 6):
        n = s["Nombre"]
        if "Industria, construcción y servicios" not in n or "Coste salarial total" not in n:
            continue
        code = region_of(n)
        pts = {(x["Anyo"], x["FK_Periodo"]): x["Valor"] for x in s["Data"]}
        if code and pts:
            y, p = max(pts)
            prev = pts.get((y - 1, p))
            rows[code] = {"mes": round(pts[(y, p)], 2), "periodo": qlabel(y, p), "key": y * 100 + p,
                          "yoy_pct": round((pts[(y, p)] / prev - 1) * 100, 1) if prev else None}
    nat = rows.get("ES")
    old = sal["national"].get("etcl", {})
    if not nat or nat["key"] <= old.get("key", 0):
        return []
    sal["national"]["etcl"] = nat
    for c in sal["ccaa"]:
        if c["code"] in rows:
            c["etcl"] = rows[c["code"]]
    return [f"ETCL actualizado a {nat['periodo']}: {nat['mes']} €/mes ({nat['yoy_pct']:+}%)"]


def update_eaes(sal) -> list[str]:
    vals, year = {}, None
    for s in ine(28191, 1):
        n = s["Nombre"]
        if not n.startswith("Ambos sexos") or "Dato base" not in n:
            continue
        kind = "media" if n.rstrip(". ").endswith("Media") else "mediana" if n.rstrip(". ").endswith("Mediana") else None
        code = region_of(n, 1)
        if kind and code and s["Data"]:
            vals.setdefault(code, {})[kind] = round(s["Data"][0]["Valor"], 2)
            year = s["Data"][0]["Anyo"]
    if not year or year <= sal.get("year", 0):
        return []
    sal["year"] = year
    sal["national"].update({k: v for k, v in vals.get("ES", {}).items()})
    for c in sal["ccaa"]:
        if c["code"] in vals:
            c.update(vals[c["code"]])
    return [f"EAES actualizada a {year}: media {sal['national'].get('media')} €, mediana {sal['national'].get('mediana')} €"]


def update_etdp(pre) -> list[str]:
    serie = next((s for s in ine(6150, 30) if s["Nombre"].startswith("Total Nacional. General. Compraventa")), None)
    if not serie:
        return []
    by_year = {}
    for x in serie["Data"]:
        by_year.setdefault(x["Anyo"], {})[x["FK_Periodo"]] = x["Valor"]
    comp = pre["national"].setdefault("compraventas_viviendas_ine_etdp", {})
    last_y = max(by_year)
    last_m = max(by_year[last_y])
    ytd_key = f"{last_y}_ene-{MONTHS[last_m - 1]}"
    if ytd_key in comp or (str(last_y) in comp and last_m == 12):
        return []
    for k in [k for k in comp if "_ene-" in k]:
        del comp[k]
    for y, months in by_year.items():
        if len(months) == 12:
            comp[str(y)] = int(sum(months.values()))
    if last_m < 12:
        comp[ytd_key] = int(sum(by_year[last_y].values()))
    pre["national"]["compraventas_ultimo_mes"] = {"periodo": f"{MONTHS[last_m - 1]} {last_y}", "valor": int(by_year[last_y][last_m])}
    return [f"Compraventas actualizadas hasta {MONTHS[last_m - 1]} {last_y}"]


def update_ipv(pre) -> list[str]:
    rows = {}
    for s in ine(80270, 1):
        n = s["Nombre"]
        if ". General. Variación anual" not in n or not s["Data"]:
            continue
        code = region_of(n)
        x = s["Data"][0]
        if code:
            rows[code] = {"periodo": qlabel(x["Anyo"], x["FK_Periodo"]), "var_anual": x["Valor"], "key": x["Anyo"] * 100 + x["FK_Periodo"]}
    nat = rows.get("ES")
    if not nat or nat["key"] <= pre["national"].get("ipv_latest", {}).get("key", 0):
        return []
    pre["national"]["ipv_latest"] = nat
    for c in pre["ccaa"]:
        if c["code"] in rows:
            c["ipv_latest"] = rows[c["code"]]
    return [f"IPV actualizado a {nat['periodo']}: {nat['var_anual']:+}% anual"]


def main() -> int:
    sal, pre = load("salarios"), load("precios")
    changes = []
    for fn, obj in ((update_etcl, sal), (update_eaes, sal), (update_etdp, pre), (update_ipv, pre)):
        try:
            changes += fn(obj)
        except Exception as e:  # una tabla caída no bloquea el resto
            print(f"WARN {fn.__name__}: {e}", file=sys.stderr)
    if changes:
        save("salarios", sal)
        save("precios", pre)
    for c in changes:
        print(c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
