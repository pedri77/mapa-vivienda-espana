# cci-08 — Investigación fuentes municipales: paro, deuda viva y PMP

Generado por `scripts/municipios/informe_cci08.py`. Municipios de referencia: **8132** (`data/municipios.json`, códigos INE 5 dígitos, Padrón 1-1-2025, población total 49,114,494 hab.). Todos los números de cobertura están medidos sobre ese fichero.

## 1. Paro registrado por municipio (SEPE)

- Periodo: **agosto 2026** (y agosto 2025 para variación interanual). Fichero agregado `ESTADISTICA_MUNICIPIOS.xls`, hojas «PARO &lt;provincia&gt;».
- Match: **6202/8132 municipios (76.3%)**, cubriendo **48,897,240 hab. (99.6% de la población)**.
- Sin dato: 1930 municipios, 1921 de ellos con menos de 500 hab.; la población sin cubrir es solo 217,254 hab. (0.4%). El SEPE simplemente no publica fila para esos municipios (la mayoría sin parados registrados o agregados en el resto provincial); no es un fallo de cruce.
- Derivados calculados: `paro_1a`, `paro_var` (interanual %), `paro_1k_hab` (paro por 1.000 hab. con `pob`).

Top 10 paro absoluto y paro por 1.000 hab. (verificables a mano):

| Municipio | Población | Paro |
|---|---|---|
| Madrid | 3,506,730 | 135168 |
| Barcelona | 1,731,649 | 66029 |
| Sevilla | 689,423 | 49275 |
| València | 840,792 | 43273 |
| Málaga | 599,063 | 39686 |
| Zaragoza | 693,091 | 29171 |
| Palmas de Gran Canaria, Las | 381,868 | 28853 |
| Alacant/Alicante | 366,221 | 25052 |
| Murcia | 479,405 | 24475 |
| Córdoba | 323,262 | 23857 |

| Municipio | Población | Paro/1.000 hab. |
|---|---|---|
| Fuente la Reina | 55 | 163.6 |
| Sempere | 33 | 151.5 |
| Castillejo de Iniesta | 94 | 148.9 |
| Cumbres de Enmedio | 54 | 148.1 |
| Ruanes | 82 | 146.3 |
| Pozondón | 53 | 132.1 |
| Leache/Leatxe | 38 | 131.6 |
| Alcaudete de la Jara | 1,720 | 123.8 |
| Villanueva de Azoague | 398 | 123.1 |
| Atalaya | 258 | 116.3 |

## 2. Deuda viva municipal (Ministerio de Hacienda)

- Periodo: **31-12-2025**, fichero «deuda-viva-ayuntamientos-202512.xlsx», hoja `Datos_Format`.
- Match: **8132/8132 municipios (100.0%)** — cobertura TOTAL de municipios, 49,114,494 hab. (100.0%).
- Derivados: `deuda` (€, convertido desde **miles de €** del original — trampa documentada) y `deuda_hab` (€/habitante). El fichero de ayuntamientos solo contiene ayuntamientos: el resto de entidades (diputaciones, cabildos, mancomunidades…) viene en ficheros separados que no se mezclan aquí.

| Municipio | Población | Deuda viva (€) |
|---|---|---|
| Madrid | 3,506,730 | 1560729607 |
| Barcelona | 1,731,649 | 1287410462 |
| Jerez de la Frontera | 213,634 | 968383022 |
| Jaén | 112,235 | 587963832 |
| Zaragoza | 693,091 | 531575963 |
| Parla | 137,471 | 520280349 |
| Algeciras | 126,589 | 257182834 |
| Gandia | 83,135 | 252844699 |
| Murcia | 479,405 | 250758861 |
| Málaga | 599,063 | 197252948 |

| Municipio | Población | Deuda €/hab. |
|---|---|---|
| Vallada | 3,091 | 8683.9 |
| Forès | 38 | 7921.1 |
| Barrios, Los | 24,449 | 7890.9 |
| Moraleja de Enmedio | 5,580 | 7451.9 |
| Plasenzuela | 536 | 6957.1 |
| Santa Marta de Magasca | 291 | 5853.1 |
| Huévar del Aljarafe | 3,388 | 5583.5 |
| Blancos, Os | 696 | 5507.6 |
| Puerto de San Vicente | 141 | 5254.2 |
| Jaén | 112,235 | 5238.7 |

