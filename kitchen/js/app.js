(function (K) {
'use strict';
const $ = (id) => document.getElementById(id);
const esc = K.esc, f1 = (n) => Math.round(n * 10) / 10;
const LS_P = 'kitchen.project.v1', LS_L = 'kitchen.lib.v1';
const TYPES = { wall: 'Стена', window: 'Окно', door: 'Дверь', water: 'Вода', sewer: 'Канализация', gas: 'Газ', socket: 'Розетка', vent: 'Вытяжка', column: 'Колонна', other: 'Прочее' };

// ---------- состояние ----------
let S = K.defaultSettings(), lib = K.defaultLib(), walls = { H: 2700, bodies: [] }, items = [], nextId = 1, sel = null;
let cache = null, view = 'plan', V = { ox: 60, oy: 500, s: 0.12, fitted: false }, cam3 = K.newCam(), cam3fit = false;

function load() {
  try { const l = JSON.parse(localStorage.getItem(LS_L)); if (Array.isArray(l) && l.length) lib = l; } catch (_) {}
  try { const p = JSON.parse(localStorage.getItem(LS_P)); if (p) { S = Object.assign(S, p.S); walls = p.walls || walls; items = p.items || []; nextId = p.nextId || 1; } } catch (_) {}
  if (!walls.bodies.length && !items.length) walls = sampleRoom();
}
function save() {
  try { localStorage.setItem(LS_L, JSON.stringify(lib)); localStorage.setItem(LS_P, JSON.stringify({ S, walls, items, nextId })); } catch (_) {}
}
const modById = (id) => lib.find((m) => m.id === id);

function sampleRoom() {
  return roomBodies(4000, 3000, 100, 2700, true);
}
function roomBodies(A, B, th, H, extras) {
  const w = (name, x0, y0, x1, y1) => ({ name, type: 'wall', min: [x0, y0, 0], max: [x1, y1, H] });
  const b = [w('Стена юг', -th, -th, A + th, 0), w('Стена север', -th, B, A + th, B + th), w('Стена запад', -th, 0, 0, B), w('Стена восток', A, 0, A + th, B)];
  if (extras) b.push(
    { name: 'Окно', type: 'window', min: [A * 0.35, B, 900], max: [A * 0.65, B + th, 2100] },
    { name: 'Дверь', type: 'door', min: [A, B * 0.55, 0], max: [A + th, B * 0.9, 2050] },
    { name: 'Вода', type: 'water', min: [A * 0.15, B - 60, 0], max: [A * 0.15 + 60, B, 600] },
    { name: 'Канализация', type: 'sewer', min: [A * 0.15 + 100, B - 60, 0], max: [A * 0.15 + 160, B, 300] },
    { name: 'Розетка', type: 'socket', min: [A * 0.5, B - 20, 1050], max: [A * 0.5 + 80, B, 1130] });
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
  const ov = (a0, a1, b0, b1) => Math.min(a1, b1) - Math.max(a0, b0) > 1;
  for (let i = 0; i < bs.length; i++) {
    const a = bs[i].ext;
    for (let j = i + 1; j < bs.length; j++) {
      const b = bs[j].ext;
      if (ov(a.minx, a.maxx, b.minx, b.maxx) && ov(a.miny, a.maxy, b.miny, b.maxy) && ov(a.z0, a.z1, b.z0, b.z1)) { bad.add(bs[i].item.id); bad.add(bs[j].item.id); }
    }
    for (const w of walls.bodies) {
      if (w.type !== 'wall' && w.type !== 'column') continue;
      if (ov(a.minx, a.maxx, w.min[0], w.max[0]) && ov(a.miny, a.maxy, w.min[1], w.max[1]) && ov(a.z0, a.z1, w.min[2], w.max[2])) bad.add(bs[i].item.id);
    }
  }
  return bad;
}
function updateStatus() {
  const e = builds().filter((b) => b.err).length, c = collisions().size;
  $('status').innerHTML = `Шкафов: ${items.length}` + (c ? ` · <span class="err">пересечений: ${c}</span>` : '') + (e ? ` · <span class="err">ошибок: ${e}</span>` : '');
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
  for (const b of walls.bodies) { if (!any) { x0 = b.min[0]; y0 = b.min[1]; x1 = b.max[0]; y1 = b.max[1]; any = true; } x0 = Math.min(x0, b.min[0]); y0 = Math.min(y0, b.min[1]); x1 = Math.max(x1, b.max[0]); y1 = Math.max(y1, b.max[1]); }
  return { x0, y0, x1, y1 };
}
function faces() {
  const out = [];
  for (const b of walls.bodies) {
    if (b.type !== 'wall') continue;
    const [a0, a1] = [b.min[0], b.max[0]], [c0, c1] = [b.min[1], b.max[1]];
    out.push({ n: [0, -1], pos: c0, t: [a0, a1], horiz: true }, { n: [0, 1], pos: c1, t: [a0, a1], horiz: true }, { n: [-1, 0], pos: a0, t: [c0, c1], horiz: false }, { n: [1, 0], pos: a1, t: [c0, c1], horiz: false });
  }
  return out;
}
function attachToWall(it, px, py) {
  const mod = modById(it.mod); const sc = K.modScope(mod, it.p, S);
  let best = null;
  for (const f of faces()) {
    const tv = f.horiz ? px : py, tc = Math.max(f.t[0], Math.min(f.t[1], tv)), nv = f.horiz ? py : px;
    // точка должна быть с внешней стороны грани (по нормали)
    const side = (nv - f.pos) * (f.horiz ? f.n[1] : f.n[0]);
    if (side < -1) continue;
    const d = Math.hypot(tv - tc, nv - f.pos);
    if (!best || d < best.d) best = { d, f };
  }
  if (!best) return;
  const { f } = best, W = sc.W, D = sc.D;
  const rot = ((Math.round(Math.atan2(f.n[0], -f.n[1]) * 180 / Math.PI / 90) * 90) % 360 + 360) % 360;
  const tv = f.horiz ? px : py;
  const lo = f.t[0] + W / 2, hi = f.t[1] - W / 2;
  const tc = lo <= hi ? Math.max(lo, Math.min(hi, tv)) : (f.t[0] + f.t[1]) / 2;
  const Q = f.horiz ? [tc, f.pos] : [f.pos, tc];
  it.rot = rot;
  const o = K.xf({ x: 0, y: 0, rot })(W / 2, D);
  it.x = Q[0] - o[0]; it.y = Q[1] - o[1];
  const s = snapPos(it, it.x, it.y, 150); it.x = s[0]; it.y = s[1];
  cache = null;
}
function snapPos(it, nx, ny, thr) {
  const mod = modById(it.mod);
  const e = K.extent(Object.assign({}, it, { x: nx, y: ny }), mod, S);
  thr = thr || 14 / V.s;
  const xt = [], yt = [];
  for (const b of walls.bodies) if (b.type === 'wall' || b.type === 'column') { xt.push(b.min[0], b.max[0]); yt.push(b.min[1], b.max[1]); }
  for (const o of okBuilds()) if (o.item !== it) { xt.push(o.ext.minx, o.ext.maxx); yt.push(o.ext.miny, o.ext.maxy); }
  let dx = null, dy = null;
  for (const t of xt) for (const ed of [e.minx, e.maxx]) { const d = t - ed; if (Math.abs(d) < thr && (dx === null || Math.abs(d) < Math.abs(dx))) dx = d; }
  for (const t of yt) for (const ed of [e.miny, e.maxy]) { const d = t - ed; if (Math.abs(d) < thr && (dy === null || Math.abs(d) < Math.abs(dy))) dy = d; }
  return [nx + (dx || 0), ny + (dy || 0)];
}
function rotateItem(it) {
  const mod = modById(it.mod); const sc = K.modScope(mod, it.p, S);
  const c = K.xf(it)(sc.W / 2, (sc.D - sc.tf) / 2);
  it.rot = (it.rot + 90) % 360;
  const o = K.xf({ x: 0, y: 0, rot: it.rot })(sc.W / 2, (sc.D - sc.tf) / 2);
  it.x = c[0] - o[0]; it.y = c[1] - o[1];
  dirty(); renderProps();
}

// ---------- план ----------
const W2S = (x, y) => [V.ox + x * V.s, V.oy - y * V.s];
const S2W = (px, py) => [(px - V.ox) / V.s, (V.oy - py) / V.s];
const BODY_COL = { wall: '#6b7684', window: '#6cb4ee', door: '#b07a4a', water: '#2f80ed', sewer: '#7a5c3c', gas: '#e5c100', socket: '#e5484d', vent: '#8e8e93', column: '#6b7684', other: '#888' };
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
  // сетка
  const [wx0, wy1] = S2W(0, 0), [wx1, wy0] = S2W(W, H);
  for (const [step, col] of [[100, '#1a2029'], [1000, '#28303c']]) {
    if (step * V.s < 6) continue;
    c.strokeStyle = col; c.lineWidth = 1; c.beginPath();
    for (let x = Math.floor(wx0 / step) * step; x <= wx1; x += step) { const p = W2S(x, 0)[0]; c.moveTo(p, 0); c.lineTo(p, H); }
    for (let y = Math.floor(wy0 / step) * step; y <= wy1; y += step) { const p = W2S(0, y)[1]; c.moveTo(0, p); c.lineTo(W, p); }
    c.stroke();
  }
  // тела
  const order = ['wall', 'column', 'window', 'door', 'water', 'sewer', 'gas', 'socket', 'vent', 'other'];
  for (const b of [...walls.bodies].sort((a, z) => order.indexOf(a.type) - order.indexOf(z.type))) {
    const [x0, y1] = W2S(b.min[0], b.min[1]), [x1, y0] = W2S(b.max[0], b.max[1]);
    c.globalAlpha = b.type === 'wall' || b.type === 'column' ? 1 : 0.85; c.fillStyle = BODY_COL[b.type] || '#888';
    c.fillRect(x0, y0, x1 - x0, y1 - y0); c.globalAlpha = 1;
    if (x1 - x0 > 40 || y1 - y0 > 40) { c.fillStyle = '#e6e9ee'; c.font = '10px sans-serif'; c.fillText(b.name || TYPES[b.type], x0 + 3, y0 + 11); }
  }
  // шкафы
  const bad = collisions();
  const bs = okBuilds().sort((a, z) => (CAT_Z[a.mod.cat] ?? 5) - (CAT_Z[z.mod.cat] ?? 5));
  for (const { item, mod, ext } of bs) {
    const pts = ext.pts.map((p) => W2S(p[0], p[1]));
    c.beginPath(); pts.forEach((p, i) => (i ? c.lineTo(p[0], p[1]) : c.moveTo(p[0], p[1]))); c.closePath();
    c.fillStyle = CAT_COL[mod.cat] || '#ccc'; c.fill();
    c.setLineDash(mod.cat === 'wall' ? [5, 3] : []);
    c.lineWidth = item.id === sel ? 2.5 : 1; c.strokeStyle = bad.has(item.id) ? '#ff4d4d' : item.id === sel ? '#4dabf7' : '#222'; c.stroke(); c.setLineDash([]);
    // фронт
    c.beginPath(); c.moveTo(pts[0][0], pts[0][1]); c.lineTo(pts[1][0], pts[1][1]); c.lineWidth = 3; c.strokeStyle = '#d6336c'; c.stroke();
    const cx = (pts[0][0] + pts[2][0]) / 2, cy = (pts[0][1] + pts[2][1]) / 2;
    if (ext.W * V.s > 22) { c.fillStyle = '#111'; c.font = '11px sans-serif'; c.textAlign = 'center'; c.fillText(item.label + ' ' + f1(ext.W), cx, cy + 4); c.textAlign = 'start'; }
  }
}

function hit(px, py) {
  const [wx, wy] = S2W(px, py);
  const bs = okBuilds().sort((a, z) => (CAT_Z[a.mod.cat] ?? 5) - (CAT_Z[z.mod.cat] ?? 5)).reverse();
  for (const { item, ext } of bs) {
    const [lx, ly] = K.inv(item, wx, wy);
    if (lx >= 0 && lx <= ext.W && ly >= -ext.tf && ly <= ext.D) return item;
  }
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
  for (const b of walls.bodies) boxes.push({ mn: b.min, mx: b.max, type: b.type, alpha: b.type === 'wall' || b.type === 'column' ? 0.3 : 0.7, layer: 0 });
  for (const { item, built } of okBuilds()) for (const w of K.worldBoxes(item, built)) { w.layer = 1; w.bad = bad.has(item.id); boxes.push(w); }
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
  if (!b) { el.innerHTML = '<p class="mut">Выберите шкаф на плане или добавьте модуль из библиотеки (перетащите на план — он сам встанет к ближайшей стене).</p><p class="mut">План: колесо — масштаб, перетаскивание пустого места — сдвиг, двойной клик — вписать. Alt при перетаскивании — без прилипания. R — повернуть, Del — удалить.</p>'; return; }
  const { item, mod } = b; let h = `<h3>${esc(item.label)} — ${esc(mod.name)}</h3>`;
  if (b.err) h += `<div class="err">${esc(b.err)}</div>`;
  h += `<div class="row"><label>Метка</label><input data-k="label" value="${esc(item.label)}" style="width:110px"></div>`;
  for (const d of mod.params || []) h += `<div class="row"><label>${esc(d.label || d.id)} <span class="mut">(${esc(d.id)})</span></label><input type="number" data-p="${esc(d.id)}" value="${item.p[d.id] ?? d.def}" min="${d.min ?? ''}" max="${d.max ?? ''}" step="${d.step ?? 1}"></div>`;
  h += `<h3>Положение</h3><div class="row"><label>X</label><input type="number" data-k="x" value="${f1(item.x)}"></div><div class="row"><label>Y</label><input type="number" data-k="y" value="${f1(item.y)}"></div>`;
  h += `<div class="row"><label>Поворот °</label><input type="number" data-k="rot" value="${item.rot}" step="90"></div><div class="row"><label>Доп. высота, мм</label><input type="number" data-k="zOff" value="${item.zOff || 0}"></div>`;
  h += `<div class="row"><button id="pRot">⟳ Повернуть</button><button id="pWall">К стене</button><button id="pDup">Копия</button><button id="pDel" class="dng">Удалить</button></div>`;
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
    const k = i.dataset.k; item[k] = k === 'label' ? i.value : parseFloat(i.value) || 0; if (k === 'rot') item.rot = ((Math.round(item.rot / 90) * 90) % 360 + 360) % 360; dirty(); renderProps();
  }));
  $('pRot').onclick = () => rotateItem(item);
  $('pWall').onclick = () => { const sc = K.modScope(mod, item.p, S); const c = K.xf(item)(sc.W / 2, (sc.D - sc.tf) / 2); attachToWall(item, c[0], c[1]); dirty(); renderProps(); };
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
      let dims = ''; try { const p = K.defaultParams(m, S); dims = `${p.W ?? ''}×${p.H ?? p.T ?? ''}×${p.D ?? ''}`; } catch (_) {}
      h += `<div class="mod" draggable="true" data-id="${esc(m.id)}"><span class="n">${esc(m.name)}<br><small>${dims}</small></span><button data-a="add" title="Добавить">＋</button><button data-a="edit" title="Редактировать">✎</button><button data-a="dup" title="Копия">⧉</button><button data-a="del" title="Удалить" class="dng">×</button></div>`;
    }
  }
  h += `<div class="row" style="margin-top:12px;flex-wrap:wrap"><button id="lNew" class="pri">Новый модуль</button><button id="lExp">Экспорт</button><button id="lImp">Импорт</button><button id="lRst" class="dng">Сброс</button></div><p class="hint">Модуль — JSON: параметры + детали с формулами (W, H, D, t, tf, tb, gap, plinth, i, n…). Правьте в редакторе ✎.</p>`;
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
  $('lRst').onclick = () => { if (confirm('Вернуть стандартную библиотеку? Свои модули будут удалены.')) { lib = K.defaultLib(); save(); renderLib(); dirty(); } };
}

