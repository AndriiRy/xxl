"""Шаблон столешницы (как Flexijet Stone): лазер обходит стены на высоте столешницы (трасса по уровню),
задняя кромка — по реальным стенам, передняя — на глубину D, вырезы под мойку/плиту -> DXF 1:1 для ЧПУ/камнереза.

Задняя кромка:
  touch — прямая по самой выступающей точке стены (камень/HPL нельзя врезать в стену; зазоры за столешницей видны в отчёте),
  fit   — средняя линия стены.
Слои worktop.dxf (мм, начало — задний левый угол, X вдоль первой стены, Y — к фасаду):
  CONTOUR — контур, CUTOUTS — вырезы, WALL_ACTUAL — стена по факту на этой высоте (подгонка), DIM — размеры, TEXT — зазоры."""
import math
import numpy as np
import room3d


def _lines(segs, P, n_sign, mode):
    """Прямые участки задней кромки: [(точка на прямой, направление, нормаль к фасаду, выступ, зазор)]."""
    L = []
    for s in segs:
        if s.get("conn"): continue
        Q = room3d.seg_pts(s, 5.0); parts = list(zip(Q[:-1], Q[1:]))           # дуга — хордами по 5°
        for a, b in parts:
            a, b = np.asarray(a, float), np.asarray(b, float); d = b - a; ln = np.linalg.norm(d)
            if ln < 5: continue
            d /= ln; n = n_sign*np.r_[-d[1], d[0]]
            t = (P - a) @ d; w = (P - a) @ n; e = min(60.0, ln/4); on = (t > e) & (t < ln - e) & (np.abs(w) < 40)   # без соседней стены у угла
            pro = float(w[on].max()) if on.any() else 0.0; gap = float(-w[on].min()) if on.any() else 0.0
            sh = pro if mode == "touch" else 0.0
            L.append(dict(p=a + sh*n, a=a, b=b, d=d, n=n, pro=pro, gap=gap + sh, len=ln))
    return L


def _x(p, d, q, e):
    M = np.array([d, -e]).T
    if abs(np.linalg.det(M)) < 1e-6: return None
    return p + np.linalg.solve(M, q - p)[0]*d


def template(XY, HZ, station_xy, depth=600.0, mode="touch", cutouts=(), e0=0.0, e1=0.0):
    """XY — трасса по уровню (кадр станции), HZ — её углы. -> контур, вырезы, отчёт (кадр станции)."""
    R = room3d.analyze_profile(XY, HZ, closed=False)
    if not R["segs"]:                                                            # одна прямая стена (кухня в линию)
        o = np.argsort(HZ); Q = XY[o]; m = Q.mean(0); _, _, vt = np.linalg.svd(Q - m); d = vt[0]
        if d @ (Q[-1] - Q[0]) < 0: d = -d
        t = (Q - m) @ d; R = dict(segs=[dict(type="L", a=m + t.min()*d, b=m + t.max()*d)])
    s0 = R["segs"][0]; nl = np.r_[-(s0["b"] - s0["a"])[1], (s0["b"] - s0["a"])[0]]
    n_sign = 1.0 if nl @ (np.asarray(station_xy) - s0["a"]) > 0 else -1.0       # фасад — в сторону станции (в комнату)
    L = _lines(R["segs"], XY, n_sign, mode)
    if not L: raise RuntimeError("нет прямых участков стены")
    B = [L[0]["p"] + ((L[0]["a"] - L[0]["p"]) @ L[0]["d"] - e0)*L[0]["d"]]
    for u, v in zip(L[:-1], L[1:]):
        q = _x(u["p"], u["d"], v["p"], v["d"]); B.append(q if q is not None else (u["b"] + v["a"])/2 + u["n"]*u["pro"])
    B.append(L[-1]["p"] + ((L[-1]["b"] - L[-1]["p"]) @ L[-1]["d"] + e1)*L[-1]["d"])
    F = [B[0] + depth*L[0]["n"]]
    for u, v in zip(L[:-1], L[1:]):
        q = _x(u["p"] + depth*u["n"], u["d"], v["p"] + depth*v["n"], v["d"]); F.append(q if q is not None else F[-1])
    F.append(B[-1] + depth*L[-1]["n"])
    B, F = np.array(B), np.array(F)
    # вырезы: s — от начала задней кромки до центра выреза, w — вдоль, dp — поперёк, f — от фасада
    cum = np.r_[0, np.cumsum(np.linalg.norm(np.diff(B, axis=0), axis=1))]; C = []
    for c in cutouts:
        k = int(np.clip(np.searchsorted(cum, c["s"]) - 1, 0, len(L) - 1)); d, n = L[k]["d"], L[k]["n"]
        p = B[k] + (c["s"] - cum[k])*d; y0, y1 = depth - c["f"] - c["dp"], depth - c["f"]
        C.append(dict(name=c["name"], poly=np.array([p + d*(-c["w"]/2) + n*y0, p + d*(c["w"]/2) + n*y0, p + d*(c["w"]/2) + n*y1, p + d*(-c["w"]/2) + n*y1])))
    poly = np.vstack([B, F[::-1]])
    area = 0.5*abs(sum(a[0]*b[1] - b[0]*a[1] for a, b in zip(poly, np.roll(poly, -1, 0))))
    ang = [180 - abs(math.degrees(math.atan2(u["d"][0]*v["d"][1] - u["d"][1]*v["d"][0], u["d"] @ v["d"]))) for u, v in zip(L[:-1], L[1:])]
    rep = dict(back=[float(np.linalg.norm(b - a)) for a, b in zip(B[:-1], B[1:])], front=[float(np.linalg.norm(b - a)) for a, b in zip(F[:-1], F[1:])],
               angles=ang, walls=[dict(len=float(np.linalg.norm(B[i + 1] - B[i])), pro=u["pro"], gap=u["gap"]) for i, u in enumerate(L)],
               area_m2=area/1e6, depth=depth, mode=mode)
    return dict(B=B, F=F, poly=poly, cut=C, wall=XY, rep=rep, d0=L[0]["d"], n0=L[0]["n"])


