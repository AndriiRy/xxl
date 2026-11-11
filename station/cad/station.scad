// Компактная полярная станция «как DISTO 3D»: голова по центру в вилке из двух закрытых башен,
// полая ось Hz (лазерный отвес вниз), встроенный 3S 21700.
// v6: Hz крутится без ограничения (больше 360°): замкнутый ремень GT2, вращается весь корпус с аккумулятором и мотором,
//     неподвижны только дно с ножками, ось-труба и шкив 188 зубьев -> провода через ось не идут (токосъёмник не нужен).
//     Все узлы закрыты: ремень — в камере под палубой, шнур V — в башне. V — сменный картридж на 1 гайке-барашке.
// v5: все наружные кромки скруглены (корпус R6, башни R8, голова R3, крышки, барабаны, ножки с шариком).
// Кромки, которые лежат на столе принтера, — «печатное» скругление (дуга до 45° + фаска 45°): без поддержек.
// Принтер: Bambu Lab P1S (256x256x256). PETG/PETG-HF, сопло 0,4, слой 0,2, 4 периметра, гироид 30-40 %.
// Экспорт: openscad -D 'part="alidade"' -o alidade.stl station.scad
// part: base | spacer | deck | housing | alidade | pod_lid_l | pod_lid_r | head | head_lid
//       v_cart | v_hub | v_drum | v_knob | collar | foot | assembly | down
part  = "assembly";
$fn = 96;

// ---------- покупное ----------
B_OD = 22.15; B_W = 7;                 // 608 (ось V)
T_OD = 30.0;  T_ID = 26;               // ось Hz: алюминиевая труба 30x2
BH_OD = 42.15; BH_W = 7;               // 6806-2RS (30x42x7) — 2 шт в Hz-барабане
MOT = 42.3; MOT_L = 23;                // NEMA17 «блинчик» 17HS4023 (23 мм); обычный — MOT_L = 40
SHAFT_R = 3.0; CORD = 0.5; PITCH = 1.2;// латунная втулка 6x0,5 на валу 5 мм; PE-плетёнка 0,5
// ---------- Hz: ремень GT2-6 (бесконечное вращение) ----------
HZ_D = 120;                                             // габарит корпуса по кругу (R_BOX = 66)
GT2_N = 192; GT2_M = 16;                                // неподвижный шкив 192 зуба (печать), шкив мотора 16 -> ровно 1:12:
                                                        // ротор мотора всегда в той же фазе при том же Hz -> биение шкива мотора калибруется программно
GT2_PD = GT2_N*2/PI; GT2_OD = GT2_PD - 0.508;           // делительный 119,7, наружный 119,2
PULLEY = "print";                                       // print: зубья печатаются заодно с дном (соосно с гнездом трубы) | metal: венец по DXF
T_FIT = -0.05;                                          // гнездо трубы: натяг (подобрать по тестовым кольцам fit_rings), без зажимных винтов
FL_T = 1.5; PL_BOLT_R = 46; PL_BOLTS = 6;               // реборды и болты М3 венца (латунные вставки в ступице дна)
MOT_X = 73.3;                                           // ось мотора Hz: ремень замкнутый GT2-6 400 мм (200 зубьев); пазы ±2 мм — натяжение (398…402 мм)
MOT_SHAFT = 24;                                         // вал мотора от фланца (до 24 мм — без укорачивания)
// высоты (от низа дна): шкив — зубья на уровне ремня, палуба над шкивом, мотор стоит на палубе валом вниз
P_HUB = 10; P_T = 8; DECK_GAP = 6; DECK_T = 3;   // зазор палуба—реборда 5 мм: TCRT5000 сверху палубы смотрит сквозь окно
SKIRT_R = 85.5;                                         // камера ремня: кольцевая юбка под палубой (вращается), снизу — диск дна R89,5
// ---------- V ----------
V_D = 70; V_W = 14; V_TURNS = 1.6;                      // передача 70,5/6,5 = 1:10,8
AXLE_Z = 64;                                            // ось V над верхом Hz-барабана (луч вниз до -46° мимо барабана)
POD_IN = 26; POD_WALL = 6; POD_Y = 39.5;                  // внутренняя грань башен, толщина, полуширина
POD_LX = 83; POD_RX = 73;                               // наружные грани башен (лев. — мотор V, прав. — электроника)
POD_H = AXLE_Z + V_D/2 + 5;                             // высота башен (барабан V под крышкой с зазором 2,5 мм)
LID_T = 4; POD_R = 8;                                   // крышки башен, радиус наружных углов башен
HEAD_X = 18; HEAD_Y0 = -26; HEAD_Y1 = 34; HEAD_Z = 22;  // голова: полуширина, зад/перед (луч +Y), полувысота
HEAD_R = 3;                                             // скругление головы
// ---------- корпус Hz (вращается вместе с алидадой) ----------
WALL = 2.6; TOP_T = 8; GAP = 1;
H_BOX = TOP_T + MOT_L + 3;                              // высота корпуса
R_BOX = HZ_D/2 + 6;
BOX_R = 6; TOP_R = 6;                                   // углы корпуса в плане, скругление верхней кромки
MOT_M = 5.5;                                            // поле вокруг мотора Hz: скругление угла + сдвиг ±2 мм (натяжение ремня)
// ---------- встроенный аккумулятор 3S1P 21700 (в корпусе Hz, напротив мотора) + дно с 3 конусами ----------
BASE_T = 5;
CELL_D = 21.6; CELL_L = 70.5; N_CELL = 3;               // 21700 (Molicel P45B / Samsung 50S); 18650: 18.6 x 65.5
PACK_X1 = -25;                                          // ближний к оси край блока (хомут трубы Ø46)
PACK_X0 = PACK_X1 - N_CELL*CELL_D - (N_CELL - 1);       // дальний край
PACK_Y = CELL_L/2 + 5;                                  // полудлина отсека (+ никель/провода)
FOOT_D = 30; FOOT_H = 26; FOOT_BOSS = 8;
FR = 96; FEET = [for (a = [180, 60, -60]) [FR*cos(a), FR*sin(a)]];   // 3 ножки на R92 (дно неподвижно, корпус крутится над ним)
BASE_R = 89.5;                                          // диск дна (закрывает камеру ремня снизу)

