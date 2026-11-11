"""Тест выноса проекта (как Leica iCON) на виртуальной кухне.
python3 t4.py <station/pi> <папка>
1) скан S1 + 3 опорные марки; 2) DXF проекта: развёртка стены (отверстия под навесные шкафы, линия 900),
план (точки на полу и потолке), стены проекта со сдвигом одной стены на 10 мм;
3) вынос с S1, 4) свободная станция S2 по маркам и вынос с S2, 5) толкнули станцию -> компенсатор,
6) лазерная линия, 7) проект — факт."""
import sys, os, shutil, math, numpy as np
sys.path.insert(0, sys.argv[1]); os.chdir(sys.argv[1])
import web, sim_room, layout as LY, ezdxf
d = sys.argv[2]; shutil.rmtree(d, ignore_errors=True)
A = web.App(d, True); A.new_project("icon"); st = A.station(); room = st.ard.room
A.job_scan()
REFS = {"1": (1000, sim_room.bump(1000, 1600), 1600), "2": (4200, 2600, 1500), "3": (1000, 3400, 2000)}
def aim(P):
    h, v = room.aim_world(P); st.ard.move(*st.deg2steps((h - st.ard.h_off) % 360, v - st.ard.v_off))
for k, P in REFS.items(): aim(P); A.job_ref(k)
m = A.model(); r0 = m["rooms"][0]

# --- проект <-> мир (только для проверки): по углам модели и истинным углам
TW = np.array([(0,0),(4200,0),(4200,1200),(4450,1200),(4450,2000),(4200,2000),(4200,3400),(2450,3400),(1750,3400),(0,3400),(0,1900),(300,1900),(300,1500),(0,1500)], float)
C = np.array([[c["x"], c["y"]] for c in r0["corners"]])
best = None
for k in range(len(TW)):
    for sgn in (1, -1):
        a, b = TW[k], TW[(k + sgn) % len(TW)]; th = math.atan2(*(b - a)[::-1]) - math.atan2(*(C[1] - C[0])[::-1])
        Rm = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]]); W = C @ Rm.T + (a - Rm @ C[0])
        e = sum(np.min(np.linalg.norm(TW - w, axis=1)) for w in W)
        if best is None or e < best[0]: best = (e, Rm, a - Rm @ C[0])
_, Rm, tm = best
pairs = [(c, TW[np.argmin(np.linalg.norm(TW - (Rm @ c + tm), axis=1))]) for c in C]
P_, Q_ = np.array([p for p, _ in pairs]), np.array([q for _, q in pairs]); p0, q0 = P_.mean(0), Q_.mean(0)
U, _, Vt = np.linalg.svd((P_ - p0).T @ (Q_ - q0)); Rm = (U @ Vt).T
if np.linalg.det(Rm) < 0: Vt[1] *= -1; Rm = (U @ Vt).T
tm = q0 - Rm @ p0
fw = lambda x, y: sim_room.FLOOR[0]*x + sim_room.FLOOR[1]*y
dz = np.mean([fw(*(Rm @ [c["x"], c["y"]] + tm)) - c["floor"] for c in r0["corners"]])
to_w = lambda P: np.r_[Rm @ np.asarray(P[:2], float) + tm, P[2] + dz]
to_p = lambda W: np.r_[Rm.T @ (np.asarray(W[:2], float) - tm), W[2] - dz]
print(f"проект->мир: поворот {math.degrees(math.atan2(Rm[1,0], Rm[0,0])):.2f}°, сдвиг {tm.round(1)}, dz {dz:+.2f}")

# стена с неровностью (мир y=0) в модели
wAB = min((w for w in r0["walls"] if w["type"] == "L"), key=lambda w: abs(to_w(w["a"] + [0])[1]) + abs(to_w(w["b"] + [0])[1]))
lc = LY.left_corner(r0, wAB["name"]); fr = LY.wall_frame(r0, wAB["name"], lc)
o_w = to_w(np.r_[fr["o"], 0]); dirx = np.sign(to_w(np.r_[fr["o"] + fr["d"]*1000, 0])[0] - o_w[0])
print(f"стена под кухню: {wAB['name']}, левый угол {fr['corner']} (мир x={o_w[0]:.0f}), вдоль x {dirx:+.0f}")

