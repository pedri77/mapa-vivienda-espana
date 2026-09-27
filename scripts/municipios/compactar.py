#!/usr/bin/env python3
"""Convierte la salida de build_municipios.py en los ficheros ligeros de la web.

Uso: python scripts/municipios/compactar.py <carpeta con municipios.json, partidos.json y municipios.topo.json>
Genera data/municipios.json, data/partidos.json, data/municipios.topo.json y data/ccaa_vt.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
src = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "scripts" / "municipios" / "out")

mun = json.loads((src / "municipios.json").read_text(encoding="utf-8"))
periods = mun["ccaa_vt"]["periodos"]
items = {}
for code, m in mun["items"].items():
    o = {k: v for k, v in m.items() if v is not None and v is not False and k not in ("vt_series", "zt_res", "zt_boe")}
    if m.get("zt"):
        o["zt"] = 1
    s = m.get("vt_series") or {}
    if s:
        o["vt"] = [s.get(p) for p in periods]
    items[code] = o

meta = mun["fields_meta"]
out = {"generated": mun["generated"], "vt_periodos": periods, "meta": meta, "items": items}
(DATA / "municipios.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

# Partidos judiciales: población sumada y tasa por 100.000 hab.
par = json.loads((src / "partidos.json").read_text(encoding="utf-8"))
years = sorted({y for p in par["partidos"].values() for y in p["lanz"]})
pj = {}
for pid, p in par["partidos"].items():
    pob = sum(mun["items"].get(c, {}).get("pob") or 0 for c in p["municipios"])
    last = p["lanz"].get(years[-1], {})
    pj[pid] = {"n": p["n"], "pob": pob, "t": [p["lanz"].get(y, {}).get("total") for y in years],
               "lau": last.get("lau"), "hip": last.get("hipotecaria"),
               "tasa": round(last["total"] / pob * 1e5, 1) if pob and last.get("total") is not None else None}
(DATA / "partidos.json").write_text(json.dumps({"years": years, "meta": par["meta"], "partidos": pj}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

# Viviendas turísticas por CCAA para el mapa principal
cv = mun["ccaa_vt"]
(DATA / "ccaa_vt.json").write_text(json.dumps(cv, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

topo = json.loads((src / "municipios.topo.json").read_text(encoding="utf-8"))
topo["objects"] = {k: v for k, v in topo["objects"].items() if k in ("municipalities", "autonomous_regions")}
(DATA / "municipios.topo.json").write_text(json.dumps(topo, separators=(",", ":")), encoding="utf-8")
for f in ("municipios.json", "partidos.json", "ccaa_vt.json", "municipios.topo.json"):
    print(f, round((DATA / f).stat().st_size / 1e6, 2), "MB")
