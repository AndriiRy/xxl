(function (K) {
'use strict';
const $ = (id) => document.getElementById(id);
const esc = K.esc, f1 = (n) => Math.round(n * 10) / 10;
const LS_P = 'kitchen.project.v1', LS_L = 'kitchen.lib.v1';
const TYPES = { wall: 'Стена', parapet: 'Парапет', window: 'Окно', door: 'Дверь', water: 'Вода', sewer: 'Канализация', gas: 'Газ', socket: 'Розетка', vent: 'Вытяжка', column: 'Колонна', other: 'Прочее' };

// ---------- состояние ----------
const SOLID = new Set(['wall', 'parapet', 'column']);
let S = K.defaultSettings(), lib = K.defaultLib(), walls = { H: 2700, bodies: [] }, items = [], nextId = 1, sel = null;
let cache = null, view = 'plan', V = { ox: 60, oy: 500, s: 0.12, fitted: false }, cam3 = K.newCam(), cam3fit = false;

function load() {
  try {
    const l = JSON.parse(localStorage.getItem(LS_L));
    if (Array.isArray(l) && l.length) { // стандартные модули обновляются, если вы их не правили; новые добавляются
      for (const d of K.defaultLib()) { const i = l.findIndex((m) => m.id === d.id); if (i < 0) l.push(d); else if (!l[i].edited && (l[i].ver || 0) < d.ver) l[i] = d; }
      lib = l;
    }
  } catch (_) {}
  try { const p = JSON.parse(localStorage.getItem(LS_P)); if (p) { S = Object.assign(S, p.S); walls = p.walls || walls; items = p.items || []; nextId = p.nextId || 1; } } catch (_) {}
  if (!walls.bodies.length && !items.length) walls = sampleRoom();
}
function save() {
  try { localStorage.setItem(LS_L, JSON.stringify(lib)); localStorage.setItem(LS_P, JSON.stringify({ S, walls, items, nextId })); } catch (_) {}
}
const modById = (id) => lib.find((m) => m.id === id);

function sampleRoom() {
  return roomBodies(4000, 3000, 100, 2700, true, null);
}
const pb = (name, type, poly, z0, z1) => { const b = { name, type, min: [0, 0, z0], max: [0, 0, z1] }; setPoly(b, poly); return b; };
function setPoly(b, poly) {
  if (!poly || poly.length < 3) { delete b.poly; return; }
  b.poly = poly.map((p) => [f1(p[0]), f1(p[1])]);
  const xs = b.poly.map((p) => p[0]), ys = b.poly.map((p) => p[1]);
  b.min[0] = Math.min(...xs); b.min[1] = Math.min(...ys); b.max[0] = Math.max(...xs); b.max[1] = Math.max(...ys);
}
const bodyPoly = (b) => (b.poly && b.poly.length >= 3 ? b.poly : [[b.min[0], b.min[1]], [b.max[0], b.min[1]], [b.max[0], b.max[1]], [b.min[0], b.max[1]]]);
// bay: {w, d, ph, wt} — эркер ½ восьмиугольника (стороны под 45°) на северной стене
function roomBodies(A, B, th, H, extras, bay) {
  const w = (name, x0, y0, x1, y1) => ({ name, type: 'wall', min: [x0, y0, 0], max: [x1, y1, H] });
  const b = [w('Стена юг', -th, -th, A + th, 0), w('Стена запад', -th, 0, 0, B), w('Стена восток', A, 0, A + th, B)];
  if (bay) {
    const bw = Math.min(bay.w, A - 200), bx0 = (A - bw) / 2, bx1 = bx0 + bw, d = Math.max(50, Math.min(bay.d, (bw - 100) / 2));
    b.push(w('Стена север 1', -th, B, bx0, B + th), w('Стена север 2', bx1, B, A + th, B + th));
    const P = [[bx0, B], [bx0 + d, B + d], [bx1 - d, B + d], [bx1, B]], N = [];
    for (let i = 0; i < 3; i++) { const dx = P[i + 1][0] - P[i][0], dy = P[i + 1][1] - P[i][1], l = Math.hypot(dx, dy); N.push([-dy / l, dx / l]); }
    const O = P.map((p, i) => { const n1 = i === 0 ? [0, 1] : N[i - 1], n2 = i === 3 ? [0, 1] : N[i], k = th / (1 + n1[0] * n2[0] + n1[1] * n2[1]); return [p[0] + (n1[0] + n2[0]) * k, p[1] + (n1[1] + n2[1]) * k]; });
    const nm = ['левая', 'фронт', 'правая'];
    for (let i = 0; i < 3; i++) {
      const q = [P[i], P[i + 1], O[i + 1], O[i]];
      b.push(pb('Парапет ' + nm[i], 'parapet', q, 0, bay.ph), pb('Окно эркера ' + nm[i], 'window', q, bay.ph, bay.wt), pb('Перемычка ' + nm[i], 'wall', q, bay.wt, H));
    }
  } else b.push(w('Стена север', -th, B, A + th, B + th));
  if (extras) {
    if (!bay) b.push({ name: 'Окно', type: 'window', min: [A * 0.35, B, 900], max: [A * 0.65, B + th, 2100] });
    b.push({ name: 'Дверь', type: 'door', min: [A, B * 0.55, 0], max: [A + th, B * 0.9, 2050] },
      { name: 'Вода', type: 'water', min: [A * 0.08, B - 60, 0], max: [A * 0.08 + 60, B, 600] },
      { name: 'Канализация', type: 'sewer', min: [A * 0.08 + 100, B - 60, 0], max: [A * 0.08 + 160, B, 300] },
      { name: 'Розетка', type: 'socket', min: [-0, B * 0.3, 1050], max: [20, B * 0.3 + 80, 1130] });
  }
  return { H, bodies: b };
}
// ---------- сборка ----------
function builds() {
  if (cache) return cache;
  cache = items.map((item) => {
    const mod = modById(item.mod);
    if (!mod) return { item, mod: { name: '?', id: item.mod }, err: 'Модуль «' + item.mod + '» отсутствует в библиотеке' };
    try { return { item, mod, built: K.buildItem(item, S, mod), ext: K.extent(item, mod, S) }; }
    catch (e) { return { item, mod, err: e.message }; }
  });
  return cache;
}
const okBuilds = () => builds().filter((b) => b.built);
function dirty(noSave) { cache = null; scene3d = null; if (!noSave) save(); redraw(); updateStatus(); }

function collisions() {
  const bad = new Set(), bs = okBuilds();
  const P = bs.map((b) => K.geo.shrink(b.ext.pts, 1));
  const zov = (a0, a1, b0, b1) => Math.min(a1, b1) - Math.max(a0, b0) > 1;
  for (let i = 0; i < bs.length; i++) {
    const a = bs[i].ext;
    for (let j = i + 1; j < bs.length; j++) {
      const b = bs[j].ext;
      if (zov(a.z0, a.z1, b.z0, b.z1) && K.geo.overlap(P[i], P[j])) { bad.add(bs[i].item.id); bad.add(bs[j].item.id); }
    }
    for (const w of walls.bodies) if (SOLID.has(w.type) && zov(a.z0, a.z1, w.min[2], w.max[2]) && K.geo.overlap(P[i], bodyPoly(w))) bad.add(bs[i].item.id);
  }
  return bad;
}
function warnings() {
  const out = [], ids = new Set();
  for (const b of builds()) {
    if (b.err) { out.push(`${b.item.label}: ошибка модуля — ${b.err}`); ids.add(b.item.id); continue; }
    for (const w of walls.bodies) {
      if (w.type !== 'window') continue;
      const e = b.ext;
      // корпус, сдвинутый на 40 мм к стене (за спину), пересекается с окном по плану и по высоте
      const [c, s] = K.cs(b.item.rot), back = K.geo.shrink(e.pts, 30).map((p) => [p[0] - s * 40, p[1] + c * 40]);
      if (e.z1 > w.min[2] + 1 && e.z0 < w.max[2] - 1 && K.geo.overlap(back, bodyPoly(w))) {
        out.push(`${b.item.label} (${b.mod.name}): заходит на «${w.name}» — изделие ${f1(e.z0)}–${f1(e.z1)}, окно ${f1(w.min[2])}–${f1(w.max[2])} мм от пола`);
        ids.add(b.item.id);
      }
    }
  }
  return { out, ids };
}
function updateStatus() {
  const c = collisions().size, w = warnings().out.length;
  $('status').innerHTML = `Шкафов: ${items.length}` + (c ? ` · <span class="err">пересечений: ${c}</span>` : '') + (w ? ` · <span class="err">замечаний: ${w}</span>` : '');
}
// ---------- добавление / привязка ----------
function addItem(modId, at) {
  const mod = modById(modId); if (!mod) return;
  const p = K.defaultParams(mod, S);
  const it = { id: nextId, mod: modId, label: 'К' + nextId, p, x: 0, y: 0, rot: 0, zOff: 0 };
  nextId++;
  let cx, cy;
  if (at) { cx = at[0]; cy = at[1]; } else { const b = bounds(); cx = (b.x0 + b.x1) / 2; cy = (b.y0 + b.y1) / 2; }
  it.x = cx - (p.W || 600) / 2; it.y = cy;
  items.push(it); cache = null;
  attachToWall(it, cx, cy);
  sel = it.id; dirty(); renderProps();
}
function bounds() {
  let x0 = 0, y0 = 0, x1 = 4000, y1 = 3000, any = false;
  for (const b of walls.bodies) for (const p of bodyPoly(b)) {
    if (!any) { x0 = x1 = p[0]; y0 = y1 = p[1]; any = true; }
    x0 = Math.min(x0, p[0]); y0 = Math.min(y0, p[1]); x1 = Math.max(x1, p[0]); y1 = Math.max(y1, p[1]);
  }
  return { x0, y0, x1, y1 };
}
const dot = (p, q) => p[0] * q[0] + p[1] * q[1];
const normRot = (r) => { r = Math.round(r * 100) / 100; return ((r % 360) + 360) % 360; };
// Открытые участки граней стен/парапетов/колонн (обрезаны по соседним телам): отрезок a–b, наружная нормаль n, направление u
function faces() {
  const sol = walls.bodies.filter((b) => SOLID.has(b.type)).map((b) => ({ b, P: K.geo.ccw(bodyPoly(b)) }));
  const out = [];
  for (const { b, P } of sol) {
    const others = sol.filter((o) => o.b !== b);
    for (let i = 0; i < P.length; i++) {
      const a = P[i], c = P[(i + 1) % P.length], dx = c[0] - a[0], dy = c[1] - a[1], l = Math.hypot(dx, dy);
      if (l < 1) continue;
      const n = [dy / l, -dx / l], ts = [0, 1];
      for (const o of others) for (let k = 0; k < o.P.length; k++) {
        const p = o.P[k], q = o.P[(k + 1) % o.P.length], sx = q[0] - p[0], sy = q[1] - p[1], den = dx * sy - dy * sx;
        if (Math.abs(den) < 1e-9) continue;
        const t = ((p[0] - a[0]) * sy - (p[1] - a[1]) * sx) / den, s = ((p[0] - a[0]) * dy - (p[1] - a[1]) * dx) / den;
        if (t > 1e-6 && t < 1 - 1e-6 && s >= -1e-6 && s <= 1 + 1e-6) ts.push(t);
      }
      ts.sort((x, y) => x - y);
      let cur = null; const segs = [];
      for (let k = 0; k < ts.length - 1; k++) {
        if (ts[k + 1] - ts[k] < 1e-9) continue;
        const tm = (ts[k] + ts[k + 1]) / 2, pt = [a[0] + dx * tm + n[0] * 2, a[1] + dy * tm + n[1] * 2];
        if (others.some((o) => K.geo.inside(pt, o.P))) { cur = null; continue; }
        if (cur) cur.t1 = ts[k + 1]; else { cur = { t0: ts[k], t1: ts[k + 1] }; segs.push(cur); }
      }
      for (const sg of segs) {
        const A = [f1(a[0] + dx * sg.t0), f1(a[1] + dy * sg.t0)], B = [f1(a[0] + dx * sg.t1), f1(a[1] + dy * sg.t1)];
        if (Math.hypot(B[0] - A[0], B[1] - A[1]) >= 1) out.push({ a: A, b: B, n, u: [dx / l, dy / l], len: l * (sg.t1 - sg.t0), body: b });
      }
    }
  }
  return out;
}
const same = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1]) < 1;
const faceRot = (f) => normRot(Math.atan2(f.n[0], -f.n[1]) * 180 / Math.PI);
const angDiff = (a, b) => { const d = (((a - b) % 360) + 540) % 360 - 180; return Math.abs(d); };
// Соседняя грань в вершине V: угол между нормалями и тип угла (наружный — стены уходят от комнаты)
function endInfo(f, V, F) {
  for (const g of F) {
    if (g === f || Math.abs(g.u[0] * f.u[1] - g.u[1] * f.u[0]) < 0.01) continue;
    let A = null; if (same(g.a, V)) A = g.b; else if (same(g.b, V)) A = g.a; else continue;
    return { g, ang: Math.acos(Math.max(-1, Math.min(1, dot(f.n, g.n)))) * 180 / Math.PI, outer: dot([A[0] - V[0], A[1] - V[1]], f.n) < 0 };
  }
  return null;
}
// Ряды нижних шкафов спиной к грани f: [[u0,u1],...] вдоль u шкафа
function runsOnFace(f) {
  const rot = faceRot(f), [c, s] = K.cs(rot), u = [c, s], iv = [];
  for (const o of okBuilds()) {
    if (o.mod.cat !== 'base' || o.mod.place === 'corner' || angDiff(o.item.rot, rot) > 0.05) continue;
    const fx = K.xf(o.item), p0 = fx(0, o.built.sc.D), p1 = fx(o.built.sc.W, o.built.sc.D);
    if (Math.abs(dot([p0[0] - f.a[0], p0[1] - f.a[1]], f.n)) > 5) continue;
    const a = dot(p0, u), b = dot(p1, u), sa = dot(f.a, u), sb = dot(f.b, u);
    if (b < Math.min(sa, sb) - 5 || a > Math.max(sa, sb) + 5) continue;
    iv.push([a, b]);
  }
  iv.sort((x, y) => x[0] - y[0]);
  const runs = [];
  for (const v of iv) { const r = runs[runs.length - 1]; if (r && v[0] <= r[1] + 5) r[1] = Math.max(r[1], v[1]); else runs.push(v.slice()); }
  return runs;
}
// Параметры и положение столешницы на грани f для участка [u0,u1] (с подрезкой торцов у изломов стен)
function counterOnFace(it, f, u0, u1, F) {
  const mod = modById(it.mod), rot = faceRot(f), [c, s] = K.cs(rot), u = [c, s];
  const sc0 = K.modScope(mod, it.p, S), dt = sc0.D + sc0.tf + 20;
  const sa = dot(f.a, u), sb = dot(f.b, u), lo = Math.min(sa, sb), hi = Math.max(sa, sb), Vlo = sa < sb ? f.a : f.b, Vhi = sa < sb ? f.b : f.a;
  let cutL = 0, cutR = 0;
  const eL = endInfo(f, Vlo, F), eR = endInfo(f, Vhi, F);
  const reach = (e) => (e.outer ? 5 : dt * Math.tan(e.ang / 2 * Math.PI / 180) + 15);
  // подрезка только если у соседней грани тоже есть ряд шкафов, подходящий к этой вершине
  const nb = (e, V) => { if (!e) return null; const ug = K.cs(faceRot(e.g)), vu = V[0] * ug[0] + V[1] * ug[1]; return runsOnFace(e.g).some((r) => Math.min(Math.abs(r[0] - vu), Math.abs(r[1] - vu)) <= reach(e)) ? e : null; };
  const eL0 = nb(eL, Vlo), eR0 = nb(eR, Vhi);
  if (!eL0 && eL && !eL.outer && u0 - lo <= 5) u0 = lo; if (!eR0 && eR && !eR.outer && hi - u1 <= 5) u1 = hi;
  if (eL0 && u0 - lo <= reach(eL0)) { u0 = lo; cutL = (eL0.outer ? 1 : -1) * Math.round(eL0.ang / 2 * 100) / 100; }
  if (eR0 && hi - u1 <= reach(eR0)) { u1 = hi; cutR = (eR0.outer ? 1 : -1) * Math.round(eR0.ang / 2 * 100) / 100; }
  it.p.W = f1(u1 - u0); it.p.cutL = cutL; it.p.cutR = cutR; it.rot = rot;
  const Q = [f.a[0] + u[0] * (u0 - sa), f.a[1] + u[1] * (u0 - sa)], o = K.xf({ x: 0, y: 0, rot })(0, sc0.D);
  it.x = Q[0] - o[0]; it.y = Q[1] - o[1]; cache = null;
}
const floorFaces = () => { const F = faces().filter((f) => f.body.min[2] < 500), out = []; for (const f of F) if (!out.some((g) => same(g.a, f.a) && same(g.b, f.b))) out.push(f); return out; };
function autoCounters() {
  const mod = lib.find((m) => m.cat === 'counter' && (m.params || []).some((d) => d.id === 'cutL'));
  if (!mod) return alert('В библиотеке нет столешницы с параметрами cutL/cutR');
  items = items.filter((i) => !i.auto); cache = null;
  const F = floorFaces(); let n = 0;
  for (const f of F) for (const [u0, u1] of runsOnFace(f)) {
    const it = { id: nextId, mod: mod.id, label: 'С' + nextId, p: K.defaultParams(mod, S), x: 0, y: 0, rot: 0, zOff: 0, auto: true };
    nextId++; counterOnFace(it, f, u0, u1, F); items.push(it); n++;
  }
  dirty(); renderProps(); alert('Столешниц создано: ' + n + (n ? '\nТорцы у изломов стен подрезаны под угол стыка.' : '\nНет рядов нижних шкафов спиной к стене.'));
}
function itemCollides(it) {
  const mod = modById(it.mod), e = K.extent(it, mod, S), P = K.geo.shrink(e.pts, 1);
  const zov = (a0, a1, b0, b1) => Math.min(a1, b1) - Math.max(a0, b0) > 1;
  for (const w of walls.bodies) if (SOLID.has(w.type) && zov(e.z0, e.z1, w.min[2], w.max[2]) && K.geo.overlap(P, bodyPoly(w))) return true;
  for (const o of okBuilds()) if (o.item.id !== it.id && zov(e.z0, e.z1, o.ext.z0, o.ext.z1) && K.geo.overlap(P, K.geo.shrink(o.ext.pts, 1))) return true;
  return false;
}
function attachToWall(it, px, py) {
  const mod = modById(it.mod);
  if (mod.place === 'corner' && attachCorner(it, px, py)) return;
  const sc = K.modScope(mod, it.p, S);
  let best = null;
  for (const f of faces()) {
    if ((px - f.a[0]) * f.n[0] + (py - f.a[1]) * f.n[1] < -1) continue; // точка за стеной
    const d = K.geo.segDist([px, py], f.a, f.b);
    if (!best || d < best.d) best = { d, f };
  }
  if (!best) return;
  const f = best.f, W = sc.W, D = sc.D;
  if (mod.cat === 'counter' && (mod.params || []).some((d) => d.id === 'cutL')) {
    const F = faces(), rot = faceRot(f), [c0, s0] = K.cs(rot), uu = [c0, s0], pv0 = dot([px, py], uu);
    const runs = runsOnFace(f); let r = runs.find((q) => pv0 >= q[0] - 50 && pv0 <= q[1] + 50) || null;
    if (!r) { const sa0 = dot(f.a, uu), sb0 = dot(f.b, uu); r = [Math.max(Math.min(sa0, sb0), pv0 - W / 2), Math.min(Math.max(sa0, sb0), pv0 + W / 2)]; }
    counterOnFace(it, f, r[0], r[1], F); return;
  }
  const rot = normRot(Math.atan2(f.n[0], -f.n[1]) * 180 / Math.PI), [c, s] = K.cs(rot), u = [c, s];
  const sa = dot(f.a, u), sb = dot(f.b, u), lo = Math.min(sa, sb) + W / 2, hi = Math.max(sa, sb) - W / 2, pv = dot([px, py], u);
  const tc = lo <= hi ? Math.max(lo, Math.min(hi, pv)) : (sa + sb) / 2;
  const Q = [f.a[0] + u[0] * (tc - sa), f.a[1] + u[1] * (tc - sa)];
  it.rot = rot;
  const o = K.xf({ x: 0, y: 0, rot })(W / 2, D);
  it.x = Q[0] - o[0]; it.y = Q[1] - o[1];
  { // прижать к ближайшему концу грани (вершине стены), если до него < 250 мм; приоритет — наружный излом
    const F = faces(), bl = tc - W / 2, br = tc + W / 2, Vlo = sa < sb ? f.a : f.b, Vhi = sa < sb ? f.b : f.a;
    const eL = endInfo(f, Vlo, F), eR = endInfo(f, Vhi, F);
    // внутренний острый излом (напр. 135° в эркере): отступ, при котором фасады соседей сходятся углами
    const off = (e) => (e && !e.outer && e.ang < 89 ? (D + sc.tf) * Math.tan(e.ang / 2 * Math.PI / 180) : 0);
    const tl = lo - W / 2 + off(eL), tr = hi + W / 2 - off(eR);
    const cand = [[tl - bl, Math.abs(tl - bl) - (eL && eL.outer ? 100 : 0)], [tr - br, Math.abs(tr - br) - (eR && eR.outer ? 100 : 0)]]
      .filter((q) => Math.abs(q[0]) < 250).sort((a, b) => a[1] - b[1]);
    if (cand.length) { it.x += u[0] * cand[0][0]; it.y += u[1] * cand[0][0]; }
  }
  const sn = snapPos(it, it.x, it.y, 150, true); it.x = sn[0]; it.y = sn[1];
  cache = null;
  if (itemCollides(it)) { // сдвиг вдоль стены до ближайшего свободного места
    const x0 = it.x, y0 = it.y;
    for (let k = 1; k <= 800; k++) {
      let ok = false;
      for (const sg of [1, -1]) { it.x = x0 + u[0] * 5 * k * sg; it.y = y0 + u[1] * 5 * k * sg; if (!itemCollides(it)) { ok = true; break; } }
      if (ok) { // доводка только вдоль стены
        const x1 = it.x, y1 = it.y, s2 = snapPos(it, x1, y1, 60, true), du = (s2[0] - x1) * u[0] + (s2[1] - y1) * u[1];
        it.x = x1 + du * u[0]; it.y = y1 + du * u[1]; if (itemCollides(it)) { it.x = x1; it.y = y1; } break;
      }
      if (k === 800) { it.x = x0; it.y = y0; }
    }
  }
}
// Угловой модуль: в наружный (выпуклый) излом стен, по биссектрисе; угол излома → параметр ang
function corners() {
  const F = faces(), out = [], same = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1]) < 1;
  for (let i = 0; i < F.length; i++) for (let j = 0; j < F.length; j++) {
    if (i === j) continue;
    const f1 = F[i], f2 = F[j];
    if (!same(f1.b, f2.a)) continue; // f1 заканчивается там, где начинается f2
    const V = f1.b, A2 = f2.b;
    if (dot([A2[0] - V[0], A2[1] - V[1]], f1.n) > -1) continue; // стены поворачивают от комнаты
    const ang = Math.acos(Math.max(-1, Math.min(1, dot(f1.n, f2.n)))) * 180 / Math.PI;
    if (ang < 5 || ang > 120) continue;
    out.push({ V, n1: f1.n, n2: f2.n, ang });
  }
  return out;
}
function attachCorner(it, px, py) {
  const mod = modById(it.mod); let best = null;
  for (const c of corners()) {
    const bx = c.n1[0] + c.n2[0], by = c.n1[1] + c.n2[1];
    if ((px - c.V[0]) * bx + (py - c.V[1]) * by < 0) continue; // точка не со стороны комнаты
    const d = Math.hypot(px - c.V[0], py - c.V[1]); if (!best || d < best.d) best = { d, c };
  }
  if (!best || best.d > 1500) return false;
  const { c } = best, bx = c.n1[0] + c.n2[0], by = c.n1[1] + c.n2[1], l = Math.hypot(bx, by), n = [bx / l, by / l];
  if ((mod.params || []).some((d) => d.id === 'ang')) it.p.ang = Math.round(c.ang * 10) / 10;
  const sc = K.modScope(mod, it.p, S), loc = K.footLocal(mod, sc);
  const apex = loc.reduce((m, p) => (p[1] > m[1] ? p : m), loc[0]);
  it.rot = normRot(Math.atan2(n[0], -n[1]) * 180 / Math.PI);
  const o = K.xf({ x: 0, y: 0, rot: it.rot })(apex[0], apex[1]);
  it.x = c.V[0] - o[0]; it.y = c.V[1] - o[1]; cache = null;
  return true;
}
function snapPos(it, nx, ny, thr, noPoint) {
  const mod = modById(it.mod);
  const e = K.extent(Object.assign({}, it, { x: nx, y: ny }), mod, S);
  thr = thr || 14 / V.s;
  const [c, s] = K.cs(it.rot), u = [c, s], v = [-s, c];
  const others = okBuilds().filter((o) => o.item.id !== it.id), F = faces();
  // 1) угол к углу (соседи, вершины стен)
  const tp = []; for (const o of others) tp.push(...o.ext.pts); for (const f of F) tp.push(f.a, f.b);
  let bp = null;
  for (const p of e.pts) for (const q of tp) { const d = Math.hypot(q[0] - p[0], q[1] - p[1]); if (d < thr && (!bp || d < bp.d)) bp = { d, dx: q[0] - p[0], dy: q[1] - p[1] }; }
  if (bp && !noPoint) return [nx + bp.dx, ny + bp.dy];
  // 2) по осям шкафа: к параллельным граням стен и параллельным соседям
  const par = (d, a) => Math.abs(d[0] * a[1] - d[1] * a[0]) < 0.01;
  const pu = e.pts.map((p) => dot(p, u)), pv = e.pts.map((p) => dot(p, v));
  const U = [Math.min(...pu), Math.max(...pu)], Vv = [Math.min(...pv), Math.max(...pv)], cu = [], cv = [];
  for (const f of F) { if (par(f.u, u)) cv.push(dot(f.a, v)); else if (par(f.u, v)) cu.push(dot(f.a, u)); }
  for (const o of others) { const rd = (((o.item.rot - it.rot) % 90) + 90) % 90; if (rd < 0.01 || rd > 89.99) for (const p of o.ext.pts) { cu.push(dot(p, u)); cv.push(dot(p, v)); } }
  const pick = (cand, ed) => { let b = null; for (const t of cand) for (const x of ed) { const d = t - x; if (Math.abs(d) < thr && (b === null || Math.abs(d) < Math.abs(b))) b = d; } return b || 0; };
  const du = pick(cu, U), dv = pick(cv, Vv);
  return [nx + du * u[0] + dv * v[0], ny + du * u[1] + dv * v[1]];
}
function rotateItem(it, step) {
  const mod = modById(it.mod), e = K.extent(it, mod, S), cl = K.geo.centroid(e.loc), cw = K.xf(it)(cl[0], cl[1]);
  it.rot = normRot(it.rot + (step || 90));
  const o = K.xf({ x: 0, y: 0, rot: it.rot })(cl[0], cl[1]);
  it.x = cw[0] - o[0]; it.y = cw[1] - o[1];
  dirty(); renderProps();
}
// ---------- план ----------
const W2S = (x, y) => [V.ox + x * V.s, V.oy - y * V.s];
const S2W = (px, py) => [(px - V.ox) / V.s, (V.oy - py) / V.s];
const BODY_COL = { wall: '#6b7684', parapet: '#8f8576', window: '#6cb4ee', door: '#b07a4a', water: '#2f80ed', sewer: '#7a5c3c', gas: '#e5c100', socket: '#e5484d', vent: '#8e8e93', column: '#6b7684', other: '#888' };
const CAT_COL = { base: '#d9c7a3', tall: '#c8b48e', wall: '#efe9dc', counter: 'rgba(80,88,100,.55)', filler: '#e5e0d4', other: '#ccc' };
const CAT_Z = { counter: 0, base: 1, tall: 2, filler: 3, wall: 4, other: 5 };

