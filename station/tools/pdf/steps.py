# Иллюстрации сборки: разнесённые виды по шагам. Позиции деталей — из module assembly() в cad/station.scad.
import numpy as np, struct, sys, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

CAD = sys.argv[1] if len(sys.argv) > 1 else "../../cad"
OUT = sys.argv[2] if len(sys.argv) > 2 else "img"

def stl(fn):
    d = open(f"{CAD}/{fn}.stl", "rb").read()
    if d[:5] == b"solid" and b"facet" in d[:300]:
        V = [list(map(float, l.split()[1:])) for l in d.decode(errors="ignore").splitlines() if l.strip().startswith("vertex")]
        return np.array(V).reshape(-1, 3, 3)
    n = struct.unpack("<I", d[80:84])[0]
    return np.frombuffer(d[84:84+n*50], dtype=np.dtype([("n", "<3f4"), ("v", "<9f4"), ("a", "<u2")]))["v"].reshape(-1, 3, 3).astype(float)

def cyl(r, h, n=40, r_in=0, axis="z"):
    a = np.linspace(0, 2*np.pi, n + 1); T = []
    for i in range(n):
        p = [(np.cos(a[i]), np.sin(a[i])), (np.cos(a[i+1]), np.sin(a[i+1]))]
        o0, o1 = [r*p[0][0], r*p[0][1]], [r*p[1][0], r*p[1][1]]
        T += [[o0+[0], o1+[0], o1+[h]], [o0+[0], o1+[h], o0+[h]]]
        if r_in:
            i0, i1 = [r_in*p[0][0], r_in*p[0][1]], [r_in*p[1][0], r_in*p[1][1]]
            T += [[i0+[0], i1+[h], i1+[0]], [i0+[0], i0+[h], i1+[h]]]
            for z in (0, h): T += [[o0+[z], o1+[z], i1+[z]], [o0+[z], i1+[z], i0+[z]]]
        else:
            for z in (0, h): T += [[[0, 0, z], o0+[z], o1+[z]]]
    T = np.array(T, float)
    if axis == "y": T = T[..., [0, 2, 1]]
    if axis == "x": T = T[..., [2, 1, 0]]
    return T

def box(p0, p1):
    x0, y0, z0 = p0; x1, y1, z1 = p1
    v = np.array([[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],[x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]], float)
    f = [(0,1,2),(0,2,3),(4,6,5),(4,7,6),(0,4,5),(0,5,1),(1,5,6),(1,6,2),(2,6,7),(2,7,3),(3,7,4),(3,4,0)]
    return v[np.array(f)]

def ry_m90(T):  # OpenSCAD rotate([0,-90,0]): x' = -z, z' = x
    R = T.copy(); R[..., 0] = -T[..., 2]; R[..., 2] = T[..., 0]; return R
def mv(T, d): return T + np.array(d, float)

# --- константы из station.scad ---
Z_BASE, Z_DK, Z_HS, Z_TOP = 26, 55, 58, 92
AXLE, POD_H, HEAD_Z = 64, 104, 22
MOT, MOT_L, MOT_X = 42.3, 23, 73.3
VC_X0, MZV = -52, 64 - (35 + 3 + 0.5 + 0.3)
PACK_X0, CELL_D, CELL_L = -91.8, 21.6, 70.5
FEET = [(96*np.cos(np.radians(a)), 96*np.sin(np.radians(a))) for a in (180, 60, -60)]

C = dict(grey=(0.50, 0.52, 0.56), dark=(0.30, 0.31, 0.34), blue=(0.27, 0.45, 0.68), white=(0.88, 0.89, 0.90),
         orange=(0.93, 0.55, 0.20), black=(0.16, 0.16, 0.18), steel=(0.74, 0.76, 0.79), cell=(0.25, 0.42, 0.85),
         tan=(0.80, 0.68, 0.48), gold=(0.85, 0.66, 0.20), green=(0.25, 0.55, 0.35), ghost=(0.78, 0.80, 0.82))

