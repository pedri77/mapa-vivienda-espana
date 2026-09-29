#!/usr/bin/env python3
"""Añade a data/municipios.json los indicadores de cuentas municipales (episodio cci-08).

Campos que añade a cada municipio, solo si hay dato:
  paro, paro_1a, paro_var, paro_1k    paro registrado (SEPE)
  deuda, deuda_hab                    deuda viva del ayuntamiento (Hacienda)
  pmp                                 periodo medio de pago a proveedores (Hacienda)

Uso: python3 scripts/municipios/merge_cci08.py [--aplicar]
Sin --aplicar solo mide y dice qué cambiaría. Es idempotente: se puede repetir.
Entrada: investigacion_cci08/{paro,deuda_viva,pmp,sources}.json (los generan los fetch_*.py).
"""
import argparse
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
DATOS = RAIZ / "data/municipios.json"
INV = RAIZ / "investigacion_cci08"

# campo del JSON del municipio -> (fichero de origen, clave en ese fichero, clave en sources.json, unidad)
CAMPOS = [
    ("paro",      "paro",       "paro",        "paro",       "personas paradas registradas"),
    ("paro_1a",   "paro",       "paro_1a",     "paro",       "parados el mismo mes del año anterior"),
    ("paro_var",  "paro",       "paro_var",    "paro",       "% de variación interanual"),
    ("paro_1k",   "paro",       "paro_1k_hab", "paro",       "parados por 1.000 habitantes"),
    ("deuda",     "deuda_viva", "deuda",       "deuda_viva", "€ de deuda viva del ayuntamiento"),
    ("deuda_hab", "deuda_viva", "deuda_hab",   "deuda_viva", "€ de deuda por habitante"),
    ("pmp",       "pmp",        "pmp",         "pmp",        "días de periodo medio de pago a proveedores"),
]


def cargar(nombre):
    d = json.loads((INV / f"{nombre}.json").read_text(encoding="utf-8"))
    return d.get("items", d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true")
    a = ap.parse_args()

    muni = json.loads(DATOS.read_text(encoding="utf-8"))
    items, meta = muni["items"], muni["meta"]
    fuentes = json.loads((INV / "sources.json").read_text(encoding="utf-8"))
    origen = {n: cargar(n) for n in ("paro", "deuda_viva", "pmp")}

    cobertura = {}
    for campo, fich, clave, src, unidad in CAMPOS:
        n = 0
        pob = 0
        for code, fila in origen[fich].items():
            if code not in items or fila.get(clave) is None:
                continue
            if a.aplicar:
                items[code][campo] = fila[clave]
            n += 1
            pob += items[code].get("pob") or 0
        f = fuentes[src]
        if a.aplicar:
            meta[campo] = {"source": f["source"], "period": f["period"], "url": f["url"], "unit": unidad}
        cobertura[campo] = (n, pob)

    total_pob = sum(v.get("pob") or 0 for v in items.values())
    print(f"{'campo':10} {'municipios':>10}  {'% de los 8.132':>14}  {'% población':>11}")
    for campo, (n, pob) in cobertura.items():
        print(f"{campo:10} {n:>10}  {100*n/len(items):>13.1f}%  {100*pob/total_pob:>10.1f}%")

    if not a.aplicar:
        print("\nModo seco: no se ha escrito nada. Repite con --aplicar.")
        return
    DATOS.write_text(json.dumps(muni, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"\nEscrito {DATOS} ({DATOS.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