module motor_holes(depth) {
    cylinder(d = 23, h = depth);
    for (x = [-15.5, 15.5], y = [-15.5, 15.5]) translate([x, y, 0]) hull() for (dx = [-1.5, 1.5]) translate([dx, 0, 0]) cylinder(d = 3.4, h = depth);
}
module helix_groove(r, turns, z0) {
    translate([0, 0, z0]) linear_extrude(height = PITCH*turns, twist = -360*turns, slices = 90*turns)
        translate([r, 0]) circle(d = CORD + 0.35, $fn = 12);
}
module hex(af, h) cylinder(d = af/cos(30), h = h, $fn = 6);

// ---------- скругления ----------
// профиль кромки: [отступ внутрь, глубина от грани]; p = «печатный» (дуга до 45° + фаска 45°, сторона на столе)
function eprof(r, p) = r <= 0 ? [[0, 0]] : concat([for (a = [0:15:(p ? 45 : 90)]) [r - r*cos(a), r - r*sin(a)]], p ? [[(2 - sqrt(2))*r, 0]] : []);
// призма из выпуклого 2D со скруглёнными верхней (rt) и нижней (rb) кромками
module rprism(h, rt = 0, rb = 0, pt = false, pb = false) hull() {
    for (q = eprof(rt, pt)) translate([0, 0, h - q[1] - 0.01]) linear_extrude(0.01) offset(delta = -q[0]) children();
    for (q = eprof(rb, pb)) translate([0, 0, q[1]]) linear_extrude(0.01) offset(delta = -q[0]) children();
}
// брусок со скруглёнными всеми рёбрами (top/bot = false — верх/низ плоские под крышку)
module rbox(p0, p1, r, top = true, bot = true) hull() for (x = [p0[0] + r, p1[0] - r], y = [p0[1] + r, p1[1] - r]) {
    if (bot) translate([x, y, p0[2] + r]) sphere(r, $fn = 32); else translate([x, y, p0[2]]) cylinder(r = r, h = 0.01, $fn = 32);
    if (top) translate([x, y, p1[2] - r]) sphere(r, $fn = 32); else translate([x, y, p1[2] - 0.01]) cylinder(r = r, h = 0.01, $fn = 32);
}
// прямоугольник 2D: радиус r0 у x0, r1 у x1
module rquad(x0, x1, y0, y1, r0, r1) hull() for (y = [y0, y1]) { s = y == y0 ? 1 : -1;
    translate([x0 + r0, y + s*r0]) circle(r0); translate([x1 - r1, y + s*r1]) circle(r1); }
// цилиндр со скруглёнными торцами
module rcyl(d, h, r) rotate_extrude() hull() { square([0.01, h]); translate([d/2 - r, r]) circle(r, $fn = 24); translate([d/2 - r, h - r]) circle(r, $fn = 24); }

// ================= КОРПУС Hz (крышка + стенки, вращается; стоит на палубе) =================
module box2d() offset(r = BOX_R) offset(delta = -BOX_R) hull() { circle(r = R_BOX); translate([MOT_X - MOT/2 - MOT_M, -MOT/2 - MOT_M]) square(MOT + 2*MOT_M);
    translate([PACK_X0 - WALL - 1, -PACK_Y - WALL]) square([PACK_X1 - PACK_X0 + WALL + 1, 2*(PACK_Y + WALL)]); }
