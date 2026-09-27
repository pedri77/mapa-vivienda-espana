#!/usr/bin/env python3
"""Corrige tildes en los textos de los JSON curados (no toca URLs, claves ni votos)."""
import json, re, sys
from pathlib import Path

W = """tasacion tasación|tasaciones tasaciones|indice índice|indices índices|segun según|cataluna Cataluña|mas más|abstencion abstención|
abstenciones abstenciones|andalucia Andalucía|malaga Málaga|publica pública|publicas públicas|publico público|publicos públicos|inversion inversión|
pais país|paises países|periodico periódico|anos años|ano año|aragon Aragón|juridica jurídica|juridicas jurídicas|juridico jurídico|
metodologia metodología|leon León|ultima última|ultimo último|ultimos últimos|ultimas últimas|boletin Boletín|categoria categoría|region región|
turisticos turísticos|turistico turístico|turistica turística|turisticas turísticas|aprobacion aprobación|ejecucion ejecución|ejecuciones ejecuciones|
cadiz Cádiz|maria María|organos órganos|espana España|espanol español|espanola española|espanoles españoles|gestion gestión|operacion operación|
operaciones operaciones|sanchez Sánchez|sabado sábado|miercoles miércoles|martes martes|convoco convocó|convocatoria convocatoria|llamo llamó|
discapacidad discapacidad|situacion situación|informacion información|compania compañía|companias compañías|credito crédito|creditos créditos|
hipotecario hipotecario|economico económico|economica económica|economicos económicos|economicas económicas|politica política|politicas políticas|
politico político|politicos políticos|vivienda vivienda|tambien también|despues después|ademas además|segun según|traves través|via vía|
estimacion estimación|estimaciones estimaciones|adquisicion adquisición|adquisiciones adquisiciones|participacion participación|
resolucion resolución|resoluciones resoluciones|modificacion modificación|regulacion regulación|prorroga prórroga|prorrogas prórrogas|
convalidacion convalidación|derogacion derogación|tramitacion tramitación|aplicacion aplicación|declaracion declaración|
emancipacion emancipación|rehabilitacion rehabilitación|financiacion financiación|actualizacion actualización|votacion votación|votaciones votaciones|
proposicion proposición|comision comisión|congreso Congreso|constitucion Constitución|constitucional constitucional|articulo artículo|articulos artículos|
nucleo núcleo|nucleos núcleos|numero número|limite límite|limites límites|minimo mínimo|maximo máximo|media media|analisis análisis|
tecnico técnico|tecnica técnica|unico único|unica única|basico básico|practica práctica|especifico específico|energetica energética|
eficiencia eficiencia|habitacion habitación|habitaciones habitaciones|alquiler alquiler|desahucio desahucio|poblacion población|
poblaciones poblaciones|jovenes jóvenes|joven joven|menores menores|familias familias|avila Ávila|cordoba Córdoba|almeria Almería|jaen Jaén|
leganes Leganés|mostoles Móstoles|alcala Alcalá|castellon Castellón|merida Mérida|caceres Cáceres|logrono Logroño|coruna Coruña|
gijon Gijón|aviles Avilés|mallorca Mallorca|valencia Valencia|pamplona Pamplona|donostia Donostia|madrid Madrid|oviedo Oviedo|
asturias Asturias|galicia Galicia|canarias Canarias|rioja Rioja|murcia Murcia|navarra Navarra|vasco Vasco|castilla Castilla|
extremadura Extremadura|balears Balears|baleares Baleares|melilla Melilla|ceuta Ceuta|ivima IVIMA|
suelo suelo|dificil difícil|facil fácil|critica crítica|criticas críticas|publicacion publicación|publicaciones publicaciones|
accion acción|acciones acciones|direccion dirección|proteccion protección|atencion atención|decision decisión|decisiones decisiones|
sesion sesión|reunion reunión|reuniones reuniones|razon razón|millon millón|millones millones|opinion opinión|union unión|
gobierno Gobierno|presidencia presidencia|region región|regiones regiones|autonomia autonomía|autonomica autonómica|autonomicas autonómicas|
autonomico autonómico|estatica estática|transicion transición|excepcion excepción|pension pensión|pensiones pensiones|
tenia tenía|tenian tenían|habia había|habian habían|seria sería|podria podría|podrian podrían|todavia todavía|aun aún|
dia día|dias días|mediodia mediodía|telefono teléfono|electronica electrónica|electronico electrónico|
area área|areas áreas|ambito ámbito|metropolitana metropolitana|guia guía|cronica crónica|terminos términos|termino término|
periodo período|caracter carácter|interes interés|ultimamente últimamente|rapido rápido|rapidos rápidos|rapida rápida|
propietario propietario|arrendatario arrendatario|arrendador arrendador|inquilino inquilino|garantia garantía|garantias garantías|
fianza fianza|deposito depósito|sociedad sociedad|patrimonio patrimonio|catalogo catálogo|codigo código|codigos códigos|
publicado publicado|sindicato Sindicato|tiendas tiendas|delegacion Delegación|organizacion organización|organizaciones organizaciones|
reivindicacion reivindicación|movilizacion movilización|movilizaciones movilizaciones|concentracion concentración|manifestacion manifestación|
manifestaciones manifestaciones|acampada acampada|indefinidos indefinidos|congelacion congelación|renovacion renovación|automatica automática|
automatico automático|regulacion regulación|reivindicativa reivindicativa|migratoria migratoria|crisis crisis|fronteriza fronteriza|
fin fin|rentismo rentismo|termino terminó|ejecuto ejecutó|subio subió|pidio pidió|anuncio anunció|aprobo aprobó|rechazo rechazo|
declaro declaró|firmo firmó|voto votó|votaron votaron|presento presentó|llego llegó|recurrio recurrió|estimo estimó|desestimo desestimó|
anulo anuló|derogo derogó|convalido convalidó|compro compró|vendio vendió|adquirio adquirió|traspaso traspaso|cedio cedió|
alianza alianza|batalla batalla|polemica polémica|polemico polémico|guardia Guardia|policia policía|metro metro|metros metros|
superficie superficie|minima mínima|maxima máxima|estadistica estadística|estadisticas estadísticas|demografia demografía|
consumo Consumo|catastro Catastro|agencia Agencia|tributaria Tributaria|hacienda Hacienda|banco banco|
alquileres alquileres|precio precio|precios precios|mercado mercado|residencial residencial|tensionado tensionado|tensionadas tensionadas|
tension tensión|construccion construcción|promocion promoción|promociones promociones|urbanistico urbanístico|urbanistica urbanística|
edificacion edificación|obligacion obligación|obligaciones obligaciones|sancion sanción|sanciones sanciones|infraccion infracción|
ocupacion ocupación|desocupacion desocupación|lanzamiento lanzamiento|juzgados juzgados|judicial judicial|proceso proceso|procesal procesal|
servicios servicios|sociales sociales|vulnerabilidad vulnerabilidad|vulnerable vulnerable|conciliacion conciliación|mediacion mediación|
alternativa alternativa|habitacional habitacional|emergencia emergencia|tramite trámite|tramites trámites|plazo plazo|plazos plazos|
obligatorio obligatorio|solucion solución|soluciones soluciones|controversias controversias|golden golden|visado visado|
parlament Parlament|generalitat Generalitat|xunta Xunta|junta Junta|consell Consell|cabildo Cabildo|diputacion Diputación|
senado Senado|ministerio Ministerio|ministra ministra|ministro ministro|secretaria secretaría|direccion dirección|
socimi SOCIMI|socimis SOCIMI|sareb Sareb|sepes SEPES|anticipa Anticipa|aliseda Aliseda|haya Haya|servihabitat Servihabitat|
solvia Solvia|altamira Altamira|divarian Divarian|tempore Témpore|nestar Nestar|encasa Encasa|fidere Fidere|testa Testa|
catalunya Catalunya|popular Popular|sabadell Sabadell|santander Santander|caixabank CaixaBank|bbva BBVA|
nomina nómina|nominas nóminas|rapidamente rápidamente|practicamente prácticamente|especificamente específicamente|
unicamente únicamente|basicamente básicamente|historico histórico|historica histórica|historicos históricos|
maximos máximos|minimos mínimos|cifra cifra|cifras cifras|grafico gráfico|graficos gráficos|analisis análisis|
opcion opción|opciones opciones|condicion condición|condiciones condiciones|relacion relación|revision revisión|
extension extensión|dimension dimensión|expansion Expansión|confidencial Confidencial|pais País|vanguardia Vanguardia|opinion Opinión|
democrata Demócrata|razon Razón|periodico Periódico|boletin Boletín|salto Salto|minutos minutos|diario diario|publico Público|
tecnologia tecnología|especulacion especulación|terminologia terminología|desinversion desinversión|valoracion valoración|negociacion negociación|ubicacion ubicación|electomania Electomanía|rio Río|alvarez Álvarez|gonzalez González|martinez Martínez|rodriguez Rodríguez|fernandez Fernández|garcia García|lopez López|perez Pérez|gomez Gómez|diaz Díaz|hernandez Hernández|ruiz Ruiz|jimenez Jiménez|estadistico estadístico|vehiculo vehículo|vehiculos vehículos|numeros números|mayoria mayoría|minoria minoría|compraron compraron|subasta subasta|carteras carteras|energia energía|economia economía|compraventa compraventa|compraventas compraventas|
vivienda vivienda|oficina oficina|oficinas oficinas|telefonica telefónica|atencion atención|informacion información"""

