// Спецификация: материалы, деталировка, присадка, сборка; CSV для раскроя; JSON для Fusion.
(function (K) {
'use strict';
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const f1 = (n) => String(Math.round(n * 10) / 10).replace('.', ',');
const ROLE_RU = { body: 'Корпус', front: 'Фасады', back: 'Задняя стенка', top: 'Столешница' };
const EDGE_RU = { L1: 'Д1', L2: 'Д2', W1: 'Ш1', W2: 'Ш2' };
const edgeStr = (p) => (p.shape === 'poly' ? (p.edgeIdx.length ? 'рёбра ' + p.edgeIdx.join(',') : '—') : p.edge.length ? p.edge.map((e) => EDGE_RU[e]).join('+') : '—');

// builds: [{item, mod, built}]
K.cutList = function (builds, S) {
  const mats = {};
  for (const { item, built } of builds) for (const p of built.parts) {
    const m = mats[p.mat] = mats[p.mat] || { key: p.mat, md: p.md, rows: new Map(), area: 0, edgeM: 0 };
    const key = [p.base, p.L, p.W, edgeStr(p), p.shape === 'poly' ? JSON.stringify(p.cutPts) : ''].join('|');
    let r = m.rows.get(key);
    if (!r) { r = { name: p.base, L: p.L, W: p.W, T: p.T, es: edgeStr(p), poly: p.shape === 'poly', qty: 0, cabs: new Set() }; m.rows.set(key, r); }
    r.qty++; r.cabs.add(item.label);
    m.area += p.L * p.W / 1e6; m.edgeM += p.edgeLen / 1000;
  }
  return Object.values(mats);
};

K.hardwareList = function (builds) {
  const m = new Map();
  for (const { built } of builds) for (const h of built.hw) m.set(h.name, (m.get(h.name) || 0) + h.qty);
  return [...m].map(([name, qty]) => ({ name, qty })).sort((a, b) => a.name.localeCompare(b.name, 'ru'));
};

K.partSVG = function (p) {
  const pad = 22, maxW = 300, maxH = 150;
  const s = Math.min(maxW / p.L, maxH / p.W);
  const w = p.L * s, h = p.W * s, X = (l) => pad + l * s, Y = (v) => pad + h - v * s;
  let o = `<svg class="psvg" width="${w + pad * 2}" height="${h + pad * 2}" viewBox="0 0 ${w + pad * 2} ${h + pad * 2}">`;
  o += `<rect x="${pad}" y="${pad}" width="${w}" height="${h}" fill="#f3efe6" stroke="#555"/>`;
  const E = { L1: [X(0), Y(0), X(p.L), Y(0)], L2: [X(0), Y(p.W), X(p.L), Y(p.W)], W1: [X(0), Y(0), X(0), Y(p.W)], W2: [X(p.L), Y(0), X(p.L), Y(p.W)] };
  for (const e of p.edge) o += `<line x1="${E[e][0]}" y1="${E[e][1]}" x2="${E[e][2]}" y2="${E[e][3]}" stroke="#d6336c" stroke-width="3"/>`;
  for (const hl of p.holes) {
    const r = Math.max(hl.d * s / 2, 2.2), cx = X(hl.l), cy = Y(hl.w);
    const col = hl.kind === 'cup' ? '#1c7ed6' : hl.kind === 'conf7' ? '#2f9e44' : hl.kind === 'conf5' ? '#e8590c' : '#7048e8';
    o += hl.face === 'торец'
      ? `<rect x="${cx - 2.5}" y="${cy - 2.5}" width="5" height="5" fill="${col}"/>`
      : `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${col}" stroke-width="1.4"/><circle cx="${cx}" cy="${cy}" r="1" fill="${col}"/>`;
  }
  o += `<text x="${pad}" y="${pad - 6}" font-size="10" fill="#555">${f1(p.L)} (Д)</text>`;
  o += `<text x="2" y="${pad + h / 2}" font-size="10" fill="#555" transform="rotate(-90 8 ${pad + h / 2})">${f1(p.W)} (Ш)</text>`;
  o += `<text x="${pad - 2}" y="${pad + h + 12}" font-size="9" fill="#999">0</text></svg>`;
  return o;
};

K.polySVG = function (p) {
  const pad = 22, s = Math.min(300 / p.L, 150 / p.W), P = p.cutPts, X = (v) => pad + v[0] * s, Y = (v) => pad + p.W * s - v[1] * s;
  let o = `<svg class="psvg" width="${p.L * s + pad * 2}" height="${p.W * s + pad * 2}"><rect x="${pad}" y="${pad}" width="${p.L * s}" height="${p.W * s}" fill="none" stroke="#bbb" stroke-dasharray="3 3"/>`;
  o += `<polygon points="${P.map((v) => X(v) + ',' + Y(v)).join(' ')}" fill="#f3efe6" stroke="#555"/>`;
  for (const k of p.edgeIdx) { const a = P[k - 1], b = P[k % P.length]; o += `<line x1="${X(a)}" y1="${Y(a)}" x2="${X(b)}" y2="${Y(b)}" stroke="#d6336c" stroke-width="3"/>`; }
  P.forEach((v, i) => { o += `<circle cx="${X(v)}" cy="${Y(v)}" r="2.5" fill="#1c7ed6"/><text x="${X(v) + 4}" y="${Y(v) - 4}" font-size="10" fill="#1c7ed6">${i + 1}</text>`; });
  return o + `<text x="${pad}" y="${pad - 6}" font-size="10" fill="#555">заготовка ${f1(p.L)}×${f1(p.W)}</text></svg>`;
};

// ---------- технологические чертежи (мм) ----------
function dimLine(o, x1, x2, y, txt, up) { // горизонтальная размерная линия
  if (Math.abs(x2 - x1) < 1) return;
  o.push(`<line x1="${x1}" y1="${y}" x2="${x2}" y2="${y}" stroke="#c92a2a" stroke-width=".8"/><line x1="${x1}" y1="${y - 4}" x2="${x1}" y2="${y + 4}" stroke="#c92a2a" stroke-width=".8"/><line x1="${x2}" y1="${y - 4}" x2="${x2}" y2="${y + 4}" stroke="#c92a2a" stroke-width=".8"/>`);
  const w = Math.abs(x2 - x1), fs = w < 26 ? 7 : 9;
  o.push(`<text x="${(x1 + x2) / 2}" y="${y + (up ? -3 : 10)}" font-size="${fs}" text-anchor="middle" fill="#c92a2a">${txt}</text>`);
}
function dimV(o, x, y1, y2, txt) {
  if (Math.abs(y2 - y1) < 1) return;
  o.push(`<line x1="${x}" y1="${y1}" x2="${x}" y2="${y2}" stroke="#c92a2a" stroke-width=".8"/><line x1="${x - 4}" y1="${y1}" x2="${x + 4}" y2="${y1}" stroke="#c92a2a" stroke-width=".8"/><line x1="${x - 4}" y1="${y2}" x2="${x + 4}" y2="${y2}" stroke="#c92a2a" stroke-width=".8"/>`);
  o.push(`<text x="${x - 3}" y="${(y1 + y2) / 2}" font-size="8" text-anchor="middle" fill="#c92a2a" transform="rotate(-90 ${x - 3} ${(y1 + y2) / 2})">${txt}</text>`);
}
function chain(vals) { return [...new Set(vals.map((v) => Math.round(v * 10) / 10))].sort((a, b) => a - b); }
// Развёртка стены: el = {title, u, lo, len, H, items:[{item,mod,built,ext}], wins:[{u0,u1,z0,z1,name}], marks:[z...]}
K.elevSVG = function (el) {
  const s = Math.min(860 / Math.max(el.len, 500), 380 / el.H), L = 70, T = 40, Wp = el.len * s, Hp = el.H * s;
  const X = (u) => L + u * s, Y = (z) => T + Hp - z * s, o = [];
  o.push(`<rect x="${X(0)}" y="${Y(el.H)}" width="${Wp}" height="${Hp}" fill="#fafafa" stroke="#222" stroke-width="1.2"/>`);
  for (const w of el.wins) o.push(`<rect x="${X(w.u0)}" y="${Y(w.z1)}" width="${(w.u1 - w.u0) * s}" height="${(w.z1 - w.z0) * s}" fill="#e7f5ff" stroke="#1c7ed6" stroke-dasharray="4 2"/><text x="${X(w.u0) + 3}" y="${Y(w.z1) + 10}" font-size="8" fill="#1c7ed6">${esc(w.name)}</text>`);
  for (const j of el.joints || []) o.push(`<line x1="${X(j)}" y1="${Y(el.H)}" x2="${X(j)}" y2="${Y(0)}" stroke="#868e96" stroke-dasharray="6 3"/>`);
  const base = [], up = [];
  for (const it of el.items) {
    const sols = K.worldSolids(it.item, it.built), cat = it.mod.cat;
    const pr = (sol) => { const V = K.solidVerts(sol), us = V.map((v) => it.pu(v)), zs = V.map((v) => v[2]); return [Math.min(...us), Math.max(...us), Math.min(...zs), Math.max(...zs)]; };
    const us = it.ext.pts.map((p) => it.pu(p)), u0 = Math.min(...us), u1 = Math.max(...us);
    if (cat !== 'counter') o.push(`<rect x="${X(u0)}" y="${Y(it.ext.z1)}" width="${(u1 - u0) * s}" height="${(it.ext.z1 - it.ext.z0) * s}" fill="none" stroke="#999" stroke-dasharray="2 2"/>`);
    for (const sl of sols) {
      if (sl.mat !== 'front' && sl.mat !== 'top' && !/Цоколь/.test(sl.part.base)) continue;
      const [a, b, c, d] = pr(sl);
      o.push(`<rect x="${X(a)}" y="${Y(d)}" width="${(b - a) * s}" height="${(d - c) * s}" fill="${sl.mat === 'top' ? '#868e96' : sl.mat === 'front' ? '#f1ece2' : '#ced4da'}" stroke="#333" stroke-width=".7"/>`);
    }
    if (cat !== 'counter') o.push(`<text x="${X((u0 + u1) / 2)}" y="${Y((it.ext.z0 + it.ext.z1) / 2)}" font-size="9" text-anchor="middle" fill="#222">${esc(it.item.label)}</text>`);
    (cat === 'wall' ? up : cat === 'counter' ? [] : base).push([u0, u1]);
  }
  const ch = (ivs, y, upw) => { const pts = chain([0, el.len, ...ivs.flat()].filter((v) => v >= -1 && v <= el.len + 1)); for (let i = 0; i < pts.length - 1; i++) dimLine(o, X(pts[i]), X(pts[i + 1]), y, K.f1(pts[i + 1] - pts[i]), upw); };
  ch(base, Y(0) + 12, false); ch(up, Y(el.H) - 8, true);
  dimLine(o, X(0), X(el.len), Y(0) + 40, K.f1(el.len) + ' (длина стены)', false);
  { const js = [0, ...(el.joints || []), el.len]; if (js.length > 2) for (let i = 0; i < js.length - 1; i++) dimLine(o, X(js[i]), X(js[i + 1]), Y(0) + 24, K.f1(js[i + 1] - js[i]), false); }
  const zs = chain([0, el.H, ...el.marks]);
  for (let i = 0; i < zs.length - 1; i++) dimV(o, X(0) - 18, Y(zs[i]), Y(zs[i + 1]), K.f1(zs[i + 1] - zs[i]));
  dimV(o, X(0) - 44, Y(0), Y(el.H), K.f1(el.H));
  return `<svg class="psvg" width="${Wp + L + 30}" height="${Hp + T + 50}" style="max-width:100%">${o.join('')}</svg>`;
};
// Чертёж корпуса: вид спереди и сбоку (локальные координаты модуля)
K.cabSVG = function (b) {
  const sc = b.built.sc, parts = b.built.parts, bb = (p, i, j) => { const V = p.P.concat(p.P.map((v) => [v[0] + p.e[0], v[1] + p.e[1], v[2] + p.e[2]])); return [Math.min(...V.map((v) => v[i])), Math.max(...V.map((v) => v[i])), Math.min(...V.map((v) => v[j])), Math.max(...V.map((v) => v[j]))]; };
  const all = parts.map((p) => bb(p, 0, 2)), zmin = Math.min(...all.map((q) => q[2])), zmax = Math.max(...all.map((q) => q[3]));
  const xmin = Math.min(...all.map((q) => q[0])), xmax = Math.max(...all.map((q) => q[1]));
  const sideB = parts.map((p) => bb(p, 1, 2)), ymin = Math.min(...sideB.map((q) => q[0])), ymax = Math.max(...sideB.map((q) => q[1]));
  const s = Math.min(240 / Math.max(xmax - xmin, 1), 230 / Math.max(zmax - zmin, 1), 170 / Math.max(ymax - ymin, 1));
  const T = 22, L = 46, Hp = (zmax - zmin) * s, o = [], Z = (z) => T + Hp - (z - zmin) * s;
  const X1 = (x) => L + (x - xmin) * s, X2off = L + (xmax - xmin) * s + 90, X2 = (y) => X2off + (y - ymin) * s;
  const ord = parts.map((p, i) => i).sort((a, c) => (parts[a].mat === 'front') - (parts[c].mat === 'front'));
  for (const i of ord) { const p = parts[i], q = all[i], f = p.mat === 'front'; o.push(`<rect x="${X1(q[0])}" y="${Z(q[3])}" width="${(q[1] - q[0]) * s}" height="${(q[3] - q[2]) * s}" fill="${f ? 'rgba(241,236,226,.85)' : 'none'}" stroke="${f ? '#333' : '#aaa'}" stroke-width="${f ? .8 : .5}"/>`); }
  for (const i of parts.map((p, k) => k)) { const q = sideB[i], p = parts[i]; o.push(`<rect x="${X2(q[0])}" y="${Z(q[3])}" width="${(q[1] - q[0]) * s}" height="${(q[3] - q[2]) * s}" fill="${p.mat === 'front' ? '#f1ece2' : 'none'}" stroke="${p.mat === 'front' ? '#333' : '#888'}" stroke-width=".6"/>`); }
  // размеры: ширина, высота, фасады
  dimLine(o, X1(0), X1(sc.W), Z(zmin) + 14, K.f1(sc.W), false);
  const fr = parts.filter((p) => p.mat === 'front').map((p) => bb(p, 0, 2));
  const fx = chain(fr.flatMap((q) => [q[0], q[1]])); for (let i = 0; i < fx.length - 1; i++) dimLine(o, X1(fx[i]), X1(fx[i + 1]), Z(zmax) - 6, K.f1(fx[i + 1] - fx[i]), true);
  const fz = chain(fr.flatMap((q) => [q[2], q[3]]).concat([zmin, 0])); for (let i = 0; i < fz.length - 1; i++) dimV(o, X1(xmin) - 12, Z(fz[i]), Z(fz[i + 1]), K.f1(fz[i + 1] - fz[i]));
  dimV(o, X1(xmin) - 32, Z(zmin), Z(zmax), K.f1(zmax - zmin));
  dimLine(o, X2(0), X2(sc.D), Z(zmin) + 14, 'D ' + K.f1(sc.D), false);
  dimLine(o, X2(ymin), X2(0), Z(zmin) + 28, K.f1(-ymin), false);
  if (b.item.wallOff) o.push(`<text x="${X2(sc.D) + 4}" y="${Z(zmax) + 10}" font-size="8" fill="#555">+${K.f1(b.item.wallOff)} до стены</text>`);
  o.push(`<text x="${L}" y="12" font-size="9" fill="#555">вид спереди</text><text x="${X2off}" y="12" font-size="9" fill="#555">вид сбоку (фронт слева)</text>`);
  return `<svg class="psvg" width="${X2(ymax) + 60}" height="${Hp + T + 46}">${o.join('')}</svg>`;
};

K.specHTML = function (builds, S, opts) {
  opts = opts || {};
  const L = [];
  L.push(`<h1>Спецификация проекта</h1>`);
  // 1
  L.push(`<h2>1. Технический анализ изделия</h2>`);
  L.push(`<table><tr><th>№</th><th>Модуль</th><th>Ш×В×Г, мм</th><th>Низ от пола, мм</th><th>Позиция (x; y), поворот</th></tr>`);
  for (const { item, mod, built } of builds) {
    const sc = built.sc; const H = sc.H !== undefined ? sc.H : sc.T;
    L.push(`<tr><td>${esc(item.label)}</td><td>${esc(mod.name)}</td><td>${f1(sc.W)}×${f1(H)}×${f1(sc.D)}</td><td>${f1(built.z0)}</td><td>${f1(item.x)}; ${f1(item.y)}, ${item.rot}°</td></tr>`);
  }
  L.push(`</table>`);
  if (opts.warnings && opts.warnings.length) L.push(`<p><b>Замечания:</b></p><ul>` + opts.warnings.map((w) => `<li>${esc(w)}</li>`).join('') + `</ul>`);
  // 2
  const cl = K.cutList(builds, S), hw = K.hardwareList(builds);
  L.push(`<h2>2. Материалы и фурнитура</h2>`);
  L.push(`<table><tr><th>Элемент</th><th>Материал</th><th>Толщина, мм</th><th>Деталей, шт</th><th>Площадь, м²</th><th>Листов ${S.sheet.L}×${S.sheet.W} (с запасом ${Math.round((S.sheet.waste - 1) * 100)}%)</th><th>Кромка</th><th>Кромка, м.п.</th></tr>`);
  for (const m of cl) {
    const qty = [...m.rows.values()].reduce((a, r) => a + r.qty, 0);
    const sheets = Math.ceil(m.area * S.sheet.waste / (S.sheet.L * S.sheet.W / 1e6) * 100) / 100;
    L.push(`<tr><td>${esc(ROLE_RU[m.key] || m.key)}</td><td>${esc(m.md.name)}</td><td>${m.md.t}</td><td>${qty}</td><td>${f1(m.area)}</td><td>${f1(sheets)}</td><td>${esc(m.md.edge || '—')}</td><td>${f1(m.edgeM)}</td></tr>`);
  }
  L.push(`</table><table><tr><th>Фурнитура / крепёж</th><th>Кол-во</th></tr>`);
  for (const h of hw) L.push(`<tr><td>${esc(h.name)}</td><td>${h.qty}</td></tr>`);
  L.push(`</table>`);
  // 3
  L.push(`<h2>3. Деталировка (карта раскроя)</h2><p class="note">Д — длина, Ш — ширина; Д1/Д2 — кромки вдоль длины, Ш1/Ш2 — кромки поперёк. Начало координат детали — угол Д1∩Ш1 (левый нижний на эскизе).</p>`);
  for (const m of cl) {
    L.push(`<h3>${esc(m.md.name)} — ${m.md.t} мм</h3><table><tr><th>Деталь</th><th>Шкафы</th><th>Шт</th><th>Д×Ш, мм</th><th>Кромка (${esc(m.md.edge || '—')})</th></tr>`);
    const rows = [...m.rows.values()].sort((a, b) => b.L * b.W - a.L * a.W);
    for (const r of rows) L.push(`<tr><td>${esc(r.name)}</td><td>${esc([...r.cabs].join(', '))}</td><td>${r.qty}</td><td>${f1(r.L)} × ${f1(r.W)}${r.poly ? ' <b>фигурная</b>' : ''}</td><td>${r.es}</td></tr>`);
    L.push(`</table>`);
  }
  // 4
  L.push(`<h2>4. Пошаговый процесс изготовления</h2>`);
  L.push(`<ol><li><b>Раскрой:</b> по таблице п.3; направление текстуры вдоль Д. Фасады — отдельным заданием.</li><li><b>Кромление:</b> кромка на стороны из таблицы; фасады — толстой кромкой, корпус — тонкой по видимым торцам.</li><li><b>Присадка:</b> ниже. ● квадрат — отверстие в торец, ○ — в пласть. Оранжевый — Ø5×50 (конфирмат, торец), зелёный — Ø7 сквозное, фиолетовый — Ø5 (полкодержатель/планка), синий — чашка петли Ø35×12,5.</li></ol>`);
  const seen = new Set();
  for (const { item, mod, built } of builds) {
    const groups = new Map();
    for (const p of built.parts) {
      if (!p.holes.length) continue;
      const key = mod.id + '|' + p.base + '|' + p.L + '|' + p.W + '|' + JSON.stringify(p.holes.map((h) => [h.kind, h.l, h.w]));
      const g = groups.get(key) || { p, qty: 0 }; g.qty++; groups.set(key, g);
    }
    if (!groups.size || seen.has(mod.id + JSON.stringify(item.p))) continue;
    seen.add(mod.id + JSON.stringify(item.p));
    L.push(`<h3>${esc(item.label)} — ${esc(mod.name)}</h3><div class="drillgrid">`);
    for (const { p, qty } of groups.values()) {
      const byKind = {};
      for (const h of p.holes) { const k = `Ø${h.d}×${h.depth === p.T && h.face === 'пласть' ? 'сквозь' : f1(h.depth)} (${h.face}${h.note ? ', ' + h.note : ''})`; (byKind[k] = byKind[k] || []).push(`(${f1(h.l)}; ${f1(h.w)})`); }
      L.push(`<div class="pcard"><b>${esc(p.base)} ×${qty}</b> <span class="note">${f1(p.L)}×${f1(p.W)}×${f1(p.T)}</span>${K.partSVG(p)}<ul>` + Object.entries(byKind).map(([k, v]) => `<li>${esc(k)}: ${v.join(' ')}</li>`).join('') + `</ul></div>`);
    }
    L.push(`</div>`);
  }
  const figs = new Map();
  for (const { item, built } of builds) for (const p of built.parts) if (p.shape === 'poly') {
    const key = p.base + JSON.stringify(p.cutPts) + p.T; const g = figs.get(key) || { p, cabs: new Set(), qty: 0 }; g.qty++; g.cabs.add(item.label); figs.set(key, g);
  }
  if (figs.size) {
    L.push(`<h3>Фигурные детали — раскрой по шаблону</h3><p class="note">Координаты вершин от угла заготовки (мм), розовым — кромка.</p><div class="drillgrid">`);
    for (const { p, cabs, qty } of figs.values()) L.push(`<div class="pcard"><b>${esc(p.base)} ×${qty}</b> <span class="note">${esc([...cabs].join(', '))}; ${esc(p.md.name)} ${f1(p.T)} мм</span>${K.polySVG(p)}<ul><li>Вершины: ${p.cutPts.map((v, i) => `${i + 1}(${f1(v[0])}; ${f1(v[1])})`).join(' ')}</li><li>Кромка: ${edgeStr(p)}, ${f1(p.edgeLen / 1000)} м</li></ul></div>`);
    L.push(`</div>`);
  }
  // чертежи
  if ((opts.elev || []).length) {
    L.push(`<h2>Развёртки стен (мм)</h2>`);
    for (const el of opts.elev) L.push(`<h3>${esc(el.title)}</h3>` + K.elevSVG(el));
  }
  L.push(`<h2>Чертежи корпусов (мм)</h2><div class="drillgrid">`);
  const seenC = new Map();
  for (const b of builds) { if (b.mod.cat === 'counter') continue; const key = b.mod.id + JSON.stringify(b.item.p) + (b.item.wallOff || 0); const g = seenC.get(key); if (g) g.labels.push(b.item.label); else seenC.set(key, { b, labels: [b.item.label] }); }
  for (const { b, labels } of seenC.values()) L.push(`<div class="pcard" style="max-width:none"><b>${esc(labels.join(', '))} — ${esc(b.mod.name)}</b><br>${K.cabSVG(b)}</div>`);
  L.push(`</div>`);
  // 5
  L.push(`<h2>5. Инструкция по сборке</h2>`);
  const mods = new Map(); for (const { mod } of builds) mods.set(mod.id, mod);
  for (const mod of mods.values()) if ((mod.assembly || []).length) L.push(`<h3>${esc(mod.name)}</h3><ol>` + mod.assembly.map((a) => `<li>${esc(a)}</li>`).join('') + `</ol>`);
  L.push(`<h3>Общий порядок на объекте</h3><ol><li>Базовый каркас: нижние и пеналы по уровню, стяжка между корпусами.</li><li>Внутреннее наполнение: полки, ящики, направляющие.</li><li>Столешница, верхние шкафы на навесах.</li><li>Фасады и фурнитура, регулировка зазоров.</li></ol>`);
  return L.join('\n');
};

K.cutCSV = function (builds) {
  const rows = [['Материал', 'Деталь', 'Шкаф', 'Длина', 'Ширина', 'Толщина', 'Кромка Д1', 'Кромка Д2', 'Кромка Ш1', 'Кромка Ш2', 'Тип кромки']];
  for (const { built } of builds) for (const p of built.parts) {
    rows.push([p.md.name, p.name + (p.shape === 'poly' ? ' (фигурная, по шаблону)' : ''), p.cab, p.L, p.W, p.T, ...['L1', 'L2', 'W1', 'W2'].map((e) => (p.edge.includes(e) ? 1 : 0)), (p.md.edge || '') + (p.shape === 'poly' && p.edgeIdx.length ? ' рёбра ' + p.edgeIdx.join(',') : '')]);
  }
  return '﻿' + rows.map((r) => r.map((c) => '"' + String(c).replace(/"/g, '""').replace('.', ',') + '"').join(';')).join('\r\n');
};

K.fusionParts = function (builds) {
  const parts = [];
  for (const { item, built } of builds) for (const b of K.worldSolids(item, built)) {
    const V = K.solidVerts(b);
    parts.push({ cab: item.label, name: b.part.name, material: b.mat, P: b.P3.map((v) => v.map(K.r1)), e: b.e.map(K.r1),
      min: [0, 1, 2].map((k) => K.r1(Math.min(...V.map((v) => v[k])))), max: [0, 1, 2].map((k) => K.r1(Math.max(...V.map((v) => v[k])))) });
  }
  return { format: 'kitchen-parts/3', units: 'mm', up: 'Z', parts };
};
K.esc = esc; K.f1 = f1;
})(window.K = window.K || {});
