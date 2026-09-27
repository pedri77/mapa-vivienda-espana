import { $, fmt, eur, pct, esc, load, ago, dateEs, link, quantileBreaks, classOf, cssVar, sparkline, sortableTable, CCAA } from "./util.js";
import { renderLegislacion } from "./legislacion.js";
import { renderAyudas } from "./ayudas.js";

// ---------- tema ----------
const THEME_KEY = "techo-theme";
function applyTheme(t) {
  if (t) document.documentElement.dataset.theme = t;
  else delete document.documentElement.dataset.theme;
}
try { applyTheme(localStorage.getItem(THEME_KEY)); } catch {}
const isDark = () =>
  document.documentElement.dataset.theme === "dark" ||
  (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
$("#themeBtn").addEventListener("click", () => {
  const next = isDark() ? "light" : "dark";
  applyTheme(next);
  try { localStorage.setItem(THEME_KEY, next); } catch {}
  window.dispatchEvent(new Event("themechange"));
});

// ---------- datos ----------
const names = ["desahucios", "precios", "salarios", "fondos", "acampadas", "senales", "noticias", "medios", "legislacion", "ayudas", "ccaa"];
const D = Object.fromEntries(await Promise.all(names.map(async (n) => [n, await (n === "ccaa" ? loadGeo() : load(n))])));
async function loadGeo() {
  try { return await (await fetch("data/ccaa.geojson")).json(); } catch { return null; }
}

// Índices por código INE
const byCode = (arr) => Object.fromEntries((arr || []).map((x) => [x.code, x]));
const DES = byCode(D.desahucios?.ccaa);
const PRE = byCode(D.precios?.ccaa);
const SAL = byCode(D.salarios?.ccaa);
const LEG = byCode(D.legislacion?.ccaa);
const AYU = byCode(D.ayudas?.ccaa);
const LAST_YEAR = D.desahucios ? String(D.desahucios.national.at(-1).year) : "2025";

const ctx = { D, DES, PRE, SAL, LEG, AYU, LAST_YEAR };

renderKpis();
renderDirecto();
const mapApi = renderMapa();
renderDesahucios();
renderPrecios();
renderFondos();
renderMedios();
safe(() => renderLegislacion(D.legislacion, $("#legBody"), ctx), "#legBody");
safe(() => renderAyudas(D.ayudas, $("#ayuBody"), ctx), "#ayuBody");
renderSources();
observeNav();

function safe(fn, sel) {
  try { fn(); } catch (e) {
    console.error(e);
    $(sel).innerHTML = `<div class="empty">No se pudo mostrar esta sección.</div>`;
  }
}

// ---------- KPIs ----------
function renderKpis() {
  const k = [];
  const nat = D.desahucios?.national;
  if (nat) {
    const a = nat.at(-1), b = nat.at(-2);
    k.push({ v: fmt(a.total), l: `desahucios practicados en ${a.year}`, s: `${pct(((a.total - b.total) / b.total) * 100)} vs ${b.year} · ${fmt((a.alquiler / a.total) * 100)}% por alquiler` });
  }
  const pn = D.precios?.national;
  if (pn) {
    k.push({ v: `${fmt(pn.venta_m2_mivau_2T2026)} €/m²`, l: "precio de venta (valor tasado, 2T 2026)", s: `${pct(pn.venta_m2_mivau_yoy_2T2026_pct)} interanual · MIVAU` });
    k.push({ v: `${fmt(pn.alquiler_80m2_fotocasa_ago2026)} €/mes`, l: "alquilar 80 m² (oferta, ago. 2026)", s: `${fmt(pn.alquiler_m2_fotocasa_ago2026, 1)} €/m² · Fotocasa` });
  }
  if (D.salarios) k.push({ v: eur(D.salarios.national.mediana), l: "salario bruto mediano anual (2024)", s: "la mitad de asalariados cobra menos · INE" });
  const sol = D.acampadas?.camps?.find((c) => c.status === "activa");
  if (sol) {
    const days = Math.max(1, Math.floor((Date.now() - new Date(sol.start_date + "T00:00:00")) / 864e5) + 1);
    k.push({ v: `Día ${days}`, l: `acampada en ${sol.place?.split("(")[0].trim() || sol.city}`, s: `desde el ${dateEs(sol.start_date)}` });
  }
  $("#kpis").innerHTML = k.map((x) => `<div class="kpi"><span class="v">${x.v}</span><span class="l">${x.l}</span><span class="s">${x.s}</span></div>`).join("");
  const gen = D.noticias?.generated_at;
  if (gen) $("#heroUpdated").textContent = `Noticias actualizadas ${ago(gen)}`;
  if (sol) $("#heroLive").hidden = false;
}

// ---------- directo ----------
function renderDirecto() {
  const A = D.acampadas;
  if (A?.summary) $("#movSummary").textContent = A.summary;
  const order = { activa: 0, convocada: 1, finalizada: 2, desalojada: 3 };
  const camps = [...(A?.camps || [])].sort((a, b) => (order[a.status] ?? 9) - (order[b.status] ?? 9));
  const pill = (s) => (s === "activa" ? `<span class="pill live">Activa</span>` : s === "convocada" ? `<span class="pill warn">Convocada</span>` : `<span class="pill">${esc(s)}</span>`);
  $("#camps").innerHTML = camps.length
    ? camps.map((c) => `<article class="camp">
        <h3>${esc(c.city)} ${pill(c.status)} ${c.verified === false ? `<span class="pill">Sin verificar</span>` : ""}</h3>
        <dl>
          ${c.place ? `<dt>Lugar</dt><dd>${esc(c.place)}</dd>` : ""}
          ${c.start_date ? `<dt>Inicio</dt><dd>${dateEs(c.start_date)}</dd>` : ""}
          ${c.organizers ? `<dt>Convoca</dt><dd>${esc(c.organizers)}</dd>` : ""}
          ${c.participants_estimate ? `<dt>Asistencia</dt><dd>${esc(c.participants_estimate)}</dd>` : ""}
          ${c.planned_until ? `<dt>Hasta</dt><dd>${esc(c.planned_until)}</dd>` : ""}
        </dl>
        <div class="small">${(c.sources || []).slice(0, 3).map((s) => link(s.url, s.outlet || s.title)).join(" · ")}</div>
      </article>`).join("") +
      (A.related || []).map((r) => `<article class="camp"><h3>${esc(r.city)} <span class="pill">${esc(r.type)}</span></h3><p class="small" style="margin:0">${dateEs(r.date)} · ${esc(r.organizers)}. ${esc(r.note)}</p></article>`).join("")
    : `<div class="empty">No hay acampadas registradas ahora mismo.</div>`;

  const items = D.noticias?.items || [];
  const tabs = [["acampadas", "Acampadas"], ["desahucios", "Desahucios"], ["alquiler", "Alquiler"], ["politica", "Política"], ["", "Todo"]];
  let cur = "acampadas";
  const draw = () => {
    const list = items.filter((n) => !cur || n.topics.includes(cur)).slice(0, 40);
    $("#feed").innerHTML = list.length
      ? list.map((n) => `<li><a href="${esc(n.url)}" target="_blank" rel="noopener">${esc(n.title)}</a><span class="meta"><span>${esc(n.outlet)}</span><span>${ago(n.date)}</span>${n.city ? `<span>${esc(n.city)}</span>` : ""}</span></li>`).join("")
      : `<li class="muted">Sin noticias en esta categoría.</li>`;
    $("#feedTabs").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.t === cur));
  };
  $("#feedTabs").innerHTML = tabs.map(([t, l]) => `<button type="button" data-t="${t}">${l}</button>`).join("");
  $("#feedTabs").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (b) { cur = b.dataset.t; draw(); }
  });
  draw();
  $("#feedNote").textContent = D.noticias
    ? `${fmt(items.length)} noticias recogidas automáticamente. Última actualización ${ago(D.noticias.generated_at)}. Los titulares enlazan al medio original.`
    : "El feed de noticias aún no está disponible.";
}