def parts():
    P = {}
    P["base"] = (mv(stl("base"), [0, 0, Z_BASE]), "dark")
    foot = stl("foot"); foot = foot.copy(); foot[..., 2] = -foot[..., 2]; foot = foot[:, ::-1]
    for i, f in enumerate(FEET): P[f"foot{i}"] = (mv(foot, [f[0], f[1], Z_BASE]), "black")
    P["tube"] = (mv(cyl(15, Z_TOP + 8 - Z_BASE - 1.5, 48, 13), [0, 0, Z_BASE + 1.5]), "steel")
    P["spacer"] = (mv(stl("spacer"), [0, 0, Z_BASE + 15 + 8 + 1.5]), "steel")
    P["deck"] = (mv(stl("deck"), [0, 0, Z_DK]), "grey")
    P["motorHz"] = (np.concatenate([box([MOT_X - MOT/2, -MOT/2, Z_HS], [MOT_X + MOT/2, MOT/2, Z_HS + MOT_L]),
                                    mv(cyl(2.5, 24, 16), [MOT_X, 0, Z_HS - 24])]), "black")
    P["pulley16"] = (mv(cyl(6.5, 10, 24), [MOT_X, 0, Z_BASE + 15 - 1]), "gold")
    P["belt"] = (mv(stl("vis_belt"), [0, 0, Z_BASE + 15 + 1]), "black")
    P["cells"] = (np.concatenate([mv(cyl(CELL_D/2, CELL_L, 28, axis="y"), [PACK_X0 + CELL_D/2 + i*(CELL_D + 1), -CELL_L/2, Z_HS + CELL_D/2 + 0.6]) for i in range(3)]), "cell")
    P["housing"] = (mv(stl("housing"), [0, 0, Z_HS]), "grey")
    P["b6806"] = (np.concatenate([mv(cyl(21, 7, 40, 15), [0, 0, Z_HS]), mv(cyl(21, 7, 40, 15), [0, 0, Z_HS + 27])]), "steel")
    P["collar"] = (mv(stl("collar"), [0, 0, Z_TOP]), "steel")
    P["alidade"] = (mv(stl("alidade"), [0, 0, Z_TOP]), "blue")
    P["b608"] = (np.concatenate([mv(cyl(11, 7, 32, 4, axis="x"), [s, 0, Z_TOP + AXLE]) for s in (-39, 32)]), "steel")
    P["pi"] = (box([66, -42.5, Z_TOP + 8], [69, 42.5, Z_TOP + 64]), "green")
    P["head"] = (mv(stl("head"), [0, 0, Z_TOP + AXLE]), "white")
    P["head_lid"] = (mv(stl("head_lid"), [0, 0, Z_TOP + AXLE + HEAD_Z]), "white")
    P["v_cart"] = (mv(stl("v_cart"), [VC_X0, 0, Z_TOP]), "tan")
    P["motorV"] = (box([VC_X0 - MOT_L, -MOT/2, Z_TOP + MZV - MOT/2], [VC_X0, MOT/2, Z_TOP + MZV + MOT/2]), "black")
    P["v_drum"] = (mv(ry_m90(stl("v_drum")), [-33, 0, Z_TOP + AXLE]), "orange")
    P["v_hub"] = (mv(ry_m90(stl("v_hub")), [-33, 0, Z_TOP + AXLE]), "steel")
    P["v_knob"] = (mv(ry_m90(stl("v_knob")), [VC_X0 - 1, 0, Z_TOP + AXLE]), "dark")
    P["lid_l"] = (mv(stl("pod_lid_l"), [0, 0, Z_TOP + POD_H]), "blue")
    P["lid_r"] = (mv(stl("pod_lid_r"), [0, 0, Z_TOP + POD_H]), "blue")
    return P

