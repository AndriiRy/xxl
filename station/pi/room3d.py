#!/usr/bin/env python3
"""room3d: замеры станции -> помещения (прямые + дуги), ниши/выступы, пол/потолок, неровности, 3D.
Проект = несколько стоянок (комнаты, лестница), связанных опорными точками (марками).
Система координат проекта: начало — угол A первой комнаты на полу, X — вдоль стены A-B, Y — внутрь, Z — вверх, мм.
  python3 room3d.py <папка_проекта>      (читает scan.json, пишет room.dxf, room_fusion.dxf, room.obj, room.stl, model.json)
Теги точек: 0 профиль, 1 пол/потолок, 2 уточнение кромки, 3 высота ниши/выступа.
"""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from scan2dxf import to_xyz

TOL = 8.0          # мм: допуск прямой/дуги (шум + неровность стены)
FULL_H = 25.0      # мм: ниша/выступ «на всю высоту», если край ближе к полу/потолку


# ================= аппроксимация =================
def line_fit(P):
    c = P.mean(0); _, _, vt = np.linalg.svd(P - c, full_matrices=False)
    d = vt[0]; n = np.array([-d[1], d[0]]); return c, d, n, (P - c) @ n


def circle_fit(P):
    A = np.c_[2*P, np.ones(len(P))]; s = np.linalg.lstsq(A, (P**2).sum(1), rcond=None)[0]
    c = s[:2].copy(); r = math.sqrt(max(s[2] + c @ c, 1e-9))
    for _ in range(10):
        q = P - c; dist = np.linalg.norm(q, axis=1); J = np.c_[-q/dist[:, None], -np.ones(len(P))]
        dl = np.linalg.lstsq(J, -(dist - r), rcond=None)[0]; c += dl[:2]; r += dl[2]
        if abs(dl).max() < 1e-4: break
    return c, r, np.linalg.norm(P - c, axis=1) - r


def dp(P, i0, i1, tol, out):
    if i1 - i0 < 2: return
    a, ab = P[i0], P[i1] - P[i0]; L = np.linalg.norm(ab); Q = P[i0:i1+1] - a
    dist = np.abs(ab[0]*Q[:, 1] - ab[1]*Q[:, 0]) / L if L > 1e-9 else np.linalg.norm(Q, axis=1)
    k = int(np.argmax(dist))
    if dist[k] > tol: m = i0 + k; out.add(m); dp(P, i0, m, tol, out); dp(P, m, i1, tol, out)


def fit_plane(p, it=6):
    """z = a x + b y + c, с отбрасыванием выбросов (люстра, мебель)."""
    m = np.ones(len(p), bool); k = np.zeros(3)
    for _ in range(it):
        A = np.c_[p[m, 0], p[m, 1], np.ones(m.sum())]; k = np.linalg.lstsq(A, p[m, 2], rcond=None)[0]
        r = p[:, 2] - (k[0]*p[:, 0] + k[1]*p[:, 1] + k[2]); s = max(2.0, 3*1.4826*np.median(np.abs(r[m] - np.median(r[m]))))
        m = np.abs(r) < s
    return k


def cross2(a, b): return a[0]*b[1] - a[1]*b[0]
def unit(v): return v / np.linalg.norm(v)
def rot2(t): c, s = math.cos(t), math.sin(t); return np.array([[c, -s], [s, c]])


# ================= элементы контура =================
def mk_line(Q, H, i0, i1):
    S = Q[i0:i1+1]; T = S[1:-1] if len(S) >= 8 else S
    c, d, n, res = line_fit(T)
    if (S[-1] - S[0]) @ d < 0: d = -d
    n = np.array([-d[1], d[0]])
    if (-c) @ n < 0: n = -n                                   # нормаль — к станции (внутрь помещения)
    pr = lambda p: c + ((p - c) @ d)*d
    return dict(type="L", c=c, d=d, n=n, p0=pr(S[0]), p1=pr(S[-1]), hz0=H[i0], hz1=H[i1], npts=len(S),
                rms=float(np.sqrt((res**2).mean())), i0=i0, i1=i1)