function fitPlan() {
  const cv = $('plan'), b = bounds(); const w = cv.clientWidth || 800, h = cv.clientHeight || 600;
  V.s = Math.min((w - 80) / (b.x1 - b.x0), (h - 80) / (b.y1 - b.y0)); if (!isFinite(V.s) || V.s <= 0) V.s = 0.1;
  V.ox = (w - (b.x1 - b.x0) * V.s) / 2 - b.x0 * V.s; V.oy = (h + (b.y1 - b.y0) * V.s) / 2 + b.y0 * V.s; V.fitted = true;
}
function drawPlan() {
  const cv = $('plan'), dpr = window.devicePixelRatio || 1, W = cv.clientWidth, H = cv.clientHeight;
  if (!W) return;
  if (!V.fitted) fitPlan();
  if (cv.width !== W * dpr || cv.height !== H * dpr) { cv.width = W * dpr; cv.height = H * dpr; }
  const c = cv.getContext('2d'); c.setTransform(dpr, 0, 0, dpr, 0, 0); c.fillStyle = '#10141a'; c.fillRect(0, 0, W, H);
  const [wx0, wy1] = S2W(0, 0), [wx1, wy0] = S2W(W, H);
  for (const [step, col] of [[100, '#1a2029'], [1000, '#28303c']]) {
    if (step * V.s < 6) continue;
    c.strokeStyle = col; c.lineWidth = 1; c.beginPath();
    for (let x = Math.floor(wx0 / step) * step; x <= wx1; x += step) { const p = W2S(x, 0)[0]; c.moveTo(p, 0); c.lineTo(p, H); }
    for (let y = Math.floor(wy0 / step) * step; y <= wy1; y += step) { const p = W2S(0, y)[1]; c.moveTo(0, p); c.lineTo(W, p); }
    c.stroke();
  }
  const path = (pts) => { c.beginPath(); pts.forEach((p, i) => { const q = W2S(p[0], p[1]); i ? c.lineTo(q[0], q[1]) : c.moveTo(q[0], q[1]); }); c.closePath(); };
  const order = ['wall', 'column', 'parapet', 'window', 'door', 'water', 'sewer', 'gas', 'socket', 'vent', 'other'];
  // перемычки над окнами не рисуем поверх окна: окно и парапет видны на плане
  const labels = [];
  const shown = walls.bodies.filter((b) => !(b.type === 'wall' && b.min[2] > 300));
  for (const b of shown.sort((a, z) => order.indexOf(a.type) - order.indexOf(z.type))) {
    const P = bodyPoly(b); path(P);
    c.globalAlpha = SOLID.has(b.type) ? 1 : 0.85; c.fillStyle = BODY_COL[b.type] || '#888'; c.fill(); c.globalAlpha = 1;
    const [x0, y1] = W2S(b.min[0], b.min[1]), [x1, y0] = W2S(b.max[0], b.max[1]);
    const m0 = W2S(...K.geo.centroid(P));
    if ((x1 - x0 > 40 || y1 - y0 > 40) && !labels.some((q) => Math.abs(q[0] - m0[0]) < 60 && Math.abs(q[1] - m0[1]) < 12) && labels.push(m0)) { const m = m0; c.fillStyle = '#e6e9ee'; c.font = '10px sans-serif'; c.textAlign = 'center'; c.fillText(b.name || TYPES[b.type], m[0], m[1] + 3); c.textAlign = 'start'; }
  }
  const bad = collisions(), warn = warnings().ids;
  const bs = okBuilds().sort((a, z) => (CAT_Z[a.mod.cat] ?? 5) - (CAT_Z[z.mod.cat] ?? 5));
  for (const { item, mod, ext } of bs) {
    path(ext.pts); c.fillStyle = CAT_COL[mod.cat] || '#ccc'; c.fill();
    c.setLineDash(mod.cat === 'wall' ? [5, 3] : []);
    c.lineWidth = item.id === sel ? 2.5 : 1;
    c.strokeStyle = bad.has(item.id) ? '#ff4d4d' : warn.has(item.id) ? '#ffa94d' : item.id === sel ? '#4dabf7' : '#222'; c.stroke(); c.setLineDash([]);
    const a = W2S(...ext.pts[0]), b = W2S(...ext.pts[1]);
    c.beginPath(); c.moveTo(a[0], a[1]); c.lineTo(b[0], b[1]); c.lineWidth = 3; c.strokeStyle = '#d6336c'; c.stroke();
    const m = W2S(...K.geo.centroid(ext.pts));
    if (ext.W * V.s > 22) {
      c.fillStyle = '#111'; c.font = '11px sans-serif'; c.textAlign = 'center';
      c.fillText(item.label + ' ' + f1(ext.W), m[0], m[1] + 4);
      if (item.rot % 90) { c.font = '9px sans-serif'; c.fillText(f1(item.rot) + '°', m[0], m[1] + 15); }
      c.textAlign = 'start';
    }
  }
}
function hit(px, py) {
  const w = S2W(px, py);
  const bs = okBuilds().sort((a, z) => (CAT_Z[a.mod.cat] ?? 5) - (CAT_Z[z.mod.cat] ?? 5)).reverse();
  for (const { item, ext } of bs) if (K.geo.inside(w, ext.pts)) return item;
  return null;
}
function initPlan() {
  const cv = $('plan'); let drag = null;
  cv.addEventListener('pointerdown', (e) => {
    const r = cv.getBoundingClientRect(), px = e.clientX - r.left, py = e.clientY - r.top;
    const h = e.button === 0 ? hit(px, py) : null;
    if (h) { sel = h.id; const [wx, wy] = S2W(px, py); drag = { it: h, dx: h.x - wx, dy: h.y - wy, moved: false }; renderProps(); }
    else { if (e.button === 0) { sel = null; renderProps(); } drag = { pan: true, x: e.clientX, y: e.clientY }; }
    cv.setPointerCapture(e.pointerId); drawPlan();
  });
  cv.addEventListener('pointermove', (e) => {
    if (!drag) return;
    if (drag.pan) { V.ox += e.clientX - drag.x; V.oy += e.clientY - drag.y; drag.x = e.clientX; drag.y = e.clientY; drawPlan(); return; }
    const r = cv.getBoundingClientRect(), [wx, wy] = S2W(e.clientX - r.left, e.clientY - r.top);
    const p = e.altKey ? [wx + drag.dx, wy + drag.dy] : snapPos(drag.it, wx + drag.dx, wy + drag.dy);
    drag.it.x = p[0]; drag.it.y = p[1]; drag.moved = true; cache = null; drawPlan();
  });
  cv.addEventListener('pointerup', () => { if (drag && drag.it && drag.moved) { dirty(); renderProps(); } drag = null; });
  cv.addEventListener('wheel', (e) => {
    e.preventDefault(); const r = cv.getBoundingClientRect(), px = e.clientX - r.left, py = e.clientY - r.top;
    const k = e.deltaY < 0 ? 1.15 : 1 / 1.15, [wx, wy] = S2W(px, py); V.s *= k; V.ox = px - wx * V.s; V.oy = py + wy * V.s; drawPlan();
  }, { passive: false });
  cv.addEventListener('dblclick', () => { fitPlan(); drawPlan(); });
  cv.addEventListener('contextmenu', (e) => e.preventDefault());
  cv.addEventListener('dragover', (e) => e.preventDefault());
  cv.addEventListener('drop', (e) => {
    e.preventDefault(); const id = e.dataTransfer.getData('text/plain'); if (!id) return;
    const r = cv.getBoundingClientRect(); addItem(id, S2W(e.clientX - r.left, e.clientY - r.top));
  });
}

