// Стандартная библиотека модулей (JSON, редактируется в приложении).
// Система координат модуля: x — ширина (слева направо, вид спереди), y — глубина (0 = передняя плоскость корпуса, D = к стене),
// z — вверх (0 = низ корпуса). Фасады в y ∈ [-tf, 0]. Отступ корпуса от стены — свойство шкафа (wallOff), по умолчанию wallGap.
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
const pDb = { id: 'D', label: 'Глубина корпуса', def: 530, defF: 'front-wallGap', min: 200, max: 700, step: 1 };
const pDw = { id: 'D', label: 'Глубина корпуса', def: 320, min: 150, max: 600, step: 1 };
const pH = (f, min, max) => ({ id: 'H', label: 'Высота', def: 720, defF: f, min, max, step: 1 });
const pShelves = (def) => ({ id: 'shelves', label: 'Полок', def, min: 0, max: 10, step: 1 });
const pDoors = { id: 'doors', label: 'Дверей (0 = авто)', def: 0, min: 0, max: 4, step: 1 };
const doorVars = [{ id: 'nd', f: 'doors>0?doors:(W>600?2:1)' }, { id: 'dw', f: '(W-gap*nd)/nd' }];
const legs = { name: 'Ножка регулируемая h=100', qty: '4+(W>900)*2' };
const handle = { name: 'Ручка', qty: 'nd' };
const asmBase = [
  'Каркас: бока + дно + царги на конфирматы 7×50 (Ø5×50 в торцы, Ø7 сквозное в боках). Проверить диагонали.',
  'Задняя стенка ХДФ: на скобы/гвозди по периметру, выставить по диагонали.',
  'Полки на полкодержатели Ø5 (отверстия в боках).',
  'Ножки в дно, цоколь на клипсы/уголки.',
  'Фасады: чашки Ø35 под петли, планки на боках, зазоры 2 мм, регулировка.'
];