def mk_arc(Q, H, i0, i1):
    S = Q[i0:i1+1]; c, r, res = circle_fit(S[1:-1] if len(S) >= 10 else S)
    pr = lambda p: c + r*unit(p - c); pm = S[len(S)//2]
    ccw = cross2(S[0] - c, pm - c) > 0
    return dict(type="A", c=c, r=float(r), ccw=bool(ccw), p0=pr(S[0]), p1=pr(S[-1]), pm=pr(pm), hz0=H[i0], hz1=H[i1],
                npts=len(S), rms=float(np.sqrt((res**2).mean())), i0=i0, i1=i1)


def chain_elements(Q, H):
    n = len(Q)
    if n < 4: return []
    br = {0, n - 1}; dp(Q, 0, n - 1, TOL, br); br = sorted(br)
    pcs = [(br[i], br[i+1]) for i in range(len(br) - 1)]
    els = []; i = 0
    while i < len(pcs):
        best = None
        for j in range(i + 1, len(pcs)):
            S = Q[pcs[i][0]:pcs[j][1] + 1]
            if len(S) < 8: continue
            c, r, res = circle_fit(S)
            if not (60 < r < 6000) or np.abs(res).max() > TOL or np.sqrt((res**2).mean()) > TOL/3: break
            if np.abs(line_fit(S)[3]).max() < TOL: break
            a = np.unwrap(np.arctan2(S[:, 1] - c[1], S[:, 0] - c[0])); best = (j, math.degrees(abs(a[-1] - a[0])))
        if best and (best[0] - i >= 2 or best[1] > 25):
            els.append(mk_arc(Q, H, pcs[i][0], pcs[best[0]][1])); i = best[0] + 1
        else:
            els.append(mk_line(Q, H, *pcs[i])); i += 1
    k = 0                                                     # короткие прямые у концов дуги -> в дугу
    while k < len(els):
        e = els[k]
        if e["type"] == "A":
            for nb in (k + 1, k - 1):
                if 0 <= nb < len(els) and els[nb]["type"] == "L" and np.linalg.norm(els[nb]["p1"] - els[nb]["p0"]) < 200:
                    i0, i1 = min(e["i0"], els[nb]["i0"]), max(e["i1"], els[nb]["i1"])
                    c, r, res = circle_fit(Q[i0:i1 + 1])
                    if np.abs(res).max() < TOL and abs(r - e["r"]) < 0.05*e["r"]:
                        els[min(k, nb)] = mk_arc(Q, H, i0, i1); del els[max(k, nb)]; k = min(k, nb); e = els[k]
        k += 1
    k = 0                                                     # слияние соосных прямых
    while k < len(els) - 1:
        a, b = els[k], els[k+1]
        if a["type"] == b["type"] == "L" and abs(cross2(a["d"], b["d"])) < math.sin(math.radians(3)):
            m = mk_line(Q, H, a["i0"], b["i1"])
            if m["rms"] < TOL/2.5: els[k:k+2] = [m]; continue
        k += 1
    els = [e for e in els if not (e["type"] == "L" and (e["npts"] < 4 or np.linalg.norm(e["p1"] - e["p0"]) < 40))]
    for e in els:                                             # дотянуть до крайних точек в допуске (кромки)
        dist = (lambda p: abs((p - e["c"]) @ e["n"])) if e["type"] == "L" else (lambda p: abs(np.linalg.norm(p - e["c"]) - e["r"]))
        pr = (lambda p: e["c"] + ((p - e["c"]) @ e["d"])*e["d"]) if e["type"] == "L" else (lambda p: e["c"] + e["r"]*unit(p - e["c"]))
        while e["i1"] + 1 < n and dist(Q[e["i1"] + 1]) < TOL: e["i1"] += 1
        while e["i0"] > 0 and dist(Q[e["i0"] - 1]) < TOL: e["i0"] -= 1
        e["p0"], e["p1"], e["hz0"], e["hz1"] = pr(Q[e["i0"]]), pr(Q[e["i1"]]), H[e["i0"]], H[e["i1"]]
    return els


def circle_line(c, r, p, d):
    f = p - c; b = f @ d; disc = b*b - (f @ f - r*r)
    if disc < 0: return []
    s = math.sqrt(disc); return [p + (-b - s)*d, p + (-b + s)*d]


def junction(e, f):
    """Стык соседних элементов -> (точки, запрос уточнения кромки или None)."""
    if e["type"] == f["type"] == "L":
        cr = cross2(e["d"], f["d"])
        if abs(cr) > math.sin(math.radians(12)):
            t = cross2(f["c"] - e["c"], f["d"]) / cr; X = e["c"] + t*e["d"]
            if np.linalg.norm(X - e["p1"]) < 1500 and np.linalg.norm(X - f["p0"]) < 1500: return [X], None
        if np.linalg.norm(e["p1"]) <= np.linalg.norm(f["p0"]):        # ближняя кромка — настоящий угол
            P = e["p1"]; Qf = P + ((f["c"] - P) @ f["n"])*f["n"]
            return [P, Qf], dict(near="e", hz_in=e["hz1"], hz_out=f["hz0"], c=e["c"].tolist(), n=e["n"].tolist())
        Qf = f["p0"]; P = Qf + ((e["c"] - Qf) @ e["n"])*e["n"]
        return [P, Qf], dict(near="f", hz_in=f["hz0"], hz_out=e["hz1"], c=f["c"].tolist(), n=f["n"].tolist())
    if e["type"] == "A" and f["type"] == "A":
        return [(e["p1"] + f["p0"])/2], None
    A, L = (e, f) if e["type"] == "A" else (f, e)
    endA = A["p1"] if A is e else A["p0"]
    X = circle_line(A["c"], A["r"], L["c"], L["d"])
    if X:
        X = min(X, key=lambda q: np.linalg.norm(q - endA))
        if np.linalg.norm(X - endA) < 2*A["r"] + 300: return [X], None
    foot = L["c"] + ((endA - L["c"]) @ L["d"])*L["d"]
    return ([endA, foot] if A is e else [foot, endA]), None


def try_merge(e, f):
    """Склейка соседних элементов через ложный разрыв (скользящий луч): одна прямая или одна дуга."""
    S = np.r_[e["pts"], f["pts"]]; Hh = np.r_[e["hzs"], f["hzs"]]
    short = lambda x: x["type"] == "L" and np.linalg.norm(x["p1"] - x["p0"]) < 300
    if e["type"] == f["type"] == "L" and abs(cross2(e["d"], f["d"])) < math.sin(math.radians(3)):
        m = mk_line(S, Hh, 0, len(S) - 1)
        if m["rms"] < TOL/2.5 and abs(line_fit(S)[3]).max() < TOL: m["pts"], m["hzs"] = S, Hh; return m
    if "A" in (e["type"], f["type"]) or (short(e) and short(f)):
        if not ("A" in (e["type"], f["type"]) or len(S) >= 8): return None
        if e["type"] == "L" and not short(e) or f["type"] == "L" and not short(f): return None
        c, r, res = circle_fit(S)
        if 60 < r < 6000 and np.abs(res).max() < TOL and np.sqrt((res**2).mean()) < TOL/3 and np.abs(line_fit(S)[3]).max() > TOL:
            m = mk_arc(S, Hh, 0, len(S) - 1); m["pts"], m["hzs"] = S, Hh; return m
    return None


def merge_across(els):
    changed = True
    while changed:
        changed = False
        for k in range(len(els) - 1):
            m = try_merge(els[k], els[k + 1])
            if m is not None:
                if m["type"] == "A" and "A" not in (els[k]["type"], els[k + 1]["type"]):
                    a = [x for x in (els[k - 1] if k else None, els[k + 2] if k + 2 < len(els) else None) if x and x["type"] == "A"]
                    if not a: continue                                 # две короткие прямые -> дуга только рядом с дугой
                els[k:k + 2] = [m]; changed = True; break
    return els


def analyze_profile(XY, HZ, closed=True):
    """XY — точки по возрастанию Hz (кадр станции). -> segs (контур), refine (кромки для уточнения)."""
    o = np.argsort(HZ); XY, HZ = XY[o], HZ[o]; n = len(XY)
    nxt = np.r_[XY[1:], XY[:1]]; g = np.linalg.norm(nxt - XY, axis=1)
    dth = np.radians(np.abs((np.r_[HZ[1:], HZ[:1] + 360] - HZ)))
    r = np.maximum(np.linalg.norm(XY, axis=1), np.linalg.norm(nxt, axis=1))
    gap = (g > 5*dth*r + 25) & (g > 40)
    if not closed: gap[-1] = True
    gi = np.where(gap)[0]; start = (gi[0] + 1) % n if len(gi) else 0
    order = [(start + k) % n for k in range(n)]
    chains, cur = [], []
    for idx in order:
        cur.append(idx)
        if gap[idx]: chains.append(cur); cur = []
    if cur: chains.append(cur)
    els = []
    for ch in chains:
        ce = chain_elements(XY[ch], HZ[ch])
        for e in ce: e["pts"] = XY[ch][e["i0"]:e["i1"]+1]; e["hzs"] = HZ[ch][e["i0"]:e["i1"]+1]
        els += ce
    els = merge_across(els)
    if closed and not len(gi) and len(els) > 2 and els[0]["type"] == els[-1]["type"] == "L" and \
       abs(cross2(els[0]["d"], els[-1]["d"])) < math.sin(math.radians(3)):
        S = np.r_[els[-1]["pts"], els[0]["pts"]]; Hh = np.r_[np.full(len(els[-1]["pts"]), els[-1]["hz0"]),
                                                            np.full(len(els[0]["pts"]), els[0]["hz1"])]
        m = mk_line(S, Hh, 0, len(S) - 1); m["pts"] = S; els = [m] + els[1:-1]
    if len(els) < 2: return dict(segs=[], refine=[])
    J, refine = [], []
    m = len(els)
    for k in range(m if closed else m - 1):
        pts, rq = junction(els[k], els[(k + 1) % m]); J.append(pts)
        if rq: refine.append(rq)
    segs = []
    for k in range(m):
        a = J[k - 1][-1] if (closed or k > 0) else els[k]["p0"]
        b = J[k][0] if (closed or k < m - 1) else els[k]["p1"]
        e = els[k]
        s = dict(type=e["type"], a=a, b=b, rms=e["rms"], npts=e["npts"])
        if e["type"] == "A": s.update(c=e["c"], r=e["r"], ccw=e["ccw"])
        segs.append(s)
        if (closed or k < m - 1) and len(J[k]) == 2: segs.append(dict(type="L", a=J[k][0], b=J[k][1], conn=True))
    return dict(segs=segs, refine=refine)


# ================= геометрия сегментов =================
def arc_sweep(s):
    a0 = math.atan2(*(s["a"] - s["c"])[::-1]); a1 = math.atan2(*(s["b"] - s["c"])[::-1]); sw = a1 - a0
    sw = sw % (2*math.pi) if s["ccw"] else -((-sw) % (2*math.pi))
    return a0, sw


def seg_len(s): return s["r"]*abs(arc_sweep(s)[1]) if s["type"] == "A" else float(np.linalg.norm(s["b"] - s["a"]))


def seg_pts(s, step=3.0):
    if s["type"] != "A": return [s["a"], s["b"]]
    a0, sw = arc_sweep(s); k = max(2, int(abs(math.degrees(sw))/step) + 1)
    return [s["c"] + s["r"]*np.array([math.cos(a0 + sw*t), math.sin(a0 + sw*t)]) for t in np.linspace(0, 1, k)]


def tangent(s, end):
    if s["type"] != "A": return unit(s["b"] - s["a"])
    p = s["b"] if end else s["a"]; q = p - s["c"]; t = np.array([-q[1], q[0]]) / np.linalg.norm(q)
    return t if s["ccw"] else -t


def polyline(segs):
    out = []
    for s in segs: out += seg_pts(s)[:-1]
    return np.array(out)


def point_seg_dist(p, s):
    if s["type"] == "A": return abs(np.linalg.norm(p - s["c"]) - s["r"])
    ab = s["b"] - s["a"]; t = np.clip((p - s["a"]) @ ab / (ab @ ab), 0, 1); return float(np.linalg.norm(p - s["a"] - t*ab))


def features(segs, closed=True):
    """Ниши/выступы: цепочка коротких сегментов между двумя соосными стенами."""
    n = len(segs); used = set(); F = []
    for i in range(n):
        if segs[i]["type"] != "L" or i in used or seg_len(segs[i]) < 200: continue
        d1 = unit(segs[i]["b"] - segs[i]["a"]); n1 = np.array([-d1[1], d1[0]])
        for span in range(2, 8):
            j = i + span
            if not closed and j >= n: break
            jj = j % n; ch = [(i + k) % n for k in range(1, span)]
            if jj == i or any(c in used for c in ch) or sum(seg_len(segs[c]) for c in ch) > 5000: break
            if segs[jj]["type"] != "L" or seg_len(segs[jj]) < 200: continue
            d2 = unit(segs[jj]["b"] - segs[jj]["a"])
            if d1 @ d2 < math.cos(math.radians(2)) or abs((segs[jj]["a"] - segs[i]["a"]) @ n1) > 15: continue
            P = np.array([p for c in ch for p in seg_pts(segs[c])]); s = (P - segs[i]["b"]) @ n1
            dep = float(s[np.argmax(np.abs(s))]); arc = [c for c in ch if segs[c]["type"] == "A"]
            kind = ("полукруглый выступ" if dep > 0 else "полукруглая ниша") if arc else ("выступ" if dep > 0 else "ниша")
            f = dict(kind=kind, i=i, j=jj, chain=ch, width=float((segs[jj]["a"] - segs[i]["b"]) @ d1),
                     depth=abs(dep), a=segs[i]["b"], b=segs[jj]["a"], out=dep < 0)
            if arc:
                s0 = segs[arc[0]]; f.update(r=s0["r"], arclen=seg_len(s0), chord=float(np.linalg.norm(s0["b"] - s0["a"])))
            F.append(f); used.update(ch); break
    return F


def niche_masks(f, X):
    """Точки внутри ниши (за линией стены) и на линии стены в пределах ширины проёма."""
    a, b = np.asarray(f["a"]), np.asarray(f["b"]); d = unit(b - a); n1 = np.array([-d[1], d[0]])
    s = (X[:, :2] - a) @ n1; t = (X[:, :2] - a) @ d; L = float(np.linalg.norm(b - a))
    within = (t > -5) & (t < L + 5)
    return within & (s < -TOL), within & (np.abs(s) < TOL)


def face_of(f, segs):
    """Главная грань ниши/выступа: самая глубокая (ниша) / самая выдвинутая (выступ)."""
    d1 = unit(f["b"] - f["a"]); n1 = np.array([-d1[1], d1[0]])
    best = max(f["chain"], key=lambda c: abs((np.mean(seg_pts(segs[c]), 0) - f["a"]) @ n1) + seg_len(segs[c])*1e-3)
    s = segs[best]; P = seg_pts(s); mid = s["c"] + s["r"]*unit(np.mean(P, 0) - s["c"]) if s["type"] == "A" else (s["a"] + s["b"])/2
    if s["type"] == "A" and f["kind"] == "полукруглый выступ":
        mid = s["c"] + s["r"]*unit(-s["c"]) if np.linalg.norm(s["c"]) > s["r"] else mid   # ближайшая к станции точка дуги
    return s, mid


# ================= стоянка =================
def setup_points(st):
    P = np.array(st["points"], float)
    if P.shape[1] == 3: P = np.c_[P, np.where(np.abs(P[:, 1]) < 30, 0, 1)]
    return P, to_xyz(P[:, :3], st.get("cal", {}))


def floor_ceiling(st, P, X):
    """Пол — нижний плоский кластер, потолок — верхний (люстры, мебель, стены отсекаются).
    Без штатива: точки ближе 400 мм (свой корпус) отброшены; на столе — и сама столешница."""
    v0 = st.get("cal", {}).get("v0", 0); tag = P[:, 3]; rho = np.hypot(X[:, 0], X[:, 1])
    ok = (tag == 1) & (P[:, 2] > 400) & (rho > 300)
    up, dn = ok & (P[:, 1] - v0 > 15), ok & (P[:, 1] - v0 < -3)
    if st.get("mount") == "table": dn &= ~((X[:, 2] > -st.get("base_drop", 212) - 60) & (rho < 2500))
    kf = kc = None
    F, C = X[dn], X[up]
    if len(F) > 8: F = F[F[:, 2] < np.percentile(F[:, 2], 5) + 40]
    if len(C) > 8: C = C[C[:, 2] > np.percentile(C[:, 2], 95) - 40]
    fp = st.get("floor_pts") or []
    if fp:                                                            # отвес / точки пола вручную
        Q = to_xyz(np.array(fp, float)[:, :3], st.get("cal", {})); F = np.r_[F, Q] if len(F) > 8 else Q
    if len(F) > 8: kf = fit_plane(F)
    elif len(F): kf = fit_plane(F, it=1) if len(F) >= 3 else np.array([0, 0, F[:, 2].mean()])
    if len(C) > 8: kc = fit_plane(C)
    return kf, kc


def analyze_setup(st):
    P, X = setup_points(st); tag = P[:, 3]
    prof = np.isin(tag, (0, 2))
    R = analyze_profile(X[prof, :2], P[prof, 0], closed=True)
    segs = R["segs"]
    if not segs: return dict(segs=[], refine=[], features=[], floor=None, ceil=None, X=X, P=P)
    kf, kc = floor_ceiling(st, P, X)
    F = features(segs)
    vp = X[tag == 3]
    for f in F:
        s, mid = face_of(f, segs); f["probe"] = mid.tolist()
        if f["out"] and len(vp):                                    # ниша: размер ПРОЁМА по кромкам на плоскости стены
            inn, onw = niche_masks(f, vp)
            zf_ = kf[0]*mid[0] + kf[1]*mid[1] + kf[2] if kf is not None else -1e9
            zc_ = kc[0]*mid[0] + kc[1]*mid[1] + kc[2] if kc is not None else 1e9
            if inn.sum() >= 2:
                zi = vp[inn, 2]; zm = zi.mean(); W_ = vp[onw]
                lo, hi = W_[W_[:, 2] < zm, 2], W_[W_[:, 2] > zm, 2]
                f["z0"] = float(lo.max()) if len(lo) else float(min(zi.min(), zf_))
                f["z1"] = float(hi.min()) if len(hi) else float(max(zi.max(), zc_))
                f["full"] = f["z0"] < zf_ + FULL_H and f["z1"] > zc_ - FULL_H
                continue
        on = vp[[point_seg_dist(p[:2], s) < TOL for p in vp]] if len(vp) else vp
        zf = kf[0]*mid[0] + kf[1]*mid[1] + kf[2] if kf is not None else -1e9
        zc = kc[0]*mid[0] + kc[1]*mid[1] + kc[2] if kc is not None else 1e9
        if len(on) >= 2:
            f["z0"], f["z1"] = float(on[:, 2].min()), float(on[:, 2].max())
            f["full"] = f["z0"] < zf + FULL_H and f["z1"] > zc - FULL_H
        else:
            f["z0"], f["z1"], f["full"] = zf, zc, True
    return dict(segs=segs, refine=R["refine"], features=F, floor=kf, ceil=kc, X=X, P=P)


# ================= регистрация стоянок по маркам =================
def register(setups):
    """Каждая стоянка выставлена по уровню (авто-нивелир) -> 4 степени свободы: поворот вокруг Z + сдвиг XYZ."""
    refs = []
    for st in setups:
        R = {}
        for k, v in st.get("refs", {}).items():
            R[k] = to_xyz(np.array([v[:3]], float), st.get("cal", {}))[0]
        refs.append(R)
    T = [None]*len(setups); T[0] = (0.0, np.zeros(3)); res = [dict(n=0, rms=0.0, max=0.0)] + [None]*(len(setups) - 1)
    known = {k: v for k, v in refs[0].items()}
    for _ in range(len(setups)):
        for i in range(1, len(setups)):
            if T[i] is not None: continue
            ids = [k for k in refs[i] if k in known]
            if len(ids) < 2: continue
            A = np.array([refs[i][k] for k in ids]); B = np.array([known[k] for k in ids])
            a0, b0 = A[:, :2].mean(0), B[:, :2].mean(0); Aa, Bb = A[:, :2] - a0, B[:, :2] - b0
            th = math.atan2(sum(cross2(p, q) for p, q in zip(Aa, Bb)), sum(p @ q for p, q in zip(Aa, Bb)))
            t = np.r_[b0 - rot2(th) @ a0, (B[:, 2] - A[:, 2]).mean()]
            T[i] = (th, t)
            e = np.array([np.linalg.norm(apply(T[i], refs[i][k]) - known[k]) for k in ids])
            res[i] = dict(n=len(ids), rms=float(np.sqrt((e**2).mean())), max=float(e.max()), ids=ids)
            for k, v in refs[i].items():
                if k not in known: known[k] = apply(T[i], v)
    return T, res, known


def apply(T, p):
    th, t = T; p = np.asarray(p, float); q = np.empty_like(p)
    q[..., :2] = p[..., :2] @ rot2(th).T + t[:2]; q[..., 2] = p[..., 2] + t[2]; return q


# ================= неровности =================
def surface_report(sf, Xp, name, outdir):
    """Стена: зазор до вертикальной плоскости по самой выступающей точке (монтаж шкафов), плоскостность, вертикаль.
    Пол: подъём ножек от самой высокой точки."""
    from PIL import Image, ImageDraw
    okm = np.isfinite(Xp).all(1); Xp = Xp[okm]                         # пропущенные точки сетки (не видно со стоянки)
    ns, nt = sf["ns"], sf["nt"]; a, b = np.array(sf["a"]), np.array(sf["b"]); d = unit(b - a); nrm = np.array([-d[1], d[0]])
    s = (Xp[:, :2] - a) @ d; z = Xp[:, 2]
    if sf["kind"] == "wall":
        w = (Xp[:, :2] - a) @ nrm                                       # + в комнату
        A = np.c_[s, z, np.ones(len(s))]; k = np.linalg.lstsq(A, w, rcond=None)[0]
        best = w - A @ k
        al = np.linalg.lstsq(np.c_[s, np.ones(len(s))], w, rcond=None)[0][0]
        gap = (w - al*s).max() - (w - al*s)
        st = dict(flatness=float(best.max() - best.min()), plumb_mm_m=float(k[1]*1000),
                  plumb_mm=float(k[1]*(z.max() - z.min())), gap_max=float(gap.max()),
                  bulge=[float(s[np.argmax(best)]), float(z[np.argmax(best)])])
        val, u, v = gap, s, z; title = (f"{name}: zazor do vertikali max {gap.max():.1f} mm | ploskostnost {st['flatness']:.1f} | "
                                       f"vertikal {st['plumb_mm_m']:+.2f} mm/m")
    else:
        t = (Xp[:, :2] - a) @ nrm; val = z.max() - z
        st = dict(level_range=float(z.max() - z.min()), high=[float(s[np.argmax(z)]), float(t[np.argmax(z)])],
                  slope_mm_m=float(np.hypot(*np.linalg.lstsq(np.c_[s, t, np.ones(len(s))], z, rcond=None)[0][:2])*1000))
        u, v = s, t; title = f"{name}: nozhki ot vysshey tochki 0..{val.max():.1f} mm | uklon {st['slope_mm_m']:.1f} mm/m"
    sc = 0.25; pad = 60; U0, V0 = u.min(), v.min(); Wd = int((u.max() - U0)*sc) + 2*pad; Ht = int((v.max() - V0)*sc) + 2*pad + 30
    im = Image.new("RGB", (Wd, Ht), (255, 255, 255)); dr = ImageDraw.Draw(im)
    try:
        from PIL import ImageFont; fnt = ImageFont.truetype("DejaVuSans.ttf", 11); fbig = ImageFont.truetype("DejaVuSans.ttf", 14)
    except Exception:
        fnt = fbig = None
    vmax = max(1.0, float(val.max())); cs = sf["step"]*sc
    for uu, vv, x in zip(u, v, val):
        q = min(1, x/vmax); col = (int(255 - 200*q), int(255 - 150*q), int(255 - 40*q))
        X0 = pad + (uu - U0)*sc - cs/2; Y0 = Ht - pad - (vv - V0)*sc - cs/2
        dr.rectangle([X0, Y0, X0 + cs, Y0 + cs], fill=col)
        if cs >= 22: dr.text((X0 + 2, Y0 + cs/2 - 6), f"{x:.0f}" if x >= 9.5 else f"{x:.1f}", fill=(0, 0, 0), font=fnt)
    dr.text((10, 8), title, fill=(0, 0, 0), font=fbig)
    for mm in range(0, int(u.max() - U0) + 1, 500):
        X0 = pad + mm*sc; dr.line([(X0, Ht - pad + 8), (X0, Ht - pad + 14)], fill=(200, 0, 0)); dr.text((X0 - 8, Ht - pad + 16), str(int(mm + U0)), fill=(200, 0, 0), font=fnt)
    for mm in range(0, int(v.max() - V0) + 1, 500):
        Y0 = Ht - pad - mm*sc; dr.line([(pad - 14, Y0), (pad - 8, Y0)], fill=(200, 0, 0)); dr.text((4, Y0 - 6), str(int(mm + V0)), fill=(200, 0, 0), font=fnt)
    fn = f"surface_{name.replace(' ', '_')}.png"; im.save(os.path.join(outdir, fn))
    vf = np.full(len(okm), np.nan); vf[okm] = val; st["missing"] = int((~okm).sum())
    return st, vf, fn


# ================= 3D =================
def ear_clip(poly):
    P = [np.asarray(p, float) for p in poly]; idx = list(range(len(P))); tris = []
    area = sum(cross2(P[i], P[(i+1) % len(P)]) for i in range(len(P)))
    if area < 0: idx.reverse()
    def inside(p, a, b, c):
        return cross2(b - a, p - a) >= -1e-9 and cross2(c - b, p - b) >= -1e-9 and cross2(a - c, p - c) >= -1e-9
    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1; ok = False
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]; a, b, c = P[i0], P[i1], P[i2]
            if cross2(b - a, c - b) <= 1e-9: continue
            if any(inside(P[j], a, b, c) for j in idx if j not in (i0, i1, i2)): continue
            tris.append((i0, i1, i2)); idx.pop(k); ok = True; break
        if not ok: break
    if len(idx) == 3: tris.append(tuple(idx))
    return tris                                                        # против часовой стрелки