// ---------- 3D ----------
let scene3d = null;
function scene() {
  if (scene3d) return scene3d;
  const boxes = [], bad = collisions();
  for (const b of walls.bodies) boxes.push({ pts: bodyPoly(b), z0: b.min[2], z1: b.max[2], type: b.type, alpha: SOLID.has(b.type) ? 0.3 : 0.6, layer: 0 });
  for (const { item, built } of okBuilds()) for (const w of K.worldSolids(item, built)) { w.layer = 1; w.bad = bad.has(item.id); boxes.push(w); }
  return (scene3d = boxes);
}
function draw3d() {
  const cv = $('c3d'); if (!cv.clientWidth) return;
  const bx = scene(); if (!cam3fit) { K.fitCam(cam3, bx, cv); cam3fit = true; }
  K.render3D(cv, bx, cam3);
}

// ---------- перерисовка ----------
function redraw() { if (view === 'plan') drawPlan(); else if (view === 'v3d') draw3d(); else if (view === 'mod') drawPrev(); }
function setView(v) {
  view = v;
  for (const b of $('ctabs').children) b.classList.toggle('on', b.dataset.v === v);
  for (const id of ['plan', 'v3d', 'spec', 'Mod']) $('pane' + id).classList.toggle('on', ('pane' + id) === 'pane' + (v === 'mod' ? 'Mod' : v));
  if (v === 'spec') showSpec();
  redraw();
}

