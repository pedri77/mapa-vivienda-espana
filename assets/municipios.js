import { $, fmt, eur, pct, esc, load, dateEs, link, quantileBreaks, classOf, cssVar, sparkline, sortableTable, CCAA } from "./util.js";
import { renderCalculadora } from "./calculadora.js";

// ---------- tema (igual que la portada) ----------
const THEME_KEY = "techo-theme";
const applyTheme = (t) => (t ? (document.documentElement.dataset.theme = t) : delete document.documentElement.dataset.theme);
try { applyTheme(localStorage.getItem(THEME_KEY)); } catch {}
const isDark = () => document.documentElement.dataset.theme === "dark" || (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
$("#themeBtn").addEventListener("click", () => {
  const next = isDark() ? "light" : "dark";
  applyTheme(next);
  try { localStorage.setItem(THEME_KEY, next); } catch {}
  window.dispatchEvent(new Event("themechange"));
});

const [M, PJ, precios, topo] = await Promise.all([
  load("municipios"), load("partidos"), load("precios"),
  fetch("data/municipios.topo.json").then((r) => r.json()).catch(() => null),
]);
if (!M || !topo || !window.L || !window.topojson) {
  $("#side").innerHTML = `<div class="empty">No se pudieron cargar los datos municipales.</div>`;
  throw new Error("datos municipales no disponibles");
}
const I = M.items;
const meta = M.meta || {};
const per = (k) => meta[k]?.period || "";
const pjOf = (code) => PJ?.partidos?.[I[code]?.pj];
const LAST_PJ = PJ?.years?.at(-1);

const ramp = (p) => [1, 2, 3, 4, 5].map((i) => `--${p}${i}`);
const LAYERS = {
  alq_m2: { label: "Alquiler €/m²", title: `Alquiler mediano €/m²/mes (SERPAVI ${per("alq_m2")})`, ramp: ramp("r"), get: (m) => m.alq_m2, f: (v) => `${fmt(v, 1)} €` },
  alq_mes: { label: "Alquiler €/mes", title: `Alquiler mediano €/mes (SERPAVI ${per("alq_mes")})`, ramp: ramp("r"), get: (m) => m.alq_mes, f: (v) => `${fmt(v)} €` },
  esfuerzo: { label: "Esfuerzo", title: "Alquiler anual sobre renta media del hogar (%)", ramp: ramp("d"), get: (m) => m.esfuerzo, f: (v) => `${fmt(v, 1)}%` },
  renta: { label: "Renta hogar", title: `Renta neta media por hogar (INE ADRH ${per("renta_hogar")})`, ramp: ramp("p"), get: (m) => m.renta_hogar, f: (v) => eur(v) },
  tasado: { label: "Venta €/m²", title: `Valor tasado €/m² (MIVAU ${per("tasado_m2")}, municipios >25.000 hab.)`, ramp: ramp("p"), get: (m) => m.tasado_m2, f: (v) => `${fmt(v)} €` },
  vut: { label: "Pisos turísticos %", title: `Viviendas turísticas sobre el total (INE ${per("vut_pct")})`, ramp: ramp("d"), get: (m) => m.vut_pct, f: (v) => `${fmt(v, 2)}%` },
  vutvar: { label: "Pisos turísticos: variación", title: `Variación interanual de viviendas turísticas (${M.vt_periodos?.at(-1)})`, ramp: ramp("d"), get: (m) => (m.vut >= 10 ? m.vt_var_pct : null), f: (v) => pct(v) },
  zt: { label: "Zona tensionada", title: "Municipios declarados zona de mercado residencial tensionado", ramp: ["--d2", "--d4"], cat: true, get: (m) => (m.zt ? 1 : null), f: () => "Declarada" },
  pj: { label: "Desahucios", title: `Desahucios por 100.000 hab. en su partido judicial (${LAST_PJ})`, ramp: ramp("d"), get: (m, c) => pjOf(c)?.tasa, f: (v) => fmt(v, 1) },
};
const NOTES = {
  alq_m2: "SERPAVI usa los alquileres declarados en el IRPF (contratos vigentes), por eso queda por debajo de los precios de anuncio. Solo hay mediana donde hay contratos suficientes.",
  alq_mes: "Mediana de la renta mensual de los contratos declarados. Sin dato en municipios con pocos contratos.",
  esfuerzo: "Cálculo propio: alquiler mediano ×12 entre renta neta media del hogar. Mezcla años distintos (alquiler 2024, renta 2023) y compara una mediana con una media: úsalo como orientación.",
  renta: "Atlas de Distribución de Renta de los Hogares del INE. Faltan algunos municipios pequeños por secreto estadístico.",
  tasado: "Solo el Ministerio publica tasación para municipios de más de 25.000 habitantes. El resto aparece en gris.",
  vut: "Estadística experimental del INE a partir de anuncios en Airbnb, Booking y Vrbo. Puede no captar pisos turísticos que no se anuncian en esas plataformas.",
  vutvar: "Compara con el mismo mes del año anterior. Solo municipios con al menos 10 viviendas turísticas.",
  zt: "Zonas declaradas por el Ministerio de Vivienda a petición de cada comunidad (Ley 12/2023). Algunas solo afectan a parte del municipio.",
  pj: "El CGPJ no publica desahucios por municipio, solo por partido judicial (agrupaciones de municipios). Todos los municipios de un mismo partido tienen el mismo color.",
};
let layer = "alq_m2";
let selected = null;

// ---------- mapa ----------
const geo = topojson.feature(topo, topo.objects.municipalities);
const mk = (el, opts) => L.map(el, { zoomSnap: 0.25, preferCanvas: true, scrollWheelZoom: false, attributionControl: el === "map", ...opts });
const map = mk("map", { minZoom: 5, maxZoom: 12 });
const inset = mk("mapCanarias", { zoomControl: false, dragging: false, doubleClickZoom: false, boxZoom: false, keyboard: false, touchZoom: false });
map.fitBounds([[35.9, -9.4], [43.8, 4.4]]);
inset.fitBounds([[27.6, -18.2], [29.45, -13.4]]);
const esri = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas";
const baseUrl = () => `${esri}/World_${isDark() ? "Dark" : "Light"}_Gray_Base/MapServer/tile/{z}/{y}/{x}`;
const base = L.tileLayer(baseUrl(), { attribution: 'Teselas © <a href="https://www.esri.com/">Esri</a>, HERE, Garmin, © OpenStreetMap', maxNativeZoom: 16 }).addTo(map);
const baseIn = L.tileLayer(baseUrl(), { maxNativeZoom: 16 }).addTo(inset);

let breaks = [];
const value = (code) => (I[code] ? LAYERS[layer].get(I[code], code) : null);
const style = (f) => {
  const L_ = LAYERS[layer];
  const v = value(f.id);
  const k = L_.cat ? (v == null ? -1 : 1) : classOf(v, breaks);
  return {
    fillColor: k < 0 ? cssVar("--surface-2") : cssVar(L_.ramp[k]),
    fillOpacity: k < 0 ? 0.55 : 0.85,
    color: f.id === selected ? cssVar("--ink") : cssVar("--line"),
    weight: f.id === selected ? 2.5 : 0.3,
  };
};
const layers = [map, inset].map((m) =>
  L.geoJSON(geo, {
    style,
    onEachFeature: (f, lyr) => {
      lyr.on("click", () => select(f.id, false));
      lyr.bindTooltip(() => {
        const m = I[f.id];
        if (!m) return "Sin datos (comunidad de términos)";
        const v = value(f.id);
        return `${esc(m.n)}<br>${v == null ? "Sin dato" : LAYERS[layer].f(v)}`;
      }, { sticky: true, className: "tt" });
    },
  }).addTo(m)
);
const byId = {};
layers[0].eachLayer((l) => (byId[l.feature.id] = l));

// Contorno de comunidades encima
const ccaaLines = topojson.mesh(topo, topo.objects.autonomous_regions, (a, b) => a !== b);
const outline = () => ({ color: cssVar("--ink"), weight: 1, opacity: 0.55, fill: false, interactive: false });
const meshLayers = [map, inset].map((m) => L.geoJSON(ccaaLines, { style: outline, interactive: false }).addTo(m));

function redraw() {
  const L_ = LAYERS[layer];
  // En pisos turísticos muchos municipios tienen 0: la escala se calcula sobre los que tienen alguno
  const vals = Object.keys(I).map(value);
  breaks = L_.cat ? [] : quantileBreaks(layer === "vut" ? vals.filter((v) => v > 0) : vals);
  layers.forEach((g) => g.setStyle(style));
  const ends = [breaks[0], breaks.at(-1)];
  $("#legend").innerHTML = L_.cat
    ? `<strong>${esc(L_.title)}</strong><div class="keys" style="margin-top:6px"><span><i style="background:var(--d4)"></i>Declarada</span><span><i style="background:var(--surface-2)"></i>No</span></div>`
    : `<strong>${esc(L_.title)}</strong><div class="ramp">${L_.ramp.map((v) => `<span style="background:var(${v})"></span>`).join("")}</div><div class="ends"><span>&lt; ${L_.f(ends[0])}</span><span>≥ ${L_.f(ends[1])}</span></div>`;
  $("#layerNote").textContent = NOTES[layer] || "";
  $("#layerBtns").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.l === layer));
  renderRanking();
}
$("#layerBtns").innerHTML = Object.entries(LAYERS).map(([k, v]) => `<button type="button" data-l="${k}">${v.label}</button>`).join("");
$("#layerBtns").addEventListener("click", (e) => {
  const b = e.target.closest("button");
  if (b) { layer = b.dataset.l; redraw(); }
});
window.addEventListener("themechange", () => {
  base.setUrl(baseUrl()); baseIn.setUrl(baseUrl());
  meshLayers.forEach((g) => g.setStyle(outline));
  redraw();
});

