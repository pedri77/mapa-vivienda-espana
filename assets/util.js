// Utilidades compartidas
export const $ = (s, el = document) => el.querySelector(s);

const nf0 = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 0, useGrouping: "always" });
const nf1 = new Intl.NumberFormat("es-ES", { maximumFractionDigits: 1, minimumFractionDigits: 1, useGrouping: "always" });
export const fmt = (v, d = 0) => (v == null || Number.isNaN(v) ? "—" : d ? nf1.format(v) : nf0.format(v));
export const eur = (v) => (v == null ? "—" : `${fmt(v)} €`);
export const pct = (v, d = 1) => (v == null ? "—" : `${v > 0 ? "+" : ""}${fmt(v, d)}%`);

export function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

export async function load(name) {
  try {
    const r = await fetch(`data/${name}.json`, { cache: "no-cache" });
    if (!r.ok) throw new Error(r.status);
    return await r.json();
  } catch (e) {
    console.warn(`No se pudo cargar ${name}.json`, e);
    return null;
  }
}

const rtf = new Intl.RelativeTimeFormat("es", { numeric: "auto" });
export function ago(iso) {
  const s = (new Date(iso) - Date.now()) / 1000;
  const abs = Math.abs(s);
  if (abs < 3600) return rtf.format(Math.round(s / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(s / 3600), "hour");
  return rtf.format(Math.round(s / 86400), "day");
}
export const dateEs = (iso) =>
  iso ? new Date(iso.length === 10 ? iso + "T12:00:00" : iso).toLocaleDateString("es-ES", { day: "numeric", month: "short", year: "numeric" }) : "—";

export function link(url, text) {
  if (!url) return esc(text);
  return `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(text)}</a>`;
}

// Cortes por cuantiles para una escala de 5 clases
export function quantileBreaks(values, n = 5) {
  const v = values.filter((x) => x != null).sort((a, b) => a - b);
  if (!v.length) return [];
  return Array.from({ length: n - 1 }, (_, i) => v[Math.floor(((i + 1) * v.length) / n)]);
}
export const classOf = (v, breaks) => (v == null ? -1 : breaks.filter((b) => v >= b).length);

export function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export function sparkline(values, { w = 120, h = 28, color = "currentColor" } = {}) {
  if (!values?.length) return "";
  const max = Math.max(1, ...values);
  const step = values.length > 1 ? w / (values.length - 1) : w;
  const pts = values.map((v, i) => [i * step, h - 2 - (v / max) * (h - 4)]);
  const line = pts.map((p, i) => `${i ? "L" : "M"}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join("");
  const area = `${line}L${w},${h}L0,${h}Z`;
  const last = pts[pts.length - 1];
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" aria-hidden="true"><path d="${area}" fill="${color}" opacity=".15"/><path d="${line}" fill="none" stroke="${color}" stroke-width="1.5"/><circle cx="${last[0]}" cy="${last[1]}" r="2.5" fill="${color}"/></svg>`;
}

// Tabla ordenable: cols = [{key, label, num, render}]
export function sortableTable(el, cols, rows, { sortKey, desc = true } = {}) {
  let key = sortKey ?? cols[0].key;
  let dir = desc ? -1 : 1;
  const draw = () => {
    const sorted = [...rows].sort((a, b) => {
      const x = a[key], y = b[key];
      if (x == null) return 1;
      if (y == null) return -1;
      return (typeof x === "string" ? x.localeCompare(y, "es") : x - y) * dir;
    });
    el.innerHTML = `<table><thead><tr>${cols
      .map((c) => `<th class="${c.num ? "r" : ""}" data-k="${c.key}" ${c.key === key ? `aria-sort="${dir < 0 ? "descending" : "ascending"}"` : ""} tabindex="0" scope="col">${c.label}</th>`)
      .join("")}</tr></thead><tbody>${sorted
      .map((r) => `<tr>${cols.map((c) => `<td class="${c.num ? "r" : ""}">${c.render ? c.render(r) : esc(r[c.key])}</td>`).join("")}</tr>`)
      .join("")}</tbody></table>`;
    el.querySelectorAll("th").forEach((th) => {
      const go = () => {
        const k = th.dataset.k;
        dir = k === key ? -dir : -1;
        key = k;
        draw();
      };
      th.addEventListener("click", go);
      th.addEventListener("keydown", (e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), go()));
    });
  };
  draw();
}

// Nombres limpios por código INE
export const CCAA = {
  "01": "Andalucía", "02": "Aragón", "03": "Asturias", "04": "Illes Balears", "05": "Canarias", "06": "Cantabria",
  "07": "Castilla y León", "08": "Castilla-La Mancha", "09": "Cataluña", "10": "Comunitat Valenciana", "11": "Extremadura",
  "12": "Galicia", "13": "Comunidad de Madrid", "14": "Región de Murcia", "15": "Navarra", "16": "País Vasco",
  "17": "La Rioja", "18": "Ceuta", "19": "Melilla",
};
