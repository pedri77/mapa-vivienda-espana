#!/usr/bin/env python3
"""Construye el dataset municipal de vivienda (municipios.json, municipios.topo.json, partidos.json).

Uso:
    python3 build_municipios.py            # usa ficheros cacheados en raw/ si existen
    python3 build_municipios.py --refresh  # vuelve a descargar todo

Todas las fuentes son oficiales (INE, MIVAU, CGPJ, Ministerio de Justicia).
Dependencias: pandas, openpyxl, xlrd.
Clave: código INE de municipio de 5 dígitos (CPRO+CMUN).
"""
import csv
import datetime as dt
import difflib
import html
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.request

import openpyxl
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
os.makedirs(RAW, exist_ok=True)
REFRESH = "--refresh" in sys.argv
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"

URL = {
    "dic": "https://www.ine.es/daco/daco42/codmun/diccionario26.xlsx",
    "pob": "https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/29005.csv",
    "adrh": "https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/30824.csv",
    "vut": "https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/39363.csv",
    "vut_pct": "https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/39366.csv",
    "vut_ccaa": "https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/39364.csv",
    "vut_ccaa_pct": "https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/39365.csv",
    "serpavi": "https://cdn.mivau.gob.es/portal-web-mivau/vivienda/serpavi/2026-03_09_bd_SERPAVI_2011-2024%20-%20DEFINITIVO%20WEB_v2.xlsx",
    "tasado": "https://apps.fomento.gob.es/boletinonline2/sedal/35103500.XLS",
    "zt": "https://www.mivau.gob.es/vivienda/alquila-bien-es-tu-derecho/serpavi/consultar-zonas-de-mercado-residencial-tensionado",
    "mj_censo": "https://www.mjusticia.gob.es/es/JusticiaEspana/OrganizacionJusticia/Documents/Censo%20Judicial.xlsx",
    "lanz": "https://www.poderjudicial.es/stfls/ESTADISTICA/FICHEROS/Crisis/Lanzamientos%20por%20PJs_2013_%202025.xlsx",
    "topo": "https://cdn.jsdelivr.net/npm/es-atlas@0.6.0/es/municipalities.json",
}
FILES = {
    "dic": "diccionario26.xlsx", "pob": "t29005.csv", "adrh": "t30824.csv", "vut": "t39363.csv",
    "vut_pct": "t39366.csv", "vut_ccaa": "t39364.csv", "vut_ccaa_pct": "t39365.csv", "serpavi": "serpavi_2011_2024.xlsx", "tasado": "35103500.XLS",
    "zt": "zt.html", "mj_censo": "mj_censo.xlsx", "lanz": "lanzamientos_pj_2013_2025.xlsx",
    "topo": "es_municipalities.json",
}
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


def fetch(key):
    path = os.path.join(RAW, FILES[key])
    if os.path.exists(path) and os.path.getsize(path) > 1000 and not REFRESH:
        return path
    log(f"descargando {URL[key]}")
    try:
        req = urllib.request.Request(URL[key], headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=600) as r, open(path + ".tmp", "wb") as f:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b)
        os.replace(path + ".tmp", path)
    except Exception as e:  # la web del MIVAU bloquea clientes no navegador (403)
        if key == "zt":
            log(f"  aviso: {e}; intentando con Playwright + Chrome")
            js = (
                "import { chromium } from 'playwright';"
                "const b=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});"
                f"const p=await b.newPage({{userAgent:'{UA}'}});"
                f"await p.goto('{URL['zt']}',{{waitUntil:'networkidle',timeout:60000}});"
                f"(await import('fs')).writeFileSync('{path}',await p.content());await b.close();"
            )
            subprocess.run(["node", "--input-type=module", "-e", js], check=True, cwd=HERE)
        elif os.path.exists(path):
            log(f"  aviso: fallo descarga ({e}); se usa copia cacheada")
        else:
            raise
    return path