ALI_BOLTS = [[30, 22], [30, -22], [-30, 22], [-30, -22]];   // М4: алидада -> верх корпуса
HUB_D = 48;                                             // ступица подшипников 2x6806 (вращается на неподвижной трубе)
module housing() {
    zt = H_BOX - TOP_T;
    difference() {
        union() {
            rprism(H_BOX, TOP_R, 0, true) box2d();                                               // печать верхом на стол
            cylinder(d = HUB_D, h = H_BOX);                                                       // ступица
        }
        difference() { translate([0, 0, -0.01]) linear_extrude(zt + 0.01) offset(-WALL) box2d(); cylinder(d = HUB_D, h = H_BOX); }
        translate([0, 0, -1]) cylinder(d = T_OD + 1.5, h = H_BOX + 2);                        // труба (неподвижна), зазор
        translate([0, 0, -0.01]) cylinder(d = BH_OD, h = BH_W);                               // нижний 6806
        translate([0, 0, H_BOX - BH_W]) cylinder(d = BH_OD, h = BH_W + 0.01);                // верхний 6806 (сверху держит алидада)
        for (p = ALI_BOLTS) translate([p[0], p[1], zt - 0.01]) { cylinder(d = 4.4, h = TOP_T + 5); rotate([0, 0, 30]) hex(7, 4); }   // М4 алидады, гайки в крышке снизу
        translate([45, 0, zt - 1]) cylinder(d = 14, h = TOP_T + 2);                           // провода -> правая башня (вращаются вместе)
        // питание на стенке -Y: выключатель KCD1 21x15, гнездо DC 5,5/2,1 (зарядка 12,6 В) Ø8
        translate([-12, -R_BOX - 1, 5]) cube([21, 12, 15]);
        translate([-30, -54, 13]) rotate([90, 0, 0]) cylinder(d = 8.2, h = 12);
        translate([-70, 49.6, 10]) rotate(15) translate([-15, -5, 0]) cube([30, 10, 6]);   // индикатор заряда 3S (скошенная стенка)
        translate([86, 0, H_BOX - 4]) cylinder(d = 15.5, h = 5);                             // пузырёк Ø15 (над мотором Hz, виден сверху справа)
        for (y = [-14:7:14]) translate([MOT_X + MOT/2 + 2, y, 8]) cube([10, 3, H_BOX - 16]); // вентиляция мотора
    }
    intersection() {
        for (p = boss_pts()) translate([p[0], p[1], 0]) difference() { cylinder(d = 8, h = 10); translate([0, 0, -1]) cylinder(d = 2.8, h = 9); }
        linear_extrude(H_BOX) box2d();
    }
}
function boss_pts() = [[PACK_X0 + 4, PACK_Y - 0.5], [PACK_X0 + 4, -PACK_Y + 0.5], [PACK_X1 - 4, PACK_Y + WALL + 3 - 6], [PACK_X1 - 4, -PACK_Y - WALL - 3 + 6],
                       [0, R_BOX - 6], [28, -R_BOX + 9], [MOT_X - 6, MOT/2 + 7], [MOT_X - 6, -MOT/2 - 7]];

// ================= ПАЛУБА (вращается): банки и мотор Hz сверху, под ней — закрытая камера ремня =================
// Печать верхом на стол (юбкой вверх). Мотор Hz стоит фланцем на палубе, вал вниз, шкив 16T — в камере.
Z_P0 = BASE_T + P_HUB; Z_DECK = Z_P0 + P_T + DECK_GAP;   // (от низа дна) низ зубьев шкива, низ палубы
SKIRT_H = Z_DECK - BASE_T - 1;                           // юбка до дна с зазором 1 мм
TCRT_A = -60; TCRT_R = 40;                               // нуль Hz: TCRT5000 смотрит вниз на белую метку неподвижного шкива
module deck() {
    difference() {
        union() {
            rprism(DECK_T, 1.2, 0) hull() { box2d(); circle(r = SKIRT_R, $fn = 180); }               // палуба накрывает камеру ремня целиком
            translate([0, 0, DECK_T - 0.01]) linear_extrude(2) difference() {                    // буртик-фиксатор корпуса
                offset(delta = -WALL - 0.25) box2d(); offset(delta = -WALL - 2) box2d();
                for (p = boss_pts()) translate(p) circle(d = 9); circle(d = HUB_D + 1);
                translate([MOT_X - MOT/2 - 3, -MOT/2 - 3]) square([MOT + 12, MOT + 6]); }             // без буртика у мотора (сдвиг ±2)
            for (y = [-CELL_L/2 + 12, CELL_L/2 - 12]) translate([PACK_X0, y - 4, DECK_T - 0.01]) difference() {      // ложементы банок
                cube([PACK_X1 - PACK_X0, 8, CELL_D/2 - 4]);
                for (i = [0:N_CELL - 1]) translate([CELL_D/2 + i*(CELL_D + 1), -1, CELL_D/2 + 0.6]) rotate([-90, 0, 0]) cylinder(d = CELL_D + 0.6, h = 10);
            }
            translate([0, 0, -SKIRT_H]) difference() { cylinder(r = SKIRT_R, h = SKIRT_H + 0.01, $fn = 180); translate([0, 0, -1]) cylinder(r = SKIRT_R - 2.5, h = SKIRT_H + 2, $fn = 180); }   // юбка
        }
        translate([0, 0, -SKIRT_H - 1]) cylinder(d = 37, h = SKIRT_H + DECK_T + 5);              // проставка оси (неподвижна)
        hull() for (dx = [-2, 2]) translate([MOT_X + dx, 0, -1]) cylinder(d = 23, h = DECK_T + 2);     // бобышка мотора, ступица шкива
        for (x = [-15.5, 15.5], y = [-15.5, 15.5]) hull() for (dx = [-2, 2]) translate([MOT_X + x + dx, y, -1]) cylinder(d = 3.4, h = DECK_T + 2);  // пазы М3: натяжение ремня
        rotate(TCRT_A) { translate([TCRT_R - 3.5, -6, -1]) cube([7, 12, DECK_T + 2]);            // окно: датчик TCRT5000 (модуль сверху палубы) смотрит вниз на метку
                         translate([TCRT_R + 20, 0, -1]) cylinder(d = 3.2, h = DECK_T + 2); }      // винт модуля
        for (p = boss_pts()) translate([p[0], p[1], -1]) cylinder(d = 3.4, h = DECK_T + 2);       // М3 к корпусу
        for (x = [-15:8:30]) translate([x, 30, -1]) cube([3, 22, DECK_T + 2]);                   // вентиляция (BMS)
        translate([62, -24, -SKIRT_H - 1]) cube([30, 48, SKIRT_H - 2]);                         // окно юбки: надеть ремень на 16T, проверить натяжение (закрыть алюм. скотчем)
    }
}
// ================= ДНО (неподвижно): 3 ножки, шкив GT2 188T, гнездо оси-трубы, отвес, гайка штатива 1/4" =================
// Печать плоско. Труба 30x2 вставляется в гнездо и зажимается 2 винтами М3 (латунные вставки в ступице шкива).
// профиль впадины GT2 2 мм (Parametric Pulley, droftarts): глубина 0,764, ширина 1,494
GT2_TOOTH = [[0.747183,-0.5],[0.747183,0],[0.647876,0.037218],[0.598311,0.130528],[0.578556,0.238423],[0.547158,0.343077],[0.504649,0.443762],
             [0.451556,0.53975],[0.358229,0.636924],[0.2484,0.707276],[0.127259,0.750044],[0,0.76447],[-0.127259,0.750044],[-0.2484,0.707276],
             [-0.358229,0.636924],[-0.451556,0.53975],[-0.504649,0.443762],[-0.547158,0.343077],[-0.578556,0.238423],[-0.598311,0.130528],
             [-0.647876,0.037218],[-0.747183,0],[-0.747183,-0.5]];
