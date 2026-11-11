"""Чертёж при замере (как Flexijet): каждый замер сразу становится элементом чертежа.
Инструменты: точка, стена (вертикальная плоскость по ≥2 точкам), ребро (3D-отрезок), плоскость (≥3 точки),
окружность (≥3 точки в плане: труба, колонна, полукруглый выступ).
Построения: пересечение (угол стен, в т.ч. закрытый мебелью; угол стен + плоскость = 3D-угол), расстояние, угол.
Кадр — проектный (как model.json / room_fusion.dxf), если стоянка привязана, иначе кадр стоянки."""
import math
import numpy as np

TOOLS = {"pt": ("Точка", 1), "wall": ("Стена", 2), "edge": ("Ребро", 2), "plane": ("Плоскость", 3), "circle": ("Окружность", 3)}


def fit_line2(P):
    m = P.mean(0); _, _, vt = np.linalg.svd(P - m); d = vt[0]
    if d @ (P[-1] - P[0]) < 0: d = -d                                   # направление — от первой точки к последней
    s = (P - m) @ d; return m, d, m + s.min()*d, m + s.max()*d, float(np.abs((P - m) @ np.r_[-d[1], d[0]]).max())


def fit_plane(P):
    m = P.mean(0); _, _, vt = np.linalg.svd(P - m); n = vt[2]
    if n[2] < 0: n = -n
    return m, n, float(np.abs((P - m) @ n).max())


def fit_circle2(P):
    A = np.c_[2*P, np.ones(len(P))]; b = (P**2).sum(1); x = np.linalg.lstsq(A, b, rcond=None)[0]
    c = x[:2]; r = math.sqrt(x[2] + c @ c); return c, r, float(np.abs(np.linalg.norm(P - c, axis=1) - r).max())


def _x2(a, da, b, db):
    """Пересечение прямых в плане."""
    M = np.array([da, -db]).T
    if abs(np.linalg.det(M)) < 1e-9: return None
    t = np.linalg.solve(M, b - a); return a + t[0]*da


def solve(P, els):
    """P: {id точки: xyz проекта}; els: элементы (type, pts | refs). -> элементы с геометрией и подписью."""
    out, G = [], {}
    for e in els:
        g = dict(e); t = e["type"]
        try:
            X = np.array([P[i] for i in e.get("pts", []) if i in P], float)
            if t == "pt":
                g.update(p=X[0], label=f"X{X[0][0]:.0f} Y{X[0][1]:.0f} Z{X[0][2]:.0f}")
            elif t == "wall":
                m, d, a, b, rms = fit_line2(X[:, :2])
                g.update(m=m, d=d, a=a, b=b, z=[float(X[:, 2].min()), float(X[:, 2].max())], dev=rms,
                         label=f"стена {math.degrees(math.atan2(d[1], d[0])) % 360:.2f}°" + (f", откл. {rms:.1f}" if len(X) > 2 else ""))
            elif t == "edge":
                a, b = X[0], X[-1]
                if len(X) > 2:
                    m = X.mean(0); _, _, vt = np.linalg.svd(X - m); d = vt[0] if vt[0] @ (X[-1] - X[0]) > 0 else -vt[0]
                    s = (X - m) @ d; a, b = m + s.min()*d, m + s.max()*d
                L = float(np.linalg.norm(b - a)); h = float(np.hypot(*(b - a)[:2]))
                g.update(a=a, b=b, len=L, label=f"ребро {L:.0f}, ΔZ {b[2] - a[2]:+.1f}, уклон {math.degrees(math.atan2(b[2] - a[2], h)):+.2f}°")
            elif t == "plane":
                m, n, rms = fit_plane(X); tilt = math.degrees(math.acos(min(1, abs(n[2]))))
                g.update(m=m, n=n, poly=X, dev=rms, tilt=tilt,
                         label=(f"плоскость: наклон {tilt:.2f}° ({math.tan(math.radians(tilt))*1000:.1f} мм/м)" if tilt < 45 else f"плоскость: от вертикали {90 - tilt:.2f}°") + (f", откл. {rms:.1f}" if len(X) > 3 else ""))
            elif t == "circle":
                c, r, rms = fit_circle2(X[:, :2]); g.update(c=c, r=r, z=float(X[:, 2].mean()), dev=rms, label=f"R{r:.1f} (Ø{2*r:.0f}), центр X{c[0]:.0f} Y{c[1]:.0f}")
            elif t == "corner":
                w = [G[i] for i in e["refs"]]; walls = [q for q in w if q["type"] == "wall"]; pl = [q for q in w if q["type"] == "plane"]
                if len(walls) < 2: raise ValueError("нужны 2 стены")
                p = _x2(walls[0]["m"], walls[0]["d"], walls[1]["m"], walls[1]["d"])
                if p is None: raise ValueError("стены параллельны")
                z = (pl[0]["m"] @ pl[0]["n"] - pl[0]["n"][:2] @ p)/pl[0]["n"][2] if pl else float(np.mean(walls[0]["z"] + walls[1]["z"]))
                ang = math.degrees(math.acos(min(1, abs(walls[0]["d"] @ walls[1]["d"]))))
                g.update(p=np.r_[p, z], ang=ang, label=f"угол X{p[0]:.0f} Y{p[1]:.0f}" + (f" Z{z:.0f}" if pl else "") + f", {ang:.2f}° / {180 - ang:.2f}°")
            elif t == "dist":
                a, b = G[e["refs"][0]], G[e["refs"][1]]; g.update(dist(a, b))
            elif t == "angle":
                a, b = G[e["refs"][0]], G[e["refs"][1]]; u, v = _dir(a), _dir(b)
                ang = math.degrees(math.acos(min(1, abs(float(u @ v)))))
                g.update(ang=ang, label=f"угол {ang:.2f}° (доп. {180 - ang:.2f}°)")
            g["ok"] = True
        except Exception as ex:
            g.update(ok=False, label=f"ошибка: {ex}")
        G[e["id"]] = g; out.append(g)
    return out


