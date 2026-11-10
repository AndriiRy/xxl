"""Вынос проекта на объект (как Leica iCON field): DXF -> точки/линии -> лазер на стену/пол/потолок,
свободная станция (привязка к известным точкам), сравнение «проект — факт».

Кадр проекта = кадр model.json / room_fusion.dxf: начало — угол A на полу, X вдоль стены A-B, Z вверх, мм.
Проект кухни рисовать в Fusion поверх room_fusion.dxf, не сдвигая начало координат.

Режимы DXF:
  plan — план: X, Y из DXF; высота: Z из DXF | на полу | на потолке | H от пола.
  wall — развёртка стены: X DXF = расстояние от выбранного угла вдоль стены, Y DXF = высота от пола в этом углу.
"""
import math
import numpy as np

OUR = {"WALLS", "DIM", "ANGLES", "HEIGHTS", "FEATURES", "LEVELS", "SURFACES", "REFS", "QUICK", "CLOUD", "MODEL3D",
       "ELEVATIONS", "DEVIATION", "PROJECT", "FACT", "DEFPOINTS"}
PT_TYPES, LN_TYPES = ("POINT", "CIRCLE", "INSERT"), ("LINE", "LWPOLYLINE", "POLYLINE")


# ================= чтение DXF =================
def _xyz(p): p = list(p); return [float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0]


def dxf_info(path):
    """Слои DXF с количеством точек и линий (наши служебные слои пропускаются)."""
    import ezdxf
    cnt = {}
    for e in ezdxf.readfile(path).modelspace():
        t = e.dxftype()
        if t not in PT_TYPES + LN_TYPES or e.dxf.layer.upper() in OUR: continue
        c = cnt.setdefault(e.dxf.layer, {"pts": 0, "lines": 0}); c["pts" if t in PT_TYPES else "lines"] += 1
    return [dict(name=k, **v) for k, v in sorted(cnt.items())]


def read_dxf(path, layers=None):
    """-> (точки [dict(p, kind, layer, name)], отрезки [dict(a, b, layer, name)]). Дуги полилиний — хордой."""
    import ezdxf
    msp = ezdxf.readfile(path).modelspace(); pts, lines, texts = [], [], []
    ok = lambda e: e.dxf.layer.upper() not in OUR and (not layers or e.dxf.layer in layers)
    for e in msp:
        t = e.dxftype()
        try:
            if t in ("TEXT", "MTEXT"):
                texts.append((np.array(_xyz(e.dxf.insert)[:2]), (e.plain_text() if t == "MTEXT" else e.dxf.text).strip())); continue
            if not ok(e): continue
            if t == "POINT": pts.append(dict(p=_xyz(e.dxf.location), kind="точка", layer=e.dxf.layer))
            elif t == "CIRCLE":
                pts.append(dict(p=_xyz(e.ocs().to_wcs(e.dxf.center)), kind=f"Ø{2*e.dxf.radius:.0f}", layer=e.dxf.layer))
            elif t == "INSERT": pts.append(dict(p=_xyz(e.ocs().to_wcs(e.dxf.insert)), kind=e.dxf.name, layer=e.dxf.layer))
            elif t == "LINE": lines.append(dict(a=_xyz(e.dxf.start), b=_xyz(e.dxf.end), layer=e.dxf.layer))
            elif t == "LWPOLYLINE":
                V = [_xyz(v) for v in e.vertices_in_wcs()]
                if e.closed: V.append(V[0])
                lines += [dict(a=a, b=b, layer=e.dxf.layer) for a, b in zip(V[:-1], V[1:])]
            elif t == "POLYLINE":
                V = [_xyz(v) for v in e.points()]
                if e.is_closed: V.append(V[0])
                lines += [dict(a=a, b=b, layer=e.dxf.layer) for a, b in zip(V[:-1], V[1:])]
        except Exception:
            continue
    uniq = []
    for q in pts:                                                     # дубли (точка + кружок в одном месте)
        if not any(np.linalg.norm(np.subtract(q["p"], u["p"])) < 0.5 for u in uniq): uniq.append(q)
    lines = [l for l in lines if np.linalg.norm(np.subtract(l["a"], l["b"])) > 1]
    def label(xy):
        if not texts: return ""
        d = [np.linalg.norm(xy - p) for p, _ in texts]; k = int(np.argmin(d)); return texts[k][1] if d[k] < 200 else ""
    for q in uniq: q["name"] = label(np.array(q["p"][:2]))
    for l in lines: l["name"] = label((np.array(l["a"][:2]) + np.array(l["b"][:2]))/2)
    return uniq, lines