def render(fn, P, new, ghost=(), off={}, arrows=(), labels=(), view=(22, -58), lim=None, size=(7.2, 5.4)):
    tris, cols = [], []
    L = np.array([0.35, -0.55, 0.76]); L /= np.linalg.norm(L)
    for k in list(ghost) + list(new):
        T, c = P[k]; T = mv(T, off.get(k, (0, 0, 0)))
        col = np.array(C["ghost"] if k in ghost else C[c])
        n = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); n /= np.linalg.norm(n, axis=1)[:, None] + 1e-12
        s = 0.55 + 0.45*np.abs(n @ L) if k in ghost else 0.42 + 0.58*np.abs(n @ L)
        tris.append(T); cols.append(np.clip(s[:, None]*col[None, :]*1.12, 0, 1))
    ng = len(ghost)
    fig = plt.figure(figsize=size); ax = fig.add_subplot(projection="3d"); ax.computed_zorder = False
    if ng: ax.add_collection3d(Poly3DCollection(np.concatenate(tris[:ng]), facecolors=np.concatenate(cols[:ng]), edgecolors="none", zorder=1))
    ax.add_collection3d(Poly3DCollection(np.concatenate(tris[ng:]), facecolors=np.concatenate(cols[ng:]), edgecolors="none", zorder=2))
    T = np.concatenate(tris)
    for a, b in arrows:
        a, b = np.array(a, float), np.array(b, float)
        ax.quiver(*a, *(b - a), color=(0.75, 0.15, 0.1), lw=1.8, arrow_length_ratio=0.18, zorder=3)
    for pos, txt in labels:
        ax.text(*pos, txt, fontsize=8.5, color=(0.1, 0.12, 0.12), fontfamily="DejaVu Sans",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=(0.75, 0.78, 0.77), lw=0.6), zorder=100)
    V = T.reshape(-1, 3); mn, mx = V.min(0), V.max(0)
    if lim: mn, mx = np.array(lim[0], float), np.array(lim[1], float)
    c = (mn + mx)/2; r = (mx - mn).max()/2*0.9
    ax.set_xlim(c[0] - r, c[0] + r); ax.set_ylim(c[1] - r, c[1] + r); ax.set_zlim(c[2] - r, c[2] + r)
    ax.set_box_aspect((1, 1, 1)); ax.view_init(*view); ax.axis("off")
    plt.subplots_adjust(0, 0, 1, 1); plt.savefig(f"{OUT}/{fn}.png", dpi=150, facecolor="white"); plt.close(fig)
    print(fn, flush=True)

P = parts()
FEETK = [f"foot{i}" for i in range(3)]
# 1. дно, труба, ножки, проставка
render("step1", P, ["base", "tube", "spacer"] + FEETK,
       off={"tube": (0, 0, 70), "spacer": (0, 0, 45), **{k: (0, 0, -35) for k in FEETK}},
       arrows=[((0, 0, 205), (0, 0, 115)), ((0, 0, 140), (0, 0, 95)), ((FEET[1][0], FEET[1][1], -45), (FEET[1][0], FEET[1][1], 10))],
       labels=[((22, 0, 175), "труба 30×2, 55 мм — на натяге"), ((25, 0, 105), "проставка"), ((-120, 0, 60), "дно со шкивом 192T"),
               ((FEET[1][0] + 10, FEET[1][1], -20), "ножки: шпилька М8×40")], view=(16, -58))
# 2. палуба: мотор, шкив, банки, ремень
render("step2", P, ["deck", "motorHz", "pulley16", "cells", "belt"], ghost=["base", "tube", "spacer"] + FEETK,
       off={"deck": (0, 0, 80), "motorHz": (0, 0, 120), "pulley16": (0, 0, 40), "cells": (0, 0, 150), "belt": (0, 0, 0)},
       arrows=[((MOT_X, 0, 255), (MOT_X, 0, 200)), ((-60, 0, 260), (-60, 0, 230)), ((-20, -60, 175), (-20, -60, 140))],
       labels=[((MOT_X + 15, 0, 215), "мотор Hz, вал вниз"), ((-140, 0, 250), "3× 21700 + BMS"), ((MOT_X + 15, 0, 75), "шкив 16T"),
               ((-60, 60, 160), "палуба"), ((-90, -60, 50), "ремень GT2 400 — сначала на шкив дна")], view=(18, -58))
