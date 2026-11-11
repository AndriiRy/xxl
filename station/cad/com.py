"""Центр масс и устойчивость станции v6 (печать PETG ~62 % плотности). python3 com.py [-v]
Вращается всё, кроме дна: корпус с аккумулятором и мотором Hz, алидада, голова. Ножки — на неподвижном дне."""
import numpy as np, struct, math, sys
def stl(fn):
    d = open(fn, "rb").read()
    if d[:5] == b"solid":
        T = np.array([list(map(float, l.split()[1:])) for l in d.decode(errors="ignore").splitlines() if l.strip().startswith("vertex")]).reshape(-1, 3, 3)
    else:
        n = struct.unpack("<I", d[80:84])[0]; T = np.frombuffer(d[84:84+n*50], dtype=np.dtype([("n","<3f4"),("v","<9f4"),("a","<u2")]))["v"].reshape(-1,3,3).astype(float)
    a, b, c = T[:,0], T[:,1], T[:,2]; v = np.einsum("ij,ij->i", a, np.cross(b, c))/6
    return abs(v.sum()), (v[:,None]*(a+b+c)/4).sum(0)/v.sum()
# из station.scad (echo): Z_BASE 26, Z_DK 55, Z_HS 58, Z_TOP 92, AXLE_Z 64, POD_H 104
Z_BASE, Z_DK, Z_HS, Z_TOP, AXLE_Z, POD_H = 26, 55, 58, 92, 64, 104
N_CELL, CELL_M = 3, 0.070; PACK_X = -25 - (N_CELL*21.6 + N_CELL - 1)/2; MOT_X = 73.3; mz = AXLE_Z - 38.8
FEET = [np.array([96*math.cos(math.radians(a)), 96*math.sin(math.radians(a))]) for a in (180, 60, -60)]
K = 1.27e-3*0.62/1000
it = []
for fn, off, rot in (("base.stl", Z_BASE, 0), ("spacer.stl", Z_BASE + 24, 0), ("deck.stl", Z_DK, 1), ("housing.stl", Z_HS, 1),
                     ("alidade.stl", Z_TOP, 1), ("pod_lid_l.stl", Z_TOP + POD_H, 1), ("pod_lid_r.stl", Z_TOP + POD_H, 1), ("head.stl", Z_TOP + AXLE_Z, 1),
                     ("v_cart.stl", Z_TOP, 1)):
    v, c = stl(fn); c = np.array(c); c[2] += off; it.append((fn[:-4], v*K, c, rot))
it.append(("v_drum+hub+barashek", 0.045, np.array([-40.0, 0, Z_TOP + AXLE_Z]), 1))
fixed = [("ножки, шпильки", 0.06, (0, 0, 12)), ("труба 30x2", 0.05, (0, 0, 60))]
rot = [(f"АКБ {N_CELL}x21700", N_CELL*CELL_M, (PACK_X, 0, Z_HS + 11)), ("BMS, выкл., гнездо, индикатор", 0.03, (-10, 0, Z_HS + 12)),
       ("NEMA17 блин Hz + шкив 16T", 0.16, (MOT_X, 0, Z_HS + 10)), ("2x6806", 0.04, (0, 0, Z_HS + 17)), ("ремень", 0.01, (30, 0, Z_BASE + 19)),
       ("NEMA17 блин V", 0.15, (-26 - 6 - 14 - 6 - 11.5, 0, Z_TOP + mz)), ("608x2 + шпилька М8", 0.06, (0, 0, Z_TOP + AXLE_Z)),
       ("дальномер + камера + датчик наклона", 0.06, (0, 5, Z_TOP + AXLE_Z)), ("Pi 4 (без корпуса, радиатор)", 0.06, (65, 0, Z_TOP + 45)),
       ("Nano + 2 драйвера + mini560 + INA219", 0.04, (45, 0, Z_TOP + 40))]
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
m0 = min(margin(FEET, c[:2]) for c in C)
print(f"масса {M:.2f} кг, ЦМ z{Cm[2]:.0f} мм, ход ЦМ при вращении ±{np.linalg.norm(C[:, :2], axis=1).max():.1f} мм")
print(f"ножки R96 (120°): запас {m0:.0f} мм, опрокидывание при {math.degrees(math.atan(m0/Cm[2])):.0f}°")
