# Dataset municipal de vivienda

Generado el 27-09-2026 con `build_municipios.py` (Python 3 + pandas, openpyxl, xlrd). Clave: código INE de municipio de 5 dígitos (CPRO+CMUN, p. ej. `28079` Madrid). Universo: 8.132 municipios de la Relación de municipios del INE a 1-1-2026.

Para regenerar: `python3 build_municipios.py` (usa la caché de `raw/`) o `python3 build_municipios.py --refresh` (lo descarga todo de nuevo). El script deja además `build_report.json`, con la cobertura, los nombres sin casar y el log.

## Ficheros

| Fichero | Tamaño | gzip | Contenido |
|---|---|---|---|
| `municipios.json` | 4,7 MB | 0,5 MB | `{generated, key, fields_meta, ccaa_vt, items}` |
| `municipios.topo.json` | 1,7 MB | 0,5 MB | TopoJSON de es-atlas 0.6.0 (objetos `municipalities`, `provinces`, `autonomous_regions`), ids = código INE |
| `partidos.json` | 0,4 MB | | 431 partidos judiciales: municipios y lanzamientos 2013-2025 |

Todos los campos están presentes en todos los municipios. Si no hay dato, el valor es `null`; no se imputa nada.

## Campos y cobertura (de 8.132 municipios)

| Campo | Fuente oficial | Periodo | Municipios con dato |
|---|---|---|---|
| `n`, `p`, `c` (nombre, provincia, CCAA) | INE, diccionario26.xlsx | 1-1-2026 | 8.132 |
| `pob` | INE, Cifras oficiales del Padrón (tabla 29005) | 1-1-2025 (la de 1-1-2026 aún no se ha publicado) | 8.132 |
| `alq_m2`, `alq_mes`, `alq_sup` (vivienda colectiva, mediana) | MIVAU SERPAVI, bd 2011-2024 | 2024 | 2.555 |
| `alq_n` (nº de viviendas colectivas arrendadas) | SERPAVI | 2024 | 6.527 (incluye 0) |
| `alq_m2_u`, `alq_mes_u` (unifamiliar) | SERPAVI | 2024 | 3.020 |
| `alq_n_u` | SERPAVI | 2024 | 6.511 |
| `renta_hogar`, `renta_persona` (renta neta media) | INE ADRH (tabla 30824) | 2023 | 8.059 |
| `tasado_m2`, `tasado_n` | MIVAU, tabla 35103500 (municipios > 25.000 hab.) | 2T 2026 | 306 (todas las filas del fichero casadas) |
| `zt` y `zt_res`, `zt_desde`, `zt_hasta`, `zt_boe`, `zt_parcial`, `zt_nota` | MIVAU, página "Consultar zonas de mercado residencial tensionado" | a 27-09-2026 | 317 `true` (271 Cataluña, 18 País Vasco, 21 Navarra, 2 Galicia, 5 Asturias), de los que 7 son parciales |
| `vut`, `vut_plazas`, `vut_pct` | INE, viviendas turísticas (tablas 39363 y 39366) | 2026-05 | 8.131 (incluye 0) |
| `vt_series` `{AAAA-MM: n}` | INE, tabla 39363 | 2020-08 a 2026-05 (13 periodos) | 8.131 |
| `vt_var_pct` | Derivado: 2026-05 frente a 2025-05 | | 5.406 (null si el año anterior es 0) |
| `esfuerzo` | DERIVADO: `alq_mes × 12 / renta_hogar × 100` | alquiler 2024 / renta 2023 | 2.555 |
| `pj` (código INE de la sede del partido judicial) | Ministerio de Justicia, Censo Judicial | vigente | 8.132 |

`ccaa_vt` recoge los agregados de viviendas turísticas por CCAA y del total nacional (`00`), de las tablas INE 39364 y 39365. Incluye el último periodo (2026-05), el mismo mes del año anterior (2025-05), la variación interanual y las series completas de número y porcentaje.

## URLs de las fuentes