class Mesh:
    def __init__(self): self.T, self.C, self.G = [], [], []
    def tri(self, a, b, c, col, grp): self.T.append([list(map(float, a)), list(map(float, b)), list(map(float, c))]); self.C.append(col); self.G.append(grp)
    def quad(self, a, b, c, d, col, grp): self.tri(a, b, c, col, grp); self.tri(a, c, d, col, grp)
    def wall(self, p, q, zf, zc, col, grp, z0=None, z1=None):
        """Вертикальная грань p->q (внутренняя сторона слева), от zf(xy) до zc(xy); опционально только [z0, z1]."""
        lo = (lambda x: zf(x)) if z0 is None else (lambda x: z0)
        hi = (lambda x: zc(x)) if z1 is None else (lambda x: z1)
        self.quad([*p, lo(p)], [*p, hi(p)], [*q, hi(q)], [*q, lo(q)], col, grp)
    def poly(self, pts, z, col, grp, up=True):
        for i, j, k in ear_clip(pts):
            a, b, c = ([*pts[i], z(pts[i])], [*pts[j], z(pts[j])], [*pts[k], z(pts[k])])
            self.tri(a, b, c, col, grp) if up else self.tri(a, c, b, col, grp)


COL = dict(wall=(222, 220, 212), floor=(170, 140, 110), ceil=(245, 245, 245), feat=(140, 190, 240))