def _dir(g):
    """Направление (стена/ребро) или нормаль (плоскость) — для угла между элементами."""
    if g["type"] == "wall": return np.r_[g["d"], 0.0]
    if g["type"] == "edge": v = g["b"] - g["a"]; return v/np.linalg.norm(v)
    if g["type"] == "plane": return g["n"]
    raise ValueError("угол — между стенами, рёбрами, плоскостями")


def _pt(g):
    if g["type"] in ("pt", "corner"): return g["p"]
    if g["type"] == "circle": return np.r_[g["c"], g["z"]]
    return None


def dist(a, b):
    pa, pb = _pt(a), _pt(b)
    if pa is None and pb is not None: a, b, pa, pb = b, a, pb, pa
    if pa is not None and pb is not None:
        d = pb - pa; h = float(np.hypot(d[0], d[1]))
        return dict(d=float(np.linalg.norm(d)), dh=h, dz=float(d[2]), a=pa, b=pb, label=f"L {np.linalg.norm(d):.1f} · гор. {h:.1f} · ΔZ {d[2]:+.1f}")
    if pa is not None:
        if b["type"] == "wall":
            n = np.r_[-b["d"][1], b["d"][0]]; s = float((pa[:2] - b["m"]) @ n); q = pa[:2] - s*n
            return dict(d=abs(s), a=pa, b=np.r_[q, pa[2]], label=f"до стены {abs(s):.1f} (по горизонтали)")
        if b["type"] == "plane":
            s = float((pa - b["m"]) @ b["n"]); return dict(d=abs(s), a=pa, b=pa - s*b["n"], label=f"до плоскости {abs(s):.1f}")
        if b["type"] == "edge":
            u = b["b"] - b["a"]; t = float(np.clip((pa - b["a"]) @ u/(u @ u), 0, 1)); q = b["a"] + t*u
            return dict(d=float(np.linalg.norm(pa - q)), a=pa, b=q, label=f"до ребра {np.linalg.norm(pa - q):.1f}")
    if a["type"] == "wall" and b["type"] == "wall":
        n = np.r_[-a["d"][1], a["d"][0]]; ang = math.degrees(math.acos(min(1, abs(a["d"] @ b["d"]))))
        da, db = float((b["a"] - a["m"]) @ n), float((b["b"] - a["m"]) @ n); mid = (b["a"] + b["b"])/2
        q = mid - ((mid - a["m"]) @ n)*n; z = float(np.mean(a["z"]))
        return dict(d=abs((da + db)/2), a=np.r_[q, z], b=np.r_[mid, z], ang=ang,
                    label=f"между стенами {abs(da):.1f} … {abs(db):.1f} (непараллельность {ang:.2f}°)")
    if a["type"] == "plane" and b["type"] == "plane":
        s = float((b["m"] - a["m"]) @ a["n"]); return dict(d=abs(s), a=b["m"] - s*a["n"], b=b["m"], label=f"между плоскостями {abs(s):.1f}")
    raise ValueError("расстояние: точка/угол/центр до чего угодно, стена–стена, плоскость–плоскость")


