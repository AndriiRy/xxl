// node build-dxf.js → dxf/sheet-NN.dxf + cutlist.csv
const fs = require('fs'), path = require('path');
const M = require('./model.js');
const out = path.join(__dirname, 'dxf');
fs.mkdirSync(out, { recursive: true });
M.sheets.forEach(s => fs.writeFileSync(path.join(out, `sheet-${String(s.n).padStart(2, '0')}.dxf`), M.dxfSheet(s)));
const rows = [['Лист', 'Деталь', 'Позиция', 'Назначение', 'L, мм', 'B, мм', 'X на листе', 'Y на листе']];
M.sheets.forEach(s => s.parts.forEach(({ p, x, y }) => rows.push([s.n, p.id, p.mark || 'обшивка', p.role, p.w, p.h, x, y])));
fs.writeFileSync(path.join(__dirname, 'cutlist.csv'), '﻿' + rows.map(r => r.join(';')).join('\n'));
console.log(`${M.sheets.length} листов → ${out}`);
