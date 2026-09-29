#!/usr/bin/env python3
"""Deuda viva de las Entidades Locales — Ayuntamientos (Ministerio de Hacienda).

Descarga el XLSX anual "deuda-viva-ayuntamientos-<AAA>12.xlsx" y parsea la hoja
'Datos_Format' (CA, Provincia, Municipio, Deuda en MILES de €).
Produce investigacion_cci08/deuda_viva.json:
  {codigo_ine: {"deuda": euros, "deuda_hab": euros/habitante}}

OJO: la columna de deuda viene en MILES de euros; se convierte a euros.
Uso: python3 fetch_deuda.py [AAAA]  (defecto: último ejercicio publicado en la web).
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "investigacion_cci08"
RAW = OUT / "raw"
PAGE = ("https://www.hacienda.gob.es/es-ES/cdi/paginas/"
        "sistemasfinanciaciondeuda/informacioneells/deudaviva.aspx")
UA = {"User-Agent": "Mozilla/5.0 (mapa-vivienda-espana)"}


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def latest_year() -> tuple[int, str]:
    html = get(PAGE).decode("utf-8", "replace")
    links = re.findall(r'href="(/cdi/[^"]*deuda-viva-ayuntamientos-(\d{4})12\.xlsx)"', html)
    if not links:
        raise RuntimeError("sin enlaces deuda-viva-ayuntamientos en la página")
    href, year = max(links, key=lambda x: int(x[1]))
    return int(year), "https://www.hacienda.gob.es" + href.replace(" ", "%20")


def main():
    OUT.mkdir(exist_ok=True)
    RAW.mkdir(exist_ok=True)
    if len(sys.argv) > 1:
        year = int(sys.argv[1])
        url = ("https://www.hacienda.gob.es/cdi/sist%20financiacion%20y%20deuda/"
               f"informacioneells/{year}/deuda-viva-ayuntamientos-{year}12.xlsx")
    else:
        year, url = latest_year()
    print(f"ejercicio: {year}")

    raw = RAW / f"deuda_viva_ayuntamientos_{year}.xlsx"
    if not raw.exists():
        raw.write_bytes(get(url))

    wb = openpyxl.load_workbook(raw, read_only=True)
    ws = wb["Datos_Format"]
    rows = list(ws.iter_rows(values_only=True))
    hdr = next(i for i, r in enumerate(rows) if r[1] == "Codigo Provin")
    src = {}
    for r in rows[hdr + 1:]:
        prov, mun, deuda = r[1], r[2], r[4]
        if prov is None or mun is None or deuda is None:
            continue
        try:
            code = f"{int(prov):02d}{int(mun):03d}"
            val = float(deuda) * 1000.0  # miles de € -> €
        except (TypeError, ValueError):
            continue
        src[code] = round(val)

    items = json.load(open(ROOT / "data" / "municipios.json"))["items"]
    result = {}
    matched = 0
    for code, v in items.items():
        d = src.get(code)
        if d is None:
            continue
        matched += 1
        row = {"deuda": d}
        pob = v.get("pob")
        if pob:
            row["deuda_hab"] = round(d / pob, 1)
        result[code] = row

    (OUT / "deuda_viva.json").write_text(json.dumps(result, ensure_ascii=False))
    (OUT / "deuda_viva_meta.json").write_text(json.dumps({
        "period": f"31-12-{year}",
        "url": url, "page": PAGE, "raw": raw.name,
        "unit": "euros (convertido desde miles de € del original)",
        "matched": matched, "total_source": len(src),
    }, ensure_ascii=False, indent=1))
    print(f"deuda_viva.json: {len(result)} municipios (fuente {len(src)}, match {matched})")


if __name__ == "__main__":
    main()
