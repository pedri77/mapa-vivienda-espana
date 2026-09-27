import { $, esc, link, CCAA } from "./util.js";

export function renderAyudas(A, el) {
  if (!A) {
    el.innerHTML = `<div class="empty">Datos de ayudas aún no disponibles.</div>`;
    return;
  }
  const codes = (A.ccaa || []).map((c) => c.code).filter((c) => CCAA[c]);
  el.innerHTML = `
    <p class="intro">Información práctica y enlaces oficiales. No sustituye al asesoramiento legal: ante una demanda, pide cita con servicios sociales y solicita abogado de oficio cuanto antes.</p>
    <div class="grid-2">
      <div>
        <h3>Si te llega una demanda de desahucio</h3>
        <ol class="steps">${(A.guia_desahucio || []).map((p) => `<li><div><strong>${esc(p.titulo)}</strong><p class="small" style="margin:4px 0 0">${esc(p.texto)}</p>${p.base_legal || p.url ? `<p class="small muted" style="margin:4px 0 0">${p.url ? link(p.url, p.base_legal || "Fuente") : esc(p.base_legal)}</p>` : ""}</div></li>`).join("")}</ol>
      </div>
      <div>
        <h3>Ayudas en tu comunidad</h3>
        <label for="ayuSel" class="small muted">Comunidad autónoma</label><br>
        <select id="ayuSel">${codes.map((c) => `<option value="${c}">${esc(CCAA[c])}</option>`).join("")}</select>
        <div id="ayuCcaa" style="margin-top:14px"></div>
        <h3 style="margin-top:24px">Ayudas estatales</h3>
        ${(A.estatales || []).map((a) => `<details><summary>${esc(a.name)} ${a.estado ? `<span class="pill">${esc(a.estado)}</span>` : ""}</summary>
          <p class="small">${esc(a.summary || "")}</p>
          ${a.requisitos ? `<p class="small"><strong>Requisitos:</strong> ${esc(a.requisitos)}</p>` : ""}
          ${a.cuantia ? `<p class="small"><strong>Cuantía:</strong> ${esc(a.cuantia)}</p>` : ""}
          ${a.url ? `<p class="small">${link(a.url, "Información oficial")}</p>` : ""}</details>`).join("")}
      </div>
    </div>
    <h3 style="margin-top:32px">Tus derechos como inquilino</h3>
    <div class="grid-3">${(A.derechos || []).map((d) => `<div class="card"><h3 style="font-size:1rem">${esc(d.titulo)}</h3><p class="small" style="margin:0">${esc(d.texto)}</p>${d.base_legal || d.url ? `<p class="small muted" style="margin:6px 0 0">${d.url ? link(d.url, d.base_legal || "Fuente") : esc(d.base_legal)}</p>` : ""}</div>`).join("")}</div>
    <h3 style="margin-top:32px">Dónde pedir ayuda</h3>
    <div class="table-wrap"><table><thead><tr><th scope="col">Organización</th><th scope="col">Tipo</th><th scope="col">Ámbito</th><th scope="col">Contacto</th></tr></thead><tbody>
    ${(A.organizaciones || []).map((o) => `<tr><td>${link(o.url, o.name)}</td><td>${esc(o.type || "")}</td><td>${esc(o.city || CCAA[o.scope] || o.scope || "")}</td><td class="small">${esc(o.contacto || "")}</td></tr>`).join("")}
    </tbody></table></div>`;

  const byCode = Object.fromEntries((A.ccaa || []).map((c) => [c.code, c]));
  const show = (code) => {
    const c = byCode[code];
    if (!c) return;
    $("#ayuSel").value = code;
    $("#ayuCcaa").innerHTML = `
      ${(c.ayudas || []).length ? (c.ayudas || []).map((a) => `<div class="card" style="margin-bottom:10px"><strong>${link(a.url, a.name)}</strong> ${a.estado ? `<span class="pill">${esc(a.estado)}</span>` : ""}<p class="small" style="margin:4px 0 0">${esc(a.summary || "")}${a.cuantia ? ` <strong>${esc(a.cuantia)}</strong>` : ""}</p></div>`).join("") : `<p class="small muted">Sin ayudas autonómicas registradas.</p>`}
      <dl class="small" style="display:grid;grid-template-columns:max-content 1fr;gap:4px 12px">
        ${c.agencia?.name ? `<dt class="muted">Agencia de vivienda</dt><dd style="margin:0">${link(c.agencia.url, c.agencia.name)}</dd>` : ""}
        ${c.fianzas?.organismo ? `<dt class="muted">Depósito de fianzas</dt><dd style="margin:0">${link(c.fianzas.url, c.fianzas.organismo)}</dd>` : ""}
        ${c.emergencia?.text || c.emergencia?.phone ? `<dt class="muted">Emergencia habitacional</dt><dd style="margin:0">${esc(c.emergencia.text || "")} ${c.emergencia.phone ? `<strong class="mono">${esc(c.emergencia.phone)}</strong>` : ""} ${c.emergencia.url ? link(c.emergencia.url, "más info") : ""}</dd>` : ""}
      </dl>`;
  };
  $("#ayuSel").addEventListener("change", (e) => show(e.target.value));
  window.addEventListener("pickccaa", (e) => show(e.detail));
  show(codes.includes("13") ? "13" : codes[0]);
}