K.LIB_VER = 4; // при изменении стандартных модулей — увеличить
K.LIB_REMOVED = ['bay_corner'];
K.defaultLib = function () {
  return JSON.parse(JSON.stringify([
    {
      id: 'base_doors', name: 'Нижний с дверцами', cat: 'base', z0: 'plinth',
      params: [pW(600, 150, 1200), pH('baseH', 300, 900), pDb, pShelves(1), pDoors], vars: doorVars,
      parts: [side('Бок левый', '0'), side('Бок правый', 'W-t'), bottomFull, railF, railB, back, shelf, door, plinthPart],
      hardware: [legs, handle], assembly: asmBase
    },
    {
      id: 'base_angled', name: 'Нижний под угол (косые боки)', cat: 'base', z0: 'plinth',
      params: [{ id: 'W', label: 'Ширина по фронту', def: 600, min: 150, max: 1500, step: 1 }, pH('baseH', 300, 900), pDb,
        { id: 'angL', label: 'Угол левого бока, ° (+ сзади уже)', def: 0, min: -60, max: 60, step: 0.5 }, { id: 'angR', label: 'Угол правого бока, °', def: 0, min: -60, max: 60, step: 0.5 }, pShelves(1), pDoors],
      vars: [{ id: 'nd', f: 'doors>0?doors:(W>600?2:1)' }, { id: 'cL', f: 'angL<0?tf*tand(-angL)+1:0' }, { id: 'cR', f: 'angR<0?tf*tand(-angR)+1:0' }, { id: 'dw', f: '(W-gap*nd-cL-cR)/nd' },
        { id: 'taL', f: 'tand(angL)' }, { id: 'taR', f: 'tand(angR)' }, { id: 'tcL', f: 't/cosd(angL)' }, { id: 'tcR', f: 't/cosd(angR)' }, { id: 'yb', f: 'D-tb' },
        { id: 'syL', f: 'max(0,t*sind(angL))' }, { id: 'syR', f: 'max(0,-t*sind(angR))' }
      ],
      foot: 'cL,-tf; W-cR,-tf; W,0; W-D*taR,D; D*taL,D; 0,0',
      parts: [
        { name: 'Бок левый (торцы под углом)', mat: 'body', count: '1', x: '0', y: 'syL', z: '0', sx: 't', sy: '(D-syL)/cosd(angL)', sz: 'H', rz: '-angL', lax: 'z', edge: 'L1', role: 'side' },
        { name: 'Бок правый (торцы под углом)', mat: 'body', count: '1', x: 'W-t*cosd(angR)', y: 'syR', z: '0', sx: 't', sy: '(D-syR)/cosd(angR)', sz: 'H', rz: 'angR', lax: 'z', edge: 'L1', role: 'side' },
        { name: 'Дно (трапеция)', mat: 'body', count: '1', poly: 'tcL,0; W-tcR,0; W-yb*taR-tcR,yb; yb*taL+tcL,yb', z: '0', sz: 't', edge: '1' },
        { name: 'Царга передняя (трапеция)', mat: 'body', count: '1', poly: 'tcL,0; W-tcR,0; W-100*taR-tcR,100; 100*taL+tcL,100', z: 'H-t', sz: 't', edge: '1' },
        { name: 'Царга задняя (трапеция)', mat: 'body', count: '1', poly: '(yb-100)*taL+tcL,yb-100; W-(yb-100)*taR-tcR,yb-100; W-yb*taR-tcR,yb; yb*taL+tcL,yb', z: 'H-t', sz: 't', edge: '' },
        { name: 'Задняя стенка', mat: 'back', count: '1', x: 'yb*taL+tcL', y: 'yb', z: 't', sx: 'W-yb*(taL+taR)-tcL-tcR', sy: 'tb', sz: 'H-2*t' },
        { name: 'Полка (трапеция)', mat: 'body', count: 'shelves', poly: '20*taL+tcL+1,20; W-20*taR-tcR-1,20; W-(yb-5)*taR-tcR-1,yb-5; (yb-5)*taL+tcL+1,yb-5', z: 't+(i+1)*(H-2*t)/(shelves+1)-t/2', sz: 't', edge: '1' },
        Object.assign({}, door, { x: 'cL+gap/2+i*(dw+gap)' }), plinthPart
      ],
      hardware: [legs, handle, { name: 'Петля Blum Clip top Blumotion 110° + планка', qty: 'nd*(2+(H>900))' }, { name: 'Уголок мебельный (крепление косого бока)', qty: '8' }],
      assembly: [
        'Бока: заготовка по таблице, передний и задний торцы под углом бока (запил на форматнике).',
        'Дно, царги, полки — трапеции по шаблону (координаты вершин в спецификации).',
        'Сборка на уголки/конфирматы по месту (присадка косых соединений — по шаблону).',
        'Ставить так, чтобы косой бок совпал со стыком столешницы.',
        'Фасады, петли, цоколь.'
      ]
    },
    {
      id: 'base_drawers', name: 'Нижний с ящиками', cat: 'base', z0: 'plinth',
      params: [pW(600, 300, 1200), pH('baseH', 300, 900), pDb, { id: 'drawers', label: 'Ящиков', def: 3, min: 1, max: 5, step: 1 }],
      vars: [{ id: 'fh', f: '(H-gap*drawers)/drawers' }, { id: 'sh', f: '(H-2*t)/drawers' }, { id: 'rl', f: 'floor((D-tb-10)/50)*50' }, { id: 'bw', f: 'W-2*t-26' }, { id: 'bh', f: 'sh-20' }],
      parts: [
        side('Бок левый', '0'), side('Бок правый', 'W-t'), bottomFull, railF, railB, back,
        { name: 'Ящик: боковина', mat: 'body', count: '2*drawers', x: 'i%2==0?t+13:W-t-13-t', y: '2', z: 't+floor(i/2)*sh+8', sx: 't', sy: 'rl', sz: 'bh', lax: 'y', edge: 'L2', role: 'dside' },
        { name: 'Ящик: перед/зад', mat: 'body', count: '2*drawers', x: 't+13+t', y: 'i%2==0?2:2+rl-t', z: 't+floor(i/2)*sh+8', sx: 'bw-2*t', sy: 't', sz: 'bh', lax: 'x', edge: 'L2', drill: 'conf', to: 'dside' },
        { name: 'Ящик: дно ХДФ', mat: 'back', count: 'drawers', x: 't+13', y: '2', z: 't+i*sh+16', sx: 'bw', sy: 'rl', sz: 'tb' },
        { name: 'Фасад (ящик)', mat: 'front', count: 'drawers', x: 'gap/2', y: '-tf', z: 'gap/2+i*(fh+gap)', sx: 'W-gap', sy: 'tf', sz: 'fh', lax: 'x', edge: 'all', role: 'drawerfront' },
        plinthPart
      ],
      hardware: [legs, { name: 'Направляющие шариковые полного выдвижения L={rl}', qty: 'drawers' }, { name: 'Ручка', qty: 'drawers' }, { name: 'Саморез 4×30 крепление фасада ящика', qty: '4*drawers' }],
      assembly: ['Каркас: бока + дно + царги на конфирматы 7×50.', 'Задняя стенка ХДФ на скобы.', 'Ящики: стенки на конфирматы, дно ХДФ в паз/на скобы; направляющие по шаблону.', 'Ножки, цоколь.', 'Фасады ящиков на саморезы, зазоры 2 мм.']
    },
    {
      id: 'wall_doors', name: 'Верхний с дверцами', cat: 'wall', z0: 'wallBottom',
      params: [pW(600, 200, 1200), pH('wallH', 300, 1100), pDw, pShelves(1), pDoors], vars: doorVars,
      parts: [side('Бок левый', '0'), side('Бок правый', 'W-t'), bottomFull, topFull, back, shelf, door],
      hardware: [{ name: 'Навес шкафа регулируемый', qty: '2' }, { name: 'Анкер/шуруп 5×70 под навес', qty: '2' }, handle],
      assembly: ['Каркас: бока + дно + крышка на конфирматы 7×50.', 'Задняя стенка ХДФ на скобы.', 'Навесы, полки на полкодержатели.', 'Фасады: чашки Ø35, планки, зазоры 2 мм.', 'Монтаж на стену по уровню.']
    },
    {
      id: 'tall_doors', name: 'Пенал', cat: 'tall', z0: 'plinth',
      params: [pW(600, 300, 900), pH('tallH', 1500, 2400), pDb, pShelves(4), pDoors], vars: doorVars,
      parts: [side('Бок левый', '0'), side('Бок правый', 'W-t'), bottomFull, topFull, back, shelf, door, plinthPart],
      hardware: [legs, handle], assembly: asmBase
    },
    {
      id: 'tall_slope', name: 'Пенал под скос (скос по ширине)', cat: 'tall', z0: 'plinth',
      params: [pW(600, 300, 1200), { id: 'hL', label: 'Высота слева', def: 2100, min: 300, max: 2600, step: 1 }, { id: 'hR', label: 'Высота справа', def: 1700, min: 300, max: 2600, step: 1 }, pDb, pShelves(3), pDoors],
      vars: doorVars.concat([{ id: 'H', f: 'max(hL,hR)' }, { id: 'kk', f: '(hR-hL)/W' }, { id: 'tz', f: 't*sqrt(1+kk*kk)' }, { id: 'hm', f: 'min(hL,hR)' }]),
      parts: [
        { name: 'Бок левый', mat: 'body', count: '1', x: '0', y: '0', z: '0', sx: 't', sy: 'D', sz: 'hL', lax: 'z', edge: 'L1', role: 'side' },
        { name: 'Бок правый', mat: 'body', count: '1', x: 'W-t', y: '0', z: '0', sx: 't', sy: 'D', sz: 'hR', lax: 'z', edge: 'L1', role: 'side' },
        bottomFull,
        { name: 'Крышка наклонная (торцы под углом)', mat: 'body', count: '1', poly: 't,hL+kk*t-tz; W-t,hL+kk*(W-t)-tz; W-t,hL+kk*(W-t); t,hL+kk*t', plane: 'xz', sec: 1, y: '0', sy: 'D-tb', edge: 'F' },
        { name: 'Задняя стенка (скос)', mat: 'back', count: '1', poly: 't,t; W-t,t; W-t,hL+kk*(W-t)-tz; t,hL+kk*t-tz', plane: 'xz', y: 'D-tb', sy: 'tb', edge: '' },
        { name: 'Полка', mat: 'body', count: 'shelves', x: 't+1', y: '20', z: 't+(i+1)*(hm-2*t)/(shelves+1)-t/2', sx: 'W-2*t-2', sy: 'D-tb-25', sz: 't', lax: 'x', edge: 'L1', drill: 'shelf' },
        { name: 'Фасад со скосом', mat: 'front', count: 'nd', poly: '(gap/2+i*(dw+gap)),gap/2; (gap/2+i*(dw+gap))+dw,gap/2; (gap/2+i*(dw+gap))+dw,hL+kk*((gap/2+i*(dw+gap))+dw)-gap/2; (gap/2+i*(dw+gap)),hL+kk*(gap/2+i*(dw+gap))-gap/2', plane: 'xz', y: '-tf', sy: 'tf', edge: 'all', role: 'door' },
        plinthPart
      ],
      hardware: [legs, handle, { name: 'Петля Blum Clip top Blumotion 110° + планка', qty: 'nd*(2+(hm>900)+(hm>1600))' }, { name: 'Уголок мебельный (крышка)', qty: '4' }],
      assembly: ['Бока разной высоты, верхний торец под углом скоса.', 'Наклонная крышка между боков на уголки/конфирматы, торцы под углом.', 'Задняя ХДФ по контуру скоса.', 'Фасады со скосом — раскрой по контуру (вершины в спецификации), кромка по периметру.', 'Чашки петель — по шаблону, ниже линии скоса.']
    },
    {
      id: 'tall_beam', name: 'Пенал с вырезом под балку', cat: 'tall', z0: 'plinth',
      params: [pW(600, 300, 1200), pH('tallH', 1500, 2600), pDb, { id: 'bh', label: 'Вырез: высота', def: 200, min: 20, max: 1000, step: 1 }, { id: 'bd', label: 'Вырез: глубина от задней стороны', def: 250, min: 20, max: 600, step: 1 }, pShelves(4), pDoors],
      vars: doorVars,
      parts: [
        { name: 'Бок левый (с вырезом)', mat: 'body', count: '1', poly: '0,0; D,0; D,H-bh; D-bd,H-bh; D-bd,H; 0,H', plane: 'yz', x: '0', sx: 't', edge: '6', role: 'side' },
        { name: 'Бок правый (с вырезом)', mat: 'body', count: '1', poly: '0,0; D,0; D,H-bh; D-bd,H-bh; D-bd,H; 0,H', plane: 'yz', x: 'W-t', sx: 't', edge: '6', role: 'side' },
        bottomFull,
        { name: 'Крышка', mat: 'body', count: '1', x: 't', y: '0', z: 'H-t', sx: 'W-2*t', sy: 'D-bd-t', sz: 't', lax: 'x', edge: 'L1' },
        { name: 'Стенка выреза', mat: 'body', count: '1', x: 't', y: 'D-bd-t', z: 'H-bh', sx: 'W-2*t', sy: 't', sz: 'bh', lax: 'x', edge: '' },
        { name: 'Полка выреза', mat: 'body', count: '1', x: 't', y: 'D-bd', z: 'H-bh-t', sx: 'W-2*t', sy: 'bd-tb', sz: 't', lax: 'x', edge: '' },
        { name: 'Задняя стенка', mat: 'back', count: '1', x: 't', y: 'D-tb', z: 't', sx: 'W-2*t', sy: 'tb', sz: 'H-bh-2*t' },
        { name: 'Полка', mat: 'body', count: 'shelves', x: 't+1', y: '20', z: 't+(i+1)*(H-bh-2*t)/(shelves+1)-t/2', sx: 'W-2*t-2', sy: 'D-tb-25', sz: 't', lax: 'x', edge: 'L1' },
        door, plinthPart
      ],
      hardware: [legs, handle, { name: 'Петля Blum Clip top Blumotion 110° + планка', qty: 'nd*(2+(H>900)+(H>1600)+(H>2000))' }, { name: 'Конфирмат 7×50 (вырез)', qty: '8' }],
      assembly: ['Бока с вырезом под балку — раскрой по контуру (вершины в спецификации).', 'Каркас: дно, крышка, стенка и полка выреза на конфирматы по месту.', 'Задняя ХДФ до полки выреза.', 'Фасады, петли, цоколь.']
    },
    {
      id: 'counter', name: 'Столешница', cat: 'counter', z0: 'plinth+baseH',
      params: [{ id: 'W', label: 'Длина по стене (по заднему краю)', def: 1200, min: 100, max: 4000, step: 1 }, { id: 'D', label: 'Глубина от стены', def: 600, defF: 'cDepth', min: 300, max: 1000, step: 1 }, { id: 'T', label: 'Толщина', def: 12, defF: 'tt', min: 6, max: 60, step: 1 },
        { id: 'cutL', label: 'Подрезка левого торца, ° (+ наружный угол, − внутренний)', def: 0, min: -60, max: 60, step: 0.5 }, { id: 'cutR', label: 'Подрезка правого торца, °', def: 0, min: -60, max: 60, step: 0.5 }],
      vars: [{ id: 'dl', f: 'D*tand(cutL)' }, { id: 'dr', f: 'D*tand(cutR)' }],
      foot: '-dl,0; W+dr,0; W,D; 0,D',
      parts: [{ name: 'Столешница', mat: 'top', count: '1', poly: '-dl,0; W+dr,0; W,D; 0,D', z: '0', sz: 'T', edge: '1' }],
      hardware: [{ name: 'Уголок/клей крепления столешницы', qty: 'ceil(W/400)*2' }, { name: 'Стяжка/ламель стыка столешницы', qty: '(cutL!=0)+(cutR!=0)' }],
      assembly: ['Раскрой по контуру (подрезка торцов под угол стыка), вырезы под мойку/варочную по шаблону техники.', 'Стык под углом — стяжка/ламели + клей/герметик.', 'Крепление к царгам.']
    },
    {
      id: 'filler', name: 'Фальшпанель / бленда', cat: 'filler', z0: 'plinth',
      params: [{ id: 'W', label: 'Ширина', def: 19, min: 5, max: 600, step: 0.5 }, pH('baseH', 50, 2600), { id: 'D', label: 'Глубина (для габарита)', def: 20, min: 1, max: 700, step: 1 }],
      vars: [],
      parts: [{ name: 'Фальшпанель', mat: 'front', count: '1', x: '0', y: '-tf', z: 'gap/2', sx: 'W', sy: 'tf', sz: 'H-gap', edge: 'all' }],
      hardware: [], assembly: ['Крепить к соседнему корпусу уголками/саморезами изнутри.']
    }
  ])).map((m) => Object.assign(m, { ver: K.LIB_VER }));
};