# ================= геометрия проекта (из model.json) =================
def _plane(room, key):
    C = np.array([[c["x"], c["y"], c[key]] for c in room["corners"]], float)
    if len(C) < 3: return np.array([0.0, 0.0, C[:, 2].mean() if len(C) else 0.0])
    A = np.c_[C[:, :2], np.ones(len(C))]; return np.linalg.lstsq(A, C[:, 2], rcond=None)[0]


def zf(room, xy): k = _plane(room, "floor"); return float(k[0]*xy[0] + k[1]*xy[1] + k[2])
def zc(room, xy): k = _plane(room, "ceil"); return float(k[0]*xy[0] + k[1]*xy[1] + k[2])


def _inside(poly, p):
    x, y = p; ins = False
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0)*(x1 - x0)/(y1 - y0): ins = not ins
    return ins


def room_at(model, xy, name=None):
    R = model.get("rooms", []) if model else []
    if not R: return None
    if name:
        for r in R:
            if r["name"] == name: return r
    for r in R:
        if _inside([tuple(p) for p in r["outline"]], xy): return r
    return R[0]


def wall_frame(room, wall, corner=0):
    """Стена прямая: начало (угол), направление, длина, нормаль в комнату, пол в начале."""
    w = next((x for x in room["walls"] if x["name"] == wall), None)
    if w is None or w["type"] != "L": raise ValueError(f"нет прямой стены {wall}")
    a, b = np.array(w["a"], float), np.array(w["b"], float)
    nn = np.array([-(b - a)[1], (b - a)[0]]); nn /= np.linalg.norm(nn)           # контур CCW: комната слева от a->b
    o, e = (a, b) if corner == 0 else (b, a)
    L = float(np.linalg.norm(e - o)); d = (e - o)/L
    return dict(o=o, d=d, L=L, n=nn, zo=zf(room, o), name=wall, corner=wall.split("-")[corner])


def left_corner(room, wall):
    """Какой угол стены левый, если стоять в комнате лицом к стене (0 = первый в имени, 1 = второй)."""
    f = wall_frame(room, wall, 0); right = np.r_[-f["n"][1], f["n"][0]]               # взгляд = -n, вправо = (-n_y, n_x)
    return 1 if right @ f["d"] < 0 else 0


def near_wall(model, xy, tol=40.0):
    best = None
    for r in (model or {}).get("rooms", []):
        for w in r["walls"]:
            if w["type"] != "L": continue
            a, b = np.array(w["a"]), np.array(w["b"]); d = b - a; L = np.linalg.norm(d); d = d/L
            s = float(np.clip((xy - a) @ d, 0, L)); dist = float(np.linalg.norm(a + s*d - xy))
            if dist < tol and (best is None or dist < best[0]): best = (dist, np.r_[-d[1], d[0], 0.0], w["name"], r["name"])
    return best


