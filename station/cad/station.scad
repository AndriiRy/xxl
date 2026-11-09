// Компактная полярная станция «как DISTO 3D»: голова по центру в вилке из двух закрытых башен,
// полая ось Hz (лазерный отвес вниз), тросиковый (capstan) привод, аккумулятор Festool 18V снизу.
// Принтер: Bambu Lab P1S (256x256x256). PETG/PETG-HF, сопло 0,4, слой 0,2, 4 периметра, гироид 30-40 %.
// Экспорт: openscad -D 'part="alidade"' -o alidade.stl station.scad
// part: base | housing | hz_drum | alidade | pod_lid_l | pod_lid_r | head | head_lid | v_drum | collar | foot | assembly
part  = "assembly";
$fn = 96;

// ---------- покупное ----------
B_OD = 22.15; B_W = 7;                 // 608 (ось V)
T_OD = 30.0;  T_ID = 26;               // ось Hz: алюминиевая труба 30x2
BH_OD = 42.15; BH_W = 7;               // 6806-2RS (30x42x7) — 2 шт в Hz-барабане
MOT = 42.3; MOT_L = 23;                // NEMA17 «блинчик» 17HS4023 (23 мм); обычный — MOT_L = 40
SHAFT_R = 3.0; CORD = 0.5; PITCH = 1.2;// латунная втулка 6x0,5 на валу 5 мм; PE-плетёнка 0,5
// ---------- Hz ----------
HZ_D = 120; HZ_H = 22; HZ_TURNS = 2.5; HZ_G0 = 4;      // передача 120,5/6,5 = 1:18,5
MOT_X = HZ_D/2 + SHAFT_R + CORD + 0.3;                  // ось мотора Hz
// ---------- V ----------
V_D = 70; V_W = 14; V_TURNS = 1.6;                      // передача 70,5/6,5 = 1:10,8
AXLE_Z = 64;                                            // ось V над верхом Hz-барабана (луч вниз до -46° мимо барабана)
POD_IN = 26; POD_WALL = 6; POD_Y = 32;                  // внутренняя грань башен, толщина, полуширина
POD_LX = 83; POD_RX = 73;                               // наружные грани башен (лев. — мотор V, прав. — электроника)
POD_H = AXLE_Z + 34;                                    // высота башен
HEAD_X = 18; HEAD_Y0 = -26; HEAD_Y1 = 34; HEAD_Z = 22;  // голова: полуширина, зад/перед (луч +Y), полувысота
// ---------- корпус Hz (неподвижный) ----------
WALL = 2.6; TOP_T = 8; GAP = 1;
H_BOX = TOP_T + MOT_L + 3;                              // высота корпуса
R_BOX = HZ_D/2 + 6;
// ---------- встроенный аккумулятор 3S1P 21700 (в корпусе Hz, напротив мотора) + дно с 3 конусами ----------
BASE_T = 5;
CELL_D = 21.6; CELL_L = 70.5; N_CELL = 3;               // 21700 (Molicel P45B / Samsung 50S); 18650: 18.6 x 65.5
PACK_X1 = -25;                                          // ближний к оси край блока (хомут трубы Ø46)
PACK_X0 = PACK_X1 - N_CELL*CELL_D - (N_CELL - 1);       // дальний край
PACK_Y = CELL_L/2 + 5;                                  // полудлина отсека (+ никель/провода)
FOOT_D = 30; FOOT_H = 26; FOOT_BOSS = 8;
FEET = [[40, 68], [40, -68], [-98, 0]];                 // опоры (com.py): 198x160, опрокидывание при 25°

module motor_holes(depth) {
    cylinder(d = 23, h = depth);
    for (x = [-15.5, 15.5], y = [-15.5, 15.5]) translate([x, y, 0]) hull() for (dx = [-1.5, 1.5]) translate([dx, 0, 0]) cylinder(d = 3.4, h = depth);
}
module helix_groove(r, turns, z0) {
    translate([0, 0, z0]) linear_extrude(height = PITCH*turns, twist = -360*turns, slices = 90*turns)
        translate([r, 0]) circle(d = CORD + 0.35, $fn = 12);
}
module hex(af, h) cylinder(d = af/cos(30), h = h, $fn = 6);