// ---------- ficha ----------
function select(code, zoom = true) {
  if (!I[code]) return;
  selected = code;
  layers.forEach((g) => g.setStyle(style));
  const lyr = byId[code];
  if (zoom && lyr && I[code].c !== "05") map.flyToBounds(lyr.getBounds(), { maxZoom: 10, duration: 0.6 });
  $("#side").innerHTML = ficha(code);
  $("#side").scrollTop = 0;
  try { history.replaceState(null, "", `#m-${code}`); } catch {}
  $("#side").querySelector("[data-calc]")?.addEventListener("click", () => {
    $("#calcBody").setMunicipio?.(code);
    $("#calculadora").scrollIntoView();
  });
}

function ficha(code) {
  const m = I[code];
  const p = pjOf(code);
  const stat = (v, l) => `<div><b>${v}</b><span>${l}</span></div>`;
  const vt = M.vt_periodos || [];
  let h = `<p class="eyebrow">${esc(CCAA[m.c] || "")} · ${fmt(m.pob)} hab.</p><h3>${esc(m.n)}</h3>`;
  if (m.zt) h += `<p class="small" style="margin:0"><span class="pill bad">Zona tensionada</span> ${m.zt_parcial ? `<span class="muted">Parcial: ${esc(m.zt_nota || "")}</span>` : ""}${m.zt_desde ? ` <span class="muted">desde ${dateEs(m.zt_desde)}</span>` : ""}</p>`;
  h += `<div class="stats">
    ${stat(m.alq_mes ? `${fmt(m.alq_mes)} €` : "—", `alquiler mediano al mes (${per("alq_mes")})`)}
    ${stat(m.alq_m2 ? `${fmt(m.alq_m2, 1)} €` : "—", "€/m²/mes")}
    ${stat(m.renta_hogar ? eur(m.renta_hogar) : "—", `renta neta por hogar (${per("renta_hogar")})`)}
    ${stat(m.esfuerzo != null ? `${fmt(m.esfuerzo, 1)}%` : "—", "de la renta en alquiler")}
    ${stat(m.tasado_m2 ? `${fmt(m.tasado_m2)} €` : "—", `€/m² tasado (${per("tasado_m2")})`)}
    ${stat(m.alq_n != null ? fmt(m.alq_n) : "—", "contratos de alquiler declarados")}
  </div>`;
  h += `<div><h3 style="font-size:1rem;text-transform:none;margin-top:4px">Pisos turísticos</h3><div class="stats">
    ${stat(fmt(m.vut ?? 0), `viviendas turísticas (${vt.at(-1) || ""})`)}
    ${stat(m.vut_pct != null ? `${fmt(m.vut_pct, 2)}%` : "—", "del total de viviendas")}
    ${stat(m.vut_plazas != null ? fmt(m.vut_plazas) : "—", "plazas")}
    ${stat(m.vt_var_pct != null ? pct(m.vt_var_pct) : "—", "vs mismo mes del año anterior")}
  </div>${m.vt?.some((x) => x) ? `<div style="color:var(--d4)">${sparkline(m.vt.map((x) => x || 0), { w: 300, h: 40 })}</div><p class="small muted" style="margin:0">${vt[0]} → ${vt.at(-1)}</p>` : ""}</div>`;
  if (p) {
    h += `<div><h3 style="font-size:1rem;text-transform:none;margin-top:4px">Desahucios · partido judicial de ${esc(p.n)}</h3><div class="stats">
      ${stat(fmt(p.t.at(-1)), `lanzamientos ${LAST_PJ}`)}
      ${stat(fmt(p.tasa, 1), "por 100.000 hab.")}
      ${stat(p.lau != null ? fmt(p.lau) : "—", "por impago de alquiler")}
      ${stat(p.hip != null ? fmt(p.hip) : "—", "por ejecución hipotecaria")}
    </div><div style="color:var(--d4)">${sparkline(p.t.map((x) => x || 0), { w: 300, h: 40 })}</div><p class="small muted" style="margin:0">${PJ.years[0]}–${LAST_PJ}. El partido judicial agrupa varios municipios; el CGPJ no da la cifra de cada uno.</p></div>`;
  }
  h += `<button type="button" class="theme-btn" style="color:var(--ink);border-color:var(--line);padding:8px 12px" data-calc>Calcular mi esfuerzo en ${esc(m.n)} →</button>`;
  return h;
}

