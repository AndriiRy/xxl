// Ядро: настройки, сборка деталей модуля, присадка, геометрия плана (любые углы).
(function (K) {
'use strict';
const r1 = (v) => Math.round(v * 10) / 10;

K.defaultSettings = function () {
  return {
    mats: {
      body: { name: 'ЛДСП корпус', t: 16, edge: 'ABS 0.4' },
      front: { name: 'МДФ/ЛДСП фасад', t: 18, edge: 'ABS 2' },
      back: { name: 'ХДФ', t: 3, edge: '' },
      top: { name: 'Столешница (спек)', t: 12, edge: '' }
    },
    g: { gap: 2, plinth: 100, baseH: 720, wallBottom: 1450, wallH: 720, tallH: 2100, wallGap: 35, wallGapUp: 0, front: 565, cDepth: 600 },
    sheet: { L: 2800, W: 2070, waste: 1.15 }
  };
};

K.globals = function (S) {
  return Object.assign({ pi: Math.PI }, S.g, { t: S.mats.body.t, tf: S.mats.front.t, tb: S.mats.back.t, tt: S.mats.top.t });
};
K.defaultParams = function (mod, S) {
  const sc = K.globals(S), p = {};
  for (const d of mod.params || []) { p[d.id] = d.defF ? K.ev(d.defF, sc) : d.def; sc[d.id] = p[d.id]; }
  return p;
};
// Параметры шкафа + недостающие (если модуль дополнили) — по умолчанию; затем переменные
K.modScope = function (mod, p, S) {
  const sc = K.globals(S);
  for (const d of mod.params || []) sc[d.id] = p && p[d.id] !== undefined ? p[d.id] : d.defF ? K.ev(d.defF, sc) : d.def;
  for (const v of mod.vars || []) sc[v.id] = K.ev(v.f, sc);
  return sc;
};

// ---------- геометрия плана ----------
function cs(rot) { const a = (rot || 0) * Math.PI / 180; let c = Math.cos(a), s = Math.sin(a); if (Math.abs(c) < 1e-12) c = 0; if (Math.abs(s) < 1e-12) s = 0; return [c, s]; }
K.cs = cs;
K.xf = function (item) { const [c, s] = cs(item.rot); return (lx, ly) => [item.x + lx * c - ly * s, item.y + lx * s + ly * c]; };
K.inv = function (item, px, py) { const [c, s] = cs(item.rot); const dx = px - item.x, dy = py - item.y; return [dx * c + dy * s, -dx * s + dy * c]; };

const G = K.geo = {
  area(p) { let a = 0; for (let i = 0; i < p.length; i++) { const q = p[i], r = p[(i + 1) % p.length]; a += q[0] * r[1] - r[0] * q[1]; } return a / 2; },
  ccw(p) { return G.area(p) < 0 ? p.slice().reverse() : p; },
  centroid(p) { let x = 0, y = 0; for (const q of p) { x += q[0]; y += q[1]; } return [x / p.length, y / p.length]; },
  inside(pt, p) {
    let c = false;
    for (let i = 0, j = p.length - 1; i < p.length; j = i++) {
      const a = p[i], b = p[j];
      if ((a[1] > pt[1]) !== (b[1] > pt[1]) && pt[0] < (b[0] - a[0]) * (pt[1] - a[1]) / (b[1] - a[1]) + a[0]) c = !c;
    }
    return c;
  },
  segX(a, b, c, d) { // строгое пересечение отрезков
    const o = (p, q, r) => (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]);
    const d1 = o(c, d, a), d2 = o(c, d, b), d3 = o(a, b, c), d4 = o(a, b, d);
    return ((d1 > 1e-9 && d2 < -1e-9) || (d1 < -1e-9 && d2 > 1e-9)) && ((d3 > 1e-9 && d4 < -1e-9) || (d3 < -1e-9 && d4 > 1e-9));
  },
  overlap(A, B) {
    for (let i = 0; i < A.length; i++) for (let j = 0; j < B.length; j++) if (G.segX(A[i], A[(i + 1) % A.length], B[j], B[(j + 1) % B.length])) return true;
    return A.some((p) => G.inside(p, B)) || B.some((p) => G.inside(p, A));
  },
  shrink(p, d) { const c = G.centroid(p); return p.map((q) => { const dx = q[0] - c[0], dy = q[1] - c[1], l = Math.hypot(dx, dy) || 1; return [q[0] - dx / l * d, q[1] - dy / l * d]; }); },
  segDist(p, a, b) { const dx = b[0] - a[0], dy = b[1] - a[1], l2 = dx * dx + dy * dy; let t = l2 ? ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / l2 : 0; t = Math.max(0, Math.min(1, t)); return Math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy); },
  dist(A, B) {
    if (G.overlap(A, B)) return 0;
    let m = Infinity;
    for (const p of A) for (let j = 0; j < B.length; j++) m = Math.min(m, G.segDist(p, B[j], B[(j + 1) % B.length]));
    for (const p of B) for (let j = 0; j < A.length; j++) m = Math.min(m, G.segDist(p, A[j], A[(j + 1) % A.length]));
    return m;
  },
  // минимальный описанный прямоугольник (заготовка фигурной детали)
  minRect(p) {
    let best = null;
    for (let i = 0; i < p.length; i++) {
      const a = p[i], b = p[(i + 1) % p.length], ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
      const c = Math.cos(-ang), s = Math.sin(-ang);
      const q = p.map((v) => [v[0] * c - v[1] * s, v[0] * s + v[1] * c]);
      const xs = q.map((v) => v[0]), ys = q.map((v) => v[1]);
      const w = Math.max(...xs) - Math.min(...xs), h = Math.max(...ys) - Math.min(...ys);
      if (!best || w * h < best.w * best.h - 1e-6) best = { w, h, q, mx: Math.min(...xs), my: Math.min(...ys) };
    }
    let pts = best.q.map((v) => [r1(v[0] - best.mx), r1(v[1] - best.my)]), L = best.w, W = best.h;
    if (W > L) { pts = pts.map((v) => [v[1], r1(L - v[0])]); [L, W] = [W, L]; }
    return { L: r1(L), W: r1(W), pts };
  }
};