// ================= КОРПУС Hz (крышка + стенки, открыт снизу) =================
module box2d(o = 0) hull() { circle(r = R_BOX + o); translate([MOT_X - MOT/2 - 3 - o, -MOT/2 - 3 - o]) square([MOT + 6 + 2*o, MOT + 6 + 2*o]);
    translate([PACK_X0 - WALL - 0.5 - o, -PACK_Y - WALL - o]) square([PACK_X1 - PACK_X0 + WALL + 0.5 + 2*o, 2*(PACK_Y + WALL + o)]); }
module housing() {
    zt = H_BOX - TOP_T;
    difference() {
        union() {
            linear_extrude(H_BOX) box2d();
            translate([0, 0, zt - 16]) cylinder(d = 46, h = 16);                              // хомут трубы
            translate([0, 0, H_BOX]) cylinder(d = 34, h = GAP);                                // упор внутр. кольца 6806
        }
        translate([0, 0, -0.01]) linear_extrude(zt + 0.01) offset(-WALL) box2d();
        translate([0, 0, -1]) cylinder(d = T_OD + 0.25, h = H_BOX + 5);                       // труба оси
        for (a = [90, 270]) rotate(a) translate([0, 0, zt - 8]) rotate([0, 90, 0]) {        // 2 x М4 зажим трубы
            cylinder(d = 4.4, h = 30); translate([0, 0, 18]) rotate([0, 0, 30]) hex(7, 3.4);
            translate([-3.5, -4, 18]) cube([20, 8, 3.4]); }
        translate([MOT_X, 0, zt - 1]) motor_holes(TOP_T + 2);
        // нуль Hz: TCRT5000 снизу крышки, окно 11x7 смотрит на белую метку барабана (зазор 1 мм)
        rotate(-60) translate([HZ_D/2 - 12, 0, zt - 1]) translate([-5.5, -3.5, 0]) cube([11, 7, TOP_T + 2]);
        rotate(-60) translate([HZ_D/2 - 12 - 22, 0, zt - 1]) cylinder(d = 3.2, h = 6);                  // винт М3 модуля
        // питание на стенке -Y: выключатель KCD1 21x15, гнездо DC 5,5/2,1 (зарядка 12,6 В) Ø8
        translate([-12, -R_BOX - 1, 4]) cube([21, 12, 15]);
        translate([-30, -54, 12]) rotate([90, 0, 0]) cylinder(d = 8.2, h = 12);
        // индикатор заряда 3S (4 светодиода): окно 30x6 на стенке отсека (+Y), модуль на клей изнутри
        translate([PACK_X0 + 8, PACK_Y + WALL - 2.6, 9]) cube([30, 5, 6]);
        translate([-R_BOX + 14, R_BOX - 20, H_BOX - 4]) cylinder(d = 15.5, h = 5);           // пузырёк Ø15
        for (y = [-14:7:14]) translate([MOT_X + MOT/2, y, 8]) cube([10, 3, H_BOX - 16]);     // вентиляция
    }
    for (p = boss_pts()) translate([p[0], p[1], 0]) difference() { cylinder(d = 8, h = 10); translate([0, 0, -1]) cylinder(d = 2.8, h = 9); }
}
function boss_pts() = [[PACK_X0 + 4, PACK_Y - 0.5], [PACK_X0 + 4, -PACK_Y + 0.5], [PACK_X1 - 4, PACK_Y + WALL + 3 - 6], [PACK_X1 - 4, -PACK_Y - WALL - 3 + 6],
                       [0, R_BOX - 6], [28, -R_BOX + 9], [MOT_X + MOT/2 - 2, MOT/2 - 2], [MOT_X + MOT/2 - 2, -MOT/2 + 2]];