def room_mesh(M, segs, F, zf, zc, name):
    bridged = {f["i"]: f for f in F if not f["full"]}
    skip = {c for f in bridged.values() for c in f["chain"]}
    outline = []                                                    # (p, q, hole)
    n = len(segs)
    for k in range(n):
        if k in skip: continue
        P = seg_pts(segs[k])
        for p, q in zip(P[:-1], P[1:]): outline.append((p, q, None))
        if k in bridged:
            f = bridged[k]; outline.append((f["a"], f["b"], (f["z0"], f["z1"])))
    for p, q, hole in outline:
        if hole is None: M.wall(p, q, zf, zc, COL["wall"], name)
        else:
            if hole[0] > max(zf(p), zf(q)) + 1: M.wall(p, q, zf, zc, COL["wall"], name, z1=hole[0])
            if hole[1] < min(zc(p), zc(q)) - 1: M.wall(p, q, zf, zc, COL["wall"], name, z0=hole[1])
    poly = [p for p, q, h in outline]
    M.poly(poly, zf, COL["floor"], name + "_floor", up=True); M.poly(poly, zc, COL["ceil"], name + "_ceiling", up=False)
    for f in bridged.values():
        cp = []
        for c in f["chain"]:
            P = seg_pts(segs[c])
            for p, q in zip(P[:-1], P[1:]): M.wall(p, q, zf, zc, COL["feat"], name + "_feat", z0=f["z0"], z1=f["z1"])
            cp += P[:-1]
        cp.append(f["b"])
        ccw = sum(cross2(cp[i], cp[(i+1) % len(cp)]) for i in range(len(cp))) > 0
        niche = f["out"]
        M.poly(cp, lambda x: f["z0"], COL["feat"], name + "_feat", up=niche)
        M.poly(cp, lambda x: f["z1"], COL["feat"], name + "_feat", up=not niche)