// ---------- mapa ----------
function renderMapa() {
  if (!window.L || !D.ccaa) {
    $("#map").innerHTML = `<div class="empty">No se pudo cargar el mapa.</div>`;
    return null;
  }
  const ramp = (p) => [1, 2, 3, 4, 5].map((i) => `--${p}${i}`);
  const LAYERS = {
    des: { label: "Desahucios", title: `Desahucios por 100.000 hab. (${LAST_YEAR})`, ramp: ramp("d"), get: (c) => DES[c]?.rate_per_100k_2025?.total, f: (v) => fmt(v, 1) },
    venta: { label: "Venta €/m²", title: "Valor tasado €/m² (MIVAU, 2T 2026)", ramp: ramp("p"), get: (c) => PRE[c]?.venta_m2_latest, f: (v) => `${fmt(v)} €` },
    subida: { label: "Subida venta", title: "Variación interanual valor tasado (%)", ramp: ramp("d"), get: (c) => PRE[c]?.venta_m2_latest_meta?.yoy_pct, f: (v) => pct(v) },
    alquiler: { label: "Alquiler €/m²", title: "Alquiler €/m²/mes (oferta Fotocasa, ago. 2026)", ramp: ramp("r"), get: (c) => PRE[c]?.alquiler_m2_latest, f: (v) => `${fmt(v, 1)} €` },
    esfuerzo: { label: "Esfuerzo alquiler", title: "% de la renta del hogar para alquilar 80 m²", ramp: ramp("d"), get: (c) => PRE[c]?.esfuerzo?.pct_renta_hogar_alquiler_80m2, f: (v) => `${fmt(v, 1)}%` },
    compra: { label: "Años para comprar", title: "Años de renta del hogar para comprar 80 m² (tasado)", ramp: ramp("d"), get: (c) => PRE[c]?.esfuerzo?.anios_renta_hogar_80m2_tasado, f: (v) => `${fmt(v, 1)} años` },
    salario: { label: "Salario medio", title: "Salario bruto medio anual (INE, 2024)", ramp: ramp("p"), get: (c) => SAL[c]?.media, f: (v) => eur(v) },
    mediano: { label: "Salario mediano", title: "Salario bruto mediano anual (INE, 2024): la mitad cobra menos", ramp: ramp("p"), get: (c) => SAL[c]?.mediana, f: (v) => eur(v) },
  };
  let layer = "des";
  let selected = null;

  const mk = (el, opts) => L.map(el, { zoomSnap: 0.25, attributionControl: el === "map", scrollWheelZoom: false, ...opts });
  const map = mk("map", { minZoom: 4.5, maxZoom: 9 });
  const inset = mk("mapCanarias", { zoomControl: false, dragging: false, doubleClickZoom: false, boxZoom: false, keyboard: false, touchZoom: false });
  map.fitBounds([[35.9, -9.4], [43.8, 4.4]]);
  inset.fitBounds([[27.6, -18.2], [29.45, -13.4]]);

  const esri = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas";
  const tileUrl = () => `${esri}/World_${isDark() ? "Dark" : "Light"}_Gray_Reference/MapServer/tile/{z}/{y}/{x}`;
  const baseUrl = () => `${esri}/World_${isDark() ? "Dark" : "Light"}_Gray_Base/MapServer/tile/{z}/{y}/{x}`;
  const attrib = 'Teselas © <a href="https://www.esri.com/">Esri</a>, HERE, Garmin, © OpenStreetMap';
  map.createPane("labels");
  map.getPane("labels").style.zIndex = 450;
  map.getPane("labels").style.pointerEvents = "none";
  const base = L.tileLayer(baseUrl(), { attribution: attrib, maxNativeZoom: 16 }).addTo(map);
  const labels = L.tileLayer(tileUrl(), { pane: "labels", maxNativeZoom: 16 }).addTo(map);
  const baseIn = L.tileLayer(baseUrl(), { maxNativeZoom: 16 }).addTo(inset);

  let breaks = [];
  const style = (f) => {
    const L_ = LAYERS[layer];
    const v = L_.get(f.properties.code);
    const k = classOf(v, breaks);
    return {
      fillColor: k < 0 ? cssVar("--surface-2") : cssVar(L_.ramp[k]),
      fillOpacity: k < 0 ? 0.5 : 0.82,
      color: f.properties.code === selected ? cssVar("--ink") : cssVar("--surface"),
      weight: f.properties.code === selected ? 2.5 : 1,
    };
  };
  const onEach = (f, lyr) => {
    lyr.on({
      mouseover: (e) => e.target.setStyle({ weight: 2.5, color: cssVar("--ink") }),
      mouseout: (e) => geo.forEach((g) => g.resetStyle(e.target)),
      click: () => select(f.properties.code),
    });
    lyr.bindTooltip(() => {
      const L_ = LAYERS[layer];
      return `${esc(CCAA[f.properties.code])}<br>${L_.f(L_.get(f.properties.code))}`;
    }, { sticky: true, className: "tt" });
  };
  const geo = [map, inset].map((m) => L.geoJSON(D.ccaa, { style, onEachFeature: onEach }).addTo(m));

  // acampadas confirmadas y señales de prensa
  const campLayer = [L.layerGroup().addTo(map), L.layerGroup().addTo(inset)];
  for (const c of D.acampadas?.camps || []) {
    if (c.lat == null) continue;
    const m = L.marker([c.lat, c.lng], { icon: L.divIcon({ className: "", html: `<div class="camp-marker ${esc(c.status)}"></div>`, iconSize: [18, 18] }), zIndexOffset: 1000 });
    m.bindPopup(`<strong>${esc(c.city)}</strong> · ${esc(c.status)}<br>${esc(c.place || "")}<br>${c.start_date ? `Desde ${dateEs(c.start_date)}<br>` : ""}${(c.sources || []).slice(0, 2).map((s) => link(s.url, s.outlet || "Fuente")).join(" · ")}`);
    m.addTo(c.ccaa_code === "05" ? campLayer[1] : campLayer[0]);
  }
  const confirmed = new Set((D.acampadas?.camps || []).map((c) => c.city));
  for (const s of D.senales?.cities || []) {
    if (confirmed.has(s.city)) continue;
    const r = Math.min(26, 8 + Math.sqrt(s.mentions) * 4);
    const m = L.marker([s.lat, s.lng], { icon: L.divIcon({ className: "", html: `<div class="signal-marker" style="width:${r}px;height:${r}px"></div>`, iconSize: [r, r] }) });
    m.bindPopup(`<strong>${esc(s.city)}</strong>: ${s.mentions} menciones de acampadas en ${s.outlets} medios (14 días). Señal automática, no confirma una acampada.<br>${s.latest.slice(0, 3).map((n) => link(n.url, n.title)).join("<br>")}`);
    m.addTo(s.ccaa === "05" ? campLayer[1] : campLayer[0]);
  }

  function redraw() {
    breaks = quantileBreaks(Object.keys(CCAA).map((c) => LAYERS[layer].get(c)));
    geo.forEach((g) => g.setStyle(style));
    const L_ = LAYERS[layer];
    const ends = [breaks[0], breaks.at(-1)];
    $("#legend").innerHTML = `<strong>${esc(L_.title)}</strong><div class="ramp">${L_.ramp.map((v) => `<span style="background:var(${v})"></span>`).join("")}</div><div class="ends"><span>&lt; ${L_.f(ends[0])}</span><span>≥ ${L_.f(ends[1])}</span></div>`;
    $("#layerBtns").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.l === layer));
  }
  $("#layerBtns").innerHTML = Object.entries(LAYERS).map(([k, v]) => `<button type="button" data-l="${k}">${v.label}</button>`).join("");
  $("#layerBtns").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (b) { layer = b.dataset.l; redraw(); }
  });

  function select(code) {
    selected = code;
    geo.forEach((g) => g.setStyle(style));
    $("#side").innerHTML = sideHtml(code);
  }
  window.addEventListener("themechange", () => {
    base.setUrl(baseUrl()); labels.setUrl(tileUrl()); baseIn.setUrl(baseUrl());
    redraw();
  });
  redraw();
  select("13");
  return { select };
}