module gt2_2d(n) difference() { circle(d = GT2_OD, $fn = 4*n); for (k = [0:n - 1]) rotate(360*k/n) translate([0, -GT2_OD/2]) polygon(GT2_TOOTH); }
module gt2_ring(n, h) linear_extrude(h) gt2_2d(n);
// металлический венец (DXF для лазера/ЧПУ): отверстие = труба 30 мм -> венец центрируется самой осью
module pl_holes() { circle(d = T_OD + 0.25, $fn = 180); for (k = [0:PL_BOLTS - 1]) rotate(360*k/PL_BOLTS + 15) translate([PL_BOLT_R, 0]) circle(d = 3.3, $fn = 24); }
module gt2_plate_2d() difference() { gt2_2d(GT2_N); pl_holes(); }                    // 2 шт., Al 4 мм (или сталь 4 мм)
module gt2_flange_2d() difference() { circle(d = GT2_OD + 4, $fn = 360); pl_holes(); } // 2 шт., Al/сталь 1,5 мм; на верхней — белая метка нуля
module base() {
    difference() {
        union() {
            rprism(BASE_T, 0, 2, false, true) union() { circle(r = BASE_R, $fn = 180); for (f = FEET) hull() { translate(f) circle(d = 26); translate(f*0.8) circle(d = 36); } }
            for (f = FEET) translate([f[0], f[1], -FOOT_BOSS]) rprism(FOOT_BOSS + 0.01, 0, 1.5, false, true) circle(d = 22);
            if (PULLEY == "metal") translate([0, 0, BASE_T - 0.01]) cylinder(d = 2*PL_BOLT_R + 12, h = P_HUB - FL_T + 0.01, $fn = 180);   // ступица под венец
            else {
                translate([0, 0, BASE_T - 0.01]) cylinder(d = GT2_OD + 4, h = P_HUB + 0.01, $fn = 180);    // ступица шкива = нижняя реборда
                translate([0, 0, Z_P0]) gt2_ring(GT2_N, P_T);                                               // зубья под ремень 6 мм
                translate([0, 0, Z_P0 + P_T - 0.01]) cylinder(d = GT2_OD + 3, h = FL_T, $fn = 180);        // верхняя реборда
            }
        }
        translate([0, 0, 1.5]) cylinder(d = T_OD + (PULLEY == "print" ? T_FIT : 0.25), h = 50, $fn = 360);   // гнездо трубы (печать: натяг, заодно с зубьями)
        translate([0, 0, -1]) cylinder(d = 16, h = 10);                                          // ОТВЕС: луч вниз по оси
        if (PULLEY == "metal") for (a = [90, 270]) rotate(a) translate([0, 0, BASE_T + P_HUB/2]) rotate([0, 90, 0]) cylinder(d = 4.2, h = 70);   // металл: 2x М3
        translate([42, 0, -1]) cylinder(d = 6.8, h = BASE_T + P_HUB - 2); translate([42, 0, -0.01]) hex(11.2, 5);   // штатив 1/4"
        for (f = FEET) translate([f[0], f[1], -FOOT_BOSS - 1]) { cylinder(d = 8.5, h = 20); hex(13.2, 7.5); }
        if (PULLEY == "metal") for (k = [0:PL_BOLTS - 1]) rotate(360*k/PL_BOLTS + 15) translate([PL_BOLT_R, 0, BASE_T + 1]) cylinder(d = 4.2, h = P_HUB);   // вставки М3
        else rotate(TCRT_A) translate([TCRT_R - 7, -2, Z_P0 + P_T + FL_T - 0.6]) cube([14, 4, 0.61]);   // метка нуля Hz (белая, AMS) на верхней реборде
    }
}
// проставка на трубе: держит внутреннее кольцо нижнего 6806 над шкивом (неподвижна)
module spacer() difference() { rcyl(36, Z_DECK + DECK_T - (Z_P0 + P_T + FL_T), 0.8); translate([0, 0, -1]) cylinder(d = T_OD + 0.25, h = 30); }

// ================= АЛИДАДА: две закрытые башни-вилка (одна деталь = соосные подшипники V) =================
// башня в плане: s = -1 левая (мотор V), +1 правая (электроника); наружные углы R8, к голове R3
module tower2d(s) if (s < 0) rquad(-POD_LX, -POD_IN, -POD_Y, POD_Y, POD_R, 3); else rquad(POD_IN, POD_RX, -POD_Y, POD_Y, 3, POD_R);
module cav2d(s) intersection() { offset(delta = -2.4) tower2d(s);
    translate([s < 0 ? -200 : POD_IN + POD_WALL, -100]) square([s < 0 ? 200 - POD_IN - POD_WALL : 200, 200]); }