PAIRS = {}
PROPER = {"cataluña", "andalucía", "málaga", "aragón", "león", "cádiz", "maría", "españa", "sánchez", "ávila", "córdoba",
          "almería", "jaén", "leganés", "móstoles", "alcalá", "castellón", "mérida", "cáceres", "logroño", "coruña", "gijón", "avilés", "álvarez", "gonzález", "martínez", "rodríguez", "fernández", "garcía", "lópez", "pérez", "gómez", "díaz", "hernández", "jiménez", "río", "electomanía"}
# Formas que también existen sin tilde con otro significado
RISKY = {"voto", "termino", "anuncio", "aun", "seria", "pais_", "rechazo", "traspaso", "estimo", "llamo", "compro", "presento", "firmo", "declaro", "tenia", "habia", "publico_", "tempore"}
for part in W.replace("\n", "").split("|"):
    part = part.strip()
    if not part:
        continue
    a, b = part.split(" ", 1)
    # Solo pares que añaden tilde o ñ; los cambios de mayúsculas se ignoran
    if a.lower() != b.lower() and a.lower() not in RISKY:
        PAIRS.setdefault(a.lower(), b)
# Palabras que no se tocan porque existen sin tilde con otro sentido
SKIP_KEYS = {"url", "source_url", "source_urls", "vote_source", "votes", "code", "ccaa_code", "id", "status_code"}
rx = re.compile(r"\b(" + "|".join(sorted(map(re.escape, PAIRS), key=len, reverse=True)) + r")\b", re.I)


def fix_word(m):
    w = m.group(0)
    target = PAIRS.get(w.lower())
    if target is None:
        return w
    # Topónimos y apellidos siempre en mayúscula; el resto respeta el original
    if target[0].isupper() and target.lower() in PROPER:
        return target if not w.isupper() else target.upper()
    target = target.lower()
    if w.isupper() and len(w) > 1:
        return target.upper()
    if w[0].isupper():
        return target[0].upper() + target[1:]
    return target


def walk(o, key=None):
    if isinstance(o, str):
        if key in SKIP_KEYS or o.startswith("http"):
            return o
        return rx.sub(fix_word, o)
    if isinstance(o, dict):
        return {k: (v if k in SKIP_KEYS else walk(v, k)) for k, v in o.items()}
    if isinstance(o, list):
        return [walk(v, key) for v in o]
    return o


if __name__ == "__main__":
    for f in sys.argv[1:]:
        p = Path(f)
        data = json.loads(p.read_text(encoding="utf-8"))
        before = json.dumps(data, ensure_ascii=False)
        data = walk(data)
        after = json.dumps(data, ensure_ascii=False)
        p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f, "cambios:", sum(1 for a, b in zip(before.split(), after.split()) if a != b))