K.footLocal = function (mod, sc) {
  if (mod.foot && String(mod.foot).trim()) return K.evPoly(mod.foot, sc);
  return [[0, -sc.tf], [sc.W, -sc.tf], [sc.W, sc.D], [0, sc.D]]; // первое ребро — фронт
};
// Габарит: полигон на плане и вертикальный диапазон
K.extent = function (item, mod, S) {
  const sc = K.modScope(mod, item.p, S);
  if (!(sc.W > 0) || !(sc.D > 0)) throw new Error('В модуле нужны W и D (параметры или переменные)');
  const f = K.xf(item), loc = K.footLocal(mod, sc), pts = loc.map((p) => f(p[0], p[1]));
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const z0 = K.ev(mod.z0 || '0', sc) + (item.zOff || 0);
  const h = sc.H !== undefined ? sc.H : sc.T !== undefined ? sc.T : 0;
  return { pts, loc, minx: Math.min(...xs), maxx: Math.max(...xs), miny: Math.min(...ys), maxy: Math.max(...ys), z0, z1: z0 + h, W: sc.W, D: sc.D, H: h, tf: sc.tf };
};

function axes(sz, lax) {
  if (lax) {
    const a = 'xyz'.indexOf(lax);
    const rest = [0, 1, 2].filter((k) => k !== a).sort((p, q) => sz[q] - sz[p] || p - q);
    return { aL: a, aW: rest[0], aT: rest[1] };
  }
  const idx = [0, 1, 2].sort((a, b) => sz[b] - sz[a] || a - b);
  return { aL: idx[0], aW: idx[1], aT: idx[2] };
}
function parseEdge(s) {
  s = String(s || '').toUpperCase().trim();
  if (s === 'ALL' || s === 'ВСЕ') return ['L1', 'L2', 'W1', 'W2'];
  return s.split(/[\s,;]+/).filter((x) => ['L1', 'L2', 'W1', 'W2'].includes(x));
}
function parsePolyEdge(s, n) {
  s = String(s || '').toUpperCase().trim();
  if (s === 'ALL' || s === 'ВСЕ') return [...Array(n).keys()].map((i) => i + 1);
  return s.split(/[\s,;]+/).map(Number).filter((k) => k >= 1 && k <= n);
}
const isSet = (v) => v !== undefined && v !== null && String(v).trim() !== '';