function lid_pts(s) = [for (x = s < 0 ? [-POD_LX + 6.5, -POD_IN - POD_WALL - 4] : [POD_IN + POD_WALL + 4, POD_RX - 6.5], y = [-POD_Y + 6, POD_Y - 6]) [x, y]];
module plate2d() offset(r = 4) offset(delta = -4) intersection() { circle(r = 47);   // r47: открыт доступ к кассете шнура
    translate([-POD_IN - 1, -60]) square([2*POD_IN + 2, 120]); }
module alidade() {
    mz = AXLE_Z - (V_D/2 + SHAFT_R + CORD + 0.3);       // ось мотора V
    difference() {
        union() {
            for (s = [-1, 1]) rprism(POD_H, 0, 1.5, false, true) tower2d(s);                    // башни, низ — печатная кромка
            rprism(6, 2, 1.5, false, true) plate2d();                                             // основание под головой
        }
        // полости башен (открыты сверху — крышки)
        for (s = [-1, 1]) translate([0, 0, 3]) linear_extrude(POD_H) cav2d(s);
        // 608 во внутренних стенках: гнездо со стороны полости, буртик 1 мм к голове
        for (s = [-1, 1]) translate([s*(POD_IN + POD_WALL + 0.01), 0, AXLE_Z]) rotate([0, -s*90, 0]) { cylinder(d = B_OD, h = B_W); cylinder(d = 14, h = POD_WALL + 2); }
        // центр: хомут трубы; провода из корпуса -> правая башня (вращаются вместе, ось без проводов)
        translate([0, 0, -1]) cylinder(d = 40, h = 10);
        translate([45, 0, -1]) cylinder(d = 14, h = 6);
        // кабели головы (лазер, камера CSI, MPU6050) — щель во внутренней стенке правой башни под осью
        translate([POD_IN - 1, -11, AXLE_Z - 30]) cube([POD_WALL + 2, 22, 7]);
        for (p = ALI_BOLTS) translate([p[0], p[1], -1]) { cylinder(d = 4.4, h = 20); translate([0, 0, 6]) cylinder(d = 8, h = 20); }
        // правая башня: Pi (3 или Zero 2 W) стоймя на наружной стенке, отверстия М2,5
        for (dy = [-24.5, 24.5], dz = [12, 70]) translate([POD_RX - 4, dy, dz]) rotate([0, 90, 0]) cylinder(d = 2.4, h = 6);
        for (y = [-20:8:20]) translate([POD_RX - 3, y, POD_H - 30]) cube([4, 3, 20]);           // вентиляция
        translate([-POD_LX - 1, 0, AXLE_Z]) rotate([0, 90, 0]) cylinder(d = 10, h = 6);         // шпилька М8 цапфы V вставляется СНАРУЖИ (внутри башни 48 мм < 60)
    }
    // направляющие картриджа V (левая башня): наружные — во всю высоту, внутренние — ниже барабана V
    for (sy = [-1, 1]) {
        translate([VC_X0 - 2.2, sy > 0 ? POD_Y - 2.4 - 4 : -POD_Y + 2.4, 3]) cube([2.2, 4, POD_H - 3]);
        translate([VC_X0 + VC_T + 0.4, sy > 0 ? POD_Y - 2.4 - 4 : -POD_Y + 2.4, 3]) cube([2.2, 4, AXLE_Z - V_D/2 - 8]);
    }
    // стойки винтов крышек М3 (с косынкой к стенке — печать без поддержек)
    intersection() {
        for (s = [-1, 1], p = lid_pts(s)) difference() {
            hull() { translate([p[0], p[1], POD_H - 8]) cylinder(d = 9, h = 8); translate([p[0], sign(p[1])*(POD_Y - 2.6), POD_H - 18]) cylinder(d = 9, h = 0.01); }
            translate([p[0], p[1], POD_H - 11]) cylinder(d = 2.6, h = 12);                                 // винты М3 (саморез 2,9 или вставка)
        }
        linear_extrude(POD_H) for (s = [-1, 1]) tower2d(s);
    }
}
// крышка башни: скруглённый верх (печать верхом на стол), буртик-фиксатор внутрь полости
module pod_lid(s) difference() {
    union() {
        rprism(LID_T, 3, 0, true) tower2d(s);
        translate([0, 0, -2.5]) linear_extrude(2.51) difference() { offset(delta = -0.25) cav2d(s); offset(delta = -2.05) cav2d(s); for (p = lid_pts(s)) translate(p) circle(d = 11); }
        if (s < 0) translate([VC_X0, -20, -(POD_H - VC_H - 3) - 0.01]) cube([VC_T, 40, POD_H - VC_H - 3 + 0.02]);   // прижим картриджа V
    }
    for (p = lid_pts(s)) translate([p[0], p[1], -4]) { cylinder(d = 3.2, h = 10); translate([0, 0, LID_T + 4 - 1.8]) cylinder(d = 6, h = 2); }
}

