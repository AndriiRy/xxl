import numpy as np, struct, sys, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
def stl(fn):
    d = open(fn, "rb").read()
    if d[:5] == b"solid":
        V = [list(map(float, l.split()[1:])) for l in d.decode(errors="ignore").splitlines() if l.strip().startswith("vertex")]
        return np.array(V).reshape(-1, 3, 3)
    n = struct.unpack("<I", d[80:84])[0]
    return np.frombuffer(d[84:84+n*50], dtype=np.dtype([("n","<3f4"),("v","<9f4"),("a","<u2")]))["v"].reshape(-1,3,3).astype(float)
fig = plt.figure(figsize=(14, 7))
for k, (fn, el, az) in enumerate([("assembly.stl", 18, -55), ("down.stl", 8, -20)]):
    T = stl(fn); n = np.cross(T[:,1]-T[:,0], T[:,2]-T[:,0]); n /= np.linalg.norm(n, axis=1)[:, None] + 1e-12
    L = np.array([0.3, -0.6, 0.75]); L /= np.linalg.norm(L); s = 0.4 + 0.6*np.abs(n @ L)
    ax = fig.add_subplot(1, 2, k + 1, projection="3d")
    ax.add_collection3d(Poly3DCollection(T, facecolors=np.c_[s*0.8, s*0.8, s*0.82], edgecolors="none"))
    if k: ax.plot([0, 0], [0, 0], [0, 152], color="red", lw=1.5)
    ax.set_xlim(-110, 110); ax.set_ylim(-110, 110); ax.set_zlim(0, 200); ax.set_box_aspect((1, 1, 1)); ax.view_init(el, az); ax.axis("off")
    ax.set_title(["Сборка: 198x160, высота 188 мм, 1,5 кг", "Голова вниз (V = -90°): отвес по оси"][k])
plt.savefig(sys.argv[1], dpi=110, bbox_inches="tight")
