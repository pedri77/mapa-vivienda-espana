import { esc, link, dateEs, sortableTable, CCAA } from "./util.js";

const PARTIES = ["PSOE", "PP", "Vox", "Sumar", "ERC", "Junts", "Bildu", "PNV", "Podemos", "BNG", "CC", "UPN"];
const VOTE = { si: ["Sí", "ok"], no: ["No", "bad"], abstencion: ["Abst.", "warn"] };

export function renderLegislacion(L, el) {
  if (!L) {
    el.innerHTML = `<div class="empty">Datos de legislación aún no disponibles.</div>`;
    return;
  }
  const normas = [...(L.normas || [])].sort((a, b) => (b.date || "").localeCompare(a.date || ""));
  const estatales = normas.filter((n) => n.level === "estatal");
  const voted = estatales.filter((n) => n.votes && Object.keys(n.votes).length);
  const parties = PARTIES.filter((p) => voted.some((n) => n.votes[p]));

  el.innerHTML = `
    <h3>Normas estatales</h3>
    <ul class="timeline" id="legTimeline">${estatales.map((n) => `<li>
      <span class="y">${dateEs(n.date)}</span> · ${statusPill(n.status)}<br>
      <strong>${link(n.url, `${n.id ? n.id + " · " : ""}${n.title}`)}</strong>
      <p class="small" style="margin:4px 0 0">${esc(n.summary || "")}</p></li>`).join("")}</ul>

    ${voted.length ? `<h3 style="margin-top:32px">Cómo votó cada partido en el Congreso</h3>
    <div class="table-wrap"><table><thead><tr><th scope="col">Norma</th>${parties.map((p) => `<th scope="col">${p}</th>`).join("")}</tr></thead><tbody>
    ${voted.map((n) => `<tr><td>${link(n.vote_source || n.url, shortTitle(n.title))}<div class="small muted">${dateEs(n.date)}</div></td>${parties
      .map((p) => { const v = VOTE[n.votes[p]]; return `<td>${v ? `<span class="pill ${v[1]}">${v[0]}</span>` : `<span class="muted">—</span>`}</td>`; })
      .join("")}</tr>`).join("")}</tbody></table></div>` : ""}

    <h3 style="margin-top:32px">Qué ha hecho cada comunidad</h3>
    <div class="table-wrap" id="legCcaa"></div>

    ${(L.partidos || []).length ? `<h3 style="margin-top:32px">Posiciones documentadas por partido</h3>
    <div class="grid-3">${L.partidos.map((p) => `<div class="card"><h3>${esc(p.name)}</h3><ul class="small" style="margin:0;padding-left:18px">${(p.positions || [])
      .map((x) => `<li>${esc(x.text)} ${x.url ? link(x.url, `(${x.date ? dateEs(x.date) : "fuente"})`) : ""}</li>`).join("")}</ul></div>`).join("")}</div>` : ""}

    ${normas.some((n) => n.level === "autonomica") ? `<h3 style="margin-top:32px">Normas autonómicas</h3><ul class="timeline">${normas
      .filter((n) => n.level === "autonomica")
      .map((n) => `<li><span class="y">${dateEs(n.date)} · ${esc(CCAA[n.ccaa_code] || "")}</span><br><strong>${link(n.url, n.title)}</strong><p class="small" style="margin:4px 0 0">${esc(n.summary || "")}</p></li>`).join("")}</ul>` : ""}`;

  const rows = (L.ccaa || []).map((c) => ({
    name: CCAA[c.code] || c.name,
    gov: (c.government?.parties || []).join(" + "),
    pres: c.government?.president,
    zt: c.zonas_tensionadas?.declared,
    ztm: c.zonas_tensionadas,
    tc: c.recurso_tc,
    propias: c.normas_propias || [],
  }));
  sortableTable(el.querySelector("#legCcaa"), [
    { key: "name", label: "Comunidad" },
    { key: "gov", label: "Gobierno", render: (r) => `${esc(r.gov)}${r.pres ? `<div class="small muted">${esc(r.pres)}</div>` : ""}` },
    { key: "zt", label: "Zonas tensionadas", render: (r) => r.zt === true
        ? `<span class="pill ok">Sí</span>${r.ztm?.municipios?.length ? `<div class="small muted">${esc(r.ztm.municipios.slice(0, 6).join(", "))}${r.ztm.municipios.length > 6 ? ` y ${r.ztm.municipios.length - 6} más` : ""}</div>` : ""}${r.ztm?.url ? `<div class="small">${link(r.ztm.url, "resolución")}</div>` : ""}`
        : r.zt === false ? `<span class="pill bad">No</span>` : `<span class="muted">Sin dato</span>` },
    { key: "tc", label: "Recurso al TC", render: (r) => r.tc?.filed ? `<span class="pill">Recurrió</span>${r.tc.outcome ? `<div class="small muted">${esc(r.tc.outcome)}</div>` : ""}${r.tc.url ? `<div class="small">${link(r.tc.url, "fuente")}</div>` : ""}` : r.tc?.filed === false ? "No" : "—" },
    { key: "propias", label: "Normas propias", render: (r) => r.propias.length ? `<ul class="small" style="margin:0;padding-left:16px">${r.propias.slice(0, 3).map((n) => `<li>${link(n.url, n.title)}${n.date ? ` <span class="muted">(${dateEs(n.date)})</span>` : ""}</li>`).join("")}</ul>` : "—" },
  ], rows, { sortKey: "name", desc: false });
}

function statusPill(s) {
  if (!s) return "";
  const cls = /vigente/i.test(s) ? "ok" : /derog/i.test(s) ? "bad" : "warn";
  return `<span class="pill ${cls}">${esc(s)}</span>`;
}

function shortTitle(t = "") {
  const s = t.split(/,| por el que | por la que /)[0];
  return s.length > 80 ? s.slice(0, 78) + "…" : s;
}