// ---------- ranking ----------
function renderRanking() {
  const L_ = LAYERS[layer];
  $("#rankTitle").textContent = L_.cat ? "Zonas tensionadas más pobladas" : `Ranking: ${L_.label}`;
  const rows = Object.entries(I)
    .filter(([c, m]) => (m.pob || 0) >= 20000 && value(c) != null)
    .map(([c, m]) => ({ code: c, n: m.n, ccaa: CCAA[m.c], pob: m.pob, v: value(c), alq: m.alq_mes, vut: m.vut_pct }));
  sortableTable($("#rankTable"), [
    { key: "n", label: "Municipio", render: (r) => `<a href="#m-${r.code}" data-go="${r.code}">${esc(r.n)}</a>` },
    { key: "ccaa", label: "Comunidad" },
    { key: "pob", label: "Habitantes", num: true, render: (r) => fmt(r.pob) },
    { key: "v", label: L_.cat ? "Estado" : L_.label, num: !L_.cat, render: (r) => L_.f(r.v) },
    { key: "alq", label: "Alquiler €/mes", num: true, render: (r) => (r.alq ? fmt(r.alq) : "—") },
    { key: "vut", label: "Pisos turísticos", num: true, render: (r) => (r.vut != null ? `${fmt(r.vut, 2)}%` : "—") },
  ], L_.cat ? rows.sort((a, b) => b.pob - a.pob).slice(0, 40) : rows, { sortKey: L_.cat ? "pob" : "v" });
}
document.addEventListener("click", (e) => {
  const a = e.target.closest("a[data-go]");
  if (a) { e.preventDefault(); select(a.dataset.go); $("#mapa").scrollIntoView(); }
});

