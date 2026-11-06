// Ядро: настройки, сборка деталей модуля по параметрам, присадка, мировые координаты.
(function (K) {
'use strict';
const r1 = (v) => Math.round(v * 10) / 10;

K.defaultSettings = function () {
  return {
    mats: {
      body: { name: 'ЛДСП корпус', t: 16, edge: 'ABS 0.4' },
      front: { name: 'МДФ/ЛДСП фасад', t: 18, edge: 'ABS 2' },
      back: { name: 'ХДФ', t: 3, edge: '' },
      top: { name: 'Столешница', t: 38, edge: '' }
    },
    g: { gap: 2, plinth: 100, baseH: 720, wallBottom: 1450, wallH: 720, tallH: 2100 },
    sheet: { L: 2800, W: 2070, waste: 1.15 }
  };
};

K.globals = function (S) {
  return Object.assign({}, S.g, { t: S.mats.body.t, tf: S.mats.front.t, tb: S.mats.back.t, tt: S.mats.top.t });
};

K.defaultParams = function (mod, S) {
  const sc = K.globals(S), p = {};
  for (const d of mod.params || []) { p[d.id] = d.defF ? K.ev(d.defF, sc) : d.def; sc[d.id] = p[d.id]; }
  return p;
};

K.modScope = function (mod, p, S) {
  const sc = Object.assign(K.globals(S), p);
  for (const v of mod.vars || []) sc[v.id] = K.ev(v.f, sc);
  return sc;
};

// Поворот: rot кратен 90. Локальная точка (lx,ly) → мировая (x,y) плана.
const COS = [1, 0, -1, 0], SIN = [0, 1, 0, -1];
K.xf = function (item) {
  const k = (((Math.round(item.rot / 90)) % 4) + 4) % 4, c = COS[k], s = SIN[k];
  return (lx, ly) => [item.x + lx * c - ly * s, item.y + lx * s + ly * c];
};
K.inv = function (item, px, py) {
  const k = (((Math.round(item.rot / 90)) % 4) + 4) % 4, c = COS[k], s = SIN[k];
  const dx = px - item.x, dy = py - item.y;
  return [dx * c + dy * s, -dx * s + dy * c];
};

// Габарит: плановый прямоугольник и вертикальный диапазон
K.extent = function (item, mod, S) {
  const sc = K.modScope(mod, item.p, S);
  const W = sc.W, D = sc.D;
  if (!(W > 0) || !(D > 0)) throw new Error('В модуле нужны параметры W и D');
  const f = K.xf(item), tf = sc.tf;
  const pts = [f(0, -tf), f(W, -tf), f(W, D), f(0, D)];
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const z0 = K.ev(mod.z0 || '0', sc) + (item.zOff || 0);
  const h = sc.H !== undefined ? sc.H : sc.T !== undefined ? sc.T : 0;
  return { pts, minx: Math.min(...xs), maxx: Math.max(...xs), miny: Math.min(...ys), maxy: Math.max(...ys), z0, z1: z0 + h, W, D, H: h, tf };
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

// Сборка деталей одного шкафа. Возвращает {parts, hw, z0, sc}
K.buildItem = function (item, S, mod) {
  const sc = K.modScope(mod, item.p, S);
  const z0 = K.ev(mod.z0 || '0', sc) + (item.zOff || 0);
  const parts = [];
  for (const d of mod.parts || []) {
    if (d.if !== undefined && String(d.if).trim() !== '' && !K.ev(d.if, sc)) continue;
    const n = Math.max(0, Math.round(K.ev(d.count === undefined || d.count === '' ? 1 : d.count, sc)));
    const md = S.mats[d.mat];
    if (!md) throw new Error('Деталь «' + d.name + '»: неизвестный материал «' + d.mat + '»');
    for (let i = 0; i < n; i++) {
      const s = Object.assign({}, sc, { i, n });
      const mn = [K.ev(d.x, s), K.ev(d.y, s), K.ev(d.z, s)].map(r1);
      const sz = [K.ev(d.sx, s), K.ev(d.sy, s), K.ev(d.sz, s)].map(r1);
      if (sz.some((v) => !(v > 0))) throw new Error('Деталь «' + d.name + '»: размер ≤ 0 (' + sz.join('×') + ')');
      const ax = axes(sz, d.lax);
      parts.push({
        cab: item.label, base: d.name, name: n > 1 ? d.name + ' ' + (i + 1) : d.name, mat: d.mat, md,
        mn, sz, ax, L: sz[ax.aL], W: sz[ax.aW], T: sz[ax.aT],
        edge: parseEdge(d.edge), role: d.role || '', drill: d.drill || '', to: d.to || 'side',
        hinge: d.hinge !== undefined && String(d.hinge).trim() !== '' ? Math.sign(K.ev(d.hinge, s)) : 0, holes: []
      });
    }
  }
  drill(parts, sc);
  const hw = [];
  for (const h of mod.hardware || []) { const q = Math.round(K.ev(h.qty, sc)); if (q > 0) hw.push({ name: K.tpl(h.name, sc), qty: q }); }
  const cnt = (k) => parts.reduce((a, p) => a + p.holes.filter((h) => h.kind === k).length, 0);
  const auto = [['Конфирмат 7×50', cnt('conf5')], ['Полкодержатель Ø5', cnt('pin')], ['Петля накладная с планкой (чашка Ø35)', cnt('cup')], ['Евровинт 6,3×13 для планки петли', cnt('cup') * 2]];
  for (const [name, qty] of auto) if (qty > 0) hw.push({ name, qty });
  return { parts, hw, z0, sc };
};

// Точка в системе детали: l — вдоль длины, w — вдоль ширины, от угла (L1∩W1), глубина — по толщине
function hole(part, kind, d, depth, p, axis, note) {
  const { aL, aW } = part.ax;
  part.holes.push({ kind, d, depth, l: r1(p[aL] - part.mn[aL]), w: r1(p[aW] - part.mn[aW]), axis, face: axis === part.ax.aT ? 'пласть' : 'торец', note: note || '' });
}
function positions(span, edgeOff) { return span >= 150 ? [edgeOff, span - edgeOff] : [span / 2]; }
const inRange = (v, a, b) => v >= a - 0.5 && v <= b + 0.5;

function drill(parts, sc) {
  const byRole = (r) => parts.filter((p) => p.role === r);
  const eq = (a, b) => Math.abs(a - b) < 0.6;

  // Конфирматы: торцы по оси X, отверстия в смежных боковинах сквозные Ø7
  for (const h of parts.filter((p) => p.drill === 'conf')) {
    if (h.ax.aT === 0) continue; // торцы по x возможны только если x — не толщина
    const inAx = h.ax.aT === 1 ? 2 : 1; // ось «вдоль торца» (не x, не толщина)
    const span = h.sz[inAx];
    const pos = positions(span, 50);
    const mid = h.mn[h.ax.aT] + h.sz[h.ax.aT] / 2;
    const targets = byRole(h.to);
    for (const ex of [h.mn[0], h.mn[0] + h.sz[0]]) {
      for (const q of pos) {
        const pt = [0, 0, 0]; pt[0] = ex; pt[inAx] = h.mn[inAx] + q; pt[h.ax.aT] = mid;
        hole(h, 'conf5', 5, 50, pt, 0, 'в торец');
        for (const s of targets) {
          const touch = eq(s.mn[0] + s.sz[0], ex) || eq(s.mn[0], ex);
          if (!touch) continue;
          if (!inRange(pt[1], s.mn[1], s.mn[1] + s.sz[1]) || !inRange(pt[2], s.mn[2], s.mn[2] + s.sz[2])) continue;
          const outer = eq(s.mn[0] + s.sz[0], ex) ? s.mn[0] : s.mn[0] + s.sz[0]; // наружная пласть боковины
          hole(s, 'conf7', 7, s.sz[0], [outer, pt[1], pt[2]], 0, 'сквозное');
        }
      }
    }
  }

  // Полкодержатели в боковинах
  for (const sh of parts.filter((p) => p.drill === 'shelf')) {
    const ys = [sh.mn[1] + 40, sh.mn[1] + sh.sz[1] - 40];
    for (const s of byRole('side')) {
      let x = null;
      if (s.mn[0] + s.sz[0] <= sh.mn[0] + 1) x = s.mn[0] + s.sz[0];
      else if (s.mn[0] >= sh.mn[0] + sh.sz[0] - 1) x = s.mn[0];
      if (x === null) continue;
      for (const y of ys) hole(s, 'pin', 5, 12, [x, y, sh.mn[2]], 0, 'под полку «' + sh.name + '»');
    }
  }

  // Петли: чашка Ø35×12,5 в фасаде, планка (2×Ø5×13) в боковине
  for (const d of parts.filter((p) => p.hinge !== 0)) {
    const hgt = d.sz[2];
    const n = 2 + (hgt > 900) + (hgt > 1600) + (hgt > 2000);
    const zs = [];
    for (let k = 0; k < n; k++) zs.push(k === 0 ? d.mn[2] + 100 : k === n - 1 ? d.mn[2] + hgt - 100 : d.mn[2] + 100 + (hgt - 200) * k / (n - 1));
    const edgeX = d.hinge < 0 ? d.mn[0] : d.mn[0] + d.sz[0];
    const cupX = edgeX + (d.hinge < 0 ? 22.5 : -22.5);
    for (const z of zs) {
      hole(d, 'cup', 35, 12.5, [cupX, d.mn[1] + d.sz[1], z], 1, 'чашка петли, 22,5 от кромки');
      for (const s of byRole('side')) {
        const ok = d.hinge < 0 ? s.mn[0] <= d.mn[0] + d.sz[0] / 2 : s.mn[0] >= d.mn[0] + d.sz[0] / 2;
        if (!ok || !inRange(z, s.mn[2], s.mn[2] + s.sz[2])) continue;
        const x = s.mn[0] === Math.min(...byRole('side').map((q) => q.mn[0])) ? s.mn[0] + s.sz[0] : s.mn[0];
        for (const y of [37, 69]) hole(s, 'plate', 5, 13, [x, y, z], 0, 'планка петли');
      }
    }
  }
}

// Мировые боксы всех деталей шкафа (AABB; поворот кратен 90)
K.worldBoxes = function (item, built) {
  const f = K.xf(item);
  return built.parts.map((p) => {
    const a = f(p.mn[0], p.mn[1]), b = f(p.mn[0] + p.sz[0], p.mn[1] + p.sz[1]);
    return {
      mn: [Math.min(a[0], b[0]), Math.min(a[1], b[1]), built.z0 + p.mn[2]],
      mx: [Math.max(a[0], b[0]), Math.max(a[1], b[1]), built.z0 + p.mn[2] + p.sz[2]],
      mat: p.mat, role: p.role, name: p.cab + ' ' + p.name, part: p
    };
  });
};

K.r1 = r1;
})(window.K = window.K || {});