def hull2(P):
    P = sorted(map(tuple, P));
    if len(P) < 3: return P
    def half(Q):
        h = []
        for p in Q:
            while len(h) >= 2 and (h[-1][0] - h[-2][0])*(p[1] - h[-2][1]) - (h[-1][1] - h[-2][1])*(p[0] - h[-2][0]) <= 0: h.pop()
            h.append(p)
        return h
    lo, up = half(P), half(P[::-1]); return lo[:-1] + up[:-1]


def plan(G):
    """Для экрана: элементы в плане (списки чисел)."""
    r = []
    for g in G:
        if not g.get("ok"): continue
        q = dict(id=g["id"], type=g["type"], label=g["label"])
        if g["type"] in ("pt", "corner"): q["p"] = np.round(g["p"], 1).tolist()
        elif g["type"] == "wall": q["a"], q["b"] = np.round(g["a"], 1).tolist(), np.round(g["b"], 1).tolist()
        elif g["type"] == "edge": q["a"], q["b"] = np.round(g["a"], 1).tolist(), np.round(g["b"], 1).tolist()
        elif g["type"] == "plane": q["poly"] = np.round(np.array(hull2(g["poly"][:, :2])), 1).tolist()
        elif g["type"] == "circle": q["c"], q["r"] = np.round(g["c"], 1).tolist(), round(g["r"], 1)
        elif g["type"] == "dist": q["a"], q["b"] = np.round(g["a"], 1).tolist(), np.round(g["b"], 1).tolist()
        r.append(q)
    return r


def to_dxf(G, P, path):
    import ezdxf
    from ezdxf.enums import TextEntityAlignment as TA
    doc = ezdxf.new("R2010", setup=True); doc.units = ezdxf.units.MM; msp = doc.modelspace()
    for lay, col in (("CAD_PT", 2), ("CAD_WALL", 7), ("CAD_EDGE", 4), ("CAD_PLANE", 6), ("CAD_CIRCLE", 3), ("CAD_DIM", 1), ("CAD_TEXT", 8)): doc.layers.add(lay, color=col)
    T = lambda s, p, lay="CAD_TEXT", h=50: msp.add_text(s, height=h, dxfattribs={"layer": lay}).set_placement(tuple(map(float, p[:2])), align=TA.MIDDLE_CENTER)
    for p in P.values(): msp.add_point(tuple(map(float, p)), dxfattribs={"layer": "CAD_PT"})
    for g in G:
        if not g.get("ok"): continue
        t = g["type"]; nm = f"{g['id']}: {g['label']}"
        if t in ("pt", "corner"): msp.add_circle(tuple(map(float, g["p"])), 15, dxfattribs={"layer": "CAD_PT"}); T(nm, g["p"][:2] + [0, 60])
        elif t == "wall":
            for z in g["z"]: msp.add_line((*map(float, g["a"]), z), (*map(float, g["b"]), z), dxfattribs={"layer": "CAD_WALL"})
            T(nm, (g["a"] + g["b"])/2 + [0, 60])
        elif t == "edge": msp.add_line(tuple(map(float, g["a"])), tuple(map(float, g["b"])), dxfattribs={"layer": "CAD_EDGE"}); T(nm, (g["a"][:2] + g["b"][:2])/2 + [0, 60])
        elif t == "plane":
            H = hull2(g["poly"][:, :2]); n, m = g["n"], g["m"]
            if abs(n[2]) > 1e-6:
                V = [(x, y, float((m @ n - n[0]*x - n[1]*y)/n[2])) for x, y in H]
                msp.add_polyline3d(V + [V[0]], dxfattribs={"layer": "CAD_PLANE"})
            T(nm, g["m"][:2])
        elif t == "circle": msp.add_circle((*map(float, g["c"]), g["z"]), g["r"], dxfattribs={"layer": "CAD_CIRCLE"}); T(nm, g["c"] + [0, g["r"] + 60])
        elif t == "dist":
            msp.add_line(tuple(map(float, g["a"])), tuple(map(float, g["b"])), dxfattribs={"layer": "CAD_DIM"}); T(g["label"], (g["a"][:2] + g["b"][:2])/2 + [0, 40], "CAD_DIM", 45)
    doc.saveas(path)
