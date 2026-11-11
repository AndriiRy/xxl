"""Самокалибровка круга Hz без эталона (как поверка круга тахеометра «по многим приёмам»).
Станция снимает профиль комнаты по горизонту (сырые углы), затем её поворачивают целиком (на штативе или на полу)
примерно на 90° и снимают снова — 3–4 положения. Ошибка круга E(угол корпуса относительно дна) в каждом положении
приходится на другие стены, поэтому профили не совпадают. Подбираем E (гармоники) и положения так, чтобы все
профили легли на одни и те же прямые стены.
Гармоники: 1–3 — эксцентриситет/эллипс напечатанного шкива 192T, 12 — биение шкива мотора 16T (передача ровно 1:12)."""
import math
import numpy as np
import room3d
from scan2dxf import to_xyz

HARM = (1, 2, 3, 12)


def E(lin, p, harm=HARM):
    t = np.radians(lin); return sum(p[2*i]*np.sin(n*t) + p[2*i + 1]*np.cos(n*t) for i, n in enumerate(harm))


def xy(pose, p):
    P = np.array(pose["pts"], float); P[:, 0] = P[:, 0] + E(P[:, 0], p)
    return to_xyz(P[:, :3], pose["cal"])[:, :2]


def R2(a): c, s = math.cos(a), math.sin(a); return np.array([[c, -s], [s, c]])


def walls(XY, HZ):
    """Прямые стены (длиннее 0,6 м) из профиля: (центр, нормаль, направление, длина)."""
    W = []
    for s in room3d.analyze_profile(XY, HZ)["segs"]:
        if s["type"] != "L" or s.get("conn"): continue
        a, b = np.asarray(s["a"]), np.asarray(s["b"]); L = np.linalg.norm(b - a)
        if L < 600: continue
        d = (b - a)/L; W.append(dict(c=(a + b)/2, d=d, n=np.r_[-d[1], d[0]], L=L))
    return W


def assign(Q, W, tol=25.0, trim=120.0):
    """Индекс стены для каждой точки (или -1): ближе tol к прямой и внутри стены без углов."""
    idx = np.full(len(Q), -1); best = np.full(len(Q), tol)
    for k, w in enumerate(W):
        t = (Q - w["c"]) @ w["d"]; e = np.abs((Q - w["c"]) @ w["n"])
        ok = (np.abs(t) < w["L"]/2 - trim) & (e < best); idx[ok] = k; best[ok] = e[ok]
    return idx


def coarse_pose(Q0, W0, Q):
    """Грубый поворот/сдвиг положения к первому профилю: перебор угла 1°, затем ICP «точка—прямая»."""
    best = None
    for ang in np.radians(np.arange(0, 360, 1.0)):
        q = Q @ R2(ang).T; t = np.zeros(2)
        for _ in range(3):
            i = assign(q + t, W0, tol=150, trim=50)
            if (i >= 0).sum() < 30: break
            N = np.array([W0[k]["n"] for k in i[i >= 0]]); r = np.array([(q[j] + t - W0[k]["c"]) @ W0[k]["n"] for j, k in zip(np.where(i >= 0)[0], i[i >= 0])])
            t -= np.linalg.lstsq(N, r, rcond=None)[0]
        i = assign(q + t, W0, tol=40, trim=50); sc = (i >= 0).sum()
        if best is None or sc > best[0]: best = (sc, ang, t)
    return best[1], best[2]


def solve(poses, harm=HARM, outer=8, log=print):
    """poses: [dict(pts=[[hz_сырой, v, d], ...], cal=...)] -> (параметры E, отчёт)."""
    if len(poses) < 3: raise RuntimeError("нужно ≥3 положения станции (лучше 4), повёрнутых на ~90°")
    npar = 2*len(harm); p = np.zeros(npar)
    Q0 = xy(poses[0], p); H0 = np.array(poses[0]["pts"])[:, 0]; W0 = walls(Q0, H0)
    if len(W0) < 3: raise RuntimeError("мало прямых стен в профиле (нужно ≥3 стены длиннее 0,6 м)")
    T = [(0.0, np.zeros(2))] + [coarse_pose(Q0, W0, xy(ps, p)) for ps in poses[1:]]
    def resid(x, W):
        pp = x[:npar]; out = []
        for k, ps in enumerate(poses):
            q = xy(ps, pp)
            if k: a, tx, ty = x[npar + 3*(k - 1): npar + 3*k]; q = q @ R2(a).T + [tx, ty]
            i = assign(q, W)
            for j in np.where(i >= 0)[0]: out.append((q[j] - W[i[j]]["c"]) @ W[i[j]]["n"])
        return np.array(out)
    x = np.r_[p, np.concatenate([[a, *t] for a, t in T[1:]])]
    r0 = None
    for it in range(outer):
        # стены — по всем положениям вместе (с текущими E и положениями)
        Qs, Hs = [], []
        for k, ps in enumerate(poses):
            q = xy(ps, x[:npar])
            if k: a, tx, ty = x[npar + 3*(k - 1): npar + 3*k]; q = q @ R2(a).T + [tx, ty]
            Qs.append(q)
        W = walls(Qs[0], H0)
        for w in W:                                           # уточнить прямую по точкам всех положений
            Pw = np.vstack([q[assign(q, [w]) == 0] for q in Qs])
            if len(Pw) > 10: c, d, n, _ = room3d.line_fit(Pw); w.update(c=c, d=d/np.linalg.norm(d), n=np.r_[-d[1], d[0]]/np.linalg.norm(d))
        r = resid(x, W)
        if r0 is None: r0 = float(np.sqrt((r**2).mean()))
        J = np.zeros((len(r), len(x)))
        for j in range(len(x)):
            h = 1e-4 if j < npar else (1e-5 if (j - npar) % 3 == 0 else 0.05)
            xx = x.copy(); xx[j] += h; rr = resid(xx, W)
            if len(rr) != len(r): rr = np.resize(rr, len(r))
            J[:, j] = (rr - r)/h
        dx = np.linalg.lstsq(J, -r, rcond=None)[0]; x += dx
        rms = float(np.sqrt((resid(x, W)**2).mean()))
        log(f"  круг Hz, итерация {it + 1}: СКО до стен {rms:.2f} мм")
        if np.abs(dx[:npar]).max() < 1e-5: break
    pp = x[:npar]
    return dict(n=list(harm), a=[float(pp[2*i]) for i in range(len(harm))], b=[float(pp[2*i + 1]) for i in range(len(harm))]), \
        dict(rms0=r0, rms=rms, amp=[float(math.hypot(pp[2*i], pp[2*i + 1])) for i in range(len(harm))], poses=len(poses))
