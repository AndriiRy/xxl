/* Сауна «Кассета-24» — параметрическая модель кассет из ОСП-3 18 мм.
   Единицы: мм. Оси: X — ширина (фасад с дверью при z=0), Y — вверх, Z — глубина.
   Один источник данных для 3D, деталировки, карты раскроя и DXF. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.SaunaModel = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const P = {
    t: 18, rib: 150, W: 2400, D: 2200,
    floorH: 186, wallH: 2100, roofIn: 2436,
    sheetL: 2500, sheetW: 1250, margin: 10, gap: 12, tool: 6,
    tabLen: 60, slotClear: 0.5, boltStep: 400, holeD: 9, markD: 3, screwStep: 150,
    wallMaxClear: 580, floorMaxClear: 380, density: 640,
    fin: { foil: 1, batten: 20, battenW: 40, lining: 14 },
  };
  const t = P.t;
  const Y0 = P.floorH, Y1 = P.floorH + P.wallH; // 186 … 2286
  const IN = P.t + P.rib + P.fin.foil + P.fin.batten + P.fin.lining; // 203 от наружной грани
  const interior = { x0: IN, x1: P.W - IN, z0: IN, z1: P.D - IN, y0: Y0 + 30, y1: P.roofIn - (P.rib + P.fin.foil + P.fin.batten + P.fin.lining) };

  const R = (u0, u1, v0, v1, extra) => Object.assign({ u0, u1, v0, v1 }, extra || {});
  const ov = (a0, a1, b0, b1) => Math.min(a1, b1) - Math.max(a0, b0);

  /* ---------- генераторы рёбер ---------- */
  function wallRibs(reg, openings, maxClear, joint) {
    const { u0: uA, u1: uB, v0: vA, v1: vB } = reg;
    const ribs = [];
    const floorOps = openings.filter(o => o.v0 <= vA + 1).sort((a, b) => a.u0 - b.u0);
    let cur = uA;
    for (const o of floorOps) {
      if (o.u0 - t > cur) ribs.push(R(cur, o.u0 - t, vA, vA + t, { role: 'Обвязка нижняя' }));
      cur = o.u1 + t;
    }
    if (uB > cur) ribs.push(R(cur, uB, vA, vA + t, { role: 'Обвязка нижняя' }));
    ribs.push(R(uA, uB, vB - t, vB, { role: 'Обвязка верхняя' }));
    ribs.push(R(uA, uA + t, vA + t, vB - t, { role: joint === 'u0' ? 'Стойка стыковая' : 'Стойка крайняя', full: true, joint: joint === 'u0' }));
    ribs.push(R(uB - t, uB, vA + t, vB - t, { role: joint === 'u1' ? 'Стойка стыковая' : 'Стойка крайняя', full: true, joint: joint === 'u1' }));
    const verts = [uA, uB - t];
    for (const o of openings) {
      const vs = o.v0 <= vA + 1 ? vA : vA + t;
      ribs.push(R(o.u0 - t, o.u0, vs, vB - t, { role: 'Стойка проёма', full: true, jamb: -1, op: o.name }));
      ribs.push(R(o.u1, o.u1 + t, vs, vB - t, { role: 'Стойка проёма', full: true, jamb: 1, op: o.name }));
      verts.push(o.u0 - t, o.u1);
      ribs.push(R(o.u0, o.u1, o.v1, o.v1 + t, { role: 'Ригель проёма' }));
      if (o.v0 > vA + 1) ribs.push(R(o.u0, o.u1, o.v0 - t, o.v0, { role: 'Подоконный ригель' }));
    }
    verts.sort((a, b) => a - b);
    for (let i = 0; i < verts.length - 1; i++) {
      const a = verts[i] + t, b = verts[i + 1], clear = b - a;
      if (clear <= maxClear) continue;
      const k = Math.ceil((clear + t) / (maxClear + t)) - 1;
      const c = (clear - k * t) / (k + 1);
      for (let j = 1; j <= k; j++) {
        const s = Math.round(a + j * c + (j - 1) * t);
        const op = openings.find(o => s + t > o.u0 && s < o.u1);
        if (!op) ribs.push(R(s, s + t, vA + t, vB - t, { role: 'Стойка', full: true }));
        else {
          if (op.v0 > vA + 1 && op.v0 - t - (vA + t) > 40) ribs.push(R(s, s + t, vA + t, op.v0 - t, { role: 'Стойка короткая' }));
          if (vB - t - (op.v1 + t) > 40) ribs.push(R(s, s + t, op.v1 + t, vB - t, { role: 'Стойка короткая' }));
        }
      }
    }
    return ribs;
  }

  function fill(fixed, maxClear) { // fixed: отсортированные начала рёбер толщиной t
    const out = [...fixed];
    for (let i = 0; i < fixed.length - 1; i++) {
      const a = fixed[i] + t, b = fixed[i + 1], clear = b - a;
      if (clear <= maxClear) continue;
      const k = Math.ceil((clear + t) / (maxClear + t)) - 1;
      const c = (clear - k * t) / (k + 1);
      for (let j = 1; j <= k; j++) out.push(Math.round(a + j * c + (j - 1) * t));
    }
    return out.sort((a, b) => a - b);
  }

  function floorRibs(reg, joint) {
    const { u0, u1, v0, v1 } = reg;
    const ribs = [
      R(u0, u1, v0, v0 + t, { role: joint === 'v0' ? 'Балка стыковая' : 'Балка обвязки', joint: joint === 'v0' }),
      R(u0, u1, v1 - t, v1, { role: joint === 'v1' ? 'Балка стыковая' : 'Балка обвязки', joint: joint === 'v1' }),
    ];
    const xs = fill([u0, 150, P.W - 168, u1 - t], P.floorMaxClear);
    xs.forEach(x => ribs.push(R(x, x + t, v0 + t, v1 - t, { role: 'Лага' })));
    return ribs;
  }

  function roofRibs(reg, joint, inner, extra) {
    const { u0, u1, v0, v1 } = reg;
    const ribs = [
      R(u0, u1, v0, v0 + t, { role: joint === 'v0' ? 'Балка стыковая' : 'Балка обвязки', joint: joint === 'v0' }),
      R(u0, u1, v1 - t, v1, { role: joint === 'v1' ? 'Балка стыковая' : 'Балка обвязки', joint: joint === 'v1' }),
      R(u0, u0 + t, v0 + t, v1 - t, { role: 'Ребро торцевое' }),
      R(u1 - t, u1, v0 + t, v1 - t, { role: 'Ребро торцевое' }),
    ];
    inner.forEach(([v, role]) => ribs.push(R(u0 + t, u1 - t, v, v + t, { role })));
    (extra || []).forEach(r => ribs.push(r));
    return ribs;
  }

  /* ---------- кассеты ---------- */
  const X = [1, 0, 0], Xn = [-1, 0, 0], Yv = [0, 1, 0], Yn = [0, -1, 0], Z = [0, 0, 1], Zn = [0, 0, -1];
  const door = { name: 'Дверной проём', kind: 'door', u0: 250, u1: 960, v0: Y0, v1: Y0 + 1910 };
  const exhaust = { name: 'Вытяжка 150×150', kind: 'vent', u0: 300, u1: 450, v0: Y0 + 1700, v1: Y0 + 1850 };
  const windowOp = { name: 'Окно', kind: 'window', u0: 495, u1: 905, v0: Y0 + 1100, v1: Y0 + 1510 };
  const supply = { name: 'Приток 150×150', kind: 'vent', u0: 612, u1: 762, v0: Y0 + 300, v1: Y0 + 450 };
  const chimney = { name: 'Проход дымохода', kind: 'chimney', u0: 1523, u1: 1903, v0: 497, v1: 877 };

  const cassettes = [];
  function wall(code, name, face, O, U, N, skinU, regU, ops, joint) {
    const reg = R(regU[0], regU[1], Y0, Y1);
    cassettes.push({
      code, name, group: 'wall', face, O, U, V: Yv, N,
      skins: [{ n: -t, ...R(skinU[0], skinU[1], 0, P.roofIn) }],
      reg, openings: ops, joint,
      ribs: wallRibs(reg, ops, P.wallMaxClear, joint),
    });
  }
  wall('ФС1', 'Фасад, левая (дверь)', 'front', [0, 0, t], X, Z, [0, 1200], [t, 1200], [door], 'u1');
  wall('ФС2', 'Фасад, правая', 'front', [0, 0, t], X, Z, [1200, 2400], [1200, 2400 - t], [], 'u0');
  wall('ЗД1', 'Задняя, левая', 'back', [0, 0, P.D - t], X, Zn, [0, 1200], [t, 1200], [exhaust], 'u1');
  wall('ЗД2', 'Задняя, правая', 'back', [0, 0, P.D - t], X, Zn, [1200, 2400], [1200, 2400 - t], [], 'u0');
  wall('ЛВ1', 'Левая, передняя (окно)', 'left', [t, 0, 0], Z, X, [t, 1100], [t + P.rib, 1100], [windowOp], 'u1');
  wall('ЛВ2', 'Левая, задняя', 'left', [t, 0, 0], Z, X, [1100, P.D - t], [1100, P.D - t - P.rib], [], 'u0');
  wall('ПР1', 'Правая, передняя (приток)', 'right', [P.W - t, 0, 0], Z, Xn, [t, 1100], [t + P.rib, 1100], [supply], 'u1');
  wall('ПР2', 'Правая, задняя', 'right', [P.W - t, 0, 0], Z, Xn, [1100, P.D - t], [1100, P.D - t - P.rib], [], 'u0');

  // потолок / кровля: рёбра вдоль X (пролёт по ширине)
  const roof1Reg = R(t, P.W - t, t, 1100);
  cassettes.push({
    code: 'ПТ1', name: 'Потолок, передний (дымоход)', group: 'roof', face: 'roof', O: [0, P.roofIn, 0], U: X, V: Z, N: Yn,
    skins: [{ n: -t, ...R(0, P.W, 0, 1100) }], reg: roof1Reg, openings: [chimney], joint: 'v1',
    ribs: roofRibs(roof1Reg, 'v1', [[250, 'Балка сдвоенная'], [268, 'Балка сдвоенная'], [479, 'Балка-обрамление'], [877, 'Балка-обрамление']],
      [R(1505, 1523, 497, 877, { role: 'Ребро обрамления' }), R(1903, 1921, 497, 877, { role: 'Ребро обрамления' })]),
  });
  const roof2Reg = R(t, P.W - t, 1100, P.D - t);
  cassettes.push({
    code: 'ПТ2', name: 'Потолок, задний', group: 'roof', face: 'roof', O: [0, P.roofIn, 0], U: X, V: Z, N: Yn,
    skins: [{ n: -t, ...R(0, P.W, 1100, P.D) }], reg: roof2Reg, openings: [], joint: 'v0',
    ribs: roofRibs(roof2Reg, 'v0', [[1443, 'Балка сдвоенная'], [1461, 'Балка сдвоенная'], [1804, 'Балка сдвоенная'], [1822, 'Балка сдвоенная']]),
  });
  // пол: две обшивки, лаги вдоль Z
  const fl1 = R(t, P.W - t, t, 1100), fl2 = R(t, P.W - t, 1100, P.D - t);
  cassettes.push({ code: 'ПЛ1', name: 'Пол, передний', group: 'floor', face: 'floor', O: [0, t, 0], U: X, V: Z, N: Yv,
    skins: [{ n: -t, ...fl1, side: 'низ' }, { n: P.rib, ...fl1, side: 'верх' }], reg: fl1, openings: [], joint: 'v1', ribs: floorRibs(fl1, 'v1') });
  cassettes.push({ code: 'ПЛ2', name: 'Пол, задний', group: 'floor', face: 'floor', O: [0, t, 0], U: X, V: Z, N: Yv,
    skins: [{ n: -t, ...fl2, side: 'низ' }, { n: P.rib, ...fl2, side: 'верх' }], reg: fl2, openings: [], joint: 'v0', ribs: floorRibs(fl2, 'v0') });

  /* ---------- внутренняя отделка по кассетам ---------- */
  cassettes.forEach(c => {
    if (c.group === 'floor') return;
    let lu0, lu1, lv0, lv1;
    if (c.group === 'wall') {
      const lim = (c.face === 'front' || c.face === 'back') ? [interior.x0, interior.x1] : [interior.z0, interior.z1];
      lu0 = Math.max(c.reg.u0, lim[0]); lu1 = Math.min(c.reg.u1, lim[1]);
      if (c.joint === 'u1') lu1 = c.reg.u1; else lu0 = c.reg.u0;
      lv0 = Y0; lv1 = interior.y1;
    } else {
      lu0 = interior.x0; lu1 = interior.x1;
      lv0 = Math.max(c.reg.v0, interior.z0); lv1 = Math.min(c.reg.v1, interior.z1);
      if (c.joint === 'v1') lv1 = c.reg.v1; else lv0 = c.reg.v0;
    }
    c.lining = R(lu0, lu1, lv0, lv1);
    const bw = P.fin.battenW;
    let pos = [];
    if (c.group === 'wall') {
      c.ribs.filter(r => r.full).forEach(r => {
        let p = r.jamb === -1 ? r.u1 - bw : r.jamb === 1 ? r.u0 : (r.u0 + r.u1) / 2 - bw / 2;
        pos.push(p);
      });
    } else {
      const n = Math.ceil((interior.x1 - interior.x0) / 480);
      for (let i = 0; i <= n; i++) pos.push(interior.x0 + (interior.x1 - interior.x0 - bw) * i / n);
    }
    pos = pos.map(p => Math.min(Math.max(p, lu0), lu1 - bw)).sort((a, b) => a - b)
      .filter((p, i, a) => i === 0 || p - a[i - 1] > 50);
    c.battens = [];
    pos.forEach(p => {
      let segs = [[lv0, lv1]];
      c.openings.forEach(o => {
        if (ov(p, p + bw, o.u0, o.u1) <= 0) return;
        segs = segs.flatMap(([a, b]) => {
          const r = [];
          if (o.v0 > a) r.push([a, Math.min(b, o.v0)]);
          if (o.v1 < b) r.push([Math.max(a, o.v1), b]);
          return r;
        }).filter(([a, b]) => b - a > 60);
      });
      segs.forEach(([a, b]) => c.battens.push(R(p, p + bw, a, b)));
    });
  });

  /* ---------- детали для ЧПУ ---------- */
  const inRect = (r, s, m) => r.u0 >= s.u0 + m && r.u1 <= s.u1 - m && r.v0 >= s.v0 + m && r.v1 <= s.v1 - m;
  const hit = (r, o, m) => ov(r.u0 - m, r.u1 + m, o.u0, o.u1) > 0 && ov(r.v0 - m, r.v1 + m, o.v0, o.v1) > 0;

  const ribParts = [], skinParts = [];
  cassettes.forEach(c => {
    c.slots = c.skins.map(() => []);
    c.marks = c.skins.map(() => []);
    c.ribs.forEach((r, i) => {
      const du = r.u1 - r.u0, dv = r.v1 - r.v0;
      const dir = du >= dv ? 'u' : 'v';
      const L = Math.max(du, dv);
      const k = L < 120 ? 0 : Math.max(1, Math.round(L / 450));
      const tl = L < 250 ? 40 : P.tabLen;
      const centers = []; for (let j = 0; j < k; j++) centers.push(Math.round(L * (j + 0.5) / k));
      const tabs = c.skins.map((s, si) => {
        const ok = [];
        centers.forEach(cc => {
          const h = (tl + P.slotClear) / 2, w = (t + P.slotClear) / 2;
          const mid = dir === 'u' ? [r.u0 + cc, (r.v0 + r.v1) / 2] : [(r.u0 + r.u1) / 2, r.v0 + cc];
          const sl = dir === 'u' ? R(mid[0] - h, mid[0] + h, mid[1] - w, mid[1] + w) : R(mid[0] - w, mid[0] + w, mid[1] - h, mid[1] + h);
          if (inRect(sl, s, 30) && !c.openings.some(o => hit(sl, o, 30))) { ok.push(cc); c.slots[si].push(sl); }
        });
        return ok;
      });
      // разметка Ø3 под саморезы по оси ребра
      c.skins.forEach((s, si) => {
        for (let p = 40; p <= L - 40; p += P.screwStep) {
          if (tabs[si].some(cc => Math.abs(cc - p) < tl / 2 + 15)) continue;
          const m = dir === 'u' ? [r.u0 + p, (r.v0 + r.v1) / 2] : [(r.u0 + r.u1) / 2, r.v0 + p];
          if (m[0] > s.u0 + 8 && m[0] < s.u1 - 8 && m[1] > s.v0 + 8 && m[1] < s.v1 - 8) c.marks[si].push(m);
        }
      });
      let holes = [];
      if (r.joint) {
        const n = Math.max(2, Math.ceil((L - 200) / P.boltStep) + 1);
        for (let j = 0; j < n; j++) holes.push(Math.round(100 + (L - 200) * j / (n - 1)));
      }
      const tb = tabs[0] || [], tt = (c.skins.length > 1 ? tabs[1] : []) || [];
      ribParts.push({
        id: `${c.code}-${String(i + 1).padStart(2, '0')}`, cas: c.code, role: r.role, L, tabLen: tl,
        tabsB: tb, tabsT: tt, holes, rect: r, dir, joint: !!r.joint,
        h: P.rib + (tb.length ? t : 0) + (tt.length ? t : 0),
      });
    });
  });

  // нахлёсты обшивки стен на пол, потолок и соседние стены — разметка саморезов
  cassettes.filter(c => c.group === 'wall').forEach(c => {
    const s = c.skins[0], m = c.marks[0];
    const lineU = (v, a, b) => { for (let p = a + 40; p <= b - 40; p += P.screwStep) m.push([p, v]); };
    const lineV = (u, a, b) => { for (let p = a + 40; p <= b - 40; p += P.screwStep) m.push([u, p]); };
    const a = Math.max(s.u0, t), b = Math.min(s.u1, (c.face === 'front' || c.face === 'back') ? P.W - t : P.D - t);
    lineU(t + P.rib / 2, a, b);                 // в балки пола
    lineU(P.roofIn - P.rib / 2, a, b);          // в балки потолка
    if (c.face === 'left' || c.face === 'right') {
      if (s.u0 <= t) lineV(t + P.rib / 2, Y0, Y1);           // в крайнюю стойку фасада
      if (s.u1 >= P.D - t) lineV(P.D - t - P.rib / 2, Y0, Y1); // в крайнюю стойку задней стены
    }
  });

  cassettes.forEach(c => {
    c.skins.forEach((s, si) => {
      const holes = c.openings.filter(o => ov(o.u0, o.u1, s.u0, s.u1) > 0 && ov(o.v0, o.v1, s.v0, s.v1) > 0);
      skinParts.push({
        id: c.skins.length > 1 ? `${c.code}-О${si ? 'В' : 'Н'}` : `${c.code}-О`, cas: c.code,
        role: c.skins.length > 1 ? `Обшивка ${s.side}` : 'Обшивка', rect: s, holes, slots: c.slots[si], marks: c.marks[si],
        mirror: dot(cross(c.U, c.V), c.N) < 0,
      });
    });
  });

  function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
  function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }

  /* ---------- 2D-развёртка деталей ---------- */
  function rectPoly(x0, y0, x1, y1) { return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]; }
  function skin2D(sp) {
    const s = sp.rect, w = s.u1 - s.u0, h = s.v1 - s.v0, rot = h > w;
    const map = (u, v) => {
      let lu = (sp.mirror ? s.u1 - u : u - s.u0), lv = v - s.v0;
      return rot ? [lv, w - lu] : [lu, lv];
    };
    const mapR = r => { const a = map(r.u0, r.v0), b = map(r.u1, r.v1); return rectPoly(Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[0], b[0]), Math.max(a[1], b[1])); };
    return {
      id: sp.id, kind: 'skin', role: sp.role, w: rot ? h : w, h: rot ? w : h,
      outer: [rectPoly(0, 0, rot ? h : w, rot ? w : h)],
      inner: [...sp.holes.map(o => ({ poly: mapR(R(Math.max(o.u0, s.u0), Math.min(o.u1, s.u1), Math.max(o.v0, s.v0), Math.min(o.v1, s.v1))), type: 'cut' })),
        ...sp.slots.map(sl => ({ poly: mapR(sl), type: 'slot' }))],
      circles: sp.marks.map(m => { const p = map(m[0], m[1]); return { x: p[0], y: p[1], d: P.markD, type: 'mark' }; }),
    };
  }
  function rib2D(rp) {
    const L = rp.L, hb = rp.tabsB.length ? t : 0, ht = rp.tabsT.length ? t : 0, y0 = hb, y1 = hb + P.rib, H = y1 + ht, tl = rp.tabLen;
    const pts = [[0, y0]];
    rp.tabsB.forEach(c => { pts.push([c - tl / 2, y0], [c - tl / 2, 0], [c + tl / 2, 0], [c + tl / 2, y0]); });
    pts.push([L, y0], [L, y1]);
    [...rp.tabsT].reverse().forEach(c => { pts.push([c + tl / 2, y1], [c + tl / 2, H], [c - tl / 2, H], [c - tl / 2, y1]); });
    pts.push([0, y1]);
    return {
      id: rp.id, kind: 'rib', role: rp.role, w: L, h: H, outer: [pts], inner: [],
      circles: rp.holes.map(x => ({ x, y: y0 + P.rib / 2, d: P.holeD, type: 'bolt' })),
    };
  }
  const parts2D = [...skinParts.map(skin2D), ...ribParts.map(rib2D)];

  // группировка одинаковых рёбер в позиции
  const groups = new Map();
  ribParts.forEach(rp => {
    const key = [rp.L, rp.h, rp.tabsB.join('.'), rp.tabsT.join('.'), rp.holes.join('.'), rp.tabLen].join('|');
    if (!groups.has(key)) groups.set(key, { key, L: rp.L, h: rp.h, tabs: rp.tabsB.length + rp.tabsT.length, holes: rp.holes.length, roles: new Set(), items: [] });
    const g = groups.get(key); g.items.push(rp); g.roles.add(rp.role);
  });
  const ribGroups = [...groups.values()].sort((a, b) => b.L - a.L || b.h - a.h || b.tabs - a.tabs);
  ribGroups.forEach((g, i) => { g.mark = 'Р' + String(i + 1).padStart(2, '0'); g.items.forEach(it => { it.mark = g.mark; }); });
  parts2D.forEach(p => { const rp = ribParts.find(r => r.id === p.id); if (rp) p.mark = rp.mark; });

  /* ---------- раскрой (полосовой, без поворота: длина детали — вдоль листа) ---------- */
  function nest(parts) {
    const UL = P.sheetL - 2 * P.margin, UW = P.sheetW - 2 * P.margin, g = P.gap;
    const sheets = [];
    const big = parts.filter(p => p.h > 600).sort((a, b) => b.w * b.h - a.w * a.h);
    const small = parts.filter(p => p.h <= 600).sort((a, b) => b.h - a.h || b.w - a.w);
    big.forEach(p => sheets.push({ parts: [{ p, x: P.margin, y: P.margin }], rows: [], usedH: p.h + g }));
    small.forEach(p => {
      for (const sh of sheets) for (const row of sh.rows) {
        if (row.h >= p.h && row.x + p.w <= UL) { sh.parts.push({ p, x: P.margin + row.x, y: P.margin + row.y }); row.x += p.w + g; return; }
      }
      for (const sh of sheets) {
        if (sh.usedH + p.h <= UW) { const row = { y: sh.usedH, h: p.h, x: p.w + g }; sh.rows.push(row); sh.usedH += p.h + g; sh.parts.push({ p, x: P.margin, y: P.margin + row.y }); return; }
      }
      const sh = { parts: [], rows: [], usedH: 0 }; sheets.push(sh);
      const row = { y: 0, h: p.h, x: p.w + g }; sh.rows.push(row); sh.usedH = p.h + g; sh.parts.push({ p, x: P.margin, y: P.margin });
    });
    sheets.forEach((s, i) => { s.n = i + 1; s.area = s.parts.reduce((a, q) => a + q.p.w * q.p.h, 0); s.util = s.area / (P.sheetL * P.sheetW); });
    return sheets;
  }
  const sheets = nest(parts2D);

  /* ---------- DXF R12 ---------- */
  function dxfSheet(sheet) {
    const L = [];
    const e = (...a) => L.push(...a.map(String));
    e(0, 'SECTION', 2, 'HEADER', 9, '$ACADVER', 1, 'AC1009', 9, '$INSUNITS', 70, 4, 0, 'ENDSEC');
    e(0, 'SECTION', 2, 'TABLES', 0, 'TABLE', 2, 'LAYER', 70, 6);
    [['SHEET', 8], ['CUT_OUTER', 1], ['CUT_INNER', 5], ['DRILL_D9', 3], ['MARK_D3', 6], ['ENGRAVE', 2]]
      .forEach(([n, c]) => e(0, 'LAYER', 2, n, 70, 0, 62, c, 6, 'CONTINUOUS'));
    e(0, 'ENDTAB', 0, 'ENDSEC', 0, 'SECTION', 2, 'ENTITIES');
    const f = v => (Math.round(v * 100) / 100).toFixed(2);
    const poly = (pts, layer, ox, oy) => {
      e(0, 'POLYLINE', 8, layer, 66, 1, 70, 1, 10, '0.0', 20, '0.0', 30, '0.0');
      pts.forEach(([x, y]) => e(0, 'VERTEX', 8, layer, 10, f(x + ox), 20, f(y + oy), 30, '0.0'));
      e(0, 'SEQEND', 8, layer);
    };
    poly(rectPoly(0, 0, P.sheetL, P.sheetW), 'SHEET', 0, 0);
    sheet.parts.forEach(({ p, x, y }) => {
      p.outer.forEach(pl => poly(pl, 'CUT_OUTER', x, y));
      p.inner.forEach(q => poly(q.poly, 'CUT_INNER', x, y));
      p.circles.forEach(c => e(0, 'CIRCLE', 8, c.type === 'bolt' ? 'DRILL_D9' : 'MARK_D3', 10, f(c.x + x), 20, f(c.y + y), 30, '0.0', 40, f(c.d / 2)));
      const th = p.kind === 'skin' ? 40 : 22;
      const tx = p.kind === 'skin' ? x + 120 : x + 40, ty = p.kind === 'skin' ? y + p.h / 2 : y + (p.h - P.rib) + 60;
      e(0, 'TEXT', 8, 'ENGRAVE', 10, f(tx), 20, f(ty), 30, '0.0', 40, th, 1, translit(`${p.id}${p.mark ? ' ' + p.mark : ''}${p.kind === 'skin' ? ' VN' : ''}`));
    });
    e(0, 'ENDSEC', 0, 'EOF');
    return L.join('\n') + '\n';
  }
  function translit(s) {
    const m = { 'А':'A','Б':'B','В':'V','Г':'G','Д':'D','Е':'E','Ж':'Zh','З':'Z','И':'I','Й':'Y','К':'K','Л':'L','М':'M','Н':'N','О':'O','П':'P','Р':'R','С':'S','Т':'T','У':'U','Ф':'F','Х':'H','Ц':'C','Ч':'Ch','Ш':'Sh','Щ':'Sch','Ы':'Y','Э':'E','Ю':'Yu','Я':'Ya' };
    return s.split('').map(ch => m[ch] || m[ch.toUpperCase()] || ch).join('');
  }

  /* ---------- сводка материалов ---------- */
  const area = r => (r.u1 - r.u0) * (r.v1 - r.v0);
  const sum = (a, f) => a.reduce((s, x) => s + f(x), 0);
  const ribLen = sum(ribParts, r => r.L);
  const osbVol = sum(parts2D, p => p.w * p.h) * t * 1e-9;
  const insul = sum(cassettes, c => (area(c.reg) - sum(c.openings, o => area(o)) - sum(c.ribs, area)) * P.rib) * 1e-9;
  const liningA = sum(cassettes.filter(c => c.lining), c => area(c.lining) - sum(c.openings, o => Math.max(0, ov(o.u0, o.u1, c.lining.u0, c.lining.u1)) * Math.max(0, ov(o.v0, o.v1, c.lining.v0, c.lining.v1)))) * 1e-6;
  const foilA = sum(cassettes.filter(c => c.lining), c => area(c.reg)) * 1e-6;
  const battenL = sum(cassettes.filter(c => c.battens), c => sum(c.battens, b => b.v1 - b.v0)) / 1000;
  const bolts = sum(ribParts, r => r.holes.length) / 2;
  const skinScrews = sum(skinParts, s => s.marks.length);
  const plateScrews = Math.round(sum(ribParts.filter(r => /Обвязка/.test(r.role)), r => r.L) / 300);
  const ribScrews = ribParts.filter(r => !/Обвязка|Балка обвязки|Балка стыковая/.test(r.role)).length * 4;
  const casWeight = cassettes.map(c => ({
    code: c.code, name: c.name,
    kg: (sum(c.skins, s => area(s) - sum(c.openings, o => Math.max(0, ov(o.u0, o.u1, s.u0, s.u1)) * Math.max(0, ov(o.v0, o.v1, s.v0, s.v1)))) + sum(c.ribs, r => Math.max(r.u1 - r.u0, r.v1 - r.v0) * P.rib)) * t * 1e-9 * P.density,
    ribs: c.ribs.length,
  }));

  return {
    P, interior, cassettes, ribParts, skinParts, parts2D, ribGroups, sheets, dxfSheet,
    openings: { door, exhaust, windowOp, supply, chimney },
    totals: {
      sheets: sheets.length, ribLen: ribLen / 1000, osbVol, osbKg: osbVol * P.density, insul, liningA, foilA, battenL,
      bolts, skinScrews, plateScrews, ribScrews, ribCount: ribParts.length, skinCount: skinParts.length,
      glueKg: ribLen / 1000 * 0.06, volume: (interior.x1 - interior.x0) * (interior.z1 - interior.z0) * (interior.y1 - interior.y0) * 1e-9,
      ext: [P.W, P.roofIn + t, P.D], int: [interior.x1 - interior.x0, interior.y1 - interior.y0, interior.z1 - interior.z0],
    },
    casWeight,
  };
});
