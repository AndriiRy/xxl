#!/usr/bin/env python3
"""scan2dxf: облако полярных замеров станции (Hz, V, D) -> стены (RANSAC+МНК) -> углы,
плоскости пола/потолка -> высоты в углах -> DXF (план + 3D точки).
Вход JSON: {"cal": {...}, "points": [[hz_deg, v_deg, d_mm], ...]}
  v = 0 горизонт, +вверх. cal: d0 (смещение нуля дальномера, мм), hz0/v0 (индекс, град),
  tilt_x/tilt_y (наклон станции по инклинометру, град), e (вынос луча от оси наклона, мм).
Запуск: python3 scan2dxf.py scan.json out.dxf
"""
import json, math, os, sys
import numpy as np
import ezdxf
from ezdxf.enums import TextEntityAlignment

TOL = 6.0      # мм, порог инлаера RANSAC
MIN_PTS = 15   # мин. точек на стену


def to_xyz(P, cal):
    hz = np.radians(P[:, 0] - cal.get("hz0", 0)); v = np.radians(P[:, 1] - cal.get("v0", 0))
    d = P[:, 2] + cal.get("d0", 0)
    e = cal.get("e", 0)                                    # эксцентриситет луча
    x = d*np.cos(v)*np.cos(hz) - e*np.sin(hz)
    y = d*np.cos(v)*np.sin(hz) + e*np.cos(hz)
    z = d*np.sin(v)
    tx, ty = np.radians(cal.get("tilt_x", 0)), np.radians(cal.get("tilt_y", 0))
    Rx = np.array([[1, 0, 0], [0, math.cos(tx), -math.sin(tx)], [0, math.sin(tx), math.cos(tx)]])
    Ry = np.array([[math.cos(ty), 0, math.sin(ty)], [0, 1, 0], [-math.sin(ty), 0, math.cos(ty)]])
    return (Ry @ Rx @ np.vstack([x, y, z])).T


def fit_line(xy):                      # ортогональная регрессия: n·p = c
    m = xy.mean(0); _, _, vt = np.linalg.svd(xy - m)
    n = vt[1]; return n, n @ m


def ransac_lines(xy, rng=np.random.default_rng(0)):
    lines, rest = [], xy.copy()
    while len(rest) >= MIN_PTS:
        best = None
        for _ in range(400):
            a, b = rest[rng.choice(len(rest), 2, replace=False)]
            t = b - a; L = np.linalg.norm(t)
            if L < 200: continue
            n = np.array([-t[1], t[0]]) / L
            inl = np.abs((rest - a) @ n) < TOL
            if best is None or inl.sum() > best.sum(): best = inl
        if best is None or best.sum() < MIN_PTS: break
        for _ in range(3):                                  # уточнение МНК
            n, c = fit_line(rest[best]); best = np.abs(rest @ n - c) < TOL
        pts = rest[best]
        lines.append({"n": n, "c": c, "pts": pts, "rms": float(np.sqrt(np.mean((pts @ n - c)**2)))})
        rest = rest[~best]
    return lines


def corners(lines):
    n = len(lines)
    return np.array([np.linalg.solve(np.array([lines[k]["n"], lines[(k+1) % n]["n"]]),
                                     [lines[k]["c"], lines[(k+1) % n]["c"]]) for k in range(n)])