K.catName = { base: 'Нижние', tall: 'Пеналы', wall: 'Верхние', counter: 'Столешницы', filler: 'Доборы', other: 'Прочее' };
K.catOrder = ['counter', 'base', 'tall', 'filler', 'wall', 'other'];

// Каталог фурнитуры для редактора (клик — добавить в модуль, кол-во — формула)
K.hwCatalog = [
  ['Петли', 'Blum Clip top Blumotion 110° + планка', 'nd*(2+(H>900)+(H>1600)+(H>2000))'],
  ['Петли', 'Blum Clip top Blumotion 155° (угловой шкаф)', '2'],
  ['Петли', 'Blum Clip top 45° (угловая петля)', '2'],
  ['Петли', 'Blum Revego uno (карманная дверь)', '1'],
  ['Ящики', 'Blum Legrabox pure M (90.5) L={rl}', 'drawers'],
  ['Ящики', 'Blum Legrabox pure K (128.5) L={rl}', 'drawers'],
  ['Ящики', 'Blum Legrabox pure C (177) L={rl}', 'drawers'],
  ['Ящики', 'Blum Legrabox pure F (241) L={rl}', 'drawers'],
  ['Ящики', 'Blum Legrabox — внутренний ящик (фронт внутр.)', '1'],
  ['Ящики', 'Blum Antaro (Tandembox) M L={rl}', 'drawers'],
  ['Ящики', 'Blum Movento 760H L={rl}', 'drawers'],
  ['Ящики', 'Blum Tip-on Blumotion', 'drawers'],
  ['Ящики', 'Blum Servo-drive (комплект)', '1'],
  ['Ящики', 'Blum Ambia-line вставка/делитель', '1'],
  ['Подъёмники', 'Blum Aventos HF (складной)', '1'],
  ['Подъёмники', 'Blum Aventos HK top', '1'],
  ['Подъёмники', 'Blum Aventos HL', '1'],
  ['Подъёмники', 'Blum Aventos HS', '1'],
  ['Аксессуары', 'Cargo 150 (2 уровня), выдвижной', '1'],
  ['Аксессуары', 'Корзина под мойку / сортер отходов', '1'],
  ['Аксессуары', 'Space corner / угловой механизм', '1'],
  ['Аксессуары', 'Сушка для посуды (верхний шкаф)', '1'],
  ['Аксессуары', 'Профиль LED (белый, 3000K), м', 'ceil(W/1000)'],
  ['Аксессуары', 'Датчик движения/двери LED', '1'],
  ['Аксессуары', 'Решётка вентиляционная / фрезы вентиляции', '1'],
  ['Корпус', 'Ножка регулируемая h=100', '4+(W>900)*2'],
  ['Корпус', 'Клипса цоколя', '2+(W>600)'],
  ['Корпус', 'Навес шкафа регулируемый (Camar)', '2'],
  ['Корпус', 'Шина монтажная навесная, мм', 'W'],
  ['Корпус', 'Стяжка межсекционная', '4'],
  ['Корпус', 'Конфирмат 7×50', '8'],
  ['Корпус', 'Эксцентрик Minifix 15 + шток', '8'],
  ['Корпус', 'Шкант 8×35', '8'],
  ['Корпус', 'Уголок мебельный', '4'],
  ['Ручки', 'Ручка', 'nd'],
  ['Ручки', 'Профиль-ручка Gola / фрезерованная ручка', '1'],
  ['Техника', 'Встраиваемая посудомойка 45 — крепёж фасада', '1'],
  ['Техника', 'Духовой шкаф 60 — крепёж', '1'],
  ['Техника', 'Холодильник встр. — направляющие фасада', '2']
];

