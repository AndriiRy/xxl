#!/usr/bin/env python3
"""room2dxf: замеры (стороны + диагонали + высоты) -> координаты углов (МНК) -> DXF.
Запуск: python3 room2dxf.py room.json room.dxf
"""
import json, math, sys
import numpy as np
import ezdxf
from ezdxf.enums import TextEntityAlignment


def initial_guess(n, sides, turns):
    # приближение по поворотам: "L" = +90 (внутренний угол), "R" = -90 (выступ)
    pts, a, p = [], 0.0, np.zeros(2)
    for i in range(n):
        pts.append(p.copy())
        p = p + sides[i] * np.array([math.cos(a), math.sin(a)])
        a += math.radians(90 if turns[(i+1) % n] == "L" else -90)
    return np.array(pts)


def solve(n, meas, x0, iters=50):
    # P0=(0,0), P1=(x,0) фиксированы -> неизвестные: x1, x2,y2 ... (2n-3 шт.)
    def unpack(v):
        P = np.zeros((n, 2)); P[1, 0] = v[0]; P[2:] = v[1:].reshape(-1, 2); return P
    v = np.concatenate([[x0[1, 0] if abs(x0[1, 1]) < 1e-9 else np.linalg.norm(x0[1])], x0[2:].ravel()])
    for _ in range(iters):
        P = unpack(v); r, J = [], []
        for i, j, d, w in meas:
            diff = P[i] - P[j]; L = np.linalg.norm(diff); u = diff / L
            row = np.zeros(2 * n); row[2*i:2*i+2] += u; row[2*j:2*j+2] -= u
            r.append(w * (L - d)); J.append(w * np.concatenate([[row[2]], row[4:]]))
        r, J = np.array(r), np.array(J)
        dv = np.linalg.lstsq(J, -r, rcond=None)[0]; v += dv
        if np.abs(dv).max() < 1e-6: break
    P = unpack(v)
    res = [(i, j, d, np.linalg.norm(P[i]-P[j]) - d) for i, j, d, _ in meas]
    return P, res


def main(src, dst):
    R = json.load(open(src))
    names = R["corners"]; n = len(names); idx = {c: k for k, c in enumerate(names)}
    sides = R["sides"]                       # мм, A->B, B->C, ... ->A
    sigma = R.get("sigma_mm", 1.5)
    meas = [(k, (k+1) % n, sides[k], 1/sigma) for k in range(n)]
    for d in R.get("diagonals", []):         # {"a":"A","b":"C","d":5000}
        meas.append((idx[d["a"]], idx[d["b"]], d["d"], 1/sigma))
    if len(meas) < 2*n - 3:
        sys.exit(f"Мало замеров: нужно >= {2*n-3} (стороны + {n-3} диагоналей)")
    P, res = solve(n, meas, initial_guess(n, sides, R.get("turns", "L"*n)))

    doc = ezdxf.new("R2010", setup=True); doc.units = ezdxf.units.MM
    msp = doc.modelspace()
    for lay, col in (("WALLS", 7), ("DIM", 1), ("ANGLES", 3), ("HEIGHTS", 5), ("OPENINGS", 4)):
        doc.layers.add(lay, color=col)
    msp.add_lwpolyline([tuple(p) for p in P], close=True, dxfattribs={"layer": "WALLS"})
    c = P.mean(axis=0)
    for k in range(n):
        a, b = P[k], P[(k+1) % n]
        nrm = np.array([-(b-a)[1], (b-a)[0]]); nrm /= np.linalg.norm(nrm)
        off = 300 if np.dot((a+b)/2 - c, nrm) > 0 else -300   # размер наружу
        msp.add_aligned_dim(p1=tuple(a), p2=tuple(b), distance=off,
                            dimstyle="EZDXF", dxfattribs={"layer": "DIM"}).render()
        # угол в вершине k
        p, q = P[k-1] - P[k], P[(k+1) % n] - P[k]
        ang = math.degrees(math.acos(np.clip(np.dot(p, q)/np.linalg.norm(p)/np.linalg.norm(q), -1, 1)))
        t = P[k] + (c - P[k]) / np.linalg.norm(c - P[k]) * 350
        msp.add_text(f"{names[k]} {ang:.2f}°", height=80, dxfattribs={"layer": "ANGLES"}
                     ).set_placement(tuple(t), align=TextEntityAlignment.MIDDLE_CENTER)
    for h in R.get("heights", []):           # {"at":"A","floor":0,"ceiling":2712} или {"xy":[x,y],...}
        xy = P[idx[h["at"]]] if "at" in h else np.array(h["xy"])
        if "at" in h: xy = xy + (c - xy) / np.linalg.norm(c - xy) * 600
        msp.add_circle(tuple(xy), 30, dxfattribs={"layer": "HEIGHTS"})
        msp.add_text(f"H={h['ceiling']-h.get('floor',0):.0f} пол{h.get('floor',0):+.0f}",
                     height=70, dxfattribs={"layer": "HEIGHTS"}).set_placement((xy[0]+50, xy[1]+50))
    for o in R.get("openings", []):          # {"wall":"A","from":350,"width":900,"type":"Д"}
        k = idx[o["wall"]]; a, b = P[k], P[(k+1) % n]; u = (b-a)/np.linalg.norm(b-a)
        s, e = a + u*o["from"], a + u*(o["from"]+o["width"])
        msp.add_line(tuple(s), tuple(e), dxfattribs={"layer": "OPENINGS", "lineweight": 70})
    doc.saveas(dst)

    print("Углы (мм):"); [print(f"  {names[k]}: {P[k,0]:9.1f} {P[k,1]:9.1f}") for k in range(n)]
    print("Невязки (мм):"); [print(f"  {names[i]}-{names[j]}: {d:.0f}  {e:+.2f}") for i, j, d, e in res]
    if max(abs(e) for *_, e in res) > 3: print("!!! невязка > 3 мм — перемерить")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
