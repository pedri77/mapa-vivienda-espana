#!/usr/bin/env python3
"""Paro registrado por municipio (SEPE).

Descarga el XLS agregado "ESTADISTICA_MUNICIPIOS.xls" del mes indicado (y del
mismo mes del año anterior para variación interanual) y lo parsea hoja a hoja
("PARO <PROVINCIA>"). Produce investigacion_cci08/paro.json:
  {codigo_ine: {"paro": int, "paro_1a": int, "paro_var": pct, "paro_1k_hab": float}}

Fuente: SEPE, "Paro registrado y contratos por municipios".
La columna 0 es el código INE de municipio a 3 dígitos; el código de provincia
se deduce del nombre de la hoja (variantes con/sin tilde y abreviaturas).
Uso: python3 fetch_paro.py [AAAA-MM]  (defecto: detecta el último mes publicado).
"""
import datetime
import json
import re
import sys
import urllib.request
from pathlib import Path

import xlrd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "investigacion_cci08"
RAW = OUT / "raw"
BASE = "https://www.sepe.es/HomeSepe/que-es-el-sepe/estadisticas/datos-estadisticos/municipios"
UA = {"User-Agent": "Mozilla/5.0 (mapa-vivienda-espana)"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# Nombre de provincia en la hoja SEPE (normalizado) -> código INE.
# Se listan variantes con/sin tilde y abreviaturas que usa el SEPE por año.
PROVINCIAS = {
    "A CORUÑA": "15", "ALBACETE": "02", "ALICANTE": "03", "ALMERÍA": "04",
    "ARABA": "01", "ASTURIAS": "33", "ÁVILA": "05", "BADAJOZ": "06",
    "BARCELONA": "08", "BIZKAIA": "48", "BURGOS": "09", "CANTABRIA": "39",
    "CASTELLÓN": "12", "CEUTA": "51", "CIUDAD REAL": "13", "CÁCERES": "10",
    "CÁDIZ": "11", "CÓRDOBA": "14", "CUENCA": "16", "GIPUZKOA": "20",
    "GIRONA": "17", "GRANADA": "18", "GUADALAJARA": "19", "HUELVA": "21",
    "HUESCA": "22", "ILLES BALEARS": "07", "JAÉN": "23", "LA RIOJA": "26",
    "LAS PALMAS": "35", "LEÓN": "24", "LLEIDA": "25", "LUGO": "27",
    "MADRID": "28", "MÁLAGA": "29", "MELILLA": "52", "MURCIA": "30",
    "NAVARRA": "31", "OURENSE": "32", "PALENCIA": "34", "PONTEVEDRA": "36",
    "SALAMANCA": "37", "TARRAGONA": "43", "TERUEL": "44", "TOLEDO": "45",
    "VALENCIA": "46", "VALLADOLID": "47", "ZAMORA": "49", "ZARAGOZA": "50",
    "SEVILLA": "41", "SEGOVIA": "40", "SORIA": "42",
    # variantes que aparecen según el año
    "ALAVA": "01", "VIZCAYA": "48", "GUIPUZCOA": "20", "GIPUZCOA": "20",
    "GERONA": "17",
    "BALEARES": "07", "A CORUNA": "15", "STA CRUZ TENERIFE": "38",
    "TENERIFE": "38", "STA CRUZ DE TENERIFE": "38",
    "STA CRUZ TENER": "38",
}
_SINTILDES = str.maketrans("ÁÉÍÓÚÜ", "AEIOUU")


def norm(s: str) -> str:
    s = s.upper().replace("TENER.", "TENERIFE").translate(_SINTILDES)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


PROV_NORM = {norm(k): v for k, v in PROVINCIAS.items()}


def prov_from_sheet(name: str) -> str | None:
    key = norm(name[5:]) if name.upper().startswith("PARO ") else norm(name)
    return PROV_NORM.get(key)


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def xls_url(year: int, month_idx: int) -> str:
    """Resuelve el enlace jcr del XLS agregado en la página del mes."""
    page = f"{BASE}/{year}/{MESES[month_idx]}.html"
    html = get(page).decode("utf-8", "replace")
    m = re.search(r'href="([^"]*ESTADISTICA_MUNICIPIOS\.xls)"', html)
    if not m:
        raise RuntimeError(f"sin enlace XLS en {page}")
    link = m.group(1)
    return link if link.startswith("http") else "https://www.sepe.es" + link


def find_latest():
    now = datetime.date.today()
    y, m = now.year, now.month - 1
    for _ in range(6):
        try:
            return y, m, xls_url(y, m)
        except Exception:
            m -= 1
            if m < 0:
                y, m = y - 1, 11
    raise RuntimeError("no se encontró ningún mes publicado")


def parse_workbook(path: Path) -> dict:
    """{codigo_ine(5): paro_total} desde las hojas 'PARO ...'."""
    book = xlrd.open_workbook(str(path))
    out = {}
    for name in book.sheet_names():
        if not name.upper().startswith("PARO"):
            continue
        prov = prov_from_sheet(name)
        if not prov:
            print(f"AVISO: hoja sin provincia reconocida: {name!r}")
            continue
        sh = book.sheet_by_name(name)
        for r in range(sh.nrows):
            row = sh.row(r)
            try:
                code = int(float(row[0].value))
            except (ValueError, TypeError, IndexError):
                continue
            # código INE sin cero inicial (8001 = 08001); exigimos nombre
            # de municipio para descartar filas de totales provinciales
            if not (1 <= code <= 99999):
                continue
            if not (isinstance(row[1].value, str) and row[1].value.strip()):
                continue
            code = f"{code:05d}"
            try:
                total = int(float(row[2].value))
            except (ValueError, TypeError, IndexError):
                continue
            out[code] = total
    return out


def main():
    OUT.mkdir(exist_ok=True)
    RAW.mkdir(exist_ok=True)
    if len(sys.argv) > 1:
        year, mi = map(int, sys.argv[1].split("-"))
        mi -= 1
        url = xls_url(year, mi)
    else:
        year, mi, url = find_latest()
    month_name = MESES[mi]
    print(f"mes actual: {month_name} {year}")

    cur_raw = RAW / f"sepe_paro_{year}{mi+1:02d}.xls"
    if not cur_raw.exists():
        cur_raw.write_bytes(get(url))
    cur = parse_workbook(cur_raw)

    prev_raw = RAW / f"sepe_paro_{year-1}{mi+1:02d}.xls"
    prev = {}
    try:
        if not prev_raw.exists():
            prev_raw.write_bytes(get(xls_url(year - 1, mi)))
        prev = parse_workbook(prev_raw)
    except Exception as e:
        print(f"AVISO: sin mes anterior ({e}); sin variación interanual")

    items = json.load(open(ROOT / "data" / "municipios.json"))["items"]
    result = {}
    matched = 0
    for code, v in items.items():
        p = cur.get(code)
        if p is None:
            continue
        matched += 1
        row = {"paro": p}
        p1 = prev.get(code)
        if p1 is not None:
            row["paro_1a"] = p1
            row["paro_var"] = round((p - p1) / p1 * 100, 1) if p1 else None
        pob = v.get("pob")
        if pob:
            row["paro_1k_hab"] = round(p / pob * 1000, 1)
        result[code] = row

    (OUT / "paro.json").write_text(json.dumps(result, ensure_ascii=False))
    (OUT / "paro_meta.json").write_text(json.dumps({
        "period": f"{month_name} {year}",
        "period_prev": f"{month_name} {year-1}" if prev else None,
        "url": f"{BASE}/{year}/{month_name}.html",
        "raw": [p.name for p in [cur_raw, prev_raw] if p.exists()],
        "matched": matched, "total_source": len(cur),
    }, ensure_ascii=False, indent=1))
    print(f"paro.json: {len(result)} municipios (fuente {len(cur)}, match {matched})")


if __name__ == "__main__":
    main()