// Сборка деталей шкафа → {parts, hw, z0, sc}
K.buildItem = function (item, S, mod) {
  const sc = K.modScope(mod, item.p, S);
  const z0 = K.ev(mod.z0 || '0', sc) + (item.zOff || 0);
  const parts = [];
  for (const d of mod.parts || []) {
    if (isSet(d.if) && !K.ev(d.if, sc)) continue;
    const n = Math.max(0, Math.round(K.ev(isSet(d.count) ? d.count : 1, sc)));
    const md = S.mats[d.mat];
    if (!md) throw new Error('Деталь «' + d.name + '»: неизвестный материал «' + d.mat + '»');
    for (let i = 0; i < n; i++) {
      const s = Object.assign({}, sc, { i, n });
      const base = { cab: item.label, base: d.name, name: n > 1 ? d.name + ' ' + (i + 1) : d.name, mat: d.mat, md, role: d.role || '', drill: d.drill || '', to: d.to || 'side', holes: [] };
      let p;
      if (isSet(d.poly)) { // фигурная пластина: контур в плоскости xy (горизонт.), xz (фронтальная) или yz (боковая)
        const pl = d.plane || 'xy', pts = K.evPoly(d.poly, s).map((v) => [r1(v[0]), r1(v[1])]);
        if (pts.length < 3) throw new Error('Деталь «' + d.name + '»: в контуре меньше 3 точек');
        const T = r1(K.ev(pl === 'xy' ? d.sz : pl === 'xz' ? d.sy : d.sx, s)), off = r1(K.ev(pl === 'xy' ? d.z : pl === 'xz' ? d.y : d.x, s));
        if (!(T > 0) || Math.abs(G.area(pts)) < 1) throw new Error('Деталь «' + d.name + '»: пустой контур или толщина ≤ 0');
        const mr = G.minRect(pts), sec = !!(d.sec && String(d.sec) !== '0'); // sec: контур — сечение, выдавливание — длина доски
        const etok = String(d.edge || '').toUpperCase(), edgeIdx = parsePolyEdge(etok.replace(/[FB]/g, ' '), pts.length);
        const caps = (etok.includes('F') ? 1 : 0) + (etok.includes('B') ? 1 : 0);
        const P = pts.map((v) => (pl === 'xy' ? [v[0], v[1], off] : pl === 'xz' ? [v[0], off, v[1]] : [off, v[0], v[1]]));
        const e = pl === 'xy' ? [0, 0, T] : pl === 'xz' ? [0, T, 0] : [T, 0, 0];
        const mn = [0, 1, 2].map((k) => Math.min(...P.map((q) => q[k]), ...P.map((q) => q[k] + e[k])));
        const mx = [0, 1, 2].map((k) => Math.max(...P.map((q) => q[k]), ...P.map((q) => q[k] + e[k])));
        const perim = edgeIdx.reduce((a, k) => { const q = pts[k - 1], r = pts[k % pts.length]; return a + Math.hypot(r[0] - q[0], r[1] - q[1]); }, 0);
        p = Object.assign(base, { shape: 'poly', plane: pl, sec, P, e, cutPts: mr.pts, edgeIdx, edge: [], caps: etok.replace(/[^FB]/g, ''),
          L: sec ? Math.max(mr.L, T) : mr.L, W: sec ? Math.min(mr.L, T) : mr.W, T: sec ? mr.W : T,
          edgeLen: sec ? edgeIdx.length * T + caps * mr.L : perim,
          mn, sz: [0, 1, 2].map((k) => mx[k] - mn[k]), z0: mn[2], z1: mx[2], hinge: 0 });
      } else {
        const mn = [K.ev(d.x, s), K.ev(d.y, s), K.ev(d.z, s)].map(r1);
        const sz = [K.ev(d.sx, s), K.ev(d.sy, s), K.ev(d.sz, s)].map(r1);
        if (sz.some((v) => !(v > 0))) throw new Error('Деталь «' + d.name + '»: размер ≤ 0 (' + sz.join('×') + ')');
        const ax = axes(sz, d.lax), rz = isSet(d.rz) ? K.ev(d.rz, s) : 0;
        const [c, sn] = cs(rz), rp = (dx, dy) => [r1(mn[0] + dx * c - dy * sn), r1(mn[1] + dx * sn + dy * c)];
        const edge = parseEdge(d.edge);
        p = Object.assign(base, { shape: 'box', mn, sz, ax, rz, L: sz[ax.aL], W: sz[ax.aW], T: sz[ax.aT], edge,
          edgeLen: edge.reduce((a, e) => a + (e[0] === 'L' ? sz[ax.aL] : sz[ax.aW]), 0),
          P: [rp(0, 0), rp(sz[0], 0), rp(sz[0], sz[1]), rp(0, sz[1])].map((v) => [v[0], v[1], mn[2]]), e: [0, 0, sz[2]], z0: mn[2], z1: mn[2] + sz[2],
          hinge: isSet(d.hinge) && !rz ? Math.sign(K.ev(d.hinge, s)) : 0 });
      }
      parts.push(p);
    }
  }
  drill(parts.filter((p) => p.shape === 'box' && !p.rz));
  const hw = [];
  for (const h of mod.hardware || []) {
    let q; try { q = Math.round(K.ev(h.qty, sc)); } catch (e) { hw.push({ name: h.name + ' — ошибка формулы кол-ва: ' + e.message, qty: 1, err: 1 }); continue; }
    if (q > 0) hw.push({ name: K.tpl(h.name, sc), qty: q });
  }
  const cnt = (k) => parts.reduce((a, p) => a + p.holes.filter((h) => h.kind === k).length, 0);
  const auto = [['Конфирмат 7×50', cnt('conf5')], ['Полкодержатель Ø5', cnt('pin')], ['Петля накладная с планкой (чашка Ø35)', cnt('cup')], ['Евровинт 6,3×13 для планки петли', cnt('cup') * 2]];
  for (const [name, qty] of auto) if (qty > 0) hw.push({ name, qty });
  return { parts, hw, z0, sc };
};