// ---------- buscador ----------
const opts = Object.entries(I).sort((a, b) => (b[1].pob || 0) - (a[1].pob || 0));
$("#mList").innerHTML = opts.map(([c, m]) => `<option value="${esc(m.n)} (${c})">${esc(CCAA[m.c] || "")}</option>`).join("");
$("#mSearch").addEventListener("change", (e) => {
  const code = e.target.value.match(/\((\d{5})\)$/)?.[1]
    || opts.find(([, m]) => m.n.toLowerCase() === e.target.value.trim().toLowerCase())?.[0];
  if (code) { select(code); $("#mapa").scrollIntoView(); }
});

// ---------- calculadora ----------
const PRE = Object.fromEntries((precios?.ccaa || []).map((x) => [x.code, x]));
renderCalculadora($("#calcBody"), { PRE }, M);

// ---------- fuentes ----------
const seen = new Set();
$("#sources").innerHTML = `<ul>${Object.entries(meta).filter(([, v]) => v?.url && !seen.has(v.url) && seen.add(v.url))
  .map(([, v]) => `<li>${link(v.url, v.source)}${v.period ? ` · ${esc(v.period)}` : ""}</li>`).join("")}
  ${PJ?.meta?.lanz ? `<li>${link(PJ.meta.lanz.url, PJ.meta.lanz.source)} · ${esc(PJ.meta.lanz.period)}</li><li>${link(PJ.meta.mapping.url, PJ.meta.mapping.source)} (municipios de cada partido judicial)</li>` : ""}</ul>`;

redraw();
const fromHash = location.hash.match(/^#m-(\d{5})$/)?.[1];
select(fromHash && I[fromHash] ? fromHash : "28079", !!fromHash);
