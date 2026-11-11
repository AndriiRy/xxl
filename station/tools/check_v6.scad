// openscad -D part=\"none\" -D t=1..5 -o out.stl check_v6.scad ; пусто = нет столкновений
include <../cad/station.scad>
mzV = AXLE_Z - (V_D/2 + SHAFT_R + CORD + 0.3);
module fixed() { translate([0, 0, Z_BASE]) base(); translate([0, 0, Z_BASE + Z_P0 + P_T + FL_T]) spacer(); translate([0, 0, Z_BASE + Z_P0 - FL_T]) gt2_pulley_metal();
    translate([0, 0, Z_BASE + 1.5]) difference() { cylinder(d = T_OD, h = Z_TOP + 8 - Z_BASE - 1.5); translate([0, 0, -1]) cylinder(d = T_ID, h = 200); } }
module rot() { translate([0, 0, Z_DK]) deck(); translate([0, 0, Z_HS]) housing();
    translate([MOT_X, 0, Z_HS - MOT_SHAFT]) cylinder(d = 5, h = MOT_SHAFT); translate([MOT_X, 0, Z_BASE + Z_P0 - 1]) cylinder(d = 16, h = P_T + 2); }
module cells() for (i = [0:N_CELL - 1]) translate([PACK_X0 + CELL_D/2 + i*(CELL_D + 1), -CELL_L/2 - 2, Z_HS + CELL_D/2 + 0.6]) rotate([-90, 0, 0]) cylinder(d = CELL_D, h = CELL_L + 4);
module vset() { translate([-POD_IN - POD_WALL - 1, 0, AXLE_Z]) rotate([0, -90, 0]) { v_drum(); v_hub(); }
    translate([VC_X0 - 1, 0, AXLE_Z]) rotate([0, -90, 0]) v_knob(); translate([VC_X0 - MOT_L, -MOT/2, mzV - MOT/2]) cube([MOT_L, MOT, MOT]); }
if (t == 1) intersection() { fixed(); for (a = [0:30:330]) rotate(a) rot(); }
if (t == 2) intersection() { cells(); union() { translate([0, 0, Z_DK]) deck(); translate([0, 0, Z_HS]) housing(); } }
if (t == 3) intersection() { alidade(); union() { vset(); translate([VC_X0, 0, 0]) v_cart(); } }
if (t == 4) intersection() { translate([VC_X0, 0, 0]) v_cart(); union() { translate([-POD_IN - POD_WALL - 1, 0, AXLE_Z]) rotate([0, -90, 0]) v_drum(); translate([VC_X0 - 1, 0, AXLE_Z]) rotate([0, -90, 0]) v_knob(); } }
if (t == 5) intersection() { for (dx = [-2, 0, 2]) translate([MOT_X - MOT/2 + dx, -MOT/2, Z_HS + 0.01]) cube([MOT, MOT, MOT_L]); union() { translate([0, 0, Z_DK]) deck(); translate([0, 0, Z_HS]) housing(); } }
if (t == 6) intersection() { translate([0, 0, Z_TOP]) alidade(); translate([0, 0, Z_HS]) housing(); }