// ---------- свойства ----------
function renderProps() {
  const el = $('props'), b = builds().find((x) => x.item.id === sel);
  if (!b) { el.innerHTML = '<p class="mut">Выберите шкаф на плане или добавьте модуль из библиотеки (перетащите на план — он сам встанет к ближайшей стене).</p><p class="mut">План: колесо — масштаб, перетаскивание пустого места — сдвиг, двойной клик — вписать. Alt при перетаскивании — без прилипания. R — повернуть 90°, Shift+R — 45°, Del — удалить. Угловой модуль эркера бросайте у наружного угла эркера.</p>'; return; }
  const { item, mod } = b; let h = `<h3>${esc(item.label)} — ${esc(mod.name)}</h3>`;
  if (b.err) h += `<div class="err">${esc(b.err)}</div>`;
  for (const w of warnings().out.filter((x) => x.startsWith(item.label + ' '))) h += `<div class="err" style="color:#ffa94d">⚠ ${esc(w.slice(item.label.length + 1))}</div>`;
  h += `<div class="row"><label>Метка</label><input data-k="label" value="${esc(item.label)}" style="width:110px"></div>`;
  for (const d of mod.params || []) h += `<div class="row"><label>${esc(d.label || d.id)} <span class="mut">(${esc(d.id)})</span></label><input type="number" data-p="${esc(d.id)}" value="${item.p[d.id] ?? d.def}" min="${d.min ?? ''}" max="${d.max ?? ''}" step="${d.step ?? 1}"></div>`;
  h += `<h3>Положение</h3><div class="row"><label>X</label><input type="number" data-k="x" value="${f1(item.x)}"></div><div class="row"><label>Y</label><input type="number" data-k="y" value="${f1(item.y)}"></div>`;
  h += `<div class="row"><label>Поворот °</label><input type="number" data-k="rot" value="${f1(item.rot)}" step="0.5"></div><div class="row"><label>Доп. высота, мм</label><input type="number" data-k="zOff" value="${item.zOff || 0}"></div>`;
  h += `<div class="row"><button id="pRot">⟳90°</button><button id="pR45">⟳45°</button><button id="pL45">⟲45°</button></div><div class="row"><button id="pWall">К стене</button><button id="pDup">Копия</button><button id="pDel" class="dng">Удалить</button></div>`;
  if (b.built) {
    h += `<h3>Детали (${b.built.parts.length})</h3><div class="scroll-x"><table class="t">` + b.built.parts.map((p) => `<tr><td>${esc(p.name)}</td><td>${f1(p.L)}×${f1(p.W)}</td></tr>`).join('') + '</table></div>';
  }
  h += `<div class="row"><button id="pEdit">✎ Редактировать модуль</button></div>`;
  el.innerHTML = h;
  el.querySelectorAll('input[data-p]').forEach((i) => i.addEventListener('change', () => {
    const d = mod.params.find((q) => q.id === i.dataset.p); let v = parseFloat(i.value); if (!isFinite(v)) v = d.def;
    if (d.min !== undefined && d.min !== '') v = Math.max(d.min, v); if (d.max !== undefined && d.max !== '') v = Math.min(d.max, v);
    item.p[d.id] = v; dirty(); renderProps();
  }));
  el.querySelectorAll('input[data-k]').forEach((i) => i.addEventListener('change', () => {
    const k = i.dataset.k; item[k] = k === 'label' ? i.value : parseFloat(i.value) || 0; if (k === 'rot') item.rot = normRot(item.rot); dirty(); renderProps();
  }));
  $('pRot').onclick = () => rotateItem(item, 90); $('pR45').onclick = () => rotateItem(item, -45); $('pL45').onclick = () => rotateItem(item, 45);
  $('pWall').onclick = () => { const c = K.geo.centroid(b.ext ? b.ext.pts : [[item.x, item.y]]); attachToWall(item, c[0], c[1]); dirty(); renderProps(); };
  $('pDup').onclick = () => { const n = JSON.parse(JSON.stringify(item)); n.id = nextId; n.label = 'К' + nextId; nextId++; n.x += 100; n.y += 100; items.push(n); sel = n.id; dirty(); renderProps(); };
  $('pDel').onclick = () => delSel();
  $('pEdit').onclick = () => openEditor(mod.id);
}
function delSel() { if (sel === null) return; items = items.filter((i) => i.id !== sel); sel = null; dirty(); renderProps(); }

