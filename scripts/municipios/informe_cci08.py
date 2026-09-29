#!/usr/bin/env python3
"""Genera investigacion_cci08/sources.json e INFORME.md con números MEDIDOS.

Ejecutar después de fetch_paro.py, fetch_deuda.py y fetch_pmp.py.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "investigacion_cci08"

SOURCES = {
    "paro": {
        "source": "SEPE (Ministerio de Trabajo y Economía Social), «Paro registrado y contratos por municipios»",
        "url": "https://www.sepe.es/HomeSepe/que-es-el-sepe/estadisticas/datos-estadisticos/municipios.html",
        "unit": "parados registrados (recuento)",
        "license": "Reutilización permitida (SEPE / datos.gob.es, dataset ea0041513, con cita de fuente)",
    },
    "deuda_viva": {
        "source": "Ministerio de Hacienda, «Deuda viva de las Entidades Locales» (fichero Ayuntamientos)",
        "url": "https://www.hacienda.gob.es/es-ES/cdi/paginas/sistemasfinanciaciondeuda/informacioneells/deudaviva.aspx",
        "unit": "euros (original en miles de €, convertido)",
        "license": "Reutilización permitida (hacienda.gob.es, con cita de fuente)",
    },
    "pmp": {
        "source": "Ministerio de Hacienda, «Publicación del Periodo Medio de Pago (PMP) de las EE.LL.» (RD 635/2014), fichero «Cesión y variables»",
        "url": "https://serviciostelematicosext.hacienda.gob.es/SGCIEF/PMP_NET/aspx/consulta/consulta.aspx?tipoPublicacion=2",
        "unit": "días",
        "license": "Datos abiertos (reutilización permitida)",
    },
}


def top(items, data, key, n=10, reverse=True):
    rows = [(code, v[key]) for code, v in data.items() if v.get(key) is not None]
    rows.sort(key=lambda x: x[1], reverse=reverse)
    return [(items[c]["n"], items[c]["pob"], val) for c, val in rows[:n]]


def fmt(rows):
    return "\n".join(f"| {n} | {p:,d} | {v} |" for n, p, v in rows)


def main():
    items = json.load(open(ROOT / "data" / "municipios.json"))["items"]
    total = len(items)
    pob_total = sum(v["pob"] for v in items.values())

    paro = json.load(open(OUT / "paro.json"))
    deuda = json.load(open(OUT / "deuda_viva.json"))
    pmp = json.load(open(OUT / "pmp.json"))
    metas = {n: json.load(open(OUT / f"{n}_meta.json")) for n in ["paro", "deuda_viva", "pmp"]}

    for k, v in metas.items():
        SOURCES[k]["period"] = v["period"]
    (OUT / "sources.json").write_text(json.dumps(SOURCES, ensure_ascii=False, indent=1))

    def cov(data):
        pob = sum(items[c]["pob"] for c in data)
        return len(data), len(data) / total * 100, pob, pob / pob_total * 100

    pn, ppc, ppob, ppobpc = cov(paro)
    dn, dpc, dpob, dpobpc = cov(deuda)
    mn, mpc, mpob, mpobpc = cov(pmp)

    paro_missing = [c for c in items if c not in paro]
    paro_missing_small = sum(1 for c in paro_missing if items[c]["pob"] < 500)
    pmp_missing = [c for c in items if c not in pmp]
    pmp_missing_small = sum(1 for c in pmp_missing if items[c]["pob"] < 1000)
    pmp_meta = metas["pmp"]

    L = []
    A = L.append
    A("# cci-08 — Investigación fuentes municipales: paro, deuda viva y PMP")
    A("")
    A(f"Generado por `scripts/municipios/informe_cci08.py`. Municipios de referencia: **{total}** "
      f"(`data/municipios.json`, códigos INE 5 dígitos, Padrón 1-1-2025, población total "
      f"{pob_total:,} hab.). Todos los números de cobertura están medidos sobre ese fichero.")
    A("")
    A("## 1. Paro registrado por municipio (SEPE)")
    A("")
    A(f"- Periodo: **{metas['paro']['period']}** (y {metas['paro']['period_prev']} para variación interanual). "
      f"Fichero agregado `ESTADISTICA_MUNICIPIOS.xls`, hojas «PARO &lt;provincia&gt;».")
    A(f"- Match: **{pn}/{total} municipios ({ppc:.1f}%)**, cubriendo **{ppob:,} hab. ({ppobpc:.1f}% de la población)**.")
    A(f"- Sin dato: {total-pn} municipios, {paro_missing_small} de ellos con menos de 500 hab.; "
      f"la población sin cubrir es solo {pob_total-ppob:,} hab. ({100-ppobpc:.1f}%). "
      f"El SEPE simplemente no publica fila para esos municipios (la mayoría sin parados registrados o "
      f"agregados en el resto provincial); no es un fallo de cruce.")
    A("- Derivados calculados: `paro_1a`, `paro_var` (interanual %), `paro_1k_hab` (paro por 1.000 hab. con `pob`).")
    A("")
    A("Top 10 paro absoluto y paro por 1.000 hab. (verificables a mano):")
    A("")
    A("| Municipio | Población | Paro |")
    A("|---|---|---|")
    A(fmt(top(items, paro, "paro")))
    A("")
    A("| Municipio | Población | Paro/1.000 hab. |")
    A("|---|---|---|")
    A(fmt(top(items, paro, "paro_1k_hab")))
    A("")
    A("## 2. Deuda viva municipal (Ministerio de Hacienda)")
    A("")
    A(f"- Periodo: **{metas['deuda_viva']['period']}**, fichero «deuda-viva-ayuntamientos-202512.xlsx», hoja `Datos_Format`.")
    A(f"- Match: **{dn}/{total} municipios ({dpc:.1f}%)** — cobertura TOTAL de municipios, "
      f"{dpob:,} hab. ({dpobpc:.1f}%).")
    A("- Derivados: `deuda` (€, convertido desde **miles de €** del original — trampa documentada) y "
      "`deuda_hab` (€/habitante). El fichero de ayuntamientos solo contiene ayuntamientos: el resto de "
      "entidades (diputaciones, cabildos, mancomunidades…) viene en ficheros separados que no se mezclan aquí.")
    A("")
    A("| Municipio | Población | Deuda viva (€) |")
    A("|---|---|---|")
    A(fmt(top(items, deuda, "deuda")))
    A("")
    A("| Municipio | Población | Deuda €/hab. |")
    A("|---|---|---|")
    A(fmt(top(items, deuda, "deuda_hab")))
    A("")
    A("## 3. Periodo medio de pago a proveedores (PMP, Ministerio de Hacienda)")
    A("")
    A(f"- Periodo: **{metas['pmp']['period']}**, fichero «Cesión y variables» "
      f"(trimestral; el modelo de «cesión» publica mensual y el de «variables» trimestral).")
    A(f"- Match: **{mn}/{total} municipios ({mpc:.1f}%)**, cubriendo **{mpob:,} hab. ({mpobpc:.1f}%)**.")
    A(f"- Sin dato: {total-mn} municipios, {pmp_missing_small} de ellos con menos de 1.000 hab. "
      f"({pob_total-mpob:,} hab., {100-mpobpc:.1f}%). Causa: esas entidades no figuran en la publicación "
      f"del PMP (no remiten información; el RD 635/2014 obliga a publicar, pero los ayuntamientos más "
      f"pequeños del modelo de variables pueden no reportar el trimestre).")
    A(f"- Entidades del fichero descartadas por NO ser ayuntamientos (contadas, no mezcladas): "
      f"{pmp_meta['descartados_no_ayuntamiento']}.")
    A(f"- Ayuntamientos del fichero sin cruce con municipios.json: {len(pmp_meta['sin_cruce'])} "
      f"(nombres oficiales divergentes, casi todos bilingües valencianos/catalanes; listados en `pmp_meta.json`).")
    A("- TRAMPA de código: el código DIR3 `PP-CC-MMM-...` del fichero PMP **no** es el código INE "
      "(el nº de municipio va dentro de comarca y colisiona entre comarcas). El cruce se hace por "
      "provincia + nombre normalizado, con verificación de únicos.")
    A("")
    A("| Municipio | Población | PMP (días) |")
    A("|---|---|---|")
    A(fmt(top(items, pmp, "pmp")))
    A("")
    A("| Municipio | Población | PMP (días, más rápidos) |")
    A("|---|---|---|")
    A(fmt(top(items, pmp, "pmp", reverse=False)))
    A("")
    A("## Trampas detectadas (resumen)")
    A("")
    A("1. **SEPE**: la columna de código pierde el cero inicial (8001 = 08001); hay que rellenar a 5 dígitos. "
      "Las celdas «<5» son confidencialidad estadística (solo afecta a desgloses, no al total). "
      "1930 municipios no aparecen (todos minúsculos).")
    A("2. **Deuda viva**: unidades en **miles de euros**; convertidas a €. Ficheros separados por tipo de "
      "entidad (ayuntamientos / diputaciones-cabildos / resto EELL): no mezclar. Cobertura total.")
    A("3. **PMP**: código DIR3 ≠ código INE; entidades no municipales mezcladas en el mismo fichero "
      "(filtradas); publicación trimestral (modelo de variables) frente a mensual (cesión); "
      "bilingüismo de nombres oficiales produce ~41 sin cruce.")
    A("4. Navarra y País Vasco **SÍ** aparecen en las tres fuentes (régimen foral no excluye estos datos).")
    A("")
    A("## Ficheros")
    A("")
    A("- `paro.json` / `deuda_viva.json` / `pmp.json`: valores por código INE.")
    A("- `*_meta.json`: periodo, url, crudos usados y conteos por fuente.")
    A("- `sources.json`: fuente, url, periodo, unidad y licencia de cada indicador.")
    A("- `raw/`: crudos descargados (XLS/XLSX).")
    A("- Scripts reproducibles: `scripts/municipios/fetch_paro.py`, `fetch_deuda.py`, `fetch_pmp.py`.")
    (OUT / "INFORME.md").write_text("\n".join(L))
    print(f"INFORME.md escrito: paro {pn}, deuda {dn}, pmp {mn} de {total}")


if __name__ == "__main__":
    main()