// ================= ДНО: ложементы банок, 3 конуса, отвес, гайка штатива 1/4" =================
// Печать плоско. Банки — на 2 ложементах + двусторонний скотч/вспененная лента, сверху прижимает крышка корпуса.
module base() {
    difference() {
        union() {
            linear_extrude(BASE_T) offset(-WALL - 0.3) box2d();
            for (f = FEET) hull() { translate([f[0], f[1], 0]) cylinder(d = 24, h = BASE_T); translate([f[0]*0.7, f[1]*0.7, 0]) cylinder(d = 30, h = BASE_T); }
            for (f = FEET) translate([f[0], f[1], -FOOT_BOSS]) cylinder(d = 22, h = FOOT_BOSS + 0.01);
            for (y = [-CELL_L/2 + 12, CELL_L/2 - 12]) translate([PACK_X0, y - 4, BASE_T - 0.01]) difference() {      // ложементы
                cube([PACK_X1 - PACK_X0, 8, CELL_D/2 - 4]);
                for (i = [0:N_CELL - 1]) translate([PACK_X0*0 + CELL_D/2 + i*(CELL_D + 1), -1, CELL_D/2 + 0.6]) rotate([-90, 0, 0]) cylinder(d = CELL_D + 0.6, h = 10);
            }
        }
        for (p = boss_pts()) translate([p[0], p[1], -1]) { cylinder(d = 3.4, h = BASE_T + 2); cylinder(d = 6.5, h = 3.2); }
        translate([0, 0, -1]) cylinder(d = 16, h = BASE_T + 2);                                // ОТВЕС: луч вниз по оси
        translate([42, 0, -1]) cylinder(d = 6.8, h = BASE_T + 2);                              // штатив 1/4"
        translate([42, 0, BASE_T - 4]) hex(11.2, 5);
        for (f = FEET) translate([f[0], f[1], -FOOT_BOSS - 1]) { cylinder(d = 8.5, h = 20); hex(13.2, 7.5); }
        for (x = [-15:8:30]) translate([x, 30, -1]) cube([3, 22, BASE_T + 2]);                 // вентиляция (BMS)
    }
}

// ================= Hz-БАРАБАН (2 x 6806 на трубе) =================
module hz_drum() {
    difference() {
        cylinder(d = HZ_D, h = HZ_H);
        translate([0, 0, -0.01]) cylinder(d = BH_OD, h = BH_W);
        translate([0, 0, HZ_H - BH_W]) cylinder(d = BH_OD, h = BH_W + 0.01);
        translate([0, 0, -1]) cylinder(d = 36, h = HZ_H + 2);
        helix_groove(HZ_D/2, HZ_TURNS, HZ_G0);
        for (k = [0, 1]) { z = HZ_G0 + (k ? PITCH*HZ_TURNS : 0); a = k ? -360*HZ_TURNS : 0;
            rotate(a) translate([HZ_D/2 - 12, 0, z]) rotate([0, 90, 0]) cylinder(d = 2, h = 20);
            rotate(a) translate([HZ_D/2 - 19, -3, -1]) cube([7, 6, HZ_H + 2]); }
        for (p = ALI_BOLTS) translate([p[0], p[1], -1]) { cylinder(d = 4.4, h = HZ_H + 2); rotate([0, 0, 30]) hex(7, 4.5); }
        rotate(-60) translate([HZ_D/2 - 19, -2, -0.01]) cube([14, 4, 0.6]);                   // метка нуля Hz: белая вставка (AMS) или белая краска
        for (a = [30, 150, 210, 330]) rotate(a) translate([40, 0, HZ_G0 + 6]) cylinder(d = 18, h = HZ_H);
    }
}
ALI_BOLTS = [[30, 22], [30, -22], [-30, 22], [-30, -22]];