// ---------- левая панель ----------
function renderLib() {
  const el = $('tab-lib'); let h = '';
  for (const cat of K.catOrder) {
    const ms = lib.filter((m) => (m.cat || 'other') === cat); if (!ms.length) continue;
    h += `<div class="cat">${K.catName[cat]}</div>`;
    for (const m of ms) {
      let dims = ''; try { const p = K.modScope(m, K.defaultParams(m, S), S); dims = `${f1(p.W ?? 0)}×${p.H ?? p.T ?? ''}×${p.D ?? ''}`; } catch (_) {}
      h += `<div class="mod" draggable="true" data-id="${esc(m.id)}"><span class="n">${esc(m.name)}<br><small>${dims}</small></span><button data-a="add" title="Добавить">＋</button><button data-a="edit" title="Редактировать">✎</button><button data-a="dup" title="Копия">⧉</button><button data-a="del" title="Удалить" class="dng">×</button></div>`;
    }
  }
  h += `<div class="row" style="margin-top:12px;flex-wrap:wrap"><button id="lNew" class="pri">Новый модуль</button><button id="lExp">Экспорт</button><button id="lImp">Импорт</button><button id="lRst" class="dng">Сброс</button></div><div class="row"><button id="lCnt">Столешницы автоматически</button></div><p class="hint">Модуль — JSON: параметры + детали с формулами (W, H, D, t, tf, tb, gap, plinth, i, n…). Правьте в редакторе ✎.</p>`;
  el.innerHTML = h;
  el.querySelectorAll('.mod').forEach((d) => {
    d.addEventListener('dragstart', (e) => e.dataTransfer.setData('text/plain', d.dataset.id));
    d.querySelectorAll('button').forEach((b) => b.addEventListener('click', (e) => {
      e.stopPropagation(); const id = d.dataset.id, a = b.dataset.a;
      if (a === 'add') addItem(id); else if (a === 'edit') openEditor(id);
      else if (a === 'dup') { const m = JSON.parse(JSON.stringify(modById(id))); m.id = 'm' + Date.now().toString(36); m.name += ' (копия)'; lib.push(m); save(); renderLib(); openEditor(m.id); }
      else if (a === 'del') { if (confirm('Удалить модуль из библиотеки?')) { lib = lib.filter((m) => m.id !== id); save(); renderLib(); dirty(); } }
    }));
  });
  $('lNew').onclick = () => { const m = JSON.parse(JSON.stringify(modById('base_doors') || lib[0])); m.id = 'm' + Date.now().toString(36); m.name = 'Новый модуль'; lib.push(m); save(); renderLib(); openEditor(m.id); };
  $('lExp').onclick = () => download('kitchen-library.json', JSON.stringify({ format: 'kitchen-lib/1', modules: lib }, null, 1));
  $('lImp').onclick = () => pickFile((txt) => {
    const j = JSON.parse(txt); const mods = Array.isArray(j) ? j : j.modules; if (!Array.isArray(mods)) throw new Error('Нет массива modules');
    for (const m of mods) { const i = lib.findIndex((x) => x.id === m.id); if (i >= 0) lib[i] = m; else lib.push(m); }
    save(); renderLib(); dirty();
  });
  $('lCnt').onclick = autoCounters;
  $('lRst').onclick = () => { if (confirm('Вернуть стандартную библиотеку? Свои модули будут удалены.')) { lib = K.defaultLib(); save(); renderLib(); dirty(); } };
}