## 3. Periodo medio de pago a proveedores (PMP, Ministerio de Hacienda)

- Periodo: **T2 2026**, fichero «Cesión y variables» (trimestral; el modelo de «cesión» publica mensual y el de «variables» trimestral).
- Match: **6385/8132 municipios (78.5%)**, cubriendo **46,336,744 hab. (94.3%)**.
- Sin dato: 1747 municipios, 1478 de ellos con menos de 1.000 hab. (2,777,750 hab., 5.7%). Causa: esas entidades no figuran en la publicación del PMP (no remiten información; el RD 635/2014 obliga a publicar, pero los ayuntamientos más pequeños del modelo de variables pueden no reportar el trimestre).
- Entidades del fichero descartadas por NO ser ayuntamientos (contadas, no mezcladas): {'Diputación/Consejo/Cabildo': 51, 'Entidades de ámbito inferior al municipio': 446, 'Mancomunidad': 435, 'Agrupación Municipios': 16, 'Comarca': 77, 'Área Metropolitana': 3, 'Ciudad Autónoma': 2}.
- Ayuntamientos del fichero sin cruce con municipios.json: 41 (nombres oficiales divergentes, casi todos bilingües valencianos/catalanes; listados en `pmp_meta.json`).
- TRAMPA de código: el código DIR3 `PP-CC-MMM-...` del fichero PMP **no** es el código INE (el nº de municipio va dentro de comarca y colisiona entre comarcas). El cruce se hace por provincia + nombre normalizado, con verificación de únicos.

| Municipio | Población | PMP (días) |
|---|---|---|
| Villamayor de Calatrava | 611 | 1805.0 |
| Rairiz de Veiga | 1,154 | 916.8 |
| Santa María de la Alameda | 1,584 | 863.1 |
| Láchar | 3,892 | 822.1 |
| Píñar | 1,040 | 727.0 |
| Rubite | 419 | 660.7 |
| Garrucha | 10,845 | 659.0 |
| Pizarra | 10,334 | 625.3 |
| Puigcerdà | 10,035 | 570.8 |
| San Martín del Pimpollar | 221 | 527.3 |

| Municipio | Población | PMP (días, más rápidos) |
|---|---|---|
| Beires | 140 | 0.0 |
| Benitagla | 63 | 0.0 |
| Benizalón | 242 | 0.0 |
| Gallardos, Los | 3,110 | 0.0 |
| Líjar | 378 | 0.0 |
| Nacimiento | 485 | 0.0 |
| Santa Fe de Mondújar | 503 | 0.0 |
| Tahal | 355 | 0.0 |
| Mojonera, La | 8,793 | 0.0 |
| Cacín | 549 | 0.0 |

## Trampas detectadas (resumen)

1. **SEPE**: la columna de código pierde el cero inicial (8001 = 08001); hay que rellenar a 5 dígitos. Las celdas «<5» son confidencialidad estadística (solo afecta a desgloses, no al total). 1930 municipios no aparecen (todos minúsculos).
2. **Deuda viva**: unidades en **miles de euros**; convertidas a €. Ficheros separados por tipo de entidad (ayuntamientos / diputaciones-cabildos / resto EELL): no mezclar. Cobertura total.
3. **PMP**: código DIR3 ≠ código INE; entidades no municipales mezcladas en el mismo fichero (filtradas); publicación trimestral (modelo de variables) frente a mensual (cesión); bilingüismo de nombres oficiales produce ~41 sin cruce.
4. Navarra y País Vasco **SÍ** aparecen en las tres fuentes (régimen foral no excluye estos datos).

## Ficheros

- `paro.json` / `deuda_viva.json` / `pmp.json`: valores por código INE.
- `*_meta.json`: periodo, url, crudos usados y conteos por fuente.
- `sources.json`: fuente, url, periodo, unidad y licencia de cada indicador.
- `raw/`: crudos descargados (XLS/XLSX).
- Scripts reproducibles: `scripts/municipios/fetch_paro.py`, `fetch_deuda.py`, `fetch_pmp.py`.