def to_local(W):
    o, d, n = W["B"][0], W["d0"], W["n0"]; f = lambda P: np.c_[(np.asarray(P) - o) @ d, (np.asarray(P) - o) @ n]
    return f


def to_dxf(W, path, title=""):
    import ezdxf
    from ezdxf.enums import TextEntityAlignment as TA
    f = to_local(W); doc = ezdxf.new("R2010", setup=True); doc.units = ezdxf.units.MM; msp = doc.modelspace()
    for lay, col in (("CONTOUR", 7), ("CUTOUTS", 1), ("WALL_ACTUAL", 8), ("DIM", 3), ("TEXT", 2)): doc.layers.add(lay, color=col)
    P = f(W["poly"]); msp.add_lwpolyline([tuple(p) for p in P], close=True, dxfattribs={"layer": "CONTOUR"})
    for c in W["cut"]:
        Q = f(c["poly"]); msp.add_lwpolyline([tuple(p) for p in Q], close=True, dxfattribs={"layer": "CUTOUTS"})
        msp.add_text(c["name"], height=40, dxfattribs={"layer": "TEXT"}).set_placement(tuple(Q.mean(0)), align=TA.MIDDLE_CENTER)
    Wl = f(W["wall"]); msp.add_lwpolyline([tuple(p) for p in Wl[:: max(1, len(Wl)//600)]], dxfattribs={"layer": "WALL_ACTUAL"})
    for a, b in zip(P, np.roll(P, -1, 0)):
        if np.linalg.norm(b - a) > 20:
            msp.add_aligned_dim(p1=tuple(a), p2=tuple(b), distance=-120, dimstyle="EZDXF", dxfattribs={"layer": "DIM"}).render()
    B = f(W["B"])
    for i, w in enumerate(W["rep"]["walls"]):
        m = (B[i] + B[i + 1])/2
        msp.add_text(f"стена: выступ {w['pro']:.1f}, зазор до {w['gap']:.1f} мм", height=35, dxfattribs={"layer": "TEXT"}).set_placement((m[0], m[1] - 60), align=TA.MIDDLE_CENTER)
    if title: msp.add_text(title, height=50, dxfattribs={"layer": "TEXT"}).set_placement((0, P[:, 1].max() + 250))
    doc.saveas(path)


def parse_cutouts(txt):
    """«мойка 1200 780 480 70; плита 2600 560 490 50» -> имя, s (центр от начала), ширина, глубина, от фасада."""
    out = []
    for part in (txt or "").replace("\n", ";").split(";"):
        w = part.replace(",", " ").split()
        if len(w) < 5: continue
        out.append(dict(name=w[0], s=float(w[1]), w=float(w[2]), dp=float(w[3]), f=float(w[4])))
    return out
