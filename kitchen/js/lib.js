// Стандартная библиотека модулей. Все модули — обычный JSON, редактируются в приложении.
// Система координат модуля: x — ширина (слева направо), y — глубина (0 = передняя плоскость корпуса, D = стена), z — вверх (0 = низ корпуса).
// Фасады лежат в y ∈ [-tf, 0].
(function (K) {
'use strict';

const side = (name, x) => ({ name, mat: 'body', count: '1', x, y: '0', z: '0', sx: 't', sy: 'D', sz: 'H', lax: 'z', edge: 'L1', role: 'side' });
const back = { name: 'Задняя стенка', mat: 'back', count: '1', x: 't', y: 'D-tb', z: 't', sx: 'W-2*t', sy: 'tb', sz: 'H-2*t' };
const shelf = { name: 'Полка', mat: 'body', count: 'shelves', x: 't+1', y: '20', z: 't+(i+1)*(H-2*t)/(shelves+1)-t/2', sx: 'W-2*t-2', sy: 'D-tb-25', sz: 't', lax: 'x', edge: 'L1', drill: 'shelf' };
const door = { name: 'Фасад (дверь)', mat: 'front', count: 'nd', x: 'gap/2+i*(dw+gap)', y: '-tf', z: 'gap/2', sx: 'dw', sy: 'tf', sz: 'H-gap', edge: 'all', role: 'door', hinge: 'i==0?-1:1' };
const plinthPart = { name: 'Цоколь', mat: 'body', count: '1', x: '0', y: '50', z: '5-plinth', sx: 'W', sy: 't', sz: 'plinth-10', lax: 'x', edge: 'L1 L2' };
const bottomFull = { name: 'Дно', mat: 'body', count: '1', x: 't', y: '0', z: '0', sx: 'W-2*t', sy: 'D-tb', sz: 't', lax: 'x', edge: 'L1', drill: 'conf' };
const topFull = { name: 'Крышка', mat: 'body', count: '1', x: 't', y: '0', z: 'H-t', sx: 'W-2*t', sy: 'D-tb', sz: 't', lax: 'x', edge: 'L1', drill: 'conf' };
const railF = { name: 'Царга передняя', mat: 'body', count: '1', x: 't', y: '0', z: 'H-t', sx: 'W-2*t', sy: '100', sz: 't', lax: 'x', edge: 'L1', drill: 'conf' };
const railB = { name: 'Царга задняя', mat: 'body', count: '1', x: 't', y: 'D-tb-100', z: 'H-t', sx: 'W-2*t', sy: '100', sz: 't', lax: 'x', edge: '', drill: 'conf' };

const pW = (def, min, max) => ({ id: 'W', label: 'Ширина', def, min, max, step: 1 });
const pD = (def) => ({ id: 'D', label: 'Глубина корпуса', def, min: 200, max: 700, step: 1 });
const pH = (f, min, max) => ({ id: 'H', label: 'Высота', def: 720, defF: f, min, max, step: 1 });
const pShelves = (def) => ({ id: 'shelves', label: 'Полок', def, min: 0, max: 10, step: 1 });
const pDoors = { id: 'doors', label: 'Дверей (0 = авто)', def: 0, min: 0, max: 4, step: 1 };
const doorVars = [{ id: 'nd', f: 'doors>0?doors:(W>600?2:1)' }, { id: 'dw', f: '(W-gap*nd)/nd' }];
const legs = { name: 'Ножка регулируемая h=100', qty: '4+(W>900)*2' };
const handle = { name: 'Ручка', qty: 'nd' };

K.defaultLib = function () {
  return JSON.parse(JSON.stringify([
    {
      id: 'base_doors', name: 'Нижний с дверцами', cat: 'base', z0: 'plinth',
      params: [pW(600, 200, 1200), pH('baseH', 300, 900), pD(560), pShelves(1), pDoors],
      vars: doorVars,
      parts: [side('Бок левый', '0'), side('Бок правый', 'W-t'), bottomFull, railF, railB, back, shelf, door, plinthPart],
      hardware: [legs, handle],
      assembly: [
        'Каркас: бока + дно + царги на конфирматы 7×50 (Ø5×50 в торцы, Ø7 сквозное в боках). Проверить диагонали.',
        'Задняя стенка ХДФ: на скобы/гвозди по периметру, выставить по диагонали.',
        'Полки на полкодержатели Ø5 (отверстия в боках, шаг 32).',
        'Ножки в дно, цоколь на клипсы/уголки.',
        'Фасады: чашки Ø35 под петли, планки на боках, зазоры 2 мм, регулировка.'
      ]
    },
    {
      id: 'base_drawers', name: 'Нижний с ящиками', cat: 'base', z0: 'plinth',
      params: [pW(600, 300, 1200), pH('baseH', 300, 900), pD(560), { id: 'drawers', label: 'Ящиков', def: 3, min: 1, max: 5, step: 1 }],
      vars: [
        { id: 'fh', f: '(H-gap*drawers)/drawers' }, { id: 'sh', f: '(H-2*t)/drawers' },
        { id: 'rl', f: 'floor((D-tb-10)/50)*50' }, { id: 'bw', f: 'W-2*t-26' }, { id: 'bh', f: 'sh-20' }
      ],
      parts: [
        side('Бок левый', '0'), side('Бок правый', 'W-t'), bottomFull, railF, railB, back,
        { name: 'Ящик: боковина', mat: 'body', count: '2*drawers', x: 'i%2==0?t+13:W-t-13-t', y: '2', z: 't+floor(i/2)*sh+8', sx: 't', sy: 'rl', sz: 'bh', lax: 'y', edge: 'L2', role: 'dside' },
        { name: 'Ящик: перед/зад', mat: 'body', count: '2*drawers', x: 't+13+t', y: 'i%2==0?2:2+rl-t', z: 't+floor(i/2)*sh+8', sx: 'bw-2*t', sy: 't', sz: 'bh', lax: 'x', edge: 'L2', drill: 'conf', to: 'dside' },
        { name: 'Ящик: дно ХДФ', mat: 'back', count: 'drawers', x: 't+13', y: '2', z: 't+i*sh+16', sx: 'bw', sy: 'rl', sz: 'tb' },
        { name: 'Фасад (ящик)', mat: 'front', count: 'drawers', x: 'gap/2', y: '-tf', z: 'gap/2+i*(fh+gap)', sx: 'W-gap', sy: 'tf', sz: 'fh', lax: 'x', edge: 'all', role: 'drawerfront' },
        plinthPart
      ],
      hardware: [
        legs, { name: 'Направляющие шариковые полного выдвижения L={rl}', qty: 'drawers' },
        { name: 'Ручка', qty: 'drawers' }, { name: 'Саморез 4×30 крепление фасада ящика', qty: '4*drawers' }
      ],
      assembly: [
        'Каркас: бока + дно + царги на конфирматы 7×50.',
        'Задняя стенка ХДФ на скобы.',
        'Ящики: стенки на конфирматы, дно ХДФ в паз/на скобы; направляющие по шаблону, на боках шкафа первая линия от дна.',
        'Ножки, цоколь.',
        'Фасады ящиков на саморезы через корпус ящика, зазоры 2 мм.'
      ]
    },
    {
      id: 'wall_doors', name: 'Верхний с дверцами', cat: 'wall', z0: 'wallBottom',
      params: [pW(600, 200, 1200), pH('wallH', 300, 1100), pD(320), pShelves(1), pDoors],
      vars: doorVars,
      parts: [side('Бок левый', '0'), side('Бок правый', 'W-t'), bottomFull, topFull, back, shelf, door],
      hardware: [{ name: 'Навес шкафа регулируемый', qty: '2' }, { name: 'Анкер/шуруп 5×70 под навес', qty: '2' }, handle],
      assembly: [
        'Каркас: бока + дно + крышка на конфирматы 7×50.',
        'Задняя стенка ХДФ на скобы.',
        'Навесы в верхние углы, полки на полкодержатели.',
        'Фасады: чашки Ø35, планки на боках, зазоры 2 мм.',
        'Монтаж на стену по уровню, регулировка навесов.'
      ]
    },
    {
      id: 'tall_doors', name: 'Пенал', cat: 'tall', z0: 'plinth',
      params: [pW(600, 300, 900), pH('tallH', 1500, 2400), pD(560), pShelves(4), pDoors],
      vars: doorVars,
      parts: [side('Бок левый', '0'), side('Бок правый', 'W-t'), bottomFull, topFull, back, shelf, door, plinthPart],
      hardware: [legs, handle],
      assembly: [
        'Каркас: бока + дно + крышка на конфирматы 7×50, диагонали.',
        'Задняя стенка ХДФ на скобы.',
        'Полки на полкодержатели Ø5.',
        'Ножки, цоколь, крепление к стене уголками.',
        'Фасады: чашки Ø35 (по формуле число петель от высоты), зазоры 2 мм.'
      ]
    },
    {
      id: 'counter', name: 'Столешница', cat: 'counter', z0: 'plinth+baseH',
      params: [{ id: 'W', label: 'Длина', def: 1200, min: 200, max: 4000, step: 1 }, { id: 'D', label: 'Глубина (от плоскости корпуса)', def: 560, min: 300, max: 900, step: 1 }, { id: 'T', label: 'Толщина', def: 38, defF: 'tt', min: 20, max: 60, step: 1 }],
      vars: [],
      parts: [{ name: 'Столешница', mat: 'top', count: '1', x: '0', y: '-tf-20', z: '0', sx: 'W', sy: 'D+tf+20', sz: 'T', lax: 'x', edge: 'L1' }],
      hardware: [{ name: 'Уголок крепления столешницы', qty: 'ceil(W/400)*2' }],
      assembly: ['Раскрой и вырезы под мойку/варочную по шаблону техники, торцы — по типу столешницы.', 'Крепление к царгам снизу уголками.']
    },
    {
      id: 'filler', name: 'Фальшпанель / доборка', cat: 'filler', z0: 'plinth',
      params: [{ id: 'W', label: 'Ширина', def: 100, min: 20, max: 600, step: 1 }, pH('baseH', 100, 2400), { id: 'D', label: 'Глубина (для габарита)', def: 20, min: 1, max: 700, step: 1 }],
      vars: [],
      parts: [{ name: 'Фальшпанель', mat: 'front', count: '1', x: '0', y: '-tf', z: 'gap/2', sx: 'W', sy: 'tf', sz: 'H-gap', edge: 'all' }],
      hardware: [],
      assembly: ['Крепить к соседнему корпусу уголками/саморезами изнутри.']
    }
  ]));
};

K.catName = { base: 'Нижние', tall: 'Пеналы', wall: 'Верхние', counter: 'Столешницы', filler: 'Доборы', other: 'Прочее' };
K.catOrder = ['counter', 'base', 'tall', 'filler', 'wall', 'other'];
})(window.K = window.K || {});
