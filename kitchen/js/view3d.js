// Лёгкий 3D-рендер на Canvas 2D (ортографическая проекция, painter's algorithm) — без внешних библиотек.
(function (K) {
'use strict';
const COL = { body: [201, 168, 117], front: [236, 230, 218], back: [138, 117, 86], top: [74, 79, 87],
  wall: [154, 163, 173], parapet: [170, 160, 150], window: [108, 180, 238], door: [176, 122, 74], water: [47, 128, 237], sewer: [122, 92, 60], gas: [229, 193, 0], socket: [229, 72, 77], vent: [142, 142, 147], column: [154, 163, 173], beam: [120, 110, 100], slope: [190, 170, 120], ceiling: [154, 163, 173], other: [136, 136, 136] };
const LIGHT = (() => { const v = [-0.4, -0.6, 0.7], n = Math.hypot(...v); return v.map((a) => a / n); })();

K.newCam = () => ({ yaw: 0.45, pitch: 0.6, zoom: 0.2, cx: 0, cy: 0, cz: 0 });
K.fitCam = function (cam, boxes, cv) {
  if (!boxes.length) return;
  const mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
  for (const b of boxes) {
    const V = b.P3 ? K.solidVerts(b) : b.pts.map((p) => [p[0], p[1], b.z0]).concat(b.pts.map((p) => [p[0], p[1], b.z1]));
    for (const p of V) for (let k = 0; k < 3; k++) { mn[k] = Math.min(mn[k], p[k]); mx[k] = Math.max(mx[k], p[k]); }
  }
  cam.cx = (mn[0] + mx[0]) / 2; cam.cy = (mn[1] + mx[1]) / 2; cam.cz = (mn[2] + mx[2]) / 2;
  const diag = Math.hypot(mx[0] - mn[0], mx[1] - mn[1], mx[2] - mn[2]) || 1000;
  cam.zoom = 0.85 * Math.min(cv.clientWidth, cv.clientHeight) / diag;
};

K.render3D = function (cv, boxes, cam) {
  const dpr = window.devicePixelRatio || 1, W = cv.clientWidth, H = cv.clientHeight;
  if (cv.width !== W * dpr || cv.height !== H * dpr) { cv.width = W * dpr; cv.height = H * dpr; }
  const ctx = cv.getContext('2d'); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, W, H);
  const cyw = Math.cos(cam.yaw), syw = Math.sin(cam.yaw), cp = Math.cos(cam.pitch), sp = Math.sin(cam.pitch);
  const pr = (x, y, z) => { const dx = x - cam.cx, dy = y - cam.cy, dz = z - cam.cz; const x1 = dx * cyw - dy * syw, y1 = dx * syw + dy * cyw; return [W / 2 + x1 * cam.zoom, H / 2 - (y1 * sp + dz * cp) * cam.zoom, y1 * cp - dz * sp]; };
  const faces = [];
  const add = (n, c, b) => {
    const n1y = n[0] * syw + n[1] * cyw;
    if (n1y * cp - n[2] * sp >= 0) return; // грань смотрит от камеры
    const pts = c.map((q) => pr(q[0], q[1], q[2]));
    faces.push({ pts, depth: pts.reduce((a, p) => a + p[2], 0) / pts.length, n, b, layer: b.layer || 0 });
  };
  const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]], crs = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
  const dt = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2], nz = (v) => { const l = Math.hypot(...v) || 1; return v.map((x) => x / l); };
  for (const b of boxes) { // призма: плоский контур P + выдавливание e
    const P = b.P3 || b.pts.map((p) => [p[0], p[1], b.z0]), e = b.e || [0, 0, b.z1 - b.z0];
    const T = P.map((p) => [p[0] + e[0], p[1] + e[1], p[2] + e[2]]);
    let nb = [0, 0, 0];
    for (let i = 0; i < P.length; i++) { const q = P[i], r = P[(i + 1) % P.length]; nb[0] += (q[1] - r[1]) * (q[2] + r[2]); nb[1] += (q[2] - r[2]) * (q[0] + r[0]); nb[2] += (q[0] - r[0]) * (q[1] + r[1]); }
    nb = nz(nb); if (dt(nb, e) > 0) nb = nb.map((x) => -x);
    add(nb, P, b); add(nb.map((x) => -x), T, b);
    const cen = P.reduce((a, p) => [a[0] + p[0] / P.length, a[1] + p[1] / P.length, a[2] + p[2] / P.length], [0, 0, 0]);
    for (let i = 0; i < P.length; i++) {
      const a = P[i], c = P[(i + 1) % P.length], ed = sub(c, a);
      if (Math.hypot(...ed) < 1e-6) continue;
      let n = nz(crs(ed, e)); if (dt(n, sub([(a[0] + c[0]) / 2, (a[1] + c[1]) / 2, (a[2] + c[2]) / 2], cen)) < 0) n = n.map((x) => -x);
      add(n, [a, c, T[(i + 1) % P.length], T[i]], b);
    }
  }
  faces.sort((a, b) => a.layer - b.layer || b.depth - a.depth);
  for (const f of faces) {
    const base = COL[f.b.color || f.b.mat || f.b.type] || COL.other;
    const sh = 0.6 + 0.4 * Math.max(0, f.n[0] * LIGHT[0] + f.n[1] * LIGHT[1] + f.n[2] * LIGHT[2]);
    ctx.globalAlpha = f.b.alpha === undefined ? 1 : f.b.alpha;
    ctx.fillStyle = `rgb(${base.map((v) => Math.round(Math.min(255, v * sh)))})`;
    ctx.strokeStyle = f.b.bad ? '#e03131' : 'rgba(0,0,0,.35)'; ctx.lineWidth = f.b.bad ? 1.6 : 0.6;
    ctx.beginPath(); f.pts.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]))); ctx.closePath(); ctx.fill(); ctx.stroke();
  }
  ctx.globalAlpha = 1;
};

K.attachOrbit = function (cv, cam, redraw) {
  let drag = null;
  cv.addEventListener('pointerdown', (e) => { drag = { x: e.clientX, y: e.clientY, pan: e.button === 2 || e.shiftKey }; cv.setPointerCapture(e.pointerId); });
  cv.addEventListener('pointermove', (e) => {
    if (!drag) return;
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y; drag.x = e.clientX; drag.y = e.clientY;
    if (drag.pan) { const k = 1 / cam.zoom; cam.cx -= (dx * Math.cos(cam.yaw)) * k; cam.cy += (dx * Math.sin(cam.yaw)) * k; cam.cz += dy * k / Math.cos(cam.pitch || 1); }
    else { cam.yaw += dx * 0.008; cam.pitch = Math.max(0.05, Math.min(1.5, cam.pitch + dy * 0.008)); }
    redraw();
  });
  cv.addEventListener('pointerup', () => { drag = null; });
  cv.addEventListener('wheel', (e) => { e.preventDefault(); cam.zoom *= e.deltaY < 0 ? 1.12 : 1 / 1.12; redraw(); }, { passive: false });
  cv.addEventListener('contextmenu', (e) => e.preventDefault());
};
})(window.K = window.K || {});
