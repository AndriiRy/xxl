# симулятор станции: Г-образная комната, шкаф-помеха, шум дальномера и угловых датчиков
import json, math, numpy as np, sys
rng = np.random.default_rng(1)
room = np.array([[0,0],[5000,0],[5003,2000],[2500,2004],[2498,4000],[-2,3998]],float)
box = np.array([[3800,300],[4600,300],[4600,900],[3800,900]],float)   # шкаф у стены
S = np.array([1200.,1500.]); hS = 1400.                                  # станция, высота над полом
sig_d, sig_a, per_a = float(sys.argv[1]), float(sys.argv[2])/3600, float(sys.argv[3])/3600
def ray(o, u, polys):
    best = 1e9
    for poly in polys:
        for k in range(len(poly)):
            a, b = poly[k], poly[(k+1)%len(poly)]; e = b-a
            M = np.array([u, -e]).T
            if abs(np.linalg.det(M)) < 1e-9: continue
            t, s = np.linalg.solve(M, a-o)
            if t > 1 and 0 <= s <= 1: best = min(best, t)
    return best
def ang_err(h): return rng.normal(0, sig_a) + per_a*math.sin(math.radians(h))  # эксцентриситет круга
pts = []
for h in np.arange(0, 360, 0.5):
    hr = math.radians(h + ang_err(h)); u = np.array([math.cos(hr), math.sin(hr)])
    d = ray(S, u, [room, box]); pts.append([h, 0.0, d + rng.normal(0, sig_d)])
cz = lambda x, y: 2700 + 0.002*x - 0.001*y      # потолок с уклоном 2 и 1 мм/м
fz = lambda x, y: 0.0005*x                      # пол
for h in np.arange(0, 360, 20):
    for v in (60, 70, 80, -60, -70, -80):
        hr, vr = math.radians(h), math.radians(v)
        u = np.array([math.cos(vr)*math.cos(hr), math.cos(vr)*math.sin(hr), math.sin(vr)])
        # итеративно до плоскости
        t = 1000.
        for _ in range(20):
            p = np.r_[S, hS] + t*u
            zt = cz(p[0], p[1]) if v > 0 else fz(p[0], p[1])
            t += (zt - p[2]) / u[2]
        p = np.r_[S, hS] + t*u
        if ray(S, u[:2]/np.linalg.norm(u[:2]), [room]) < t*math.cos(vr): continue  # за стеной
        pts.append([h + ang_err(h)*0, v + rng.normal(0, sig_a), t + rng.normal(0, sig_d)])
json.dump({"cal": {}, "points": pts}, open("scan.json", "w"))
# эталон: координаты углов в системе станции
true = room - S
print("Эталон:", "  ".join(f"{np.linalg.norm(true[(k+1)%6]-true[k]):.1f}" for k in range(6)))
print("Эталон H в углах:", "  ".join(f"{cz(*r)-fz(*r):.1f}" for r in room))