// Мастер корпуса: генерация деталей каркаса по выбранной конструкции
K.carcass = function (o) {
  const P = [];
  const sideH = o.bottom === 'under' ? 'H-t' : o.top === 'over' ? 'H-t' : 'H';
  const sideZ = o.bottom === 'under' ? 't' : '0';
  const sh = o.bottom === 'under' && o.top === 'over' ? 'H-2*t' : sideH;
  P.push({ name: 'Бок левый', mat: 'body', count: '1', x: '0', y: '0', z: sideZ, sx: 't', sy: 'D', sz: sh, lax: 'z', edge: 'L1', role: 'side', tag: 'carcass' });
  P.push({ name: 'Бок правый', mat: 'body', count: '1', x: 'W-t', y: '0', z: sideZ, sx: 't', sy: 'D', sz: sh, lax: 'z', edge: 'L1', role: 'side', tag: 'carcass' });
  const bk = o.back === 'groove' ? 'D-10-tb' : o.back === 'over' ? 'D-tb' : 'D-tb'; // y задней стенки
  const inner = o.back === 'groove' ? 'D-10-tb' : 'D-tb';
  if (o.bottom === 'under') P.push({ name: 'Дно (бока на дне)', mat: 'body', count: '1', x: '0', y: '0', z: '0', sx: 'W', sy: o.back === 'over' ? 'D-tb' : 'D', sz: 't', lax: 'x', edge: 'L1 W1 W2', tag: 'carcass' });
  else P.push({ name: 'Дно (между боков)', mat: 'body', count: '1', x: 't', y: '0', z: '0', sx: 'W-2*t', sy: inner, sz: 't', lax: 'x', edge: 'L1', drill: 'conf', tag: 'carcass' });
  if (o.top === 'rails') {
    P.push({ name: 'Царга передняя', mat: 'body', count: '1', x: 't', y: '0', z: 'H-t', sx: 'W-2*t', sy: '100', sz: 't', lax: 'x', edge: 'L1', drill: 'conf', tag: 'carcass' });
    P.push({ name: 'Царга задняя', mat: 'body', count: '1', x: 't', y: inner + '-100', z: 'H-t', sx: 'W-2*t', sy: '100', sz: 't', lax: 'x', edge: '', drill: 'conf', tag: 'carcass' });
  } else if (o.top === 'over') P.push({ name: 'Крышка (на боках)', mat: 'body', count: '1', x: '0', y: '0', z: 'H-t', sx: 'W', sy: o.back === 'over' ? 'D-tb' : 'D', sz: 't', lax: 'x', edge: 'L1 W1 W2', tag: 'carcass' });
  else if (o.top === 'inner') P.push({ name: 'Крышка (между боков)', mat: 'body', count: '1', x: 't', y: '0', z: 'H-t', sx: 'W-2*t', sy: inner, sz: 't', lax: 'x', edge: 'L1', drill: 'conf', tag: 'carcass' });
  if (o.back === 'over') P.push({ name: 'Задняя стенка (накладная)', mat: 'back', count: '1', x: '0', y: 'D-tb', z: '0', sx: 'W', sy: 'tb', sz: 'H', tag: 'carcass' });
  else if (o.back === 'groove') P.push({ name: 'Задняя стенка (в паз 10 мм)', mat: 'back', count: '1', x: 't-8', y: bk, z: o.bottom === 'under' ? 't-8' : '8', sx: 'W-2*t+16', sy: 'tb', sz: 'H-16-(' + (o.bottom === 'under' ? 't' : '0') + ')-(' + (o.top === 'over' ? 't' : '0') + ')', tag: 'carcass' });
  else P.push({ name: 'Задняя стенка (внутри)', mat: 'back', count: '1', x: 't', y: 'D-tb', z: 't', sx: 'W-2*t', sy: 'tb', sz: 'H-2*t', tag: 'carcass' });
  return P;
};
})(window.K = window.K || {});