# 3. корпус Hz, подшипники, хомут
render("step3", P, ["housing", "b6806", "collar"], ghost=["base", "tube", "spacer", "deck", "motorHz", "cells", "belt", "pulley16"] + FEETK,
       off={"housing": (0, 0, 70), "b6806": (0, 0, 70), "collar": (0, 0, 130)},
       arrows=[((0, 0, 250), (0, 0, 228)), ((90, -40, 200), (90, -40, 160))],
       labels=[((25, 0, 245), "хомут М3×20 — преднатяг"), ((-150, -40, 190), "корпус: 2× 6806, KCD1, DC, индикатор"),
               ((95, -60, 185), "8 винтов снизу в бобышки")], view=(18, -58))
# 4. алидада
render("step4", P, ["alidade", "b608", "pi"], ghost=["base", "tube", "deck", "housing", "collar", "cells"] + FEETK,
       off={"alidade": (0, 0, 80), "b608": (0, 0, 80), "pi": (0, 0, 80)},
       arrows=[((0, -30, 300), (0, -30, 210)), ((30, 22, 180), (30, 22, 135))],
       labels=[((-170, 0, 290), "алидада: левая башня — картридж V"), ((75, 0, 260), "правая — Pi 4, Nano, драйверы"),
               ((40, 30, 160), "4× М4×16, гайки в корпусе"), ((-20, 0, 250), "608 ×2")], view=(18, -58))
# 5. голова
render("step5", P, ["head", "head_lid"], ghost=["alidade", "housing", "b608", "deck"],
       off={"head": (0, -150, 20), "head_lid": (0, -150, 70)},
       arrows=[((0, -110, 175), (0, -40, 160)), ((60, 0, 156), (40, 0, 156)), ((-75, 0, 156), (-45, 0, 156))],
       labels=[((30, -150, 255), "крышка + оргстекло 30×33×2"), ((30, -170, 150), "голова: дальномер, камера, инклинометр"),
               ((62, 0, 165), "болт М8×20"), ((-140, 0, 170), "шпилька М8×60 → 608 → конус")],
       view=(18, -50), lim=((-120, -160, 80), (120, 80, 280)))
# 6. картридж V
render("step6", P, ["v_cart", "motorV", "v_drum", "v_hub", "v_knob"], ghost=["alidade", "head", "head_lid", "housing"],
       off={"v_cart": (0, 0, 150), "motorV": (0, 0, 150), "v_drum": (0, 0, 150), "v_knob": (-40, 0, 0), "v_hub": (15, 0, 0)},
       arrows=[((-60, 0, 380), (-60, 0, 290)), ((-120, 0, 156), (-75, 0, 156))],
       labels=[((-150, -60, 370), "картридж: рамка + мотор V + барабан + шнур"), ((-110, -30, 135), "барашек М8"),
               ((10, -40, 95), "конус v_hub")], view=(16, -135), lim=((-170, -100, 60), (90, 100, 400)))
# 7. крышки и итог
render("step7", P, ["lid_l", "lid_r", "alidade", "head", "head_lid", "housing", "deck", "base", "v_drum", "v_cart", "collar"] + FEETK,
       off={"lid_l": (0, 0, 60), "lid_r": (0, 0, 60)},
       arrows=[((-55, 0, 290), (-55, 0, 205)), ((50, 0, 290), (50, 0, 205))],
       labels=[((-160, 0, 300), "крышки: 4 винта каждая"), ((60, -60, 60), "Hz: обороты рукой, V: −90…+90°")], view=(20, -58))