// ================= ГОЛОВА: дальномер + камера + MPU6050, окно из оргстекла 2 мм =================
// Луч (+Y) проходит через ось V (X) и ось Hz -> при V = -90° светит вниз через трубу (отвес).
module head_outer() {
    rbox([-HEAD_X, HEAD_Y0, -HEAD_Z], [HEAD_X, HEAD_Y1, HEAD_Z], HEAD_R, top = false);
    for (s = [-1, 1]) translate([s*(HEAD_X - 1), 0, 0]) rotate([0, s*90, 0]) cylinder(d = 16, h = POD_IN - HEAD_X);
}
module head() intersection() { union() {
    t = 2.4;
    difference() {
        head_outer();
        rbox([-HEAD_X + t, HEAD_Y0 + t, -HEAD_Z + t], [HEAD_X - t, HEAD_Y1 - t, HEAD_Z + 1], 1, top = false);
        for (s = [-1, 1]) translate([s*(HEAD_X - t - 0.01), 0, 0]) rotate([0, s*90, 0]) { hex(13.2, 6.6); cylinder(d = 8.4, h = 20); }   // гайки М8 цапф
        translate([-13, HEAD_Y1 - t - 1, -9]) cube([26, t + 2, 34]);                    // окно: лазер (z=0) + камера (z≈13)
        translate([-15, HEAD_Y1 - 1.6, -11]) cube([30, 2, HEAD_Z + 11.01]);              // паз под оргстекло 30x33x2 (вставляется сверху)
        for (dx = [-10.5, 10.5], dz = [13 - 6.25, 13 + 6.25]) translate([dx, HEAD_Y1 - t - 1, dz]) rotate([-90, 0, 0]) cylinder(d = 2.2, h = 5);   // Pi Camera
        translate([0, HEAD_Y0 - 1, -2]) rotate([-90, 0, 0]) cylinder(d = 9, h = 5);       // провода сзади
        translate([-9, HEAD_Y0 - 1, 5]) cube([18, 5, 2.5]);                                // шлейф CSI
    }
    // рельсы лазерного модуля (центр модуля на оси луча z=0, ширина до 26), стяжки
    difference() {
        for (x = [-13.5, 11]) translate([x, HEAD_Y0 + 14, -HEAD_Z + t - 0.3]) cube([2.5, HEAD_Y1 - HEAD_Y0 - 16, HEAD_Z - t - 6.2]);
        for (y = [HEAD_Y0 + 20, HEAD_Y1 - 10]) translate([-20, y, -HEAD_Z + 4]) cube([40, 3.5, 3]);
    }
    // MPU6050 сзади на полу (ось X датчика — по лучу), стойки крышки
    for (p = [[-6.5, HEAD_Y0 + 5], [6.5, HEAD_Y0 + 5]]) translate([p[0], p[1], -HEAD_Z + t - 0.3]) difference() { cylinder(d = 5, h = 4.3); cylinder(d = 2.2, h = 5); }
    for (p = head_pts()) translate([p[0], p[1], -HEAD_Z]) difference() { cylinder(d = 6, h = 2*HEAD_Z); cylinder(d = 2.2, h = 2*HEAD_Z + 1); }
} head_outer(); }
function head_pts() = [for (x = [-HEAD_X + 4, HEAD_X - 4], y = [HEAD_Y0 + 4, HEAD_Y1 - 6]) [x, y]];
module head2d() offset(r = HEAD_R) offset(delta = -HEAD_R) translate([-HEAD_X, HEAD_Y0]) square([2*HEAD_X, HEAD_Y1 - HEAD_Y0]);
// крышка головы: скруглённый верх (печать верхом на стол), буртик по полости, прижимает оргстекло
module head_lid() difference() {
    union() {
        rprism(2.4, 2, 0, true) head2d();
        translate([0, 0, -2]) linear_extrude(2.01) difference() { offset(delta = -2.65) head2d(); offset(delta = -4.4) head2d();
            for (p = head_pts()) translate(p) circle(d = 8); translate([-16, HEAD_Y1 - 6]) square([32, 6]); }
    }
    for (p = head_pts()) translate([p[0], p[1], -3]) { cylinder(d = 2.8, h = 6); translate([0, 0, 3 + 2.4 - 1.4]) cylinder(d = 5.5, h = 2); }
}