# --- DXF проекта
HOLES = [(300, 1450), (900, 1450), (1500, 1450), (2100, 1450), (300, 2100), (2100, 2100), (3500, 300)]
doc = ezdxf.new(); msp = doc.modelspace()
for u, h in HOLES: msp.add_circle((u, h), 4, dxfattribs={"layer": "HOLES"})
msp.add_line((200, 900), (3000, 900), dxfattribs={"layer": "LINE900"})
msp.add_text("кран", height=40, dxfattribs={"layer": "HOLES"}).set_placement((3500, 340))
doc.saveas(os.path.join(d, "elev.dxf"))
doc = ezdxf.new(); msp = doc.modelspace()
FP = [(300, 500), (3900, 600), (600, 3000)]                     # мир: точки на полу (выводы, ножки)
for x, y in FP: q = to_p((x, y, 0)); msp.add_point((q[0], q[1], 0), dxfattribs={"layer": "FLOOR"})
TWs = TW.copy(); TWs[[2, 5], 0] += 0; sh = np.zeros_like(TW); sh[0:2, 1] = -10          # стена AB «по проекту» на 10 мм дальше
Tp = [to_p(np.r_[w + s, 0])[:2] for w, s in zip(TW, sh)]
msp.add_lwpolyline([tuple(p) for p in Tp], close=True, dxfattribs={"layer": "ARCH"})
doc.saveas(os.path.join(d, "plan.dxf"))
for f in ("elev.dxf", "plan.dxf"): print(A.upload(f, open(os.path.join(d, f), "rb").read()))

def check_wall(label):
    A.set_layout(dict(file="elev.dxf", layers=["HOLES"], mode="wall", room=r0["name"], wall=wAB["name"], corner=lc), save=False)
    E = []
    for t in A.targets:
        A.job_stake(t["id"]); W = to_w(A.stk["hit"]); u, h = t["src"]
        ex = o_w[0] + dirx*u; ez = fw(o_w[0], o_w[1]) + h
        on = abs(W[1] - sim_room.bump(W[0], W[2]))
        E.append((abs(W[0] - ex), abs(W[2] - ez), on, A.stk["dev"]))
    E = np.array(E)
    print(f"{label} стена: {len(E)} точек, ошибка вдоль стены max {E[:,0].max():.2f}, по высоте max {E[:,1].max():.2f}, "
          f"на поверхности {E[:,2].max():.2f} мм; неровность (выступ) {E[:,3].min():+.1f}…{E[:,3].max():+.1f}")
    A.set_layout(dict(file="plan.dxf", layers=["FLOOR"], mode="plan", hmode="floor"), save=False)
    E = []
    for t, (x, y) in zip(sorted(A.targets, key=lambda t: to_w(t["P"])[0]), sorted(FP)):
        A.job_stake(t["id"]); W = to_w(A.stk["hit"]); E.append((math.hypot(W[0] - x, W[1] - y), W[2] - fw(W[0], W[1])))
    E = np.array(E); print(f"{label} пол: {len(E)} точек, ошибка в плане max {E[:,0].max():.2f} мм, на полу {np.abs(E[:,1]).max():.2f} мм")

check_wall("S1")
# --- линия 900 по развёртке
A.set_layout(dict(file="elev.dxf", layers=["LINE900"], mode="wall", room=r0["name"], wall=wAB["name"], corner=lc), save=False)
A.job_line(dict(id=A.targets[0]["id"], passes=1, exact=True, step=100)); print("линия:", A.lres)
# --- S2: свободная станция по 3 маркам (без скана)
A.job_newsetup("S2"); room.set_pose((2900, 2300, 1180), -0.4, 0.9, 211); A.job_calib()
for k, P in REFS.items(): aim(P); A.job_ref(k)
A.job_resect(); print("S2 свободная станция:", {k: v for k, v in A.cur(A.proj())["resect"].items() if k in ("n", "rms", "max", "dz")})
check_wall("S2")
# --- толкнули станцию: наклон +0.1°
room.set_pose(room.O + [3, 0, 0], -0.4 + 0.1, 0.9, 211)
try: A.job_stake(1); print("компенсатор: НЕ сработал")
except web.S.Moved as e: print("компенсатор:", e)
A.job_check(); print("проверка стоянки:", A.chk["ok"], f"наклон {A.chk['tilt']:.3f}°", [f"{r['name']} {r['dD']:+.1f}" for r in A.chk["rows"]])
# --- проект — факт
A.job_compare("plan.dxf", ["ARCH"])
for w in A.cmp["walls"]:
    if w["off_a"] is not None: print(f"  {w['wall']}: {w['off_a']:+.1f}/{w['off_b']:+.1f} мм, {w['ang']:+.2f}°")
