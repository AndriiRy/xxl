"""Центр масс и устойчивость станции (печать PETG ~62 % плотности). python3 com.py [BAT_H BAT_M]"""
import numpy as np, struct, math, sys, itertools
def stl(fn):
    d = open(fn, "rb").read()
    if d[:5] == b"solid":
        T = np.array([list(map(float, l.split()[1:])) for l in d.decode(errors="ignore").splitlines() if l.strip().startswith("vertex")]).reshape(-1, 3, 3)
    else:
        n = struct.unpack("<I", d[80:84])[0]; T = np.frombuffer(d[84:84+n*50], dtype=np.dtype([("n","<3f4"),("v","<9f4"),("a","<u2")]))["v"].reshape(-1,3,3).astype(float)
    a, b, c = T[:,0], T[:,1], T[:,2]; v = np.einsum("ij,ij->i", a, np.cross(b, c))/6
    return abs(v.sum()), (v[:,None]*(a+b+c)/4).sum(0)/v.sum()
N_CELL = int(sys.argv[1]) if len(sys.argv) > 1 else 3; CELL_M = float(sys.argv[2]) if len(sys.argv) > 2 else 0.070
BASE_T, H_BOX, TOP_T, GAP, HZ_H, AXLE_Z = 5, 34, 8, 1, 22, 64
Z_BASE = 26; Z_DRUM = Z_BASE + BASE_T + H_BOX + GAP; Z_TOP = Z_DRUM + HZ_H
PACK_X = -25 - (N_CELL*21.6 + N_CELL - 1)/2; MOT_X = 60 + 3.8; mz = AXLE_Z - (35 + 3.8)
K = 1.27e-3*0.62/1000
it = []
for fn, off, rot in (("base.stl", Z_BASE, 0), ("housing.stl", Z_BASE + BASE_T, 0), ("hz_drum.stl", Z_DRUM, 1), ("alidade.stl", Z_TOP, 1),
                     ("pod_lid_l.stl", Z_TOP + AXLE_Z + 34, 1), ("pod_lid_r.stl", Z_TOP + AXLE_Z + 34, 1), ("head.stl", Z_TOP + AXLE_Z, 1), ("v_drum.stl", Z_TOP + AXLE_Z, 1)):
    v, c = stl(fn); c = np.array(c); c[2] += off
    if fn == "v_drum.stl": c = np.array([-26 - 6 - 1 - 7, 0, Z_TOP + AXLE_Z])
    it.append((fn[:-4], v*K, c, rot))
fixed = [(f"АКБ {N_CELL}x21700", N_CELL*CELL_M, (PACK_X, 0, Z_BASE + BASE_T + 11)), ("BMS, выкл., гнездо, индикатор", 0.03, (-10, 0, Z_BASE + 15)),
         ("NEMA17 блин Hz", 0.15, (MOT_X, 0, Z_BASE + BASE_T + H_BOX - TOP_T - 11.5)), ("труба + 2x6806 + хомут", 0.07, (0, 0, Z_DRUM)),
         ("ножки, шпильки", 0.06, (0, 0, 12))]
rot = [("NEMA17 блин V", 0.15, (-26 - 6 - 14 - 5 - 11.5, 0, Z_TOP + mz)), ("608x2 + болты М8", 0.06, (0, 0, Z_TOP + AXLE_Z)),
       ("дальномер + камера + MPU6050", 0.05, (0, 5, Z_TOP + AXLE_Z)), ("Pi 4 (без корпуса, радиатор)", 0.06, (65, 0, Z_TOP + 45)), ("Nano + 2 драйвера + mini560 + INA219", 0.04, (45, 0, Z_TOP + 40))]
it += [(n, m, np.array(c, float), 0) for n, m, c in fixed] + [(n, m, np.array(c, float), 1) for n, m, c in rot]
M = sum(i[1] for i in it)
def com(th):
    R = np.array([[math.cos(th), -math.sin(th), 0], [math.sin(th), math.cos(th), 0], [0, 0, 1]])
    return sum(m*(R @ c if r else c) for _, m, c, r in it)/M
if "-v" in sys.argv:
    for n, m, c, r in sorted(it, key=lambda i: -i[1]): print(f"  {n:36s} {m*1000:4.0f} г  x{c[0]:+5.0f} z{c[2]:4.0f}{'  вращ.' if r else ''}")
C = np.array([com(t) for t in np.linspace(0, 2*math.pi, 73)]); Cm = C.mean(0)
def margin(F, p):
    out = 1e9
    for i in range(3):
        a, b = F[i], F[(i+1) % 3]; d = (b - a)/np.linalg.norm(b - a); n = np.array([-d[1], d[0]])
        if (F[(i+2) % 3] - a) @ n < 0: n = -n
        out = min(out, (p - a) @ n)
    return out
print(f"масса {M:.2f} кг, ЦМ x{Cm[0]:+.1f} z{Cm[2]:.0f} мм, ход при вращении ±{np.linalg.norm(C[:, :2] - Cm[:2], axis=1).max():.1f} мм")
best = None
for xf, yf, xr in itertools.product(range(30, 81, 5), range(40, 81, 2), range(-98, -79, 2)):
    F = [np.array([xf, yf]), np.array([xf, -yf]), np.array([xr, 0])]
    ext = max(xf + 12, 88) - min(xr - 12, -96); wid = max(2*yf + 24, 132)
    if wid > 160: continue                                  # не шире 160 мм
    mm = min(margin(F, c[:2]) for c in C)
    if best is None or mm > best[0]: best = (mm, xf, yf, xr, ext, wid)
F0 = [np.array([40, 68]), np.array([40, -68]), np.array([-98, 0])]
m0 = min(margin(F0, c[:2]) for c in C)
print(f"ножки (40,±68),(-98,0): запас {m0:.0f} мм, опрокидывание при {math.degrees(math.atan(m0/Cm[2])):.0f}°")
print(f"оптимум (ширина ≤160): ({best[1]},±{best[2]}),({best[3]},0): запас {best[0]:.0f} мм, опрокид. {math.degrees(math.atan(best[0]/Cm[2])):.0f}°, габарит {best[4]}x{best[5]}")