def norm(s):
    s = unicodedata.normalize("NFD", str(s).lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("’", "'").replace("`", "'")
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


ARTS = ["el", "la", "los", "las", "l'", "els", "les", "o", "a", "os", "as", "lo", "sa", "es", "ses"]


def _art_variants(p):
    out = {norm(p)}
    m = re.match(r"^(.*),\s*(el|la|los|las|l'|els|les|o|a|os|as|lo|sa|es|ses)$", p, flags=re.I)
    if m:
        base, art = m.group(1), m.group(2)
        out.add(norm(base))
        out.add(norm(f"{art}{'' if art.endswith(chr(39)) else ' '}{base}"))
        out.add(norm(f"{base} ({art})"))
    return out


def aliases(name, tier=None):
    """Variantes normalizadas de un nombre ("Rozas de Madrid, Las", "Aldea, L'", "Donostia/San Sebastián").

    tier 1: nombre completo (con variantes de artículo); tier 2: partes de nombres bilingües (/ o -)."""
    t1 = _art_variants(name.strip())
    t2 = set()
    for p in re.split(r"\s*/\s*", name):
        t2 |= _art_variants(p.strip())
        if "-" in p and len(p.split("-")) == 2:
            for q in p.split("-"):
                if len(q.strip()) > 3:
                    t2 |= _art_variants(q.strip())
    t2 -= t1
    if tier == 1:
        return {a for a in t1 if a}
    if tier == 2:
        return {a for a in t2 if a}
    return {a for a in t1 | t2 if a}


def num(s):
    """Convierte cadenas INE ('1.234,5', '..', '') a float o None."""
    s = (s or "").strip().strip('"')
    if s in ("", "..", ".", "-"):
        return None
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def r(x, nd=0):
    if x is None or (isinstance(x, float) and x != x):
        return None
    return int(round(x)) if nd == 0 else round(float(x), nd)


# ---------------------------------------------------------------- 1. municipios INE
def load_dic():
    d = pd.read_excel(fetch("dic"), header=1, dtype=str)
    items = {}
    for _, row in d.iterrows():
        if pd.isna(row["CPRO"]):
            continue
        code = row["CPRO"].zfill(2) + row["CMUN"].zfill(3)
        items[code] = {"n": row["NOMBRE"].strip(), "p": row["CPRO"].zfill(2), "c": row["CODAUTO"].zfill(2)}
    log(f"diccionario INE 2026: {len(items)} municipios")
    return items


def load_pob(items):
    best = {}
    with open(fetch("pob"), encoding="utf-8-sig") as f:
        rd = csv.reader(f, delimiter=";")
        next(rd)
        for mun, sexo, per, val in rd:
            if sexo != "Total":
                continue
            code = mun[:5]
            y = int(per)
            if code not in best or y > best[code][0]:
                best[code] = (y, num(val))
    years = {y for y, _ in best.values()}
    n = 0
    for code, it in items.items():
        if code in best:
            it["pob"] = r(best[code][1])
            n += 1
    log(f"padrón: {n} municipios, años {sorted(years)[-3:]}")
    return max(years)


# ---------------------------------------------------------------- 2. SERPAVI
SERPAVI_COLS = {
    "alq_m2": "ALQM2_LV_M_VC_{y}", "alq_mes": "ALQTBID12_M_VC_{y}", "alq_n": "BI_ALVHEPCO_TVC_{y}",
    "alq_sup": "SLVM2_M_VC_{y}", "alq_m2_u": "ALQM2_LV_M_VU_{y}", "alq_mes_u": "ALQTBID12_M_VU_{y}",
    "alq_n_u": "BI_ALVHEPCO_TVU_{y}",
}


def load_serpavi(items):
    wb = openpyxl.load_workbook(fetch("serpavi"), read_only=True)
    ws = wb["Municipios"]
    rows = ws.iter_rows(values_only=True)
    hdr = list(next(rows))
    years = sorted({int(h[-2:]) for h in hdr if h and re.search(r"_\d\d$", h)})
    y = f"{years[-1]:02d}"
    idx = {k: hdr.index(v.format(y=y)) for k, v in SERPAVI_COLS.items()}
    i_code = hdr.index("CUMUN")
    n = miss = 0
    for row in rows:
        code = row[i_code]
        if code is None:
            continue
        code = str(code).zfill(5)
        vals = {k: (row[i] if isinstance(row[i], (int, float)) else None) for k, i in idx.items()}
        if all(v is None for v in vals.values()):
            continue
        if code not in items:
            miss += 1
            continue
        it = items[code]
        for k, v in vals.items():
            nd = 2 if k in ("alq_m2", "alq_m2_u") else 0
            it[k] = r(v, nd) if v is not None else None
        n += 1
    log(f"SERPAVI 20{y}: {n} municipios con algún dato; {miss} códigos sin correspondencia INE 2026")
    return 2000 + int(y)


# ---------------------------------------------------------------- 3. ADRH
def load_adrh(items):
    want = {"Renta neta media por hogar": "renta_hogar", "Renta neta media por persona": "renta_persona"}
    data = {}
    with open(fetch("adrh"), encoding="utf-8-sig") as f:
        next(f)
        for line in f:
            p = line.rstrip("\n").split(";")
            if p[1] or p[2] or p[3] not in want:
                continue
            data.setdefault(p[0][:5], {}).setdefault(int(p[4]), {})[want[p[3]]] = num(p[5])
    year = max(y for d in data.values() for y in d)
    n = 0
    for code, d in data.items():
        if code in items and year in d:
            v = d[year]
            items[code]["renta_hogar"] = r(v.get("renta_hogar"))
            items[code]["renta_persona"] = r(v.get("renta_persona"))
            if v.get("renta_hogar") is not None:
                n += 1
    log(f"ADRH {year}: {n} municipios con renta por hogar")
    return year


# ---------------------------------------------------------------- 6. Viviendas turísticas + nombres de provincias
def pl(per):  # '2026M05' -> '2026-05'
    return f"{per[:4]}-{per[5:]}"


def prev_year(per):
    return f"{int(per[:4]) - 1}M{per[5:]}"


def var(a, b):
    return round((a / b - 1) * 100, 1) if a is not None and b else None


def read_vt(key, level):
    """Devuelve {(código, periodo): {var: valor}} y nombres. level: 'mun' o 'ccaa'."""
    vals, names = {}, {}
    with open(fetch(key), encoding="utf-8-sig") as f:
        rd = csv.reader(f, delimiter=";")
        hdr = next(rd)
        has_mun = "Municipios" in hdr
        has_var = "Viviendas y plazas" in hdr
        for row in rd:
            tn, ca, pr = row[0], row[1], row[2]
            mun = row[3] if has_mun else ""
            varn = row[-3] if has_var else "pct"
            per, val = row[-2], row[-1]
            if level == "mun":
                if pr and not mun:
                    names[pr[:2]] = pr[3:]
                if not mun:
                    continue
                code = mun[:5]
            else:
                if pr or mun:
                    continue
                code = ca[:2] if ca else "00"
                names[code] = ca[3:] if ca else "Total Nacional"
            vals.setdefault((code, per), {})[varn] = num(val)
    return vals, names


def load_vut(items):
    vals, provn = read_vt("vut", "mun")
    pct, _ = read_vt("vut_pct", "mun")
    periods = sorted({p for _, p in vals})
    last = periods[-1]
    py = prev_year(last)
    n = 0
    for code, it in items.items():
        v = vals.get((code, last))
        if not v:
            continue
        it["vut"] = r(v.get("Viviendas turísticas"))
        it["vut_plazas"] = r(v.get("Plazas"))
        it["vut_pct"] = r(pct.get((code, last), {}).get("pct"), 2)
        ser = {pl(p): r(vals.get((code, p), {}).get("Viviendas turísticas")) for p in periods}
        ser = {k: x for k, x in ser.items() if x is not None}
        it["vt_series"] = ser or None
        it["vt_var_pct"] = var(it["vut"], vals.get((code, py), {}).get("Viviendas turísticas"))
        if it["vut"] is not None:
            n += 1
    log(f"Viviendas turísticas {last}: {n} municipios; periodos {periods}")
    # agregado CCAA (tablas 39364 y 39365)
    cv, cn = read_vt("vut_ccaa", "ccaa")
    cp, _ = read_vt("vut_ccaa_pct", "ccaa")
    ccaa = {}
    for code in sorted(cn):
        g = lambda p, k="Viviendas turísticas": cv.get((code, p), {}).get(k)
        ccaa[code] = {
            "n": cn[code],
            "vut": r(g(last)), "vut_plazas": r(g(last, "Plazas")), "vut_pct": r(cp.get((code, last), {}).get("pct"), 2),
            "prev": {"periodo": pl(py), "vut": r(g(py)), "vut_plazas": r(g(py, "Plazas")),
                     "vut_pct": r(cp.get((code, py), {}).get("pct"), 2)},
            "vt_var_pct": var(g(last), g(py)),
            "vt_series": {pl(p): r(g(p)) for p in periods if g(p) is not None},
            "pct_series": {pl(p): r(cp.get((code, p), {}).get("pct"), 2) for p in periods if cp.get((code, p))},
        }
    ccaa_vt = {"periodo": pl(last), "periodo_prev": pl(py), "periodos": [pl(p) for p in periods],
               "source": "INE, Medición del número de viviendas turísticas en España (estadística experimental), tablas 39364 y 39365",
               "urls": [URL["vut_ccaa"], URL["vut_ccaa_pct"]], "items": ccaa}
    return last, provn, periods, ccaa_vt


# ---------------------------------------------------------------- 4. Valor tasado MIVAU
PROV_ALIAS = {"la coruna": "15", "santa cruz de": "38", "tenerife": "38", "illes balears": "07", "asturias": "33",
              "cantabria": "39", "valladodid": "47", "araba alava": "01", "alicante": "03", "las palmas": "35",
              "castellon castello": "12", "valencia": "46", "la rioja": "26", "navarra": "31", "murcia": "30"}


def build_name_index(items, prov=None, minpop=0):
    """Índice {alias: {tier: set(códigos)}}."""
    idx = {}
    for code, it in items.items():
        if prov and it["p"] != prov:
            continue
        if (it.get("pob") or 0) < minpop:
            continue
        for tier in (1, 2):
            for a in aliases(it["n"], tier):
                idx.setdefault(a, {}).setdefault(tier, set()).add(code)
    return idx


def match_name(name, idx, cutoff=0.88, hint=None):
    """Casa un nombre con el índice: primero nombre completo, luego partes bilingües, luego aproximado."""
    for qt in (1, 2):
        for it_ in (1, 2):
            cands = set()
            for a in aliases(name, qt):
                cands |= idx.get(a, {}).get(it_, set())
            if hint and len(cands) > 1:
                cands = {c for c in cands if c[:2] == hint} or cands
            if len(cands) == 1:
                return cands.pop(), "exacto"
            if len(cands) > 1:
                return None, f"ambiguo {sorted(cands)}"
    m = difflib.get_close_matches(norm(name), list(idx), n=2, cutoff=cutoff)
    if m:
        cands = set().union(*idx[m[0]].values())
        if len(cands) == 1:
            return cands.pop(), f"aprox ('{m[0]}')"
    return None, "sin coincidencia"


# Denominaciones del fichero MIVAU que no coinciden con el nombre oficial INE (verificadas a mano)
TASADO_ALIAS = {"mahon": "07032", "palma de mallorca": "07040", "santa eulalia del rio": "07054",
                "san cristobal laguna": "38023"}


def load_tasado(items, provn):
    x = pd.ExcelFile(fetch("tasado"))
    sheet = x.sheet_names[-1].strip()
    v = x.parse(x.sheet_names[-1], header=None)
    periodo = str(v.iloc[11, 1]).replace("(*)", "").strip()
    provnorm = {norm(n): c for c, n in provn.items()}
    for c, n in provn.items():
        for a in re.split(r"[/,]", n):
            provnorm.setdefault(norm(a), c)
    prov = None
    n = 0
    unmatched = []
    IDX10K = build_name_index(items, minpop=10000)
    for i in range(17, len(v)):
        p, m, tot, ntas = v.iloc[i, 1], v.iloc[i, 2], v.iloc[i, 5], v.iloc[i, 9]
        if isinstance(p, str) and p.strip():
            k = norm(p)
            prov = PROV_ALIAS.get(k) or provnorm.get(k) or prov
        if not isinstance(m, str) or not m.strip():
            continue
        try:
            tot = float(tot)
        except (TypeError, ValueError):
            tot = None
        # las etiquetas de provincia del XLS están desalineadas (celdas combinadas): se casa a nivel nacional
        # entre municipios de >= 10.000 hab. y la provincia solo se usa para desempatar
        code, how = (TASADO_ALIAS[norm(m)], "alias manual") if norm(m) in TASADO_ALIAS else match_name(m.strip(), IDX10K, hint=prov)
        if code is None:
            unmatched.append(f"{prov} {m.strip()} ({how})")
            continue
        if how != "exacto":
            log(f"  tasado: '{m.strip()}' -> {code} {items[code]['n']} [{how}]")
        items[code]["tasado_m2"] = r(tot, 1) if tot is not None else None
        try:
            items[code]["tasado_n"] = int(ntas)
        except (TypeError, ValueError):
            items[code]["tasado_n"] = None
        n += 1
    log(f"Valor tasado {sheet} ({periodo}): {n} municipios; sin casar: {unmatched}")
    return sheet, periodo, unmatched


# ---------------------------------------------------------------- 5. Zonas tensionadas
MESES = {m: i + 1 for i, m in enumerate(["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                                          "septiembre", "octubre", "noviembre", "diciembre"])}
CCAA_ZT = {"Cataluña": "09", "País Vasco": "16", "Navarra": "15", "Galicia": "12", "Asturias": "03"}


def fecha(s):
    m = re.search(r"(\d{1,2}) de (\w+) de (\d{4})", s)
    return dt.date(int(m.group(3)), MESES[m.group(2).lower()], int(m.group(1))).isoformat() if m else None


def split_top(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [t.strip() for t in out if t.strip()]


def load_zt(items):
    t = open(fetch("zt"), encoding="utf-8", errors="ignore").read()
    s = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    s = re.sub(r"\s+", " ", s)
    parts = re.split(r"Zonas de mercado residencial tensionado según (Resolución de \d+ de \w+ de \d{4})", s)
    records = []
    for i in range(1, len(parts), 2):
        res = parts[i]
        body = parts[i + 1]
        for blk in re.finditer(r"Comunidad autónoma (.+?) Municipios (.+?) Periodo de vigencia de la zona tensionada "
                               r"Desde el (.+?) hasta el (.+?) Resolución MIVAU .*?(BOE núm\. \d+, de \d+ de \w+ de \d{4})",
                               body):
            records.append({"ccaa": blk.group(1).strip(), "munis": blk.group(2).strip().rstrip("."),
                            "res": fecha(res), "desde": fecha(blk.group(3)), "hasta": fecha(blk.group(4)),
                            "boe": blk.group(5)})
    log(f"zonas tensionadas: {len(records)} bloques de resolución en la web MIVAU")
    unmatched, n_ok = [], 0
    for rec in records:
        cc = CCAA_ZT.get(rec["ccaa"])
        sub = {c: it for c, it in items.items() if it["c"] == cc}
        idx = build_name_index(sub)
        toks = split_top(re.sub(r"(^|, )i ", r"\1", rec["munis"]))
        j = 0
        code_prev = None
        while j < len(toks):
            tok = toks[j]
            # nombres oficiales con coma interna ("Castell d'Aro, Platja d'Aro i S'Agaró")
            if j + 1 < len(toks) and norm(tok + ", " + toks[j + 1]) in idx:
                tok = tok + ", " + toks[j + 1]
                j += 1
            j += 1
            if tok.startswith("excepto") and j < len(toks) + 1 and code_prev:
                items[code_prev]["zt_parcial"] = True
                items[code_prev]["zt_nota"] = tok
                continue
            nota = None
            m = re.match(r"^(.*?)\s*\((.+)\)$", tok)
            base = tok
            if m:
                base, nota = m.group(1), m.group(2)
            code, how = match_name(base, idx, cutoff=0.9)
            if code is None:
                unmatched.append(f"{rec['ccaa']}: {tok} ({how})")
                continue
            if how != "exacto":
                log(f"  zt: '{base}' -> {code} {items[code]['n']} [{how}]")
            it = items[code]
            code_prev = code
            prev = it.get("zt_res")
            if prev and prev <= rec["res"] and not it.get("zt_nota"):
                continue
            if prev and nota and it.get("zt_nota"):  # ámbitos parciales sucesivos (p. ej. Llanes)
                it["zt_nota"] += "; " + nota
                continue
            it.update({"zt": True, "zt_res": rec["res"], "zt_desde": rec["desde"], "zt_hasta": rec["hasta"],
                       "zt_boe": rec["boe"], "zt_parcial": bool(nota), "zt_nota": nota})
            n_ok += 1
    for it in items.values():
        it.setdefault("zt", False)
    n = sum(1 for it in items.values() if it["zt"])
    log(f"zonas tensionadas: {n} municipios marcados; sin casar: {unmatched}")
    return n, unmatched


# ---------------------------------------------------------------- partidos judiciales
PJ_ALIAS = {"CANGAS DE NARCEA": "33011", "MAO-MAHON": "07032", "BURGO DE OSMA-CIUDAD DE OSMA": "42043",
            "VILLAROBLEDO": "02081", "VILLAJOYOSA/VILA JOIOSA-LA": "03139",
            "SAN VICENTE DEL RASPEIG/SANT VICENT DEL RASPEIG": "03122",
            "CASTELLON DE LA PLANA/CASTELLO DE LA PLANA": "12040", "VILLARREAL/VILA-REAL": "12135",
            "CATARROJA": "46094", "MONCADA": "46171", "ESTRADA (A)": "36017", "ESTELLA/LIZARRA": "31097",
            "PAMPLONA/IRUÑA": "31201", "DONOSTIA-SAN SEBASTIAN": "20069"}


def load_partidos(items):
    c = pd.read_excel(fetch("mj_censo"), header=0, dtype=str)
    c.columns = [x.replace("\n", " ").strip() for x in c.columns]
    pj = {}
    n = 0
    c = c[c["CODM"].notna() & c["CODM PJ"].notna()]
    for _, row in c.iterrows():
        code, seat = str(row["CODM"]).zfill(5), str(row["CODM PJ"]).zfill(5)
        if code in items:
            items[code]["pj"] = seat
            n += 1
        p = pj.setdefault(seat, {"id": seat, "n": items.get(seat, {}).get("n") or row["PARTIDO"],
                                 "p": seat[:2], "municipios": [], "lanz": {}})
        if code in items:
            p["municipios"].append(code)
    log(f"partidos judiciales (MJ Censo Judicial): {len(pj)} partidos, {n} municipios asignados")
    # lanzamientos CGPJ
    l = pd.read_excel(fetch("lanz"), header=None)
    years = {}
    for j in range(1, l.shape[1]):
        v = l.iloc[5, j]
        if pd.notna(v):
            years[j] = int(v)
    byname = {norm(p["n"]): k for k, p in pj.items()}
    for k, p in pj.items():  # nombre MJ (mayúsculas) como alias
        pass
    mjnames = {}
    for _, row in c.iterrows():
        mjnames.setdefault(norm(row["PARTIDO"]), str(row["CODM PJ"]).zfill(5))
    miss = []
    for i in range(7, len(l)):
        name = l.iloc[i, 0]
        if not isinstance(name, str) or not name.strip():
            continue
        name = name.strip()
        k = PJ_ALIAS.get(name) or mjnames.get(norm(name)) or byname.get(norm(name))
        if k not in pj:
            miss.append(name)
            continue
        pj[k]["n_cgpj"] = name
        for j, y in years.items():
            vals = [l.iloc[i, j + q] for q in range(4)]
            vals = [int(x) if pd.notna(x) else None for x in vals]
            pj[k]["lanz"][str(y)] = {"total": vals[0], "hipotecaria": vals[1], "lau": vals[2], "otros": vals[3]}
    log(f"lanzamientos CGPJ: {sum(1 for p in pj.values() if p['lanz'])} partidos con datos; sin casar: {miss}")
    return pj, miss, sorted(years.values())


# ---------------------------------------------------------------- geometría
def build_topo(items):
    src = fetch("topo")
    out = os.path.join(HERE, "municipios.topo.json")
    t = json.load(open(src))
    t["objects"].pop("border", None)
    ids = {g.get("id") for g in t["objects"]["municipalities"]["geometries"]}
    json.dump(t, open(out, "w"), separators=(",", ":"))
    # simplificación opcional con mapshaper si el fichero supera 2,5 MB
    if os.path.getsize(out) > 2.5e6:
        subprocess.run(["npx", "-y", "mapshaper", out, "-simplify", "30%", "keep-shapes", "-o", out, "force"], check=True)
    missing_geo = sorted(c for c in items if c not in ids)
    extra_geo = sorted(i for i in ids if i not in items)
    log(f"TopoJSON: {len(ids)} geometrías; municipios sin geometría: {len(missing_geo)} {missing_geo[:20]}; "
        f"geometrías sin municipio INE 2026: {len(extra_geo)} {extra_geo[:20]}")
    return missing_geo, extra_geo


def main():
    items = load_dic()
    pob_year = load_pob(items)
    serpavi_year = load_serpavi(items)
    adrh_year = load_adrh(items)
    vut_period, provn, vut_periods, ccaa_vt = load_vut(items)
    tas_sheet, tas_periodo, tas_un = load_tasado(items, provn)
    zt_n, zt_un = load_zt(items)
    pj, pj_miss, lanz_years = load_partidos(items)
    # 7. derivado
    for it in items.values():
        a, h = it.get("alq_mes"), it.get("renta_hogar")
        it["esfuerzo"] = round(a * 12 / h * 100, 1) if a and h else None
    missing_geo, extra_geo = build_topo(items)

    keys = ["n", "p", "c", "pob", "alq_m2", "alq_mes", "alq_n", "alq_sup", "alq_m2_u", "alq_mes_u", "alq_n_u",
            "renta_hogar", "renta_persona", "tasado_m2", "tasado_n", "zt", "zt_res", "zt_desde", "zt_hasta",
            "zt_boe", "zt_parcial", "zt_nota", "vut", "vut_plazas", "vut_pct", "vt_var_pct", "vt_series", "esfuerzo", "pj"]
    for it in items.values():
        for k in keys:
            it.setdefault(k, None)
    items = {c: {k: items[c][k] for k in keys} for c in sorted(items)}

    vp = f"{vut_period[:4]}-{vut_period[5:]}"
    meta = {
        "n": {"source": "INE, Relación de municipios y códigos 2026", "period": "1-1-2026", "url": URL["dic"], "unit": "texto"},
        "p": {"source": "INE", "period": "2026", "url": URL["dic"], "unit": "código provincia (2 dígitos)"},
        "c": {"source": "INE", "period": "2026", "url": URL["dic"], "unit": "código CCAA INE (2 dígitos)"},
        "pob": {"source": "INE, Cifras oficiales de población (Padrón), tabla 29005", "period": f"1-1-{pob_year}", "url": URL["pob"], "unit": "habitantes"},
        "alq_m2": {"source": "MIVAU, SERPAVI (fuentes tributarias AEAT)", "period": str(serpavi_year), "url": URL["serpavi"], "unit": "€/m²/mes, mediana, vivienda colectiva"},
        "alq_mes": {"source": "MIVAU, SERPAVI", "period": str(serpavi_year), "url": URL["serpavi"], "unit": "€/mes, mediana, vivienda colectiva"},
        "alq_n": {"source": "MIVAU, SERPAVI", "period": str(serpavi_year), "url": URL["serpavi"], "unit": "nº viviendas colectivas arrendadas (vivienda habitual) en la muestra"},
        "alq_sup": {"source": "MIVAU, SERPAVI", "period": str(serpavi_year), "url": URL["serpavi"], "unit": "m², mediana superficie, vivienda colectiva"},
        "alq_m2_u": {"source": "MIVAU, SERPAVI", "period": str(serpavi_year), "url": URL["serpavi"], "unit": "€/m²/mes, mediana, vivienda unifamiliar"},
        "alq_mes_u": {"source": "MIVAU, SERPAVI", "period": str(serpavi_year), "url": URL["serpavi"], "unit": "€/mes, mediana, vivienda unifamiliar"},
        "alq_n_u": {"source": "MIVAU, SERPAVI", "period": str(serpavi_year), "url": URL["serpavi"], "unit": "nº viviendas unifamiliares arrendadas en la muestra"},
        "renta_hogar": {"source": "INE, Atlas de Distribución de Renta de los Hogares, tabla 30824", "period": str(adrh_year), "url": URL["adrh"], "unit": "€/año, renta neta media por hogar"},
        "renta_persona": {"source": "INE, ADRH, tabla 30824", "period": str(adrh_year), "url": URL["adrh"], "unit": "€/año, renta neta media por persona"},
        "tasado_m2": {"source": "MIVAU, Valor tasado de vivienda libre, municipios > 25.000 hab. (tabla 35103500)", "period": tas_periodo, "url": URL["tasado"], "unit": "€/m², total"},
        "tasado_n": {"source": "MIVAU, tabla 35103500", "period": tas_periodo, "url": URL["tasado"], "unit": "nº de tasaciones"},
        "zt": {"source": "MIVAU, Consultar zonas de mercado residencial tensionado (resoluciones BOE, art. 18 Ley 12/2023)", "period": f"a {dt.date.today().isoformat()}", "url": URL["zt"], "unit": "booleano (true si todo o parte del municipio está declarado)"},
        "zt_res": {"source": "MIVAU", "period": "", "url": URL["zt"], "unit": "fecha de la resolución de la Secretaría de Estado (ISO)"},
        "zt_desde": {"source": "MIVAU", "period": "", "url": URL["zt"], "unit": "inicio de vigencia (ISO)"},
        "zt_hasta": {"source": "MIVAU", "period": "", "url": URL["zt"], "unit": "fin de vigencia (ISO)"},
        "zt_boe": {"source": "MIVAU", "period": "", "url": URL["zt"], "unit": "referencia BOE"},
        "zt_parcial": {"source": "MIVAU", "period": "", "url": URL["zt"], "unit": "booleano: solo parte del término municipal"},
        "zt_nota": {"source": "MIVAU", "period": "", "url": URL["zt"], "unit": "ámbito declarado si es parcial"},
        "vut": {"source": "INE, Medición del número de viviendas turísticas (estadística experimental), tabla 39363", "period": vp, "url": URL["vut"], "unit": "nº viviendas turísticas"},
        "vut_plazas": {"source": "INE, tabla 39363", "period": vp, "url": URL["vut"], "unit": "plazas"},
        "vut_pct": {"source": "INE, tabla 39366", "period": vp, "url": URL["vut_pct"], "unit": "% sobre total de viviendas"},
        "vt_var_pct": {"source": "DERIVADO de INE tabla 39363", "period": f"{vp} vs {pl(prev_year(vut_period))}", "url": URL["vut"], "unit": "% variación interanual del nº de viviendas turísticas"},
        "vt_series": {"source": "INE, tabla 39363", "period": ", ".join(pl(p) for p in vut_periods), "url": URL["vut"], "unit": "{periodo AAAA-MM: nº viviendas turísticas}"},
        "esfuerzo": {"source": "DERIVADO: alq_mes × 12 / renta_hogar × 100", "period": f"alquiler {serpavi_year} / renta {adrh_year} (años distintos)", "url": None, "unit": "% de la renta neta media del hogar"},
        "pj": {"source": "Ministerio de Justicia, Censo Judicial (código INE del municipio sede del partido judicial); ver partidos.json", "period": "vigente", "url": URL["mj_censo"], "unit": "código INE municipio sede"},
    }
    out = {"generated": dt.date.today().isoformat(), "key": "código INE municipio 5 dígitos (CPRO+CMUN)",
           "fields_meta": meta, "ccaa_vt": ccaa_vt, "items": items}
    json.dump(out, open(os.path.join(HERE, "municipios.json"), "w"), ensure_ascii=False, separators=(",", ":"))

    pjout = {"generated": dt.date.today().isoformat(),
             "meta": {"mapping": {"source": "Ministerio de Justicia, Censo Judicial", "url": URL["mj_censo"]},
                      "lanz": {"source": "CGPJ, Lanzamientos practicados por partido judicial", "period": f"{lanz_years[0]}-{lanz_years[-1]}",
                               "url": URL["lanz"], "unit": "nº lanzamientos; hipotecaria = consecuencia de ejecución hipotecaria; lau = Ley de Arrendamientos Urbanos"},
                      "id": "código INE del municipio sede del partido", "unmatched_cgpj": pj_miss},
             "partidos": {k: {"n": v["n"], "n_cgpj": v.get("n_cgpj"), "p": v["p"], "municipios": sorted(v["municipios"]), "lanz": v["lanz"]}
                          for k, v in sorted(pj.items())}}
    json.dump(pjout, open(os.path.join(HERE, "partidos.json"), "w"), ensure_ascii=False, separators=(",", ":"))

    cov = {k: sum(1 for it in items.values() if it[k] is not None) for k in keys}
    cov["zt"] = sum(1 for it in items.values() if it["zt"])
    cov["zt_parcial"] = sum(1 for it in items.values() if it["zt_parcial"])
    log("cobertura:", json.dumps(cov, ensure_ascii=False))
    json.dump({"coverage": cov, "total": len(items), "tasado_unmatched": tas_un, "zt_unmatched": zt_un,
               "pj_unmatched": pj_miss, "geo_missing": missing_geo, "geo_extra": extra_geo, "log": LOG},
              open(os.path.join(HERE, "build_report.json"), "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