function renderWalls() {
  const el = $('tab-walls');
  let h = `<h3>Комната-заготовка</h3><div class="row"><label>Длина X</label><input type="number" id="rA" value="4000"></div><div class="row"><label>Глубина Y</label><input type="number" id="rB" value="3000"></div><div class="row"><label>Толщина стен</label><input type="number" id="rT" value="100"></div><div class="row"><label>Высота</label><input type="number" id="rH" value="2700"></div><div class="row"><label><input type="checkbox" id="rX" checked> окно, дверь, вода, розетка</label><button id="rGo">Создать</button></div>`;
  h += `<div class="row"><button id="wImp" class="pri">Импорт стен из Fusion (JSON)</button></div><h3>Тела (${walls.bodies.length})</h3><div class="scroll-x"><table class="t"><tr><th>Имя</th><th>Тип</th><th>x1</th><th>y1</th><th>z1</th><th>x2</th><th>y2</th><th>z2</th><th></th></tr>`;
  walls.bodies.forEach((b, i) => {
    h += `<tr><td><input data-i="${i}" data-f="name" value="${esc(b.name || '')}" style="min-width:70px"></td><td><select data-i="${i}" data-f="type">${Object.entries(TYPES).map(([k, v]) => `<option value="${k}"${k === b.type ? ' selected' : ''}>${v}</option>`).join('')}</select></td>` +
      [0, 1, 2].map((k) => `<td><input type="number" data-i="${i}" data-f="min${k}" value="${f1(b.min[k])}" style="min-width:56px"></td>`).join('') +
      [0, 1, 2].map((k) => `<td><input type="number" data-i="${i}" data-f="max${k}" value="${f1(b.max[k])}" style="min-width:56px"></td>`).join('') + `<td><button data-del="${i}" class="dng">×</button></td></tr>`;
  });
  h += `</table></div><div class="row"><button id="wAdd">+ Тело</button></div><p class="hint">Оси: X вправо, Y вверх на плане, Z вверх. Fusion-скрипт fusion/export_walls.py кладёт тела по имени: «Стена…», «Окно…», «Дверь…», «Вода…», «Газ…», «Розетка…».</p>`;
  el.innerHTML = h;
  $('rGo').onclick = () => { if (walls.bodies.length && !confirm('Заменить текущие стены?')) return; walls = roomBodies(+$('rA').value, +$('rB').value, +$('rT').value, +$('rH').value, $('rX').checked); V.fitted = false; cam3fit = false; renderWalls(); dirty(); };
  $('wImp').onclick = importWalls;
  $('wAdd').onclick = () => { walls.bodies.push({ name: 'Новое', type: 'wall', min: [0, 0, 0], max: [1000, 100, walls.H || 2700] }); renderWalls(); dirty(); };
  el.querySelectorAll('[data-f]').forEach((i) => i.addEventListener('change', () => {
    const b = walls.bodies[+i.dataset.i], f = i.dataset.f;
    if (f === 'name' || f === 'type') b[f] = i.value; else b[f.slice(0, 3)][+f[3]] = parseFloat(i.value) || 0;
    dirty();
  }));
  el.querySelectorAll('[data-del]').forEach((b) => b.addEventListener('click', () => { walls.bodies.splice(+b.dataset.del, 1); renderWalls(); dirty(); }));
}
function importWalls() {
  pickFile((txt) => {
    const j = JSON.parse(txt), arr = Array.isArray(j) ? j : j.bodies; if (!Array.isArray(arr)) throw new Error('В файле нет массива bodies');
    walls = { H: j.height || 2700, bodies: arr.map((b) => ({ name: b.name || '', type: TYPES[b.type] ? b.type : 'other', min: b.min.map(Number), max: b.max.map(Number) })) };
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
  el.innerHTML = bar + (bs.length ? K.specHTML(bs, S) : '<p>Добавьте шкафы на план.</p>');
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
const PART_COLS = [['name', 'Деталь', 130], ['mat', 'Матер.', 70, ['body', 'front', 'back', 'top']], ['count', 'Кол-во', 56], ['x', 'x', 80], ['y', 'y', 80], ['z', 'z', 110], ['sx', 'размер x', 80], ['sy', 'размер y', 80], ['sz', 'размер z', 80], ['lax', 'Ось Д', 50, ['', 'x', 'y', 'z']], ['edge', 'Кромка', 80], ['role', 'Роль', 70, ['', 'side', 'dside', 'door', 'drawerfront']], ['drill', 'Присадка', 70, ['', 'conf', 'shelf']], ['to', 'Присадка в', 60], ['hinge', 'Петли', 90], ['if', 'Если', 70]];
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
  $('edTop').innerHTML = `<button id="eSave" class="pri">Сохранить в библиотеку</button><button id="eClose">Закрыть</button><input id="eName" value="${esc(m.name)}" style="width:210px"><select id="eCat">${Object.entries(K.catName).map(([k, v]) => `<option value="${k}"${k === m.cat ? ' selected' : ''}>${v}</option>`).join('')}</select><label class="mut">Низ от пола:</label><input id="eZ0" value="${esc(m.z0 || '0')}" style="width:120px"><span class="mut">id: ${esc(m.id)}</span>`;
  $('eName').oninput = (e) => (m.name = e.target.value); $('eCat').onchange = (e) => (m.cat = e.target.value); $('eZ0').oninput = (e) => { m.z0 = e.target.value; edChange(false); };
  $('eClose').onclick = closeEditor; $('eSave').onclick = () => { const i = lib.findIndex((x) => x.id === m.id); const err = edValidate(); if (err && !confirm('В модуле есть ошибка:\n' + err + '\nСохранить всё равно?')) return; lib[i] = JSON.parse(JSON.stringify(m)); save(); renderLib(); dirty(); alert('Сохранено'); };
  const F = $('edForm'); F.innerHTML = '<h3>Параметры</h3><div id="tP"></div><h3>Переменные (считаются по порядку)</h3><div id="tV"></div><h3>Детали</h3><p class="hint">Бокс детали в системе модуля: x — ширина, y — глубина (0 = перед, D = стена), z — вверх (0 = низ корпуса). i — номер экземпляра (с 0), n — их количество. Кромка: L1 L2 W1 W2 или all. Д — длина детали (по оси «Ось Д» или по самой длинной стороне).</p><div id="tD"></div><h3>Фурнитура</h3><div id="tH"></div><h3>Шаги сборки (по строке на шаг)</h3><textarea id="eAs" rows="6" style="width:100%"></textarea><div id="eErr" class="err" style="margin-top:8px"></div>';
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
  try { const { item, built } = edBuild(); boxes = K.worldBoxes(item, built).map((b) => Object.assign(b, { layer: 1 })); } catch (_) {}
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
    else if ((e.key === 'r' || e.key === 'к') && sel !== null) { const it = items.find((i) => i.id === sel); if (it) rotateItem(it); }
    else if (e.key === 'Escape') { sel = null; renderProps(); redraw(); }
  });
  window.addEventListener('resize', redraw);
  updateStatus(); setTimeout(() => { V.fitted = false; redraw(); }, 0);
}
K._dbg = { get items() { return items; }, addItem, builds, get S() { return S; }, get lib() { return lib; }, setView };
document.addEventListener('DOMContentLoaded', init);
})(window.K = window.K || {});