// ================= АЛИДАДА: две закрытые башни-вилка (одна деталь = соосные подшипники V) =================
module alidade() {
    mz = AXLE_Z - (V_D/2 + SHAFT_R + CORD + 0.3);       // ось мотора V
    difference() {
        union() {
            translate([-POD_LX, -POD_Y, 0]) cube([POD_LX - POD_IN, 2*POD_Y, POD_H]);             // левая башня
            translate([POD_IN, -POD_Y, 0]) cube([POD_RX - POD_IN, 2*POD_Y, POD_H]);              // правая башня
            intersection() { cylinder(r = 52, h = 6); translate([-POD_IN - 1, -60, 0]) cube([2*POD_IN + 2, 120, 6]); } // основание под головой
            translate([-POD_IN - 1, -POD_Y, 0]) cube([2*POD_IN + 2, 2*POD_Y, 6]);
        }
        // полости башен (открыты сверху — крышки)
        translate([-POD_LX + 2.4, -POD_Y + 2.4, 3]) cube([POD_LX - POD_IN - POD_WALL - 2.4, 2*POD_Y - 4.8, POD_H]);
        translate([POD_IN + POD_WALL, -POD_Y + 2.4, 3]) cube([POD_RX - POD_IN - POD_WALL - 2.4, 2*POD_Y - 4.8, POD_H]);
        // 608 во внутренних стенках: гнездо со стороны полости, буртик 1 мм к голове
        for (s = [-1, 1]) translate([s*(POD_IN + POD_WALL + 0.01), 0, AXLE_Z]) rotate([0, -s*90, 0]) { cylinder(d = B_OD, h = B_W); cylinder(d = 14, h = POD_WALL + 2); }
        // мотор V: фланец на внутренней перегородке левой башни (вал к барабану V)
        translate([-POD_IN - POD_WALL - V_W - 5 - 0.01, 0, mz]) rotate([0, -90, 0]) motor_holes(5);
        // центр: труба/хомут, провода из трубы -> в правую башню (канал в основании)
        translate([0, 0, -1]) cylinder(d = 40, h = 10);
        translate([0, -7, 1]) cube([POD_IN + POD_WALL + 3, 14, 4]);
        // кабели головы (лазер, камера CSI, MPU6050) — щель во внутренней стенке правой башни под осью
        translate([POD_IN - 1, -11, AXLE_Z - 30]) cube([POD_WALL + 2, 22, 7]);
        for (p = ALI_BOLTS) translate([p[0], p[1], -1]) { cylinder(d = 4.4, h = 20); translate([0, 0, 6]) cylinder(d = 8, h = 20); }
        // винты крышек
        for (x = [-POD_LX + 6, -POD_IN - POD_WALL - 4, POD_IN + POD_WALL + 4, POD_RX - 6], y = [-POD_Y + 5, POD_Y - 5]) translate([x, y, POD_H - 10]) cylinder(d = 2.6, h = 11);
        // правая башня: Pi (3 или Zero 2 W) стоймя на наружной стенке, отверстия М2,5
        for (dy = [-24.5, 24.5], dz = [12, 70]) translate([POD_RX - 4, dy, dz]) rotate([0, 90, 0]) cylinder(d = 2.4, h = 6);
        for (y = [-20:8:20]) translate([POD_RX - 3, y, POD_H - 30]) cube([4, 3, 20]);           // вентиляция
    }
    // перегородка мотора V (левая башня), стойки винтов крышек
    difference() {
        translate([-POD_IN - POD_WALL - V_W - 5, -POD_Y + 1.5, 1]) cube([4, 2*POD_Y - 3, mz + MOT/2 + 2]);
        translate([-POD_IN - POD_WALL - V_W - 6, 0, mz]) rotate([0, 90, 0]) motor_holes(7);
    }
}
module pod_lid(w) difference() {
    union() { cube([w, 2*POD_Y, 2.4]); translate([2.6, 2.6, -3]) cube([w - 5.2, 2*POD_Y - 5.2, 3]); }
    for (x = [6, w - 6], y = [5, 2*POD_Y - 5]) translate([x, y, -4]) cylinder(d = 3.2, h = 8);
}