function renderWalls() {
  const el = $('tab-walls');
  const num = (id, v, lab) => `<div class="row"><label>${lab}</label><input type="number" id="${id}" value="${v}"></div>`;
  let h = `<h3>Комната-заготовка</h3>` + num('rA', 4000, 'Длина X') + num('rB', 3000, 'Глубина Y') + num('rT', 100, 'Толщина стен') + num('rH', 2700, 'Высота');
  h += `<div class="row"><label><input type="checkbox" id="rBay"> Эркер ½ восьмиугольника (север)</label></div><div id="bayP" style="display:none;padding-left:10px">` + num('bW', 2400, 'Ширина проёма') + num('bD', 700, 'Глубина (стороны 45°)') + num('bP', 850, 'Высота парапета') + num('bWt', 2250, 'Верх окна') + `</div>`;
  h += `<div class="row"><label><input type="checkbox" id="rX" checked> дверь, вода, розетка</label><button id="rGo">Создать</button></div>`;
  h += `<div class="row"><button id="wImp" class="pri">Импорт стен из Fusion (JSON)</button></div><h3>Тела (${walls.bodies.length})</h3><div class="scroll-x"><table class="t"><tr><th>Имя</th><th>Тип</th><th>x1</th><th>y1</th><th>z1</th><th>x2</th><th>y2</th><th>z2</th><th>Контур x,y; x,y…</th><th></th></tr>`;
  walls.bodies.forEach((b, i) => {
    const ro = b.poly ? ' readonly title="задан контуром"' : '';
    h += `<tr><td><input data-i="${i}" data-f="name" value="${esc(b.name || '')}" style="min-width:70px"></td><td><select data-i="${i}" data-f="type">${Object.entries(TYPES).map(([k, v]) => `<option value="${k}"${k === b.type ? ' selected' : ''}>${v}</option>`).join('')}</select></td>` +
      [0, 1, 2].map((k) => `<td><input type="number" data-i="${i}" data-f="min${k}" value="${f1(b.min[k])}" style="min-width:56px"${k < 2 ? ro : ''}></td>`).join('') +
      [0, 1, 2].map((k) => `<td><input type="number" data-i="${i}" data-f="max${k}" value="${f1(b.max[k])}" style="min-width:56px"${k < 2 ? ro : ''}></td>`).join('') +
      `<td><input data-i="${i}" data-f="poly" value="${b.poly ? esc(b.poly.map((p) => p.join(',')).join('; ')) : ''}" style="min-width:150px"></td><td><button data-del="${i}" class="dng">×</button></td></tr>`;
  });
  h += `</table></div><div class="row"><button id="wAdd">+ Тело</button></div><p class="hint">Оси: X вправо, Y вверх на плане, Z вверх. Наклонные стены — контуром (из Fusion приходит автоматически). Имена тел во Fusion: «Стена…», «Парапет…», «Окно…», «Дверь…», «Вода…», «Газ…», «Розетка…». Парапет = стена до подоконника; окно — отдельное тело над ним.</p>`;
  el.innerHTML = h;
  $('rBay').onchange = () => ($('bayP').style.display = $('rBay').checked ? '' : 'none');
  $('rGo').onclick = () => {
    if (walls.bodies.length && !confirm('Заменить текущие стены?')) return;
    const bay = $('rBay').checked ? { w: +$('bW').value, d: +$('bD').value, ph: +$('bP').value, wt: +$('bWt').value } : null;
    walls = roomBodies(+$('rA').value, +$('rB').value, +$('rT').value, +$('rH').value, $('rX').checked, bay); V.fitted = false; cam3fit = false; renderWalls(); dirty();
  };
  $('wImp').onclick = importWalls;
  $('wAdd').onclick = () => { walls.bodies.push({ name: 'Новое', type: 'wall', min: [0, 0, 0], max: [1000, 100, walls.H || 2700] }); renderWalls(); dirty(); };
  el.querySelectorAll('[data-f]').forEach((i) => i.addEventListener('change', () => {
    const b = walls.bodies[+i.dataset.i], f = i.dataset.f;
    if (f === 'name' || f === 'type') b[f] = i.value;
    else if (f === 'poly') {
      try { setPoly(b, i.value.trim() ? i.value.split(';').map((p) => { const q = p.split(',').map(Number); if (q.length !== 2 || q.some((v) => !isFinite(v))) throw new Error(p); return q; }) : null); }
      catch (e) { alert('Контур: «x,y; x,y; …», ошибка в «' + e.message + '»'); }
      renderWalls();
    } else b[f.slice(0, 3)][+f[3]] = parseFloat(i.value) || 0;
    dirty();
  }));
  el.querySelectorAll('[data-del]').forEach((b) => b.addEventListener('click', () => { walls.bodies.splice(+b.dataset.del, 1); renderWalls(); dirty(); }));
}
function importWalls() {
  pickFile((txt) => {
    const j = JSON.parse(txt), arr = Array.isArray(j) ? j : j.bodies; if (!Array.isArray(arr)) throw new Error('В файле нет массива bodies');
    walls = { H: j.height || 2700, bodies: arr.map((b) => { const o = { name: b.name || '', type: TYPES[b.type] ? b.type : 'other', min: b.min.map(Number), max: b.max.map(Number) }; if (Array.isArray(b.poly)) setPoly(o, b.poly.map((p) => [+p[0], +p[1]])); return o; }) };
    V.fitted = false; cam3fit = false; renderWalls(); dirty();
  });
}
// ---------- файлы ----------
function download(name, text, type) {
  const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type: type || 'application/json' })); a.download = name; document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
}
function pickFile(cb) {
  const inp = $('fileAny'); inp.value = '';
  inp.onchange = () => { const f = inp.files[0]; if (!f) return; const r = new FileReader(); r.onload = () => { try { cb(String(r.result).replace(/^﻿/, '')); } catch (e) { alert('Ошибка файла: ' + e.message); } }; r.readAsText(f); };
  inp.click();
}
function saveProject() {
  const used = [...new Set(items.map((i) => i.mod))].map(modById).filter(Boolean);
  download('kitchen-project.json', JSON.stringify({ format: 'kitchen-project/1', S, walls, items, nextId, lib: used }, null, 1));
}
function openProject() {
  pickFile((txt) => {
    const j = JSON.parse(txt); if (j.format !== 'kitchen-project/1') throw new Error('Это не файл проекта');
    S = Object.assign(K.defaultSettings(), j.S); walls = j.walls; items = j.items; nextId = j.nextId || items.length + 1; sel = null;
    for (const m of j.lib || []) if (!modById(m.id)) lib.push(m);
    V.fitted = false; cam3fit = false; save(); renderLib(); renderWalls(); renderProps(); dirty();
  });
}
function showSpec() {
  const bs = okBuilds(), el = $('specView');
  const bar = `<div id="specBar"><button onclick="window.print()">Печать / PDF</button><button id="sCsv">CSV для раскроя</button><button id="sFx">JSON → Fusion</button></div>`;
  el.innerHTML = bar + (bs.length ? K.specHTML(bs, S, { warnings: warnings().out }) : '<p>Добавьте шкафы на план.</p>');
  $('sCsv').onclick = exportCsv; $('sFx').onclick = exportFusion;
}
function exportCsv() { const bs = okBuilds(); if (!bs.length) return alert('Нет шкафов'); download('raskroy.csv', K.cutCSV(bs), 'text/csv;charset=utf-8'); }
function exportFusion() { const bs = okBuilds(); if (!bs.length) return alert('Нет шкафов'); download('kitchen-parts.json', JSON.stringify(K.fusionParts(bs), null, 1)); }

