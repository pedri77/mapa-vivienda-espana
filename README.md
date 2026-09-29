# Techo · La vivienda en España, en datos

Web estática con mapa interactivo sobre la situación de la vivienda en España:

- **Directo**: acampadas y movilizaciones, con un feed de noticias que se actualiza cada 30 minutos.
- **Mapa por comunidad**: desahucios por 100.000 habitantes, precio de venta y alquiler, subida interanual, esfuerzo (años de renta para comprar y % de la renta para alquilar) y salarios.
- **Desahucios**: serie del CGPJ 2013-2025 por tipo (alquiler, hipotecario, otros) y por comunidad.
- **Precios**: valor tasado (MIVAU), oferta (Fotocasa/Idealista), compraventas y construcción.
- **Grandes tenedores**: viviendas por entidad (Civio), grandes operaciones y peso en el alquiler.
- **Leyes y partidos**: normas estatales y autonómicas, votaciones en el Congreso y zonas tensionadas por comunidad.
- **Medios**: volumen de cobertura por medio y tendencia semanal.
- **Ayudas**: ayudas al alquiler, qué hacer ante un desahucio y directorio de organizaciones.
- **Tu municipio**: alquiler, renta, esfuerzo, pisos turísticos y zona tensionada de los 8.132 municipios; y las cuentas de su ayuntamiento: paro registrado (SEPE), deuda viva por habitante y periodo medio de pago a proveedores (Ministerio de Hacienda).

## Cómo funciona

- `index.html` + `assets/`: HTML, CSS y JavaScript sin dependencias de build. Leaflet desde cdnjs.
- `data/*.json`: datos curados con su fuente. `data/ccaa.geojson` procede de [es-atlas](https://github.com/martgnz/es-atlas) (IGN).
- `scripts/fetch_news.py`: recoge RSS públicos (Google News y medios) y genera `noticias.json`, `medios.json` y `senales.json`. Solo librería estándar de Python.
- `.github/workflows/noticias.yml`: ejecuta el recolector cada 30 minutos y hace commit de los cambios.
- `scripts/config.json`: búsquedas, feeds, temas y ciudades que reconoce el recolector.

### Actualizar acampadas

Las acampadas confirmadas se editan a mano en `data/acampadas.json` (ciudad, lugar, coordenadas, estado, fuentes). Las menciones automáticas por ciudad (`senales.json`) aparecen en el mapa como círculos discontinuos y **no** confirman una acampada.

### Local

```bash
python3 scripts/fetch_news.py      # opcional: refrescar noticias
python3 -m http.server 8000        # abrir http://localhost:8000
```

## Fuentes

CGPJ, INE (EAES, IPV, ECV, ETDP), Ministerio de Vivienda (valor tasado, SERPAVI, vivienda iniciada), BOE y boletines autonómicos, Congreso, Tribunal Constitucional, Civio, Banco de España, Fotocasa, Idealista y prensa. Cada dato enlaza a su fuente en la web y en los JSON.

## Licencia

Código: MIT. Datos elaborados: CC BY 4.0, citando a las fuentes originales. Los titulares del feed pertenecen a cada medio y enlazan al original.