# ================= цели выноса =================
def targets(path, model, p):
    """Цели в кадре проекта. p: layers, mode (plan|wall), room, wall, corner (0|1), hmode (dxf|floor|ceil|h), h.
    -> [dict(id, name, kind, P (точка) или A/B (линия), n (нормаль поверхности или None), src, note)]."""
    pts, lines = read_dxf(path, p.get("layers") or None)
    out = []; mode = p.get("mode", "plan")
    if mode == "wall":
        room = room_at(model, (0, 0), p.get("room"))
        if room is None: raise RuntimeError("нет модели помещения — сначала «Скан»")
        fr = wall_frame(room, p["wall"], int(p.get("corner", 0))); n3 = np.r_[fr["n"], 0.0]
        def m(q):
            u, hh = q[0], q[1]; xy = fr["o"] + u*fr["d"]
            note = "" if -50 <= u <= fr["L"] + 50 else "за пределами стены"
            return np.r_[xy, fr["zo"] + hh], note
        for q in sorted(pts, key=lambda q: (round(q["p"][0]), q["p"][1])):
            P, note = m(q["p"]); out.append(dict(kind="pt", name=q["name"] or q["kind"], P=P, n=n3, src=q["p"][:2], note=note, layer=q["layer"]))
        for l in lines:
            A, na = m(l["a"]); B, nb = m(l["b"])
            out.append(dict(kind="line", name=l["name"] or "линия", A=A, B=B, n=n3, src=l["a"][:2] + l["b"][:2], note=na or nb, layer=l["layer"]))
    else:
        hm = p.get("hmode", "dxf"); H = float(p.get("h", 0) or 0)
        def m(q):
            xy = np.array(q[:2], float); room = room_at(model, xy, p.get("room")); n = None; note = ""
            if hm == "dxf" or room is None:
                z = q[2]
                if room is None and hm != "dxf": note = "нет модели: Z из DXF"
            elif hm == "floor": z = zf(room, xy); n = np.r_[0, 0, 1.0]
            elif hm == "ceil": z = zc(room, xy); n = np.r_[0, 0, -1.0]
            else: z = zf(room, xy) + H
            if n is None:
                w = near_wall(model, xy)
                if w: n = w[1]; note = note or f"на стене {w[2]}"
                elif room is not None and abs(z - zf(room, xy)) < 30: n = np.r_[0, 0, 1.0]
                elif room is not None and abs(z - zc(room, xy)) < 30: n = np.r_[0, 0, -1.0]
            return np.r_[xy, z], n, note
        for q in sorted(pts, key=lambda q: (q["layer"], round(q["p"][0]), q["p"][1])):
            P, n, note = m(q["p"]); out.append(dict(kind="pt", name=q["name"] or q["kind"], P=P, n=n, src=q["p"][:2], note=note, layer=q["layer"]))
        for l in lines:
            A, na, x1 = m(l["a"]); B, nb, x2 = m(l["b"])
            out.append(dict(kind="line", name=l["name"] or "линия", A=A, B=B, n=na if na is not None else nb, src=l["a"][:2] + l["b"][:2], note=x1 or x2, layer=l["layer"]))
    for k, t in enumerate(out): t["id"] = k + 1
    return out


def line_points(A, B, step):
    A, B = np.asarray(A, float), np.asarray(B, float); L = np.linalg.norm(B - A); n = max(1, int(math.ceil(L/step)))
    return [A + (B - A)*k/n for k in range(n + 1)]


# ================= вынос точки (итерации по замеру) =================
def stake(measure_at, P, n, iters=4, tol=0.3):
    """measure_at(Q) -> X: навести луч на Q (кадр станции), замерить, вернуть точку попадания.
    Поверхность не совпадает с проектной плоскостью (стена неровная) -> попадание смещено вдоль стены.
    Сдвигаем прицел на это смещение, пока точка на поверхности не встанет над проектной (вдоль нормали).
    -> X, dict(lat — остаток смещения вдоль поверхности, dev — отклонение поверхности по нормали
       (+ = выступает в комнату / пол выше проекта), it — итераций)."""
    P = np.asarray(P, float); Q = P.copy(); n = None if n is None else np.asarray(n, float)/np.linalg.norm(n)
    for k in range(iters):
        X = measure_at(Q); err = P - X
        if n is None:
            return X, dict(lat=0.0, dev=float(np.linalg.norm(X) - np.linalg.norm(P)), it=k + 1, free=True)
        lat = err - (err @ n)*n
        if np.linalg.norm(lat) < tol: break
        Q = Q + lat
    return X, dict(lat=float(np.linalg.norm(lat)), dev=float((X - P) @ n), it=k + 1, free=False)


# ================= свободная станция =================
def resect(A, B):
    """A — точки в кадре станции (по уровню), B — те же точки в кадре проекта. 4 степени свободы
    (поворот вокруг Z + сдвиг XYZ): станция выставлена по уровню. -> R, t, отчёт (P = R X + t)."""
    A, B = np.asarray(A, float), np.asarray(B, float)
    if len(A) < 2: raise RuntimeError("нужно ≥2 точки с известными координатами (лучше 3)")
    a0, b0 = A[:, :2].mean(0), B[:, :2].mean(0); Aa, Bb = A[:, :2] - a0, B[:, :2] - b0
    if np.linalg.norm(Aa, axis=1).max() < 300: raise RuntimeError("точки слишком близко друг к другу (нужно ≥0,5 м в плане)")
    th = math.atan2(sum(p[0]*q[1] - p[1]*q[0] for p, q in zip(Aa, Bb)), sum(p @ q for p, q in zip(Aa, Bb)))
    c, s = math.cos(th), math.sin(th); R = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])
    t = np.r_[b0 - R[:2, :2] @ a0, (B[:, 2] - A[:, 2]).mean()]
    E = A @ R.T + t - B; e = np.linalg.norm(E, axis=1)
    return R, t, dict(n=len(A), rms=float(np.sqrt((e**2).mean())), max=float(e.max()), err=e.round(2).tolist(),
                      dz=float(np.abs(E[:, 2]).max()))