// ================= V: СМЕННЫЙ КАРТРИДЖ (рамка + мотор + барабан + шнур, натянут заранее на столе) =================
// Цапфа головы: шпилька М8 (в гайку головы) -> внутреннее кольцо 608 -> конус v_hub (контргайка М8 внутри) -> конус барабана -> гайка-барашек.
// Замена: снять крышку башни (4 винта) -> открутить барашек -> вынуть картридж вверх по направляющим -> вставить новый -> барашек -> крышка.
// Конус 1:4 центрирует барабан без люфта; рамка стоит в направляющих, сверху прижата крышкой; мотор V — разъём JST-XH 4.
VC_X0 = -POD_IN - POD_WALL - V_W - 6; VC_T = 4;         // рамка картриджа (на месте бывшей перегородки)
VC_H = POD_H - 6;                                       // высота рамки (над полом башни 3 мм, под крышкой — прижим)
VCONE = [26, 20.5, 10];                                 // конус: Ø у подшипника, Ø снаружи, длина
module v_cart() {
    mz = AXLE_Z - (V_D/2 + SHAFT_R + CORD + 0.3); w = 2*(POD_Y - 2.4) - 0.6;
    difference() {
        translate([0, -w/2, 3]) cube([VC_T, w, VC_H - 3]);
        translate([-1, 0, mz]) rotate([0, 90, 0]) motor_holes(VC_T + 2);
        translate([-1, 0, AXLE_Z]) rotate([0, 90, 0]) cylinder(d = 30, h = VC_T + 2);   // окно барашка
        translate([-1, 0, VC_H - 6]) rotate([0, 90, 0]) cylinder(d = 14, h = VC_T + 2);  // ручка-проём: вынимать за него
        translate([-1, -w/2 + 4, 8]) cube([VC_T + 2, 8, 12]);                             // разъём мотора
    }
}
module v_hub() difference() {                          // пакет: барашек -> барабан -> конус -> буртик -> внутр. кольцо 608 -> бобышка головы (гайка М8)
    union() { cylinder(d1 = VCONE[0], d2 = VCONE[1], h = VCONE[2]); translate([0, 0, -1.2]) cylinder(d = 12, h = 1.21); }   // буртик Ø12: только внутреннее кольцо 608
    translate([0, 0, -2]) cylinder(d = 8.4, h = VCONE[2] + 3);
}
module v_drum() difference() {
    rcyl(V_D, V_W, 1.2);
    translate([0, 0, -0.01]) cylinder(d1 = VCONE[0] + 0.3, d2 = VCONE[1] + 0.3, h = VCONE[2]);   // конусное гнездо
    translate([0, 0, -1]) cylinder(d = 8.6, h = V_W + 2);
    helix_groove(V_D/2, V_TURNS, 3);
    for (k = [0, 1]) { z = 3 + (k ? PITCH*V_TURNS : 0); a = k ? -360*V_TURNS : 0;
        rotate(a) translate([V_D/2 - 10, 0, z]) rotate([0, 90, 0]) cylinder(d = 2, h = 20);
        rotate(a) translate([V_D/2 - 16, -3, -1]) cube([6, 6, V_W + 2]); }
    for (a = [0:60:300]) rotate(a) translate([22, 0, -1]) cylinder(d = 9, h = V_W + 2);
}
module v_knob() difference() {                         // гайка-барашек М8 (гайка вплавить/вклеить)
    union() { cylinder(d = 22, h = 7, $fn = 12); cylinder(d = 14, h = 10); }
    translate([0, 0, -1]) cylinder(d = 8.4, h = 12); translate([0, 0, 3]) hex(13.2, 8);
}

// ================= ХОМУТ трубы над барабаном (преднатяг 6806) =================
module collar() difference() { rcyl(36, 8, 1.2); translate([0, 0, -1]) cylinder(d = T_OD + 0.2, h = 10);
    translate([-0.75, 0, -1]) cube([1.5, 20, 10]); translate([0, 15, 4]) rotate([0, 90, 0]) translate([0, 0, -10]) cylinder(d = 3.2, h = 20); }

// ================= НОЖКА-КОНУС (3 шт., шпилька М8 + гайка; TPU для плитки/паркета) =================
module foot() difference() {
    union() { rprism(9, 1, 1.5, false, true) circle(d = FOOT_D, $fn = 48);
        hull() { translate([0, 0, 8.99]) cylinder(d = FOOT_D - 2, h = 0.01, $fn = 48); translate([0, 0, FOOT_H - 2.5]) sphere(2.5, $fn = 24); } }   // наконечник — шарик R2,5
    translate([0, 0, -0.01]) hex(13.2, 7); translate([0, 0, -1]) cylinder(d = 8.5, h = FOOT_H - 6);
    for (a = [0:30:330]) rotate(a) translate([FOOT_D/2 + 1, 0, -1]) cylinder(d = 3, h = 11);
}

