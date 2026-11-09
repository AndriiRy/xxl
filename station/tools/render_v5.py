"""Картинка сборки из STL деталей (без CGAL-сборки). python3 render_v5.py <cad_dir> <out.png>"""
import numpy as np, struct, sys, math, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
D = sys.argv[1]
def stl(fn):
    d = open(f"{D}/{fn}.stl", "rb").read()
    if d[:5] == b"solid":
        V = [list(map(float, l.split()[1:])) for l in d.decode(errors="ignore").splitlines() if l.strip().startswith("vertex")]
        return np.array(V).reshape(-1, 3, 3)
    n = struct.unpack("<I", d[80:84])[0]
    return np.frombuffer(d[84:84+n*50], dtype=np.dtype([("n","<3f4"),("v","<9f4"),("a","<u2")]))["v"].reshape(-1,3,3).astype(float)
def Rx(a): a = math.radians(a); return np.array([[1,0,0],[0,math.cos(a),-math.sin(a)],[0,math.sin(a),math.cos(a)]])
def Ry(a): a = math.radians(a); return np.array([[math.cos(a),0,math.sin(a)],[0,1,0],[-math.sin(a),0,math.cos(a)]])
ZB, ZD, ZT, AX, PH, HZ = 26, 66, 88, 64, 104, 22
FEET = [(40, 68), (40, -68), (-98, 0)]
P = {k: stl(k) for k in ["base", "housing", "hz_drum", "alidade", "pod_lid_l", "pod_lid_r", "head", "head_lid", "v_drum", "foot"]}
def scene(v):
    out = []
    def add(k, R=np.eye(3), t=(0, 0, 0), c=(.75, .75, .78)): out.append((P[k] @ R.T + np.array(t, float), c))
    add("base", t=(0, 0, ZB), c=(.35, .35, .38)); add("housing", t=(0, 0, ZB + 5), c=(.55, .56, .6))
    for f in FEET: add("foot", R=np.diag([1, 1, -1]), t=(f[0], f[1], ZB - 8 + 8), c=(.15, .15, .15))
    add("hz_drum", t=(0, 0, ZD), c=(.95, .55, .15)); add("alidade", t=(0, 0, ZT), c=(.4, .55, .75))
    add("pod_lid_l", t=(0, 0, ZT + PH), c=(.5, .65, .85)); add("pod_lid_r", t=(0, 0, ZT + PH), c=(.5, .65, .85))
    add("head", R=Rx(v), t=(0, 0, ZT + AX), c=(.92, .92, .92))
    hl = P["head_lid"] + np.array([0, 0, HZ]); out.append((hl @ Rx(v).T + np.array([0, 0, ZT + AX]), (.92, .92, .92)))
    add("v_drum", R=Ry(-90), t=(-33, 0, ZT + AX), c=(.95, .55, .15))
    return out
fig = plt.figure(figsize=(15, 7.5))
for k, (v, el, az, title) in enumerate([(0, 18, -55, "v5: скруглённый корпус, 198x160x196 мм, 1,5 кг"), (-90, 10, 35, "голова вниз (V = -90°), отвес по оси")]):
    ax = fig.add_subplot(1, 2, k + 1, projection="3d"); L = np.array([0.3, -0.6, 0.75]); L /= np.linalg.norm(L)
    for T, c in scene(v):
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.linalg.norm(n, axis=1)[:, None] + 1e-12
        s = (0.45 + 0.55*np.abs(n @ L))[:, None]
        ax.add_collection3d(Poly3DCollection(T, facecolors=np.clip(s*np.array(c), 0, 1), edgecolors="none"))
    if v == -90: ax.plot([0, 0], [0, 0], [0, ZT + AX], color="red", lw=1.5)
    ax.set_xlim(-110, 110); ax.set_ylim(-110, 110); ax.set_zlim(0, 220); ax.set_box_aspect((1, 1, 1)); ax.view_init(el, az); ax.axis("off"); ax.set_title(title)
plt.savefig(sys.argv[2], dpi=110, bbox_inches="tight")