# ================= проект — факт =================
def compare(path, layers, model, outdxf=None):
    """Стены проекта (отрезки DXF на выбранных слоях) против отсканированных: смещение концов стены
    от проектной линии (+ = стена выступает в комнату), разница угла, длины; углы — до ближайшей вершины проекта."""
    _, lines = read_dxf(path, layers or None)
    segs = [(np.array(l["a"][:2]), np.array(l["b"][:2])) for l in lines]
    if not segs: raise RuntimeError("в DXF нет отрезков на выбранных слоях")
    V = np.array([p for s in segs for p in s])
    walls, corners = [], []
    for r in model.get("rooms", []):
        for w in r["walls"]:
            if w["type"] != "L" or w.get("conn") or w["len"] < 150: continue
            a, b = np.array(w["a"]), np.array(w["b"]); d = (b - a)/np.linalg.norm(b - a); nn = np.r_[-d[1], d[0]]
            best = None
            for pa, pb in segs:
                pd = pb - pa; L = np.linalg.norm(pd); pd = pd/L
                ang = math.degrees(math.asin(max(-1, min(1, d[0]*pd[1] - d[1]*pd[0]))))
                if abs(ang) > 8 or abs(d @ pd) < 0.9: continue
                pn = np.r_[-pd[1], pd[0]]; da, db = (a - pa) @ pn, (b - pa) @ pn
                s = sorted([(a - pa) @ pd, (b - pa) @ pd]); ov = min(s[1], L) - max(s[0], 0)
                if ov < 0.3*min(L, w["len"]) or max(abs(da), abs(db)) > 300: continue
                sg = 1 if pn @ nn > 0 else -1
                cand = (abs(da) + abs(db), dict(wall=w["name"], room=r["name"], off_a=float(da*sg), off_b=float(db*sg),
                                                 ang=float(ang), len=w["len"], len_p=float(L)))
                if best is None or cand[0] < best[0]: best = cand
            walls.append(best[1] if best else dict(wall=w["name"], room=r["name"], off_a=None, off_b=None, ang=None, len=w["len"], len_p=None))
        for c in r["corners"]:
            p = np.array([c["x"], c["y"]]); k = int(np.argmin(np.linalg.norm(V - p, axis=1)))
            corners.append(dict(name=c["name"], room=r["name"], d=float(np.linalg.norm(V[k] - p)), dx=float(p[0] - V[k][0]), dy=float(p[1] - V[k][1])))
    if outdxf:
        import ezdxf
        from ezdxf.enums import TextEntityAlignment as TA
        doc = ezdxf.new("R2010", setup=True); doc.units = ezdxf.units.MM; msp = doc.modelspace()
        for lay, col in (("PROJECT", 3), ("FACT", 7), ("DEVIATION", 1)): doc.layers.add(lay, color=col)
        for pa, pb in segs: msp.add_line(tuple(pa), tuple(pb), dxfattribs={"layer": "PROJECT"})
        for r in model.get("rooms", []):
            msp.add_lwpolyline([tuple(p) for p in r["outline"]], close=True, dxfattribs={"layer": "FACT"})
            for w in r["walls"]:
                q = next((x for x in walls if x["wall"] == w["name"] and x["room"] == r["name"] and x["off_a"] is not None), None)
                if q is None: continue
                m = (np.array(w["a"]) + np.array(w["b"]))/2
                msp.add_text(f"{w['name']}: {q['off_a']:+.0f}/{q['off_b']:+.0f} мм, {q['ang']:+.2f}°", height=60,
                             dxfattribs={"layer": "DEVIATION"}).set_placement(tuple(map(float, m)), align=TA.MIDDLE_CENTER)
        doc.saveas(outdxf)
    return dict(walls=walls, corners=corners)