// ================= СБОРКА =================
Z_BASE = FOOT_H - 8 + FOOT_BOSS;                        // низ дна над полом (конус накручен на 8 мм)
Z_DK = Z_BASE + Z_DECK;                                 // низ палубы
Z_HS = Z_DK + DECK_T;                                   // верх палубы = низ корпуса
Z_TOP = Z_HS + H_BOX;                                   // верх корпуса = низ алидады
module assembly(v = 0, hz = 0) {
    color("dimgray") translate([0, 0, Z_BASE]) base();
    for (f = FEET) color("black") translate([f[0], f[1], Z_BASE - FOOT_BOSS + 8]) mirror([0, 0, 1]) foot();
    color("silver") translate([0, 0, Z_BASE + 1.5]) difference() { cylinder(d = T_OD, h = Z_TOP + 8 - Z_BASE - 1.5); translate([0, 0, -1]) cylinder(d = T_ID, h = 200); }
    color("silver") translate([0, 0, Z_BASE + Z_P0 + P_T + FL_T]) spacer();
    if (PULLEY == "metal") color("lightsteelblue") translate([0, 0, Z_BASE + Z_P0 - FL_T]) gt2_pulley_metal();
    rotate(hz) {
        color("gray") translate([0, 0, Z_DK]) deck();
        color("gray") translate([0, 0, Z_HS]) housing();
        for (i = [0:N_CELL - 1]) color("royalblue") translate([PACK_X0 + CELL_D/2 + i*(CELL_D + 1), -CELL_L/2, Z_HS + CELL_D/2 + 0.6]) rotate([-90, 0, 0]) cylinder(d = CELL_D, h = CELL_L);
        color("black") translate([MOT_X - MOT/2, -MOT/2, Z_HS]) cube([MOT, MOT, MOT_L]);
        color("goldenrod") translate([MOT_X, 0, Z_BASE + Z_P0 - 1]) cylinder(d = 13, h = P_T + 2);       // шкив 16T
        color("darkslategray") translate([0, 0, Z_BASE + Z_P0 + 1]) linear_extrude(6) belt2d();
        translate([0, 0, Z_TOP]) {
            color("silver") collar();
            color("steelblue") alidade();
            for (s = [-1, 1]) color("steelblue", 0.6) translate([0, 0, POD_H]) pod_lid(s);
            translate([0, 0, AXLE_Z]) rotate([v, 0, 0]) { color("white") head(); color("white") translate([0, 0, HEAD_Z]) head_lid(); }
            color("orange") translate([-POD_IN - POD_WALL - 1, 0, AXLE_Z]) rotate([0, -90, 0]) v_drum();
            color("silver") translate([-POD_IN - POD_WALL - 1, 0, AXLE_Z]) rotate([0, -90, 0]) v_hub();
            color("dimgray") translate([-POD_IN - POD_WALL - 1 - V_W, 0, AXLE_Z]) rotate([0, -90, 0]) v_knob();   // торец барашка — на барабан (через окно рамки)
            color("tan") translate([VC_X0, 0, 0]) v_cart();
            color("black") translate([VC_X0 - MOT_L, -MOT/2, AXLE_Z - (V_D/2 + SHAFT_R + CORD + 0.3) - MOT/2]) cube([MOT_L, MOT, MOT]);
        }
    }
}
module gt2_pulley_metal() {                              // для сборки/картинок: реборда + 2 венца + реборда
    linear_extrude(FL_T) gt2_flange_2d(); translate([0, 0, FL_T]) linear_extrude(P_T) gt2_plate_2d(); translate([0, 0, FL_T + P_T]) linear_extrude(FL_T) gt2_flange_2d();
}
module belt2d() difference() {                         // ремень (для картинки): огибающая двух шкивов
    hull() { circle(d = GT2_PD + 1.5, $fn = 120); translate([MOT_X, 0]) circle(d = 16*2/PI + 1.5); }
    hull() { circle(d = GT2_PD - 0.5, $fn = 120); translate([MOT_X, 0]) circle(d = 16*2/PI - 0.5); }
}
echo(BEAM_H = Z_TOP + AXLE_Z, Z_BASE = Z_BASE, Z_DK = Z_DK, Z_TOP = Z_TOP, POD_H = POD_H, TOTAL_H = Z_TOP + POD_H + LID_T, SHAFT_END = Z_HS - MOT_SHAFT, BASE_TOP = Z_BASE + BASE_T);

if (part == "base") base();
else if (part == "spacer") spacer();
else if (part == "deck") deck();
else if (part == "housing") housing();
else if (part == "alidade") alidade();
else if (part == "pod_lid_l") pod_lid(-1);
else if (part == "pod_lid_r") pod_lid(1);
else if (part == "head") head();
else if (part == "head_lid") head_lid();
else if (part == "v_cart") v_cart();
else if (part == "v_hub") v_hub();
else if (part == "v_drum") v_drum();
else if (part == "v_knob") v_knob();
else if (part == "collar") collar();
else if (part == "foot") foot();
else if (part == "down") assembly(-90);
else if (part == "vis_belt") linear_extrude(6) belt2d();                     // только для картинок
else if (part == "vis_motor") { translate([MOT_X - MOT/2, -MOT/2, 0]) cube([MOT, MOT, MOT_L]); translate([MOT_X, 0, -MOT_SHAFT]) cylinder(d = 5, h = MOT_SHAFT); translate([MOT_X, 0, -(Z_HS - Z_BASE - Z_P0) - 1]) cylinder(d = 13, h = P_T + 2); }
else if (part == "gt2_plate_2d") gt2_plate_2d();       // -> DXF: openscad -D 'part="gt2_plate_2d"' -o gt2_188_plate.dxf station.scad
else if (part == "gt2_flange_2d") gt2_flange_2d();
else if (part == "pulley_metal") { gt2_pulley_metal(); }
else if (part == "fit_rings") for (i = [0:3]) translate([i*40, 0, 0]) difference() {   // подбор натяга трубы: Ø-0,15 / -0,05 / +0,05 / +0,15
    cylinder(d = 38, h = 6); translate([0, 0, -1]) cylinder(d = T_OD - 0.15 + 0.1*i, h = 8, $fn = 360);
    for (k = [0:i]) rotate(90*k) translate([17.5, -1, 4]) cube([3, 2, 3]); }
else if (part == "target_cyl") difference() {          // цилиндр-марка Ø100 x 250 (печать белым матовым, 3 шт.): гайка 1/4" снизу — на стойку/штатив
    union() { cylinder(d = 100, h = 250, $fn = 360); }
    translate([0, 0, 3]) cylinder(d = 96, h = 244, $fn = 180);                        // стенка 2 мм, крышка и дно 3 мм — острая верхняя кромка
    translate([0, 0, -1]) cylinder(d = 6.8, h = 5); translate([0, 0, -0.01]) hex(11.2, 5.2);   // 1/4"-20 (фотостойка); на полу — просто ставить
}
else if (part == "target_mini") difference() {         // мини-марка Ø50 x 70 (3 шт. в кейс): гайка 1/4" снизу + лапка под струбцину/скотч
    union() { cylinder(d = 50, h = 70, $fn = 360); translate([-3, -25 - 30, 0]) cube([6, 30, 30]); }
    translate([0, 0, 3]) cylinder(d = 46, h = 64, $fn = 180);                          // стенка 2, крышка 3 мм — острая верхняя кромка
    translate([0, 0, -1]) cylinder(d = 6.8, h = 5); translate([0, 0, -0.01]) hex(11.2, 5.2);
}
else if (part == "none") {}
else assembly();