# ================= сборка проекта =================
def load(pdir):
    p = os.path.join(pdir, "scan.json")
    if not os.path.exists(p): return {"setups": []}
    S = json.load(open(p))
    if "setups" not in S: S = {"setups": [dict(name="S1", **S)]}
    return S


def letters(k):
    s = ""; k += 1
    while k: k, r = divmod(k - 1, 26); s = chr(65 + r) + s
    return s


def build(pdir, log=print):
    import ezdxf
    S = load(pdir); setups = S["setups"]
    if not setups: raise RuntimeError("нет данных")
    T, regres, refs_base = register(setups)
    rooms = []
    for si, st in enumerate(setups):
        if not st.get("points"): rooms.append(None); continue
        A = analyze_setup(st); A["si"] = si; rooms.append(A)
        if A["segs"] and T[si] is None: log(f"  {st['name']}: НЕ привязана (нужно ≥2 общих опорных точки)")
    base = next((r for r in rooms if r and r["segs"] and T[r["si"]] is not None), None)
    if base is None: raise RuntimeError("нет контура помещения")
    segs0 = base["segs"]
    k0 = max((k for k in range(len(segs0)) if segs0[k]["type"] == "L"), key=lambda k: seg_len(segs0[k]))
    A0 = apply(T[base["si"]], np.r_[segs0[k0]["a"], 0]); B0 = apply(T[base["si"]], np.r_[segs0[k0]["b"], 0])
    phi = math.atan2(B0[1] - A0[1], B0[0] - A0[0]); kf0 = base["floor"]
    pa = segs0[k0]["a"]; zA = (kf0[0]*pa[0] + kf0[1]*pa[1] + kf0[2] if kf0 is not None else 0) + T[base["si"]][1][2]
    Og = np.r_[A0[:2], zA]

    def to_proj(si):
        th, t = T[si]; R = rot2(th - phi); tt = rot2(-phi) @ (t[:2] - Og[:2]); tz = t[2] - Og[2]
        f = lambda p: np.r_[R @ np.asarray(p, float)[:2] + tt, (np.asarray(p, float)[2] + tz) if len(p) > 2 else 0.0][:len(p)]
        fx = lambda X: np.c_[X[:, :2] @ R.T + tt, X[:, 2] + tz]
        return f, fx, R, tt, tz

    M = Mesh(); out = dict(rooms=[], levels=[], surfaces=[], refs=[], setups=[], cloud=[])
    doc = ezdxf.new("R2010", setup=True); doc.units = ezdxf.units.MM; msp = doc.modelspace()
    for lay, col in (("WALLS", 7), ("DIM", 1), ("ANGLES", 3), ("HEIGHTS", 5), ("FEATURES", 30), ("LEVELS", 4),
                     ("SURFACES", 6), ("REFS", 2), ("QUICK", 2), ("CLOUD", 8), ("MODEL3D", 9)):
        doc.layers.add(lay, color=col)
    from ezdxf.enums import TextEntityAlignment as TA
    txt = lambda s, p, h=70, lay="ANGLES": msp.add_text(s, height=h, dxfattribs={"layer": lay}).set_placement(tuple(map(float, p[:2])), align=TA.MIDDLE_CENTER)

    for A in rooms:
        if not A or not A["segs"] or T[A["si"]] is None: continue
        si = A["si"]; st = setups[si]; f, fx, R, tt, tz = to_proj(si)
        rot = lambda s: dict(s, a=f(s["a"]), b=f(s["b"]), **({"c": f(s["c"])} if "c" in s else {}))
        segs = [rot(s) for s in A["segs"]]
        k0 = max((k for k in range(len(segs)) if segs[k]["type"] == "L"), key=lambda k: seg_len(segs[k]))
        if si == base["si"]: k0 = max((k for k in range(len(segs)) if segs[k]["type"] == "L"), key=lambda k: seg_len(segs[k]))
        segs = segs[k0:] + segs[:k0]
        F = features(segs)
        for fe in F:                                     # высоты ниш из анализа в кадре стоянки
            cand = min(A["features"], key=lambda q: np.linalg.norm(f(q["a"]) - fe["a"]) + np.linalg.norm(f(q["b"]) - fe["b"]), default=None)
            if cand is not None and np.linalg.norm(f(cand["a"]) - fe["a"]) < 50:
                fe.update(z0=cand["z0"] + tz, z1=cand["z1"] + tz, full=cand["full"])
            else: fe.update(z0=-1e9, z1=1e9, full=True)
        kf, kc = A["floor"], A["ceil"]
        def plane(k):
            if k is None: return None
            g = R @ np.array(k[:2]); p0 = R.T @ (-tt); c = k[0]*p0[0] + k[1]*p0[1] + k[2] + tz
            return np.array([g[0], g[1], c])
        pf, pc = plane(kf), plane(kc)
        zf = (lambda p: pf[0]*p[0] + pf[1]*p[1] + pf[2]) if pf is not None else (lambda p: 0.0)
        zc = (lambda p: pc[0]*p[0] + pc[1]*p[1] + pc[2]) if pc is not None else (lambda p: 2600.0)
        for fe in F:
            if fe["full"]: continue
            fe["z0"] = max(fe["z0"], min(zf(fe["a"]), zf(fe["b"]))); fe["z1"] = min(fe["z1"], max(zc(fe["a"]), zc(fe["b"])))
        rname = st.get("name", f"S{si+1}")
        room_mesh(M, segs, F, zf, zc, rname)
        n = len(segs); corners = []
        cen = polyline(segs).mean(0)
        for k in range(n):
            s0, s1 = segs[k - 1], segs[k]; t0, t1 = tangent(s0, True), tangent(s1, False)
            ang = 180 - math.degrees(math.atan2(cross2(t0, t1), t0 @ t1))
            p = s1["a"]; corners.append(dict(name=letters(k), x=float(p[0]), y=float(p[1]), angle=ang,
                                             h=float(zc(p) - zf(p)), floor=float(zf(p)), ceil=float(zc(p))))
        walls = []
        for k in range(n):
            s = segs[k]; nm = f"{letters(k)}-{letters((k + 1) % n)}"; L = seg_len(s)
            w = dict(name=nm, type=s["type"], len=L, a=s["a"].tolist(), b=s["b"].tolist(), rms=s.get("rms"), conn=bool(s.get("conn")))
            if s["type"] == "A": w.update(r=s["r"], chord=float(np.linalg.norm(s["b"] - s["a"])), c=s["c"].tolist(), ccw=s["ccw"])
            sh = os.path.join(pdir, f"photos_{rname}", f"sheet_{nm}.png")
            w["sheet"] = os.path.relpath(sh, pdir) if os.path.exists(sh) else None
            walls.append(w)
        feats = []
        for fe in F:
            d1 = unit(fe["b"] - fe["a"]); mid = (fe["a"] + fe["b"])/2 + np.array([-d1[1], d1[0]])*(-fe["depth"]/2 if fe["out"] else fe["depth"]/2)
            q = dict(kind=fe["kind"], width=fe["width"], depth=fe["depth"], x=float(mid[0]), y=float(mid[1]),
                     z0=None if fe["full"] else fe["z0"], z1=None if fe["full"] else fe["z1"], full=fe["full"],
                     at=f"{letters(fe['i'])}-{letters((fe['i'] + 1) % n)} .. {letters(fe['j'])}-{letters((fe['j'] + 1) % n)}")
            if "r" in fe: q.update(r=fe["r"], arclen=fe["arclen"], chord=fe["chord"])
            lab = f"{q['kind']} {q['width']:.0f}x"
            lab += "на всю высоту" if q["full"] else f"{q['z1'] - q['z0']:.0f} (низ {q['z0'] - zf(mid):.0f})"
            lab += f", глуб. {q['depth']:.0f}" + (f", R{q['r']:.0f}, дуга {q['arclen']:.0f}" if "r" in q else "")
            q["label"] = lab; feats.append(q)
        # --- DXF: контур с дугами (bulge) ---
        pl = []
        for s in segs:
            bl = 0.0
            if s["type"] == "A": bl = math.tan(arc_sweep(s)[1]/4)
            pl.append((float(s["a"][0]), float(s["a"][1]), bl))
        msp.add_lwpolyline(pl, format="xyb", close=True, dxfattribs={"layer": "WALLS"})
        for k, s in enumerate(segs):
            if s["type"] == "L":
                d = unit(s["b"] - s["a"]); nn = np.array([d[1], -d[0]])
                msp.add_aligned_dim(p1=tuple(map(float, s["a"])), p2=tuple(map(float, s["b"])), distance=250,
                                    dimstyle="EZDXF", dxfattribs={"layer": "DIM"}).render()
            else:
                a0, sw = arc_sweep(s); am = a0 + sw/2; pm = s["c"] + s["r"]*np.array([math.cos(am), math.sin(am)])
                txt(f"R{s['r']:.0f} L{seg_len(s):.0f} хорда {np.linalg.norm(s['b'] - s['a']):.0f}", pm + 200*unit(pm - s["c"]), 60, "DIM")
        for c in corners:
            p = np.array([c["x"], c["y"]]); q = p + unit(cen - p)*350
            txt(f"{c['name']} {c['angle']:.2f}°", q, 70); txt(f"H{c['h']:.0f} пол {c['floor']:+.0f}", q - [0, 100], 50, "HEIGHTS")
        for q in feats: txt(q["label"], (q["x"], q["y"]), 55, "FEATURES")
        P2 = fx(A["X"]); prof = np.isin(A["P"][:, 3], (0, 2))
        for p in P2[::2]: msp.add_point(tuple(map(float, p)), dxfattribs={"layer": "CLOUD"})
        out["cloud"] += np.round(P2[prof][:, :2][:: max(1, prof.sum()//1500)]).tolist()
        station = fx(np.zeros((1, 3)))[0]
        out["rooms"].append(dict(name=rname, outline=np.round(polyline(segs), 1).tolist(), corners=corners, walls=walls,
                                 features=feats, station=station.tolist(),
                                 floor_mm_m=float(math.hypot(*pf[:2])*1000) if pf is not None else None,
                                 ceil_mm_m=float(math.hypot(*pc[:2])*1000) if pc is not None else None))
        # --- геометрия для фото (кадр стоянки; дуги — хордой) ---
        Rinv = lambda p: R.T @ (np.asarray(p) - tt)
        json.dump({"names": [c["name"] for c in corners], "corners": [Rinv([c["x"], c["y"]]).tolist() for c in corners],
                   "floor": list(map(float, kf)) if kf is not None else [0, 0, -1400],
                   "ceiling": list(map(float, kc)) if kc is not None else [0, 0, 1300]},
                  open(os.path.join(pdir, f"geom_{rname}.json"), "w"), indent=1)
        # --- трассы по уровню ---
        for lv in st.get("levels", []):
            Pl = np.array(lv["points"], float); Xl = to_xyz(Pl[:, :3], st.get("cal", {}))
            Rl = analyze_profile(Xl[:, :2], Pl[:, 0], closed=lv.get("closed", False))
            ls = [rot(s) for s in Rl["segs"]]; fl = features(ls, lv.get("closed", False))
            parts = []
            for s in ls:
                if s.get("conn"): continue
                parts.append(dict(type=s["type"], len=seg_len(s), **({"r": s["r"], "chord": float(np.linalg.norm(s["b"] - s["a"]))} if s["type"] == "A" else {})))
            Pz = fx(Xl)
            dz = float(np.percentile(np.abs(Pz[:, 2] - lv["h"]), 90)) if len(Pz) else 0
            pts2 = np.round(np.vstack([seg_pts(s) for s in ls]) if ls else Pz[:, :2], 1).tolist()
            out["levels"].append(dict(room=rname, h=lv["h"], pts=pts2, parts=parts, dz_max=dz,
                                      features=[dict(kind=q["kind"], width=q["width"], depth=q["depth"], **({"r": q["r"], "arclen": q["arclen"]} if "r" in q else {})) for q in fl]))
            if ls:
                msp.add_lwpolyline([(float(s["a"][0]), float(s["a"][1]), math.tan(arc_sweep(s)[1]/4) if s["type"] == "A" else 0) for s in ls] +
                                   [(float(ls[-1]["b"][0]), float(ls[-1]["b"][1]), 0)], format="xyb",
                                   dxfattribs={"layer": "LEVELS", "elevation": float(lv["h"])})
            for s in ls:
                if s["type"] == "A":
                    a0, sw = arc_sweep(s); am = a0 + sw/2; pm = s["c"] + s["r"]*np.array([math.cos(am), math.sin(am)])
                    txt(f"Z{lv['h']:.0f}: R{s['r']:.0f} дуга {seg_len(s):.0f} хорда {np.linalg.norm(s['b'] - s['a']):.0f}", pm - 250*unit(pm - s["c"]), 55, "LEVELS")
            M_line = Pz.tolist()
            out.setdefault("lines", []).append(M_line[:: max(1, len(M_line)//400)])
        # --- неровности ---
        for sf in st.get("surfaces", []):
            Ps = np.array(sf["points"], float)
            if np.isfinite(Ps[:, 2]).sum() < 6: continue
            Xs = fx(to_xyz(Ps[:, :3], st.get("cal", {})))
            nm = f"{rname} {sf['wall']} {'стена' if sf['kind'] == 'wall' else 'пол'}"
            stt, val, png = surface_report(sf, Xs, nm, pdir)
            out["surfaces"].append(dict(name=nm, kind=sf["kind"], png=png, **stt))
            ns, nt = sf["ns"], sf["nt"]
            if len(Xs) == ns*nt:
                G = Xs.reshape(nt, ns, 3).copy(); V = val.reshape(nt, ns); vmax = max(1.0, np.nanmax(val))
                d = unit(np.array(sf["b"]) - np.array(sf["a"])); inn = np.r_[-d[1], d[0], 0] if sf["kind"] == "wall" else np.r_[0, 0, 1]
                G += inn*3
                for r_ in range(nt - 1):
                    for c_ in range(ns - 1):
                        if not np.isfinite(V[r_:r_+2, c_:c_+2]).all(): continue
                        q = min(1, V[r_:r_+2, c_:c_+2].mean()/vmax); col = (int(255 - 200*q), int(255 - 150*q), int(255 - 40*q))
                        a_, b_, c2, d_ = G[r_, c_], G[r_, c_+1], G[r_+1, c_+1], G[r_+1, c_]
                        nrm = np.cross(b_ - a_, d_ - a_)
                        if nrm @ inn > 0: M.quad(a_, b_, c2, d_, col, nm)
                        else: M.quad(a_, d_, c2, b_, col, nm)
            mid = np.nanmean(Xs[:, :2], 0)
            txt(f"{nm}: " + ", ".join(f"{k}={v:.1f}" for k, v in stt.items() if isinstance(v, float)), mid, 50, "SURFACES")
        Qk = st.get("quick") or []
        if Qk:
            Qx = fx(to_xyz(np.array(Qk, float)[:, :3], st.get("cal", {})))
            for k, p in enumerate(Qx):
                msp.add_point(tuple(map(float, p)), dxfattribs={"layer": "QUICK"}); txt(f"P{k + 1} Z{p[2]:.0f}", p[:2] + [0, 60], 45, "QUICK")
                if k:
                    a_ = Qx[k - 1]; msp.add_line(tuple(map(float, a_)), tuple(map(float, p)), dxfattribs={"layer": "QUICK"})
                    txt(f"{np.linalg.norm(p - a_):.0f}", (a_[:2] + p[:2])/2, 45, "QUICK")
        out["setups"].append(dict(name=rname, station=station.tolist(), reg=regres[si],
                                  R=[[float(x) for x in r] for r in np.c_[np.r_[R, [[0, 0]]], [0, 0, 1]][:3]],
                                  t=[float(tt[0]), float(tt[1]), float(tz)], cal=st.get("cal", {})))
    for si, st in enumerate(setups):
        if T[si] is None:
            out["setups"].append(dict(name=st.get("name", f"S{si+1}"), reg=None)); continue
        f, fx, *_ = to_proj(si)
        for k, v in st.get("refs", {}).items():
            p = fx(to_xyz(np.array([v[:3]], float), st.get("cal", {})))[0]
            out["refs"].append(dict(id=k, setup=st.get("name"), x=float(p[0]), y=float(p[1]), z=float(p[2])))
            msp.add_circle(tuple(map(float, p[:2])), 40, dxfattribs={"layer": "REFS"}); txt(f"Т{k} Z{p[2]:.0f}", p[:2] + [0, 80], 50, "REFS")
    for (a, b, c), grp in zip(M.T, M.G):
        msp.add_3dface([a, b, c, c], dxfattribs={"layer": "MODEL3D"})
    # --- фото-развёртки ---
    try:
        import photos
        for st in setups:
            od = os.path.join(pdir, f"photos_{st.get('name')}"); sj = os.path.join(od, "sheets.json")
            if os.path.exists(sj):
                doc.saveas(os.path.join(pdir, "room.dxf")); photos.add_to_dxf(os.path.join(pdir, "room.dxf"), [tuple(x) for x in json.load(open(sj))], od)
                doc = ezdxf.readfile(os.path.join(pdir, "room.dxf")); msp = doc.modelspace()
    except Exception as e:
        log(f"  фото в DXF: {e}")
    doc.saveas(os.path.join(pdir, "room.dxf"))
    fus = ezdxf.readfile(os.path.join(pdir, "room.dxf")); fm = fus.modelspace()
    for e in list(fm.query("*[layer=='CLOUD' | layer=='MODEL3D' | layer=='ELEVATIONS']")): fm.delete_entity(e)
    fus.saveas(os.path.join(pdir, "room_fusion.dxf"))
    write_obj(os.path.join(pdir, "room.obj"), M); write_stl(os.path.join(pdir, "room.stl"), M)
    out["tris"] = np.round(np.array(M.T).reshape(-1), 1).tolist() if M.T else []
    out["cols"] = [c for col in M.C for c in col]
    json.dump(out, open(os.path.join(pdir, "model.json"), "w"), ensure_ascii=False, default=float)
    for r in out["rooms"]:
        log(f"  {r['name']}: углов {len(r['corners'])}, элементов: " + ", ".join(f["label"] for f in r["features"]))
    return out


def write_obj(fn, M):
    with open(fn, "w") as f:
        f.write("# room3d: мм, Z вверх, начало — угол A на полу\n"); k = 1; last = None
        for (a, b, c), col, g in zip(M.T, M.C, M.G):
            if g != last: f.write(f"o {g}\n"); last = g
            for p in (a, b, c): f.write(f"v {p[0]:.1f} {p[1]:.1f} {p[2]:.1f} {col[0]/255:.3f} {col[1]/255:.3f} {col[2]/255:.3f}\n")
            f.write(f"f {k} {k+1} {k+2}\n"); k += 3


def write_stl(fn, M):
    import struct
    with open(fn, "wb") as f:
        f.write(b"room3d".ljust(80, b" ")); f.write(struct.pack("<I", len(M.T)))
        for a, b, c in M.T:
            a, b, c = map(np.array, (a, b, c)); n = np.cross(b - a, c - a); L = np.linalg.norm(n); n = n/L if L else n
            f.write(struct.pack("<12fH", *n, *a, *b, *c, 0))


if __name__ == "__main__":
    build(sys.argv[1])
