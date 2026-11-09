
include <../cad/station.scad>   // openscad -D part=\"none\" -D t=1..7 -o out.stl check_interference.scad ; пусто = нет столкновений
mz = AXLE_Z - (V_D/2 + SHAFT_R + CORD + 0.3);
module cells() for (i = [0:N_CELL - 1]) translate([PACK_X0 + CELL_D/2 + i*(CELL_D + 1), -CELL_L/2 - 2, CELL_D/2 + 0.6]) rotate([-90, 0, 0]) cylinder(d = CELL_D, h = CELL_L + 4);
module motHz() translate([MOT_X - MOT/2, -MOT/2, H_BOX - TOP_T - MOT_L]) cube([MOT, MOT, MOT_L]);
if (t == 1) intersection() { housing(); cells(); }
if (t == 2) intersection() { housing(); motHz(); }
if (t == 3) intersection() { union() { alidade(); for (s = [-1, 1]) translate([0, 0, POD_H]) pod_lid(s); } translate([-POD_IN - POD_WALL - 1, 0, AXLE_Z]) rotate([0, -90, 0]) cylinder(d = V_D + 1, h = V_W); }
if (t == 4) intersection() { alidade(); for (v = [-90, -45, 0, 45, 90]) translate([0, 0, AXLE_Z]) rotate([v, 0, 0]) head(); }
if (t == 5) intersection() { translate([0, 0, -BASE_T]) base(); housing(); }
if (t == 6) intersection() { alidade(); translate([-POD_IN - POD_WALL - V_W - 6 - MOT_L, -MOT/2, mz - MOT/2]) cube([MOT_L, MOT, MOT]); }
if (t == 7) intersection() { translate([0, 0, AXLE_Z + HEAD_Z]) head_lid(); translate([0, 0, AXLE_Z]) head(); }
