"""Только для тестов: проект (model.json) <-> мир виртуальной кухни по углам помещения."""
import math, numpy as np, sim_room
TW = np.array([(0,0),(4200,0),(4200,1200),(4450,1200),(4450,2000),(4200,2000),(4200,3400),(2450,3400),(1750,3400),(0,3400),(0,1900),(300,1900),(300,1500),(0,1500)], float)
fw = lambda x, y: sim_room.FLOOR[0]*x + sim_room.FLOOR[1]*y


def maps(room0):
    C = np.array([[c["x"], c["y"]] for c in room0["corners"]]); best = None
    for k in range(len(TW)):
        for sgn in (1, -1):
            a, b = TW[k], TW[(k + sgn) % len(TW)]; th = math.atan2(*(b - a)[::-1]) - math.atan2(*(C[1] - C[0])[::-1])
            Rm = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]]); W = C @ Rm.T + (a - Rm @ C[0])
            e = sum(np.min(np.linalg.norm(TW - w, axis=1)) for w in W)
            if best is None or e < best[0]: best = (e, Rm, a - Rm @ C[0])
    _, Rm, tm = best
    Q = np.array([TW[np.argmin(np.linalg.norm(TW - (Rm @ c + tm), axis=1))] for c in C]); p0, q0 = C.mean(0), Q.mean(0)
    U, _, Vt = np.linalg.svd((C - p0).T @ (Q - q0)); Rm = (U @ Vt).T
    if np.linalg.det(Rm) < 0: Vt[1] *= -1; Rm = (U @ Vt).T
    tm = q0 - Rm @ p0; dz = np.mean([fw(*(Rm @ [c["x"], c["y"]] + tm)) - c["floor"] for c in room0["corners"]])
    to_w = lambda P: np.r_[Rm @ np.asarray(P[:2], float) + tm, (P[2] if len(P) > 2 else 0) + dz]
    to_p = lambda W: np.r_[Rm.T @ (np.asarray(W[:2], float) - tm), (W[2] if len(W) > 2 else 0) - dz]
    return to_w, to_p