// ---------- настройки ----------
function openSettings() {
  const d = $('dlgSet'); let h = '<h3>Материалы</h3><table class="t"><tr><th>Роль</th><th>Название</th><th>Толщина</th><th>Кромка</th></tr>';
  const roles = { body: 'Корпус', front: 'Фасады', back: 'Задняя стенка', top: 'Столешница' };
  for (const [k, n] of Object.entries(roles)) h += `<tr><td>${n}</td><td><input data-m="${k}" data-f="name" value="${esc(S.mats[k].name)}"></td><td><input type="number" data-m="${k}" data-f="t" value="${S.mats[k].t}"></td><td><input data-m="${k}" data-f="edge" value="${esc(S.mats[k].edge)}"></td></tr>`;
  h += '</table><h3>Размеры кухни, мм</h3>';
  const gl = { gap: 'Зазор между фасадами', plinth: 'Высота цоколя', baseH: 'Высота корпуса нижних', wallBottom: 'Низ верхних шкафов от пола', wallH: 'Высота верхних', tallH: 'Высота пеналов' };
  for (const [k, n] of Object.entries(gl)) h += `<div class="row"><label>${n} <span class="mut">(${k})</span></label><input type="number" data-g="${k}" value="${S.g[k]}"></div>`;
  h += `<h3>Лист</h3><div class="row"><label>Длина × ширина</label><input type="number" data-s="L" value="${S.sheet.L}"><input type="number" data-s="W" value="${S.sheet.W}"></div><div class="row"><label>Запас на отход</label><input type="number" step="0.01" data-s="waste" value="${S.sheet.waste}"></div>`;
  h += '<div class="row"><span style="flex:1"></span><button id="sOk" class="pri">Применить</button><button id="sCancel">Отмена</button></div>';
  d.innerHTML = h; d.showModal();
  $('sCancel').onclick = () => d.close();
  $('sOk').onclick = () => {
    d.querySelectorAll('[data-m]').forEach((i) => { S.mats[i.dataset.m][i.dataset.f] = i.dataset.f === 't' ? parseFloat(i.value) || 1 : i.value; });
    d.querySelectorAll('[data-g]').forEach((i) => { S.g[i.dataset.g] = parseFloat(i.value) || 0; });
    d.querySelectorAll('[data-s]').forEach((i) => { S.sheet[i.dataset.s] = parseFloat(i.value) || 1; });
    d.close(); dirty(); renderProps(); renderLib();
  };
}

// ---------- редактор модуля ----------
let ed = null;
const PART_COLS = [['name', 'Деталь', 130], ['mat', 'Матер.', 70, ['body', 'front', 'back', 'top']], ['count', 'Кол-во', 56], ['x', 'x', 80], ['y', 'y', 80], ['z', 'z', 110], ['sx', 'размер x', 80], ['sy', 'размер y', 80], ['sz', 'размер z / толщина', 80], ['rz', 'поворот z°', 60], ['poly', 'Контур (вместо x,y,sx,sy)', 160], ['lax', 'Ось Д', 50, ['', 'x', 'y', 'z']], ['edge', 'Кромка', 80], ['role', 'Роль', 70, ['', 'side', 'dside', 'door', 'drawerfront']], ['drill', 'Присадка', 70, ['', 'conf', 'shelf']], ['to', 'Присадка в', 60], ['hinge', 'Петли', 90], ['if', 'Если', 70]];
const PAR_COLS = [['id', 'id', 70], ['label', 'Название', 150], ['def', 'По умолч.', 70, null, 'num'], ['defF', 'или формула', 100], ['min', 'min', 60, null, 'num'], ['max', 'max', 60, null, 'num'], ['step', 'шаг', 50, null, 'num']];
const VAR_COLS = [['id', 'id', 70], ['f', 'Формула', 300]];
const HW_COLS = [['name', 'Название ({формула} допускается)', 300], ['qty', 'Кол-во (формула)', 200]];