// ================= ГОЛОВА: дальномер + камера + MPU6050, окно из оргстекла 2 мм =================
// Луч (+Y) проходит через ось V (X) и ось Hz -> при V = -90° светит вниз через трубу (отвес).
module head() {
    t = 2.4;
    difference() {
        union() {
            translate([-HEAD_X, HEAD_Y0, -HEAD_Z]) cube([2*HEAD_X, HEAD_Y1 - HEAD_Y0, 2*HEAD_Z]);
            for (s = [-1, 1]) translate([s*HEAD_X, 0, 0]) rotate([0, s*90, 0]) cylinder(d = 16, h = POD_IN - HEAD_X - 1);
        }
        translate([-HEAD_X + t, HEAD_Y0 + t, -HEAD_Z + t]) cube([2*HEAD_X - 2*t, HEAD_Y1 - HEAD_Y0 - 2*t, 2*HEAD_Z + 1]);
        for (s = [-1, 1]) translate([s*(HEAD_X - t - 0.01), 0, 0]) rotate([0, s*90, 0]) { hex(13.2, 6.6); cylinder(d = 8.4, h = 20); }   // гайки М8 цапф
        translate([-14, HEAD_Y1 - t - 1, -9]) cube([28, t + 2, 34]);                    // окно: лазер (z=0) + камера (z=16)
        translate([-16, HEAD_Y1 - 1.6, -11]) cube([32, 2, 38]);                           // паз под оргстекло 32x38x2
        for (dx = [-10.5, 10.5], dz = [16 - 6.25, 16 + 6.25]) translate([dx, HEAD_Y1 - t - 1, dz]) rotate([-90, 0, 0]) cylinder(d = 2.2, h = 5);   // Pi Camera
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
    for (x = [-HEAD_X + 4, HEAD_X - 4], y = [HEAD_Y0 + 4, HEAD_Y1 - 6]) translate([x, y, -HEAD_Z]) difference() { cylinder(d = 6, h = 2*HEAD_Z); cylinder(d = 2.2, h = 2*HEAD_Z + 1); }
}
module head_lid() difference() {
    union() { translate([-HEAD_X, HEAD_Y0, 0]) cube([2*HEAD_X, HEAD_Y1 - HEAD_Y0, 2]); translate([-HEAD_X + 2.6, HEAD_Y0 + 2.6, -2]) cube([2*HEAD_X - 5.2, HEAD_Y1 - HEAD_Y0 - 5.2, 2]); }
    for (x = [-HEAD_X + 4, HEAD_X - 4], y = [HEAD_Y0 + 4, HEAD_Y1 - 6]) translate([x, y, -3]) cylinder(d = 2.8, h = 6);
}

// ================= V-БАРАБАН (на болте М8 левой цапфы, зажат через внутреннее кольцо 608) =================
module v_drum() difference() {
    cylinder(d = V_D, h = V_W);
    translate([0, 0, -1]) cylinder(d = 8.4, h = V_W + 2);
    translate([0, 0, V_W - 5]) hex(13.2, 6);                                                    // головка болта
    helix_groove(V_D/2, V_TURNS, 3);
    for (k = [0, 1]) { z = 3 + (k ? PITCH*V_TURNS : 0); a = k ? -360*V_TURNS : 0;
        rotate(a) translate([V_D/2 - 10, 0, z]) rotate([0, 90, 0]) cylinder(d = 2, h = 20);
        rotate(a) translate([V_D/2 - 16, -3, -1]) cube([6, 6, V_W + 2]); }
    for (a = [0:60:300]) rotate(a) translate([20, 0, -1]) cylinder(d = 10, h = V_W + 2);
}

// ================= ХОМУТ трубы над барабаном (преднатяг 6806) =================
module collar() difference() { cylinder(d = 36, h = 8); translate([0, 0, -1]) cylinder(d = T_OD + 0.2, h = 10);
    translate([-0.75, 0, -1]) cube([1.5, 20, 10]); translate([0, 15, 4]) rotate([0, 90, 0]) translate([0, 0, -10]) cylinder(d = 3.2, h = 20); }

// ================= НОЖКА-КОНУС (3 шт., шпилька М8 + гайка; TPU для плитки/паркета) =================
module foot() difference() {
    union() { cylinder(d = FOOT_D, h = 9, $fn = 24); translate([0, 0, 9]) cylinder(d1 = FOOT_D - 2, d2 = 3, h = FOOT_H - 9); }
    translate([0, 0, -0.01]) hex(13.2, 7); translate([0, 0, -1]) cylinder(d = 8.5, h = FOOT_H - 6);
    for (a = [0:30:330]) rotate(a) translate([FOOT_D/2 + 1, 0, -1]) cylinder(d = 3, h = 11);
}

// ================= СБОРКА =================
Z_BASE = FOOT_H - 8 + FOOT_BOSS;                        // низ дна над полом (конус накручен на 8 мм)
Z_DRUM = Z_BASE + BASE_T + H_BOX + GAP;                 // низ Hz-барабана
Z_TOP = Z_DRUM + HZ_H;                                  // верх барабана (основание алидады)
module assembly(v = 0) {
    color("dimgray") translate([0, 0, Z_BASE]) base();
    color("gray") translate([0, 0, Z_BASE + BASE_T]) housing();
    for (i = [0:N_CELL - 1]) color("royalblue") translate([PACK_X0 + CELL_D/2 + i*(CELL_D + 1), -CELL_L/2, Z_BASE + BASE_T + CELL_D/2 + 0.6]) rotate([-90, 0, 0]) cylinder(d = CELL_D, h = CELL_L);
    for (f = FEET) color("black") translate([f[0], f[1], Z_BASE - FOOT_BOSS + 8]) mirror([0, 0, 1]) foot();
    color("black") translate([MOT_X - MOT/2, -MOT/2, Z_BASE + BASE_T + H_BOX - TOP_T - MOT_L]) cube([MOT, MOT, MOT_L]);
    color("silver") translate([0, 0, Z_BASE + BASE_T + H_BOX - TOP_T - 16]) difference() { cylinder(d = T_OD, h = 16 + TOP_T + GAP + HZ_H + 8); translate([0, 0, -1]) cylinder(d = T_ID, h = 99); }
    color("orange") translate([0, 0, Z_DRUM]) hz_drum();
    translate([0, 0, Z_TOP]) {
        color("silver") collar();
        color("steelblue") alidade();
        color("steelblue", 0.6) translate([-POD_LX, -POD_Y, POD_H]) pod_lid(POD_LX - POD_IN);
        color("steelblue", 0.6) translate([POD_IN, -POD_Y, POD_H]) pod_lid(POD_RX - POD_IN);
        translate([0, 0, AXLE_Z]) rotate([v, 0, 0]) { color("white") head(); color("white") translate([0, 0, HEAD_Z]) head_lid(); }
        color("orange") translate([-POD_IN - POD_WALL - 1, 0, AXLE_Z]) rotate([0, -90, 0]) v_drum();
        color("black") translate([-POD_IN - POD_WALL - V_W - 5 - MOT_L, -MOT/2, AXLE_Z - (V_D/2 + SHAFT_R + CORD + 0.3) - MOT/2]) cube([MOT_L, MOT, MOT]);
    }
}
echo(BEAM_H = Z_TOP + AXLE_Z, Z_BASE = Z_BASE, TOTAL_H = Z_TOP + POD_H + 2.4);

if (part == "base") base();
else if (part == "housing") housing();
else if (part == "hz_drum") hz_drum();
else if (part == "alidade") alidade();
else if (part == "pod_lid_l") pod_lid(POD_LX - POD_IN);
else if (part == "pod_lid_r") pod_lid(POD_RX - POD_IN);
else if (part == "head") head();
else if (part == "head_lid") head_lid();
else if (part == "v_drum") v_drum();
else if (part == "collar") collar();
else if (part == "foot") foot();
else if (part == "down") assembly(-90);
else assembly();