function sideHtml(code) {
  const d = DES[code], p = PRE[code], s = SAL[code], lg = LEG[code], ay = AYU[code];
  const y = d?.years?.[LAST_YEAR];
  const prev = d?.years?.[String(+LAST_YEAR - 1)];
  const series = d ? Object.keys(d.years).sort().map((k) => d.years[k].total) : [];
  const note = code === "18" || code === "19" ? `<p class="note">El CGPJ incluye Ceuta y Melilla en el TSJ de Andalucía. Estas cifras proceden del desglose por partido judicial y ya están sumadas en Andalucía.</p>` : code === "01" ? `<p class="note">Cifra del TSJ de Andalucía, que incluye Ceuta y Melilla. La tasa usa la población de las tres.</p>` : "";
  const stat = (v, l) => `<div><b>${v}</b><span>${l}</span></div>`;
  let h = `<p class="eyebrow">Ficha</p><h3>${esc(CCAA[code])}</h3>`;
  h += `<div class="stats">
    ${stat(fmt(y?.total), `desahucios ${LAST_YEAR}`)}
    ${stat(fmt(d?.rate_per_100k_2025?.total, 1), "por 100.000 hab.")}
    ${stat(y && prev ? pct(((y.total - prev.total) / prev.total) * 100) : "—", `vs ${+LAST_YEAR - 1}`)}
    ${stat(y ? `${fmt((y.alquiler / y.total) * 100)}%` : "—", "por impago de alquiler")}
  </div>`;
  if (series.length) h += `<div><span class="small muted">Desahucios 2013–${LAST_YEAR}</span><div style="color:var(--d4)">${sparkline(series, { w: 300, h: 44 })}</div></div>`;
  h += note;
  if (p) {
    h += `<div class="stats">
      ${stat(p.venta_m2_latest ? `${fmt(p.venta_m2_latest)} €` : "—", "€/m² tasado (2T 2026)")}
      ${stat(pct(p.venta_m2_latest_meta?.yoy_pct), "interanual")}
      ${stat(p.alquiler_m2_latest ? `${fmt(p.alquiler_m2_latest, 1)} €` : "—", "alquiler €/m²/mes")}
      ${stat(p.alquiler_80m2_mes_latest ? `${fmt(p.alquiler_80m2_mes_latest)} €` : "—", "80 m² al mes")}
      ${stat(p.esfuerzo?.pct_renta_hogar_alquiler_80m2 != null ? `${fmt(p.esfuerzo.pct_renta_hogar_alquiler_80m2, 1)}%` : "—", "renta del hogar en alquiler")}
      ${stat(p.esfuerzo?.anios_renta_hogar_80m2_tasado != null ? fmt(p.esfuerzo.anios_renta_hogar_80m2_tasado, 1) : "—", "años de renta para comprar 80 m²")}
    </div>`;
  }
  if (s?.media) h += `<div class="stats">${stat(eur(s.media), "salario medio bruto")}${stat(eur(s.mediana), "salario mediano bruto")}</div>`;
  if (lg) {
    const gov = lg.government;
    const zt = lg.zonas_tensionadas;
    h += `<div><h3 style="font-size:1rem;text-transform:none">Gobierno y Ley de Vivienda</h3><p class="small" style="margin:0">
      ${gov ? `${esc((gov.parties || []).join(" + "))}${gov.president ? `, ${esc(gov.president)}` : ""}.<br>` : ""}
      Zonas tensionadas: ${zt?.declared === true ? `<span class="pill ok">Declaradas</span>` : zt?.declared === false ? `<span class="pill bad">No declaradas</span>` : "sin dato"}
      ${lg.recurso_tc?.filed ? ` · <span class="pill">Recurrió la ley al TC</span>` : ""}</p></div>`;
  }
  if (ay?.ayudas?.length) h += `<div><h3 style="font-size:1rem;text-transform:none">Ayudas al alquiler</h3><ul class="small" style="margin:0;padding-left:18px">${ay.ayudas.slice(0, 3).map((a) => `<li>${link(a.url, a.name)}</li>`).join("")}</ul><a class="small" href="#ayudas" data-ccaa="${code}">Ver todas las ayudas y recursos →</a></div>`;
  return h;
}
document.addEventListener("click", (e) => {
  const a = e.target.closest("a[data-ccaa]");
  if (a) window.dispatchEvent(new CustomEvent("pickccaa", { detail: a.dataset.ccaa }));
});