def coverage(l, a, b, bin_=50.0):       # доля отрезка стены a-b, покрытая точками
    t = b - a; L = np.linalg.norm(t)
    if L < 1: return 0.0
    s = (l["pts"] - a) @ (t / L)
    s = s[(s >= 0) & (s <= L)]
    return len(np.unique((s // bin_).astype(int))) / math.ceil(L / bin_)


def prune(lines):
    # отсев мебели/помех: обход по азимуту (видимая область звёздная), затем удаление
    # параллельных соседей (ближняя = мебель) и стен с покрытием < 50 % между своими углами
    ang = [math.atan2(*l["pts"].mean(0)[::-1]) for l in lines]
    lines = [lines[i] for i in np.argsort(ang)]
    while len(lines) > 3:
        n = len(lines); drop = None
        for k in range(n):
            a, b = lines[k], lines[(k+1) % n]
            if abs(np.linalg.det(np.array([a["n"], b["n"]]))) < 0.1:      # параллельны
                drop = k if abs(a["c"]) < abs(b["c"]) else (k+1) % n; break
        if drop is None:
            C = corners(lines)
            cov = [coverage(lines[k], C[k-1], C[k]) for k in range(n)]
            k = int(np.argmin(cov))
            if cov[k] < 0.5: drop = k
        if drop is None: break
        lines.pop(drop)
    return lines


def fit_plane(p):                      # z = a x + b y + c
    A = np.c_[p[:, 0], p[:, 1], np.ones(len(p))]
    k, *_ = np.linalg.lstsq(A, p[:, 2], rcond=None); return k


def main(src, dst):
    R = json.load(open(src)); cal = R.get("cal", {})
    P = np.array(R["points"], float); X = to_xyz(P, cal)
    wall = X[np.abs(P[:, 1] - cal.get("v0", 0)) < 30]       # профиль стен
    ceil = X[P[:, 1] > 50]; floor = X[P[:, 1] < -50]

    lines = ransac_lines(wall[:, :2])
    lines = prune(lines)
    C = corners(lines)

    kc = fit_plane(ceil) if len(ceil) > 10 else None
    kf = fit_plane(floor) if len(floor) > 10 else None
    z = lambda k, p: k[0]*p[0] + k[1]*p[1] + k[2]

    doc = ezdxf.new("R2010", setup=True); doc.units = ezdxf.units.MM; msp = doc.modelspace()
    for lay, col in (("WALLS", 7), ("DIM", 1), ("ANGLES", 3), ("HEIGHTS", 5), ("CLOUD", 8)):
        doc.layers.add(lay, color=col)
    msp.add_lwpolyline([tuple(p) for p in C], close=True, dxfattribs={"layer": "WALLS"})
    for p in X: msp.add_point(tuple(p), dxfattribs={"layer": "CLOUD"})
    cen = C.mean(0); n = len(C)
    print(f"Стен: {len(lines)}  СКО по стенам (мм): " + " ".join(f"{l['rms']:.1f}" for l in lines))
    for k in range(n):
        a, b = C[k], C[(k+1) % n]; t = b - a; nrm = np.array([-t[1], t[0]])
        off = 300 if np.dot((a+b)/2 - cen, nrm) > 0 else -300
        msp.add_aligned_dim(p1=tuple(a), p2=tuple(b), distance=off, dimstyle="EZDXF",
                            dxfattribs={"layer": "DIM"}).render()
        p, q = C[k-1] - C[k], C[(k+1) % n] - C[k]
        A = math.degrees(math.acos(np.clip(p @ q / np.linalg.norm(p) / np.linalg.norm(q), -1, 1)))
        tp = C[k] + (cen - C[k]) / np.linalg.norm(cen - C[k]) * 400
        txt = f"{chr(65+k)} {A:.2f}°"
        if kc is not None and kf is not None:
            txt += f" H{z(kc, C[k]) - z(kf, C[k]):.0f}"
        msp.add_text(txt, height=80, dxfattribs={"layer": "ANGLES"}
                     ).set_placement(tuple(tp), align=TextEntityAlignment.MIDDLE_CENTER)
        print(f"  {chr(65+k)}: x={C[k,0]:8.1f} y={C[k,1]:8.1f}  угол={A:6.2f}°  "
              f"{chr(65+k)}{chr(65+(k+1)%n)}={np.linalg.norm(t):7.1f}" +
              (f"  H={z(kc, C[k]) - z(kf, C[k]):.1f}" if kc is not None and kf is not None else ""))
    if kc is not None:
        sl = math.degrees(math.atan(math.hypot(kc[0], kc[1])))
        print(f"Потолок: уклон {sl:.3f}° ({math.tan(math.radians(sl))*1000:.1f} мм/м)")
    if kf is not None:
        sl = math.degrees(math.atan(math.hypot(kf[0], kf[1])))
        print(f"Пол:     уклон {sl:.3f}° ({math.tan(math.radians(sl))*1000:.1f} мм/м)")
    doc.saveas(dst)
    if kc is not None and kf is not None:                    # геометрия для фото/развёрток
        json.dump({"names": [chr(65+k) for k in range(n)], "corners": C.tolist(),
                   "floor": list(map(float, kf)), "ceiling": list(map(float, kc))},
                  open(os.path.splitext(dst)[0] + "_geom.json", "w"), indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
