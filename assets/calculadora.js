import { $, fmt, esc, CCAA } from "./util.js";

// Umbrales de referencia para el esfuerzo en vivienda
const UMBRAL_ALTO = 30; // criterio habitual en políticas de vivienda
const UMBRAL_SOBRECARGA = 40; // "housing cost overburden" de Eurostat

// Cuota mensual de un préstamo francés
function cuota(capital, tipoAnual, anos) {
  const i = tipoAnual / 100 / 12;
  const n = anos * 12;
  return i === 0 ? capital / n : (capital * i) / (1 - (1 + i) ** -n);
}

export function renderCalculadora(el, ctx, municipios = null) {
  const { PRE } = ctx;
  const codes = Object.keys(CCAA).filter((c) => PRE[c]?.venta_m2_latest);
  el.innerHTML = `
    <div class="calc">
      <form class="card calc-form" id="calcForm" novalidate>
        <div class="field"><label for="cIng">Ingresos netos del hogar al mes</label>
          <div class="unit"><input id="cIng" type="number" inputmode="decimal" min="0" step="50" value="1800"><span>€</span></div>
          <small class="muted">Suma de nóminas y otros ingresos, después de impuestos.</small></div>
        <div class="field"><label for="cZona">Dónde</label>
          <select id="cZona">${codes.map((c) => `<option value="${c}">${esc(CCAA[c])}</option>`).join("")}</select>
          ${municipios ? `<input id="cMuni" type="search" list="cMuniList" placeholder="o escribe tu municipio" autocomplete="off"><datalist id="cMuniList"></datalist>` : ""}</div>
        <div class="field"><label for="cM2">Tamaño de la vivienda</label>
          <div class="unit"><input id="cM2" type="number" min="20" max="300" step="5" value="70"><span>m²</span></div></div>
        <div class="field"><label for="cAlq">Tu alquiler actual (opcional)</label>
          <div class="unit"><input id="cAlq" type="number" min="0" step="10" placeholder="—"><span>€/mes</span></div></div>
        <details><summary>Supuestos de la hipoteca</summary>
          <div class="field"><label for="cTipo">Tipo de interés anual</label><div class="unit"><input id="cTipo" type="number" min="0" max="15" step="0.1" value="3"><span>%</span></div></div>
          <div class="field"><label for="cAnos">Plazo</label><div class="unit"><input id="cAnos" type="number" min="5" max="40" step="1" value="30"><span>años</span></div></div>
          <div class="field"><label for="cAhorro">Ahorro mensual para la entrada</label><div class="unit"><input id="cAhorro" type="number" min="1" max="80" step="1" value="15"><span>% de ingresos</span></div></div>
        </details>
      </form>
      <div class="calc-out" id="calcOut" aria-live="polite"></div>
    </div>`;

  const val = (id) => parseFloat($(id)?.value);
  const muniCode = () => {
    const v = $("#cMuni")?.value?.trim();
    if (!v || !municipios) return null;
    const m = v.match(/\((\d{5})\)$/);
    return m && municipios.items[m[1]] ? m[1] : null;
  };

  function compute() {
    const ing = val("#cIng"), m2 = val("#cM2");
    const ccaa = $("#cZona").value;
    const mc = muniCode();
    const mu = mc ? municipios.items[mc] : null;
    const P = PRE[ccaa];
    const out = $("#calcOut");
    if (!(ing > 0) || !(m2 > 0)) {
      out.innerHTML = `<div class="empty">Escribe tus ingresos y el tamaño de la vivienda.</div>`;
      return;
    }
    // Alquiler: precio de oferta de la comunidad; si hay municipio, mediana SERPAVI (contratos vigentes)
    const alqM2 = mu?.serpavi_m2 ?? P?.alquiler_m2_latest;
    const alqFuente = mu?.serpavi_m2 != null ? `mediana de contratos en ${esc(mu.name)} (SERPAVI ${esc(municipios.fields_meta?.serpavi_m2?.period || "")}), suele estar por debajo del precio de anuncio` : `precio medio de anuncio en ${esc(CCAA[ccaa])} (Fotocasa, ${esc(P?.alquiler_m2_latest_meta?.period || "")})`;
    const ventaM2 = mu?.tasado_m2 ?? P?.venta_m2_latest;
    const ventaFuente = mu?.tasado_m2 != null ? `valor tasado en ${esc(mu.name)}` : `valor tasado medio en ${esc(CCAA[ccaa])} (${esc(P?.venta_m2_latest_meta?.period || "")})`;

    const alq = alqM2 ? alqM2 * m2 : null;
    const pAlq = alq ? (alq / ing) * 100 : null;
    const precio = ventaM2 ? ventaM2 * m2 : null;
    const entrada = precio ? precio * 0.2 : null;
    const gastos = precio ? precio * 0.1 : null; // impuestos, notaría, registro: orientativo
    const ahorroMes = (ing * val("#cAhorro")) / 100;
    const anosAhorro = entrada && ahorroMes > 0 ? (entrada + gastos) / ahorroMes / 12 : null;
    const hip = precio ? cuota(precio * 0.8, val("#cTipo"), val("#cAnos")) : null;
    const pHip = hip ? (hip / ing) * 100 : null;
    const alqActual = val("#cAlq");

    const verdict = (p) =>
      p == null ? "" : p >= UMBRAL_SOBRECARGA ? `<span class="pill bad">Sobrecarga (≥${UMBRAL_SOBRECARGA}%)</span>`
        : p >= UMBRAL_ALTO ? `<span class="pill warn">Esfuerzo alto (≥${UMBRAL_ALTO}%)</span>` : `<span class="pill ok">Asumible (&lt;${UMBRAL_ALTO}%)</span>`;
    const meter = (p) => `<div class="meter" role="img" aria-label="${fmt(p, 1)}% de los ingresos"><i style="width:${Math.min(100, p)}%"></i><b style="left:${UMBRAL_ALTO}%"></b><b style="left:${UMBRAL_SOBRECARGA}%"></b></div>`;

    out.innerHTML = `
      <div class="card">
        <p class="eyebrow">Alquilar ${fmt(m2)} m²</p>
        <p class="big">${alq ? `${fmt(alq)} €<small>/mes</small>` : "Sin dato"}</p>
        ${pAlq != null ? `<p><strong>${fmt(pAlq, 1)}%</strong> de tus ingresos ${verdict(pAlq)}</p>${meter(pAlq)}` : ""}
        <p class="small muted">Con ${alqFuente}.</p>
        ${alqActual > 0 ? `<p class="small">Tu alquiler actual supone el <strong>${fmt((alqActual / ing) * 100, 1)}%</strong> de tus ingresos ${verdict((alqActual / ing) * 100)}${alq ? `, ${alqActual > alq ? "por encima" : "por debajo"} de la referencia (${fmt(Math.abs(alqActual - alq))} € de diferencia)` : ""}.</p>` : ""}
      </div>
      <div class="card">
        <p class="eyebrow">Comprar ${fmt(m2)} m²</p>
        <p class="big">${precio ? `${fmt(precio)} €` : "Sin dato"}</p>
        ${precio ? `
        <dl class="calc-dl">
          <dt>Entrada (20%) + gastos (~10%)</dt><dd>${fmt(entrada + gastos)} €</dd>
          <dt>Años ahorrando ${fmt(val("#cAhorro"))}% de tus ingresos</dt><dd><strong>${fmt(anosAhorro, 1)} años</strong></dd>
          <dt>Cuota hipoteca (${fmt(val("#cTipo"), 1)}%, ${fmt(val("#cAnos"))} años)</dt><dd>${fmt(hip)} €/mes</dd>
          <dt>Cuota sobre tus ingresos</dt><dd>${fmt(pHip, 1)}% ${verdict(pHip)}</dd>
        </dl>
        ${meter(pHip)}` : ""}
        <p class="small muted">Con ${ventaFuente}. El precio de anuncio suele ser más alto que la tasación.</p>
      </div>`;
  }

  if (municipios) {
    const list = Object.entries(municipios.items)
      .filter(([, m]) => m.serpavi_m2 != null || m.tasado_m2 != null)
      .sort((a, b) => (b[1].poblacion || 0) - (a[1].poblacion || 0));
    $("#cMuniList").innerHTML = list.map(([c, m]) => `<option value="${esc(m.name)} (${c})"></option>`).join("");
    $("#cMuni").addEventListener("change", () => {
      const mc = muniCode();
      if (mc) $("#cZona").value = municipios.items[mc].ccaa;
      compute();
    });
  }
  $("#calcForm").addEventListener("input", compute);
  $("#calcForm").addEventListener("submit", (e) => e.preventDefault());
  $("#cZona").value = codes.includes("13") ? "13" : codes[0];
  compute();
}
