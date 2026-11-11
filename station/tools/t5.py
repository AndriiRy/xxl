"""Тест: масштаб шнура Hz по метке, проскальзывание, чертёж при замере (как Flexijet), шаблон столешницы.
python3 t5.py <station/pi> <папка>"""
import sys, os, shutil, math, numpy as np
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); os.chdir(sys.argv[1])
import web, sim_room, simmap
d = sys.argv[2]; shutil.rmtree(d, ignore_errors=True)


def corners_err(A):
    r0 = A.model()["rooms"][0]; to_w, _ = simmap.maps(r0)
    return max(np.min(np.linalg.norm(simmap.TW - to_w([c["x"], c["y"], 0])[:2], axis=1)) for c in r0["corners"])


# --- 1. шнур Hz вытянут на 0,4 %: без метки и с меткой
for mark in (False, True):
    A = web.App(os.path.join(d, f"m{int(mark)}"), True); A.cfg["sim_scale_err"] = [0.004, 0.0]; A.cfg["hz_mark"] = mark
    A.new_project("x"); A.job_scan()
    print(f"шнур +0,4 %, {'с меткой TCRT' if mark else 'без метки   '}: шаги/об {A.cfg['steps_per_rev_hz']} (истина {A.st.ard._sh():.0f}), "
          f"ошибка углов комнаты max {corners_err(A):.1f} мм")
st = A.st; room = st.ard.room
# --- 2. проскальзывание шнура на 0,1° во время работы
st.ard.h_off += 0.1; A._slip(st); print("проскальзывание:", A.alert); A.alert = None

# --- 3. чертёж при замере
def aim(P):
    h, v = room.aim_world(P); st.ard.move(*st.deg2steps(h - st.ard.h_off, v - st.ard.v_off))
def take(tool, pts):
    A.cad_cmd(dict(cmd="cad_tool", tool=tool))
    for P in pts: aim(P); A.job_cad_point()
    return A.cad()["els"][-1]["id"]
ceil = lambda x, y: sim_room.CEIL[0]*x + sim_room.CEIL[1]*y + sim_room.CEIL[2]
to_w, to_p = simmap.maps(A.model()["rooms"][0])
wBC = take("wall", [(4200, 600, 1000), (4200, 1100, 1400)])
wCD = take("wall", [(3800, 3400, 1200), (2600, 3400, 1500)])
p1 = take("pt", [(1000, sim_room.bump(1000, 1600), 1600)])
pl = take("plane", [(1000, 1000, ceil(1000, 1000)), (3000, 1200, ceil(3000, 1200)), (2000, 2800, ceil(2000, 2800))])
t = np.radians([-30, -90, -150]); cx, cy, r = sim_room.ARC.values()
ci = take("circle", [(cx + r*math.cos(a), cy + r*math.sin(a), 1000) for a in t])
for op, ids in (("corner", [wBC, wCD, pl]), ("dist", [p1, wBC]), ("angle", [wBC, wCD])): A.cad_cmd(dict(cmd="cad_make", op=op, ids=ids))
S = A.cad_state(); G = {e["id"]: e for e in S["els"]}
for e in S["els"]: print(f"  {e['id']} {e['type']:6s} {e['label']}")
cor = next(q for q in S["plan"] if q["type"] == "corner"); W = to_w(cor["p"])
print(f"угол C по 2 стенам + потолок: ошибка в плане {math.hypot(W[0] - 4200, W[1] - 3400):.2f} мм, Z {W[2] - ceil(4200, 3400):+.2f} мм от потолка")
print(f"плоскость потолка: истина {math.hypot(*sim_room.CEIL[:2])*1000:.2f} мм/м; окружность: истина R{r:.0f}")

# --- 4. шаблон столешницы: Г-образная по стенам AB (с выпуклостью) и BC, H 900, глубина 600, мойка
H = 900.0; zw = H + (to_w([0, 0, 0])[2])
h0 = room.aim_world((400, 0, zw))[0] - st.ard.h_off; h1 = room.aim_world((4200, 1100, zw))[0] - st.ard.h_off
A.job_worktop(dict(h=H, depth=600, hz0=h0 % 360, hz1=h1 % 360, step=0.5, mode="touch", cut="мойка 1500 780 480 70"))
P = np.array([to_w([*p, 0])[:2] for p in A.wt["poly"]])
print("контур (мир):", " ".join(f"({x:.1f},{y:.1f})" for x, y in P))
exp = np.array([(400, 2.6), (4200, 2.6), (4200, 1100), (3600, 1100), (3600, 602.6), (400, 602.6)])
print("ошибка вершин против ожидаемых:", " ".join(f"{np.min(np.linalg.norm(exp - p, axis=1)):.1f}" for p in P))
print("кромки:", A.wt["back"], A.wt["front"], "углы", A.wt["angles"], "стены", A.wt["walls"])
C = np.array([to_w([*p, 0])[:2] for p in A.wt["cut"][0]]); print("мойка (мир):", C.round(1).tolist())
print("файлы:", [f for f in os.listdir(A.pdir()) if f.endswith(".dxf")])