- INE municipios: https://www.ine.es/daco/daco42/codmun/diccionario26.xlsx
- INE Padrón: https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/29005.csv
- INE ADRH: https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/30824.csv (350 MB, se lee en streaming)
- INE viviendas turísticas: tablas `39363`, `39366`, `39364` y `39365` en https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/{id}.csv
- SERPAVI: https://cdn.mivau.gob.es/portal-web-mivau/vivienda/serpavi/2026-03_09_bd_SERPAVI_2011-2024%20-%20DEFINITIVO%20WEB_v2.xlsx
- Valor tasado: https://apps.fomento.gob.es/boletinonline2/sedal/35103500.XLS (hoja `T2A2026`)
- Zonas tensionadas: https://www.mivau.gob.es/vivienda/alquila-bien-es-tu-derecho/serpavi/consultar-zonas-de-mercado-residencial-tensionado
- Censo Judicial (municipio → partido judicial): https://www.mjusticia.gob.es/es/JusticiaEspana/OrganizacionJusticia/Documents/Censo%20Judicial.xlsx
- Lanzamientos CGPJ: https://www.poderjudicial.es/stfls/ESTADISTICA/FICHEROS/Crisis/Lanzamientos%20por%20PJs_2013_%202025.xlsx
- Geometría: https://cdn.jsdelivr.net/npm/es-atlas@0.6.0/es/municipalities.json

## Limitaciones

- **SERPAVI.** El último año disponible es 2024. La mediana solo se publica si hay suficientes observaciones, por eso hay 2.555 municipios con precio y 6.527 con recuento. El País Vasco y Navarra tienen haciendas forales y el SERPAVI solo recoge datos parciales para ellos (en Álava, por ejemplo, solo aparece 2024). Los códigos del SERPAVI son de 2021 y todos casan con los de 2026.
- **Esfuerzo.** Compara años distintos (alquiler 2024, renta 2023) y una mediana de alquiler con una renta media por hogar. Es un indicador orientativo y está marcado como derivado.
- **Valor tasado.** El fichero no trae códigos, así que se casa por nombre a nivel nacional entre municipios de 10.000 habitantes o más. Las etiquetas de provincia del XLS están desalineadas por celdas combinadas y solo se usan para desempatar. Cuatro nombres se casan con un alias manual (Mahón → Maó, Palma de Mallorca → Palma, Santa Eulalia del Río → Santa Eulària des Riu, San Cristóbal Laguna → San Cristóbal de La Laguna) y dos por aproximación (Santa Cruz deTenerife, Santa Coloma Gramanet). He revisado a mano los casos cuyo nombre difiere.
- **Zonas tensionadas.** Se parsea la página oficial del MIVAU, que devuelve 403 a curl. El script usa entonces Playwright con Chrome del sistema (`node_modules/playwright` en el directorio padre) o, si falla, la copia cacheada `raw/zt.html`. `zt = true` también cuando la declaración es parcial: Vitoria-Gasteiz (trama urbana), Galdakao (distrito 2) y los ámbitos de Gijón, Avilés, Llanes, Cabrales y Gozón. En esos casos `zt_parcial = true` y `zt_nota` describe el ámbito. `zt_res` es la fecha de la resolución de la Secretaría de Estado de Vivienda publicada en el BOE. Para Galicia, la resolución autonómica es anterior (IGVS, 30-05-2025 para A Coruña y 24-04-2026 para Santiago). La lista de nombres de `data_legislacion.json` se sustituyó por esta fuente oficial y los 317 nombres casan sin pendientes.
- **Viviendas turísticas.** Es una estadística experimental del INE. Los periodos no son homogéneos: agosto y febrero hasta 2024, y después noviembre y mayo. Por eso `vt_var_pct` compara solo el mismo mes del año anterior.
- **Renta ADRH.** 73 municipios pequeños no tienen dato por secreto estadístico.
- **Partidos judiciales.** El Censo Judicial del Ministerio de Justicia trae el código INE del municipio y el de la sede. Los 431 nombres del fichero de lanzamientos del CGPJ casan, 14 de ellos con alias manual (grafías distintas, por ejemplo "MAO-MAHON", "VILLAROBLEDO" o "CATARROJA", cuyo nombre en el Censo está corrupto).
- **Geometría.** Es la de es-atlas 0.6.0 sin simplificar (ya ocupa menos de 2,5 MB y se ha quitado el objeto `border`). Coordenadas lon/lat sin proyectar, con Canarias en su posición real. Usansolo (`48916`, segregado de Galdakao) no tiene polígono propio: está dentro del de Galdakao. Hay 82 geometrías `53xxx` que corresponden a condominios o comunidades de términos sin municipio INE; conviene ignorarlas o pintarlas en gris.