// ---------- присадка (только прямоугольные детали без поворота) ----------
function hole(part, kind, d, depth, p, axis, note) {
  const { aL, aW } = part.ax;
  part.holes.push({ kind, d, depth, l: r1(p[aL] - part.mn[aL]), w: r1(p[aW] - part.mn[aW]), axis, face: axis === part.ax.aT ? 'пласть' : 'торец', note: note || '' });
}
const positions = (span, off) => (span >= 150 ? [off, span - off] : [span / 2]);
const inRange = (v, a, b) => v >= a - 0.5 && v <= b + 0.5;
function drill(parts) {
  const byRole = (r) => parts.filter((p) => p.role === r);
  const eq = (a, b) => Math.abs(a - b) < 0.6;
  for (const h of parts.filter((p) => p.drill === 'conf')) {
    if (h.ax.aT === 0) continue;
    const inAx = h.ax.aT === 1 ? 2 : 1, pos = positions(h.sz[inAx], 50), mid = h.mn[h.ax.aT] + h.sz[h.ax.aT] / 2;
    for (const ex of [h.mn[0], h.mn[0] + h.sz[0]]) for (const q of pos) {
      const pt = [0, 0, 0]; pt[0] = ex; pt[inAx] = h.mn[inAx] + q; pt[h.ax.aT] = mid;
      hole(h, 'conf5', 5, 50, pt, 0, 'в торец');
      for (const s of byRole(h.to)) {
        if (!(eq(s.mn[0] + s.sz[0], ex) || eq(s.mn[0], ex))) continue;
        if (!inRange(pt[1], s.mn[1], s.mn[1] + s.sz[1]) || !inRange(pt[2], s.mn[2], s.mn[2] + s.sz[2])) continue;
        const outer = eq(s.mn[0] + s.sz[0], ex) ? s.mn[0] : s.mn[0] + s.sz[0];
        hole(s, 'conf7', 7, s.sz[0], [outer, pt[1], pt[2]], 0, 'сквозное');
      }
    }
  }
  for (const sh of parts.filter((p) => p.drill === 'shelf')) {
    const ys = [sh.mn[1] + 40, sh.mn[1] + sh.sz[1] - 40];
    for (const s of byRole('side')) {
      let x = null;
      if (s.mn[0] + s.sz[0] <= sh.mn[0] + 1) x = s.mn[0] + s.sz[0]; else if (s.mn[0] >= sh.mn[0] + sh.sz[0] - 1) x = s.mn[0];
      if (x === null) continue;
      for (const y of ys) hole(s, 'pin', 5, 12, [x, y, sh.mn[2]], 0, 'под полку «' + sh.name + '»');
    }
  }
  const sides = byRole('side'), minX = sides.length ? Math.min(...sides.map((q) => q.mn[0])) : 0;
  for (const d of parts.filter((p) => p.hinge !== 0)) {
    const hgt = d.sz[2], n = 2 + (hgt > 900) + (hgt > 1600) + (hgt > 2000), zs = [];
    for (let k = 0; k < n; k++) zs.push(k === 0 ? d.mn[2] + 100 : k === n - 1 ? d.mn[2] + hgt - 100 : d.mn[2] + 100 + (hgt - 200) * k / (n - 1));
    const edgeX = d.hinge < 0 ? d.mn[0] : d.mn[0] + d.sz[0], cupX = edgeX + (d.hinge < 0 ? 22.5 : -22.5);
    for (const z of zs) {
      hole(d, 'cup', 35, 12.5, [cupX, d.mn[1] + d.sz[1], z], 1, 'чашка петли, 22,5 от кромки');
      for (const s of sides) {
        const ok = d.hinge < 0 ? s.mn[0] <= d.mn[0] + d.sz[0] / 2 : s.mn[0] >= d.mn[0] + d.sz[0] / 2;
        if (!ok || !inRange(z, s.mn[2], s.mn[2] + s.sz[2])) continue;
        const x = s.mn[0] === minX ? s.mn[0] + s.sz[0] : s.mn[0];
        for (const y of [37, 69]) hole(s, 'plate', 5, 13, [x, y, z], 0, 'планка петли');
      }
    }
  }
}

// Мировые призмы всех деталей шкафа
K.worldSolids = function (item, built) {
  const f = K.xf(item);
  const [c, s] = cs(item.rot);
  return built.parts.map((p) => ({
    P3: p.P.map((v) => { const w = f(v[0], v[1]); return [w[0], w[1], built.z0 + v[2]]; }),
    e: [p.e[0] * c - p.e[1] * s, p.e[0] * s + p.e[1] * c, p.e[2]], mat: p.mat, role: p.role, name: p.cab + ' ' + p.name, part: p
  }));
};
// Мировые вершины призмы (для проверок)
K.solidVerts = (b) => b.P3.concat(b.P3.map((v) => [v[0] + b.e[0], v[1] + b.e[1], v[2] + b.e[2]]));
K.r1 = r1;
})(window.K = window.K || {});
