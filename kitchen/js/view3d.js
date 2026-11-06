// Лёгкий 3D-рендер на Canvas 2D (ортографическая проекция, painter's algorithm) — без внешних библиотек.
(function (K) {
'use strict';
const COL = { body: [201, 168, 117], front: [236, 230, 218], back: [138, 117, 86], top: [74, 79, 87],
  wall: [154, 163, 173], window: [108, 180, 238], door: [176, 122, 74], water: [47, 128, 237], sewer: [122, 92, 60], gas: [229, 193, 0], socket: [229, 72, 77], vent: [142, 142, 147], column: [154, 163, 173], other: [136, 136, 136] };
const LIGHT = (() => { const v = [-0.4, -0.6, 0.7], n = Math.hypot(...v); return v.map((a) => a / n); })();

K.newCam = () => ({ yaw: 0.45, pitch: 0.6, zoom: 0.2, cx: 0, cy: 0, cz: 0 });
K.fitCam = function (cam, boxes, cv) {
  if (!boxes.length) return;
  const mn = [1e9, 1e9, 1e9], mx = [-1e9, -1e9, -1e9];
  for (const b of boxes) for (let k = 0; k < 3; k++) { mn[k] = Math.min(mn[k], b.mn[k]); mx[k] = Math.max(mx[k], b.mx[k]); }
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
  for (const b of boxes) {
    const [x0, y0, z0] = b.mn, [x1, y1, z1] = b.mx;
    const F = [
      [[0, 0, 1], [[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]]], [[0, 0, -1], [[x0, y0, z0], [x0, y1, z0], [x1, y1, z0], [x1, y0, z0]]],
      [[0, -1, 0], [[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]]], [[0, 1, 0], [[x0, y1, z0], [x0, y1, z1], [x1, y1, z1], [x1, y1, z0]]],
      [[-1, 0, 0], [[x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0]]], [[1, 0, 0], [[x1, y0, z0], [x1, y1, z0], [x1, y1, z1], [x1, y0, z1]]]
    ];
    for (const [n, c] of F) {
      const n1y = n[0] * syw + n[1] * cyw;
      if (n1y * cp - n[2] * sp >= 0) continue; // грань смотрит от камеры
      const pts = c.map((q) => pr(q[0], q[1], q[2]));
      faces.push({ pts, depth: (pts[0][2] + pts[1][2] + pts[2][2] + pts[3][2]) / 4, n, b, layer: b.layer || 0 });
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