// ---------- desahucios ----------
function renderDesahucios() {
  const X = D.desahucios;
  if (!X) return;
  const nat = X.national;
  const last = nat.at(-1), peak = nat.reduce((a, b) => (b.total > a.total ? b : a));
  const q = X.national_2026;
  $("#desIntro").innerHTML = `En ${last.year} se practicaron <strong>${fmt(last.total)}</strong> lanzamientos, un ${fmt((1 - last.total / peak.total) * 100)}% menos que en el máximo de ${peak.year} (${fmt(peak.total)}). El impago de alquiler supone ya el ${fmt((last.alquiler / last.total) * 100)}% del total, frente al ${fmt((peak.alquiler / peak.total) * 100)}% en ${peak.year}.${q?.Q1?.total ? ` En el primer trimestre de 2026 hubo ${fmt(q.Q1.total)} (${pct(q.Q1.var_interanual_total_pct)} interanual), aunque la moratoria dejó de estar en vigor en febrero. La PAH atribuye parte de la caída a retrasos procesales tras la obligatoriedad del MASC.` : ""}`;

  const keys = [["alquiler", "--d4", "Alquiler (LAU)"], ["hipotecario", "--p4", "Ejecución hipotecaria"], ["otros", "--d2", "Otros"]];
  const W = 900, H = 320, m = { t: 24, r: 10, b: 28, l: 52 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const max = Math.ceil(peak.total / 10000) * 10000;
  const bw = iw / nat.length;
  const y = (v) => m.t + ih - (v / max) * ih;
  let svg = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Lanzamientos practicados por año y tipo, ${nat[0].year}-${last.year}"><g class="grid">`;
  for (let v = 0; v <= max; v += 10000) svg += `<line x1="${m.l}" x2="${W - m.r}" y1="${y(v)}" y2="${y(v)}"/><text x="${m.l - 8}" y="${y(v) + 4}" text-anchor="end">${fmt(v)}</text>`;
  svg += `</g>`;
  nat.forEach((d, i) => {
    let acc = 0;
    const x = m.l + i * bw + bw * 0.15;
    for (const [k, c] of keys) {
      const v = d[k] || 0;
      svg += `<rect x="${x}" y="${y(acc + v)}" width="${bw * 0.7}" height="${y(acc) - y(acc + v)}" fill="var(${c})"><title>${d.year} · ${k}: ${fmt(v)}</title></rect>`;
      acc += v;
    }
    svg += `<text x="${x + bw * 0.35}" y="${H - 8}" text-anchor="middle">${d.year}</text>`;
    if (d.year === peak.year || d.year === last.year) svg += `<text x="${x + bw * 0.35}" y="${y(d.total) - 6}" text-anchor="middle" style="fill:var(--ink);font-weight:600">${fmt(d.total)}</text>`;
  });
  const annots = [[2020, "Moratoria (RDL 11/2020)"], [2023, "Ley 12/2023"], [2025, "MASC obligatorio"]];
  annots.forEach(([yr, t], j) => {
    const i = nat.findIndex((d) => d.year === yr);
    if (i < 0) return;
    const x = m.l + i * bw + bw / 2;
    const ty = m.t + 12 + j * 14;
    svg += `<g class="annot"><line x1="${x}" x2="${x}" y1="${ty + 4}" y2="${y(nat[i].total) - (nat[i].year === last.year ? 20 : 4)}"/><text x="${x - 4}" y="${ty}" text-anchor="end">${t}</text></g>`;
  });
  svg += `</svg>`;
  $("#desChart").innerHTML = svg;
  $("#desKeys").innerHTML = keys.map(([, c, l]) => `<span><i style="background:var(${c})"></i>${l}</span>`).join("");

  const rows = X.ccaa.filter((c) => !["18", "19"].includes(c.code)).map((c) => {
    const a = c.years[LAST_YEAR], b = c.years[String(+LAST_YEAR - 1)], z = c.years["2019"];
    return { name: CCAA[c.code], total: a?.total, tasa: c.rate_per_100k_2025?.total, alq: a ? (a.alquiler / a.total) * 100 : null,
      var1: a && b ? ((a.total - b.total) / b.total) * 100 : null, var19: a && z ? ((a.total - z.total) / z.total) * 100 : null,
      hip: a?.hipotecario, series: Object.keys(c.years).sort().map((k) => c.years[k].total) };
  });
  const maxT = Math.max(...rows.map((r) => r.tasa || 0));
  sortableTable($("#desTable"), [
    { key: "name", label: "Comunidad" },
    { key: "total", label: `Total ${LAST_YEAR}`, num: true, render: (r) => fmt(r.total) },
    { key: "tasa", label: "Por 100.000 hab.", render: (r) => `<span class="bar-cell"><i style="width:${(r.tasa / maxT) * 90}px"></i>${fmt(r.tasa, 1)}</span>` },
    { key: "alq", label: "% alquiler", num: true, render: (r) => `${fmt(r.alq)}%` },
    { key: "hip", label: "Hipotecarios", num: true, render: (r) => fmt(r.hip) },
    { key: "var1", label: `vs ${+LAST_YEAR - 1}`, num: true, render: (r) => pct(r.var1) },
    { key: "var19", label: "vs 2019", num: true, render: (r) => pct(r.var19) },
    { key: "series", label: "2013–" + LAST_YEAR, render: (r) => `<span style="color:var(--d4)">${sparkline(r.series)}</span>` },
  ], rows, { sortKey: "tasa" });
  $("#desNotes").innerHTML = (X.notes || []).slice(0, 4).map((n) => `<p class="note">${esc(n)}</p>`).join("");
}

// ---------- precios ----------
function renderPrecios() {
  const P = D.precios;
  if (!P) return;
  const n = P.national;
  $("#preIntro").innerHTML = `El valor tasado medio de la vivienda libre es de <strong>${fmt(n.venta_m2_mivau_2T2026)} €/m²</strong> (${pct(n.venta_m2_mivau_yoy_2T2026_pct)} en un año). En portales, el precio de oferta llega a ${fmt(n.venta_m2_fotocasa_ago2026)} €/m² (Fotocasa) y el alquiler a ${fmt(n.alquiler_m2_fotocasa_ago2026, 1)} €/m² al mes. Tasación y oferta miden cosas distintas y no se mezclan.`;
  const rows = P.ccaa.map((c) => ({
    name: CCAA[c.code], venta: c.venta_m2_latest, yoy: c.venta_m2_latest_meta?.yoy_pct, oferta: c.venta_m2_fotocasa_ago2026,
    alq: c.alquiler_m2_latest, alq80: c.alquiler_80m2_mes_latest, esf: c.esfuerzo?.pct_renta_hogar_alquiler_80m2,
    anios: c.esfuerzo?.anios_renta_hogar_80m2_tasado, renta: c.renta_hogar,
    series: Object.keys(c.venta_series || {}).sort().map((k) => c.venta_series[k]),
  }));
  const serie = n.venta_m2_mivau_series || {};
  const comp = n.compraventas_viviendas_ine_etdp || {};
  const ini = n.viviendas_libres_iniciadas_mivau || {};
  const lastIni = Object.keys(ini).sort().at(-1);
  const top = (arr, k, f) => `<ol class="small" style="margin:0;padding-left:20px">${(arr || []).slice(0, 10).map((x) => `<li>${esc(x.city)} <strong class="num">${f(x[k])}</strong></li>`).join("")}</ol>`;
  $("#preBody").innerHTML = `
    <div class="grid-3">
      <div class="card"><h3>Valor tasado, España</h3><p class="small muted">€/m², media anual (MIVAU)</p><div style="color:var(--p4)">${sparkline(Object.values(serie), { w: 300, h: 60 })}</div><p class="small">${Object.keys(serie)[0]}: ${fmt(Object.values(serie)[0])} € → ${Object.keys(serie).at(-1)}: <strong>${fmt(Object.values(serie).at(-1))} €</strong></p></div>
      <div class="card"><h3>Compraventas de vivienda</h3><p class="small muted">Por año (INE, ETDP)</p><div style="color:var(--p4)">${sparkline(Object.entries(comp).filter(([k]) => /^\d{4}$/.test(k)).map(([, v]) => v), { w: 300, h: 60 })}</div><p class="small">2015: ${fmt(comp["2015"])} → 2025: <strong>${fmt(comp["2025"])}</strong>${comp["2026_ene-jul"] ? ` · ene-jul 2026: ${fmt(comp["2026_ene-jul"])}` : ""}</p></div>
      <div class="card"><h3>Se construye poco</h3><p class="small muted">Viviendas libres iniciadas (MIVAU)</p><div style="color:var(--p4)">${sparkline(Object.values(ini), { w: 300, h: 60 })}</div><p class="small">${lastIni}: <strong>${fmt(ini[lastIni])}</strong>, frente a ${fmt(n.iniciadas_2006_pico_libre)} en el pico de 2006.</p></div>
    </div>
    <h3 style="margin-top:32px">Por comunidad</h3>
    <div class="table-wrap" id="preTable"></div>
    <div class="grid-3" style="margin-top:28px">
      <div class="card"><h3>Capitales más caras para comprar</h3><p class="small muted">Valor tasado €/m², 2T 2026 (MIVAU)</p>${top(P.cities?.venta?.mivau_valor_tasado_2T2026_capitales, "eur_m2", (v) => `${fmt(v)} €`)}</div>
      <div class="card"><h3>Ciudades más caras para alquilar</h3><p class="small muted">€/m²/mes, agosto 2026 (Idealista)</p>${top(P.cities?.alquiler?.idealista_ago2026, "eur_m2_mes", (v) => `${fmt(v, 1)} €`)}</div>
      <div class="card"><h3>Vivienda social</h3><p class="small muted">% del parque de vivienda</p><p class="small"><strong>España:</strong> ${esc(n.vivienda_social_pct_parque?.espana)}</p><p class="small"><strong>UE:</strong> ${esc(n.vivienda_social_pct_parque?.ue_media)}</p><p class="small muted">Las estimaciones varían entre fuentes; no hay un dato oficial único.</p></div>
    </div>
    ${(P.notes || []).map((x) => `<p class="note">${esc(x)}</p>`).join("")}`;
  sortableTable($("#preTable"), [
    { key: "name", label: "Comunidad" },
    { key: "venta", label: "Tasado €/m²", num: true, render: (r) => fmt(r.venta) },
    { key: "yoy", label: "Interanual", num: true, render: (r) => pct(r.yoy) },
    { key: "oferta", label: "Oferta €/m²", num: true, render: (r) => fmt(r.oferta) },
    { key: "alq", label: "Alquiler €/m²", num: true, render: (r) => fmt(r.alq, 1) },
    { key: "alq80", label: "80 m²/mes", num: true, render: (r) => (r.alq80 ? `${fmt(r.alq80)} €` : "—") },
    { key: "esf", label: "% renta hogar", num: true, render: (r) => (r.esf != null ? `${fmt(r.esf, 1)}%` : "—") },
    { key: "anios", label: "Años comprar", num: true, render: (r) => fmt(r.anios, 1) },
    { key: "series", label: "Tasado 2015–25", render: (r) => `<span style="color:var(--p4)">${sparkline(r.series)}</span>` },
  ], rows, { sortKey: "esf" });
}

// ---------- fondos ----------
function renderFondos() {
  const F = D.fondos;
  if (!F) return;
  const isCivio = (e) => e.units && e.units_year === 2022 && (e.source_urls || []).some((u) => u.includes("civio.es")) && !/^Otros|Ares/.test(e.name);
  const civ = F.entities.filter(isCivio).sort((a, b) => b.units - a.units);
  const max = Math.max(...civ.map((e) => e.units));
  const short = (n) => n.split("(")[0].trim();
  $("#fonChartSub").innerHTML = `Datos de fianzas depositadas en 11 comunidades, 2022-2023. Fuente: ${link("https://civio.es/poder/2024/04/02/caixabank-y-blackstone-los-dos-mayores-caseros-del-pais-suman-cerca-de-41-dot-400-viviendas-alquiladas", "Civio")}.`;
  $("#fonChart").innerHTML = civ.map((e) => `<span>${esc(short(e.name))}</span><div class="track"><div class="fill" style="width:${(e.units / max) * 100}%"></div><span class="val" style="${e.units / max < 0.2 ? `left:calc(${(e.units / max) * 100}% + 8px);color:var(--ink)` : ""}">${fmt(e.units)}</span></div>`).join("");

  const pick = ["Viviendas alquiladas por empresas", "Total megatenedores", "Viviendas en manos de fondos", "Viviendas en manos de bancos", "Peso de megatenedores en la Comunidad de Madrid", "Banco de Espa", "Barcelona: desahucios instados", "Barcelona: desahucios por fondos"];
  const agg = pick.map((p) => F.aggregates.find((a) => a.metric.startsWith(p))).filter(Boolean);
  $("#fonAgg").innerHTML = agg.map((a) => `<details><summary>${esc(a.metric)} <span class="muted small">(${a.year})</span></summary><p class="small">${esc(a.value)} · ${link(a.source_url, "fuente")}</p></details>`).join("");

  // Las ventas ("VENTA por X a Y") ya figuran como compra en la entidad compradora
  const acq = F.entities.flatMap((e) => (e.acquisitions || []).filter((a) => a.year && (a.units || a.price_eur) && !/^VENTA/i.test(a.seller || "")).map((a) => ({ ...a, buyer: short(e.name) })))
    .sort((a, b) => a.year - b.year);
  const verb = (a) => /^TRASPASO por/i.test(a.seller) ? `traspasa a ${esc(a.seller.replace(/^TRASPASO por [^ ]+ a /i, ""))}` : `compra a ${esc(a.seller)}`;
  $("#fonTimeline").innerHTML = acq.map((a) => `<li><span class="y">${a.year}</span> · <strong>${esc(a.buyer)}</strong> ${verb(a)}${a.units ? ` · ${fmt(a.units)} viviendas/activos` : ""}${a.price_eur ? ` · ${fmt(a.price_eur / 1e6)} M€` : ""}${a.location ? ` <span class="muted small">(${esc(a.location)})</span>` : ""}</li>`).join("");

  $("#fonEntities").innerHTML = F.entities.map((e) => `<details><summary>${esc(short(e.name))} <span class="muted small">${esc(e.origin || "")}</span></summary>
    <p class="small"><span class="pill">${esc(e.type)}</span> ${e.units ? `<strong>${fmt(e.units)}</strong> viviendas (${e.units_year})` : "Sin cifra pública de viviendas"}</p>
    <p class="small">${esc(e.notes || "")}</p>
    <p class="small">${(e.source_urls || []).slice(0, 4).map((u, i) => link(u, `fuente ${i + 1}`)).join(" · ")}</p></details>`).join("");
}

// ---------- medios ----------
function renderMedios() {
  const items = D.noticias?.items || [];
  if (!items.length) {
    $("#medTable").innerHTML = `<div class="empty">El monitor de medios aún no tiene datos.</div>`;
    return;
  }
  const M = D.medios;
  const now = Date.now();
  const days = Array.from({ length: 60 }, (_, i) => new Date(now - (59 - i) * 864e5).toISOString().slice(0, 10));
  const trendReady = M?.trend_ready;

  const daily = Object.fromEntries(days.map((d) => [d, 0]));
  items.forEach((n) => { const d = n.date.slice(0, 10); if (d in daily) daily[d]++; });
  const vals = Object.values(daily);
  const W = 900, H = 160, pad = 30, bw = (W - pad) / vals.length, mx = Math.max(1, ...vals);
  $("#medChart").innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Noticias por día, últimos 60 días"><g class="grid"><line x1="${pad}" x2="${W}" y1="${H - 20}" y2="${H - 20}"/></g>${vals
    .map((v, i) => `<rect x="${pad + i * bw + 1}" y="${H - 20 - (v / mx) * (H - 40)}" width="${bw - 2}" height="${(v / mx) * (H - 40)}" fill="var(--ink)" opacity="${i >= vals.length - 7 ? 1 : 0.45}"><title>${days[i]}: ${v}</title></rect>`)
    .join("")}<text x="${pad}" y="${H - 4}">${dateEs(days[0])}</text><text x="${W}" y="${H - 4}" text-anchor="end">hoy</text><text x="${pad - 6}" y="24" text-anchor="end">${mx}</text></svg>`;

  const topics = [["", "Todos"], ["acampadas", "Acampadas"], ["desahucios", "Desahucios"], ["alquiler", "Alquiler"], ["precios", "Precios"], ["fondos", "Fondos"], ["politica", "Política"], ["protesta", "Protestas"]];
  let cur = "";
  let all = false;
  const draw = () => {
    const d7 = now - 7 * 864e5, d14 = now - 14 * 864e5, d30 = now - 30 * 864e5;
    const by = {};
    for (const n of items) {
      if (cur && !n.topics.includes(cur)) continue;
      (by[n.outlet_key] ||= { name: n.outlet, list: [] }).list.push(n);
    }
    const rows = Object.values(by).map((o) => {
      const t = o.list.map((n) => +new Date(n.date));
      const last7 = t.filter((x) => x >= d7).length, prev7 = t.filter((x) => x >= d14 && x < d7).length;
      const dd = Object.fromEntries(days.slice(-30).map((d) => [d, 0]));
      o.list.forEach((n) => { const k = n.date.slice(0, 10); if (k in dd) dd[k]++; });
      const tc = {};
      o.list.forEach((n) => n.topics.forEach((x) => (tc[x] = (tc[x] || 0) + 1)));
      return { name: o.name, last7, prev7, last30: t.filter((x) => x >= d30).length, total: o.list.length,
        trend: !trendReady ? null : last7 === prev7 ? 0 : prev7 === 0 ? 1 : (last7 - prev7) / prev7,
        spark: Object.values(dd), topics: Object.entries(tc).sort((a, b) => b[1] - a[1]).slice(0, 2).map(([k]) => k), latest: o.list[0] };
    }).filter((r) => r.total >= 2);
    const chip = (r) => r.trend == null ? `<span class="pill">Calculando</span>` : r.trend >= 0.25 ? `<span class="pill bad">▲ Sube</span>` : r.trend <= -0.25 ? `<span class="pill ok">▼ Baja</span>` : `<span class="pill">Estable</span>`;
    sortableTable($("#medTable"), [
      { key: "name", label: "Medio" },
      { key: "last7", label: "7 días", num: true },
      { key: "prev7", label: "7 previos", num: true },
      { key: "last30", label: "30 días", num: true },
      { key: "trend", label: "Tendencia", render: chip },
      { key: "spark", label: "Últimos 30 días", render: (r) => sparkline(r.spark) },
      { key: "topics", label: "Temas", render: (r) => r.topics.map((t) => `<span class="pill">${esc(t)}</span>`).join(" ") },
      { key: "latest", label: "Último titular", render: (r) => `<a href="${esc(r.latest.url)}" target="_blank" rel="noopener">${esc(r.latest.title.slice(0, 90))}${r.latest.title.length > 90 ? "…" : ""}</a> <span class="muted small">${ago(r.latest.date)}</span>` },
    ], all ? rows : [...rows].sort((a, b) => b.last7 - a.last7 || b.total - a.total).slice(0, 25), { sortKey: "last7" });
    $("#medMore").hidden = rows.length <= 25;
    $("#medMore").textContent = all ? "Ver solo los 25 principales" : `Ver los ${rows.length} medios`;
    $("#medTopics").querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", b.dataset.t === cur));
  };
  $("#medTopics").innerHTML = topics.map(([t, l]) => `<button type="button" data-t="${t}">${l}</button>`).join("");
  $("#medMore").addEventListener("click", () => { all = !all; draw(); });
  $("#medTopics").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { cur = b.dataset.t; draw(); } });
  draw();
  $("#medNote").innerHTML = `Recogida desde el ${dateEs(M?.history_since || D.noticias.history_since)}. ${trendReady ? "La tendencia compara los últimos 7 días con los 7 anteriores (±25%)." : "La tendencia se mostrará cuando haya 14 días de histórico; antes, los datos de la semana previa están incompletos."} Google News agrega por medio de origen; un mismo titular solo se cuenta una vez.`;
}

// ---------- fuentes ----------
function renderSources() {
  const groups = [
    ["Desahucios", D.desahucios?.sources],
    ["Precios, renta y construcción", D.precios?.sources],
    ["Salarios", D.salarios?.sources],
    ["Grandes tenedores", (D.fondos?.sources || []).map((s) => (typeof s === "string" ? { url: s } : s))],
    ["Leyes y partidos", D.legislacion?.sources],
    ["Ayudas", D.ayudas?.sources],
    ["Acampadas", D.acampadas?.camps?.flatMap((c) => c.sources)],
  ];
  $("#sources").innerHTML = groups.filter(([, s]) => s?.length).map(([t, s]) => `<details><summary>${t} (${s.length})</summary><ul>${s.map((x) => {
    const o = typeof x === "string" ? { url: x } : x;
    const label = o.name || o.title || o.url;
    return `<li>${o.url ? link(o.url, label) : esc(label)}${o.period ? ` · ${esc(o.period)}` : ""}${o.accessed ? ` · consultado ${esc(o.accessed)}` : ""}</li>`;
  }).join("")}</ul></details>`).join("");
}

// ---------- navegación ----------
function observeNav() {
  const links = [...document.querySelectorAll(".nav a")];
  const io = new IntersectionObserver((es) => es.forEach((e) => {
    if (e.isIntersecting) links.forEach((a) => a.classList.toggle("active", a.getAttribute("href") === `#${e.target.id}`));
  }), { rootMargin: "-40% 0px -55% 0px" });
  document.querySelectorAll("section.block, footer").forEach((s) => io.observe(s));
}