function openEditor(id) {
  const m = modById(id); if (!m) return;
  ed = { id, mod: JSON.parse(JSON.stringify(m)), cam: K.newCam(), fit: false };
  try { ed.pp = K.defaultParams(ed.mod, S); } catch (_) { ed.pp = {}; }
  $('tabMod').style.display = ''; setView('mod'); renderEditor();
}
function tableEd(host, arr, cols, defaults, onCh) {
  const draw = () => {
    let h = '<div class="scroll-x"><table class="t"><tr>' + cols.map((c) => `<th>${c[1]}</th>`).join('') + '<th></th></tr>';
    arr.forEach((r, i) => {
      h += '<tr>' + cols.map((c) => {
        const v = r[c[0]] ?? '';
        return c[3] ? `<td><select data-i="${i}" data-k="${c[0]}">${c[3].map((o) => `<option${o === v ? ' selected' : ''}>${o}</option>`).join('')}</select></td>` : `<td><input data-i="${i}" data-k="${c[0]}" value="${esc(v)}" style="min-width:${c[2]}px"></td>`;
      }).join('') + `<td style="white-space:nowrap"><button data-a="up" data-i="${i}">↑</button><button data-a="dn" data-i="${i}">↓</button><button data-a="dp" data-i="${i}">⧉</button><button data-a="x" data-i="${i}" class="dng">×</button></td></tr>`;
    });
    h += '</table></div><button data-a="add">+ строка</button>';
    host.innerHTML = h;
    host.querySelectorAll('[data-k]').forEach((inp) => inp.addEventListener('input', () => {
      const c = cols.find((q) => q[0] === inp.dataset.k), r = arr[+inp.dataset.i];
      if (c[4] === 'num') { const v = parseFloat(inp.value); if (inp.value === '' || !isFinite(v)) delete r[c[0]]; else r[c[0]] = v; } else if (inp.value === '' && c[0] !== 'name' && c[0] !== 'id') delete r[c[0]]; else r[c[0]] = inp.value;
      onCh(false);
    }));
    host.querySelectorAll('button[data-a]').forEach((b) => b.addEventListener('click', () => {
      const i = +b.dataset.i, a = b.dataset.a;
      if (a === 'add') arr.push(JSON.parse(JSON.stringify(defaults))); else if (a === 'x') arr.splice(i, 1);
      else if (a === 'dp') arr.splice(i + 1, 0, JSON.parse(JSON.stringify(arr[i]))); else if (a === 'up' && i > 0) arr.splice(i - 1, 0, arr.splice(i, 1)[0]); else if (a === 'dn' && i < arr.length - 1) arr.splice(i + 1, 0, arr.splice(i, 1)[0]);
      draw(); onCh(true);
    }));
  };
  draw();
}
function renderEditor() {
  const m = ed.mod;
  $('edTop').innerHTML = `<button id="eSave" class="pri">Сохранить в библиотеку</button><button id="eClose">Закрыть</button><input id="eName" value="${esc(m.name)}" style="width:210px"><select id="eCat">${Object.entries(K.catName).map(([k, v]) => `<option value="${k}"${k === m.cat ? ' selected' : ''}>${v}</option>`).join('')}</select><label class="mut">Низ от пола:</label><input id="eZ0" value="${esc(m.z0 || '0')}" style="width:120px"><label class="mut">Габарит (контур, пусто = W×D):</label><input id="eFoot" value="${esc(m.foot || '')}" style="width:220px" placeholder="x,y; x,y; … первое ребро — фронт"><select id="ePlace"><option value="">к стене</option><option value="corner"${m.place === 'corner' ? ' selected' : ''}>в наружный угол</option></select><span class="mut">id: ${esc(m.id)}</span>`;
  $('eName').oninput = (e) => (m.name = e.target.value); $('eCat').onchange = (e) => (m.cat = e.target.value); $('eZ0').oninput = (e) => { m.z0 = e.target.value; edChange(false); }; $('eFoot').oninput = (e) => { if (e.target.value.trim()) m.foot = e.target.value; else delete m.foot; edChange(false); }; $('ePlace').onchange = (e) => { if (e.target.value) m.place = e.target.value; else delete m.place; };
  $('eClose').onclick = closeEditor; $('eSave').onclick = () => { const i = lib.findIndex((x) => x.id === m.id); const err = edValidate(); if (err && !confirm('В модуле есть ошибка:\n' + err + '\nСохранить всё равно?')) return; m.edited = true; lib[i] = JSON.parse(JSON.stringify(m)); save(); renderLib(); dirty(); alert('Сохранено'); };
  const F = $('edForm'); F.innerHTML = '<h3>Параметры</h3><div id="tP"></div><h3>Переменные (считаются по порядку)</h3><div id="tV"></div><h3>Детали</h3><p class="hint">Бокс детали в системе модуля: x — ширина, y — глубина (0 = перед, D = стена), z — вверх (0 = низ корпуса). i — номер экземпляра (с 0), n — их количество. Кромка: L1 L2 W1 W2 или all. Поворот z° — вокруг угла (x,y), такие детали без присадки. Контур «x,y; x,y; …» — фигурная пластина в плане (z — низ, «размер z» — толщина), кромка — номера рёбер «1 3» или all; функции sind/cosd/tand в градусах. Д — длина детали (по оси «Ось Д» или по самой длинной стороне).</p><div id="tD"></div><h3>Фурнитура</h3><div id="tH"></div><h3>Шаги сборки (по строке на шаг)</h3><textarea id="eAs" rows="6" style="width:100%"></textarea><div id="eErr" class="err" style="margin-top:8px"></div>';
  $('eAs').value = (m.assembly || []).join('\n'); $('eAs').oninput = (e) => (m.assembly = e.target.value.split('\n').filter(Boolean));
  m.params = m.params || []; m.vars = m.vars || []; m.parts = m.parts || []; m.hardware = m.hardware || [];
  tableEd($('tP'), m.params, PAR_COLS, { id: 'p1', label: 'Параметр', def: 1, min: 0, max: 100, step: 1 }, edChange);
  tableEd($('tV'), m.vars, VAR_COLS, { id: 'v1', f: '0' }, edChange);
  tableEd($('tD'), m.parts, PART_COLS, { name: 'Деталь', mat: 'body', count: '1', x: '0', y: '0', z: '0', sx: 't', sy: 'D', sz: 'H' }, edChange);
  tableEd($('tH'), m.hardware, HW_COLS, { name: 'Крепёж', qty: '1' }, edChange);
  $('edPrev').innerHTML = '<div id="edPP"></div><div class="hint">Предпросмотр: тяните — вращение, колесо — масштаб, Shift+тяните — сдвиг.</div><canvas id="edCv"></canvas>';
  K.attachOrbit($('edCv'), ed.cam, drawPrev); renderPP(); edChange(false); setTimeout(() => { ed.fit = false; drawPrev(); }, 50);
}
function renderPP() {
  const m = ed.mod; let h = '<div class="row" style="flex-wrap:wrap">';
  for (const d of m.params) h += `<label style="flex:none">${esc(d.id)} <input type="number" data-pp="${esc(d.id)}" value="${ed.pp[d.id] ?? d.def}" style="width:68px"></label>`;
  $('edPP').innerHTML = h + '</div>';
  $('edPP').querySelectorAll('input').forEach((i) => i.addEventListener('input', () => { ed.pp[i.dataset.pp] = parseFloat(i.value) || 0; edChange(false); }));
}
function edBuild() { const item = { id: 0, label: 'М', mod: ed.mod.id, p: Object.assign({}, ed.pp), x: 0, y: 0, rot: 0, zOff: 0 }; return { item, built: K.buildItem(item, S, ed.mod) }; }
function edValidate() { try { edBuild(); return null; } catch (e) { return e.message; } }
function edChange(structural) {
  if (structural) { for (const d of ed.mod.params) if (!(d.id in ed.pp)) ed.pp[d.id] = d.defF ? 0 : d.def; renderPP(); }
  const err = edValidate(); $('eErr').textContent = err || ''; drawPrev();
}
function drawPrev() {
  if (!ed || view !== 'mod') return;
  const cv = $('edCv'); if (!cv || !cv.clientWidth) return;
  let boxes = [];
  try { const { item, built } = edBuild(); boxes = K.worldSolids(item, built).map((b) => Object.assign(b, { layer: 1 })); } catch (_) {}
  if (boxes.length && !ed.fit) { K.fitCam(ed.cam, boxes, cv); ed.fit = true; }
  K.render3D(cv, boxes, ed.cam);
}
function closeEditor() { ed = null; $('tabMod').style.display = 'none'; setView('plan'); renderProps(); }

// ---------- запуск ----------
function init() {
  load(); renderLib(); renderWalls(); renderProps(); initPlan();
  K.attachOrbit($('c3d'), cam3, () => draw3d());
  $('c3d').addEventListener('dblclick', () => { cam3 = Object.assign(cam3, K.newCam()); cam3fit = false; draw3d(); });
  document.querySelectorAll('#left .tabs button').forEach((b) => b.addEventListener('click', () => {
    document.querySelectorAll('#left .tabs button').forEach((x) => x.classList.toggle('on', x === b));
    $('tab-lib').classList.toggle('on', b.dataset.t === 'lib'); $('tab-walls').classList.toggle('on', b.dataset.t === 'walls');
  }));
  $('ctabs').addEventListener('click', (e) => { const v = e.target.dataset && e.target.dataset.v; if (v) setView(v); });
  $('bNew').onclick = () => { if (!confirm('Очистить проект (шкафы и стены)? Библиотека сохранится.')) return; items = []; sel = null; nextId = 1; walls = sampleRoom(); V.fitted = false; cam3fit = false; renderWalls(); renderProps(); dirty(); };
  $('bOpen').onclick = openProject; $('bSave').onclick = saveProject; $('bWalls').onclick = importWalls;
  $('bCsv').onclick = exportCsv; $('bFusion').onclick = exportFusion; $('bSettings').onclick = openSettings;
  window.addEventListener('keydown', (e) => {
    if (/INPUT|TEXTAREA|SELECT/.test((e.target.tagName || ''))) return;
    if (e.key === 'Delete' || e.key === 'Backspace') delSel();
    else if (/^[rRкК]$/.test(e.key) && sel !== null) { const it = items.find((i) => i.id === sel); if (it) rotateItem(it, e.shiftKey ? -45 : 90); }
    else if (e.key === 'Escape') { sel = null; renderProps(); redraw(); }
  });
  window.addEventListener('resize', redraw);
  updateStatus(); setTimeout(() => { V.fitted = false; redraw(); }, 0);
}
K._dbg = { get items() { return items; }, get walls() { return walls; }, addItem, builds, get S() { return S; }, get lib() { return lib; }, setView };
document.addEventListener('DOMContentLoaded', init);
})(window.K = window.K || {});
