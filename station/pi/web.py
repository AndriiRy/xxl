#!/usr/bin/env python3
"""Веб-пульт станции: всё считается на Pi, планшет/телефон/ТВ — только экран (браузер).
  python3 web.py [--sim] [--port 8000] [--dir ~/scans]
  точка доступа Pi: http://10.42.0.1:8000   домашняя сеть: http://station.local:8000
Без зависимостей сверх station.py (stdlib http.server).
"""
import argparse, contextlib, io, json, math, os, re, sys, threading, time, traceback, zipfile
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, unquote

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import station as S
import scan2dxf
import room3d
import layout as LY
import cadm
import worktop as WT
import hzcal
S_cfg_path = lambda: S.CFG_PATH
POS_PATH = os.path.join(HERE, "hz_pos.json")
HZCAL_PATH = os.path.join(HERE, "hzcal.json")              # самокалибровка круга Hz: профили в разных положениях станции              # последний счётчик Hz (после перезапуска — тот же виток шнура)


class Abort(Exception): pass


class App:
    def __init__(self, root, sim):
        self.root, self.sim = os.path.expanduser(root), sim
        os.makedirs(self.root, exist_ok=True)
        self.cfg = S.load_cfg(); self.st = None
        self.file_cal = (json.load(open(S.CFG_PATH)).get("cal", {}) if os.path.exists(S.CFG_PATH) else {})
        self.lock = threading.Lock()
        self.busy = None; self.progress = 0.0; self.error = None; self.stop = False
        self.log = []; self.last = {}; self.zref = None; self.marks = {}; self.alert = None
        self.targets = []; self.lay = {}; self.sel = None; self.stk = None; self.chk = None; self.cmp = None; self.lres = None
        self.wt = None
        projs = self.projects(); self.project = projs[0] if projs else None
        self.load_layout()

    # ---------- проекты ----------
    def projects(self):
        return sorted((d for d in os.listdir(self.root) if os.path.isdir(os.path.join(self.root, d))), reverse=True)

    def pdir(self, p=None):
        p = p or self.project
        if not p or "/" in p or p.startswith("."): raise ValueError("нет проекта")
        return os.path.join(self.root, p)

    def new_project(self, name):
        name = re.sub(r"[^\w\-]+", "_", name.strip(), flags=re.U)[:40] or "obj"
        p = time.strftime("%Y%m%d_%H%M_") + name; os.makedirs(os.path.join(self.root, p), exist_ok=True)
        self.project = p; self.load_layout(); return p

    # ---------- журнал ----------
    def say(self, s):
        for line in s.splitlines():
            if line.strip(): self.log.append(time.strftime("%H:%M:%S ") + line)
        del self.log[:-300]

    class _Out(io.TextIOBase):
        def __init__(self, app): self.app, self.buf = app, ""
        def write(self, s):
            self.buf += s
            while "\n" in self.buf:
                line, self.buf = self.buf.split("\n", 1); self.app.say(line)
            return len(s)

    def station(self):
        if self.st is None:
            self.say("подключение к станции" + (" (симуляция)" if self.sim else ""))
            self.st = S.Station(self.cfg, self.sim)
            with contextlib.suppress(Exception):                # Arduino перезапущен, а барабан стоит, где стоял: вернуть счётчик
                if not self.sim and os.path.exists(POS_PATH):
                    p = json.load(open(POS_PATH)); self.st.ard.setpos(p["h"], self.st.ard.pos[1])
            with contextlib.suppress(Exception):                # перезапуск программы: ноль V — с наклоном из калибровки стоянки
                cur = self.cur(self.proj())
                if self.calibrated(cur):
                    self.cfg["cal"].update(cur["cal"])
                    if cur["cal"].get("hz_mark"): self.st.home_near()                         # ноль Hz — снова по метке
                    self.st.v_home(); print("  калибровка стоянки восстановлена")
        return self.st

    # ---------- задания (одно за раз, в фоне) ----------
    def run(self, name, fn, *a):
        with self.lock:
            if self.busy: raise RuntimeError(f"занято: {self.busy}")
            self.busy, self.progress, self.error, self.stop = name, 0.0, None, False
        def work():
            try:
                with contextlib.redirect_stdout(self._Out(self)):
                    fn(*a)
                self.say(f"готово: {name}")
            except Abort:
                self.say("остановлено"); self.error = "остановлено"
            except S.Moved as e:
                self.error = self.alert = str(e); self.say("СДВИГ: " + str(e))
            except Exception as e:
                self.error = f"{type(e).__name__}: {e}"; self.say("ОШИБКА " + self.error)
                self.say(traceback.format_exc(limit=4))
            finally:
                self.busy = None
                if self.st is not None and not self.sim and getattr(self.st, "homed", False):
                    with contextlib.suppress(Exception): json.dump({"h": self.st.ard.pos[0]}, open(POS_PATH, "w"))   # виток барабана Hz
                with contextlib.suppress(Exception): self.cord_save()
                if self.st is not None and self.st.cord_warn: self.alert = self.st.cord_warn
        threading.Thread(target=work, daemon=True).start()

    def _counted(self, total, f):
        n = [0]
        def g(*a, **k):
            if self.stop: raise Abort()
            r = f(*a, **k); n[0] += 1; self.progress = min(1.0, n[0] / max(1, total)); return r
        return g

    # ---------- проект: стоянки ----------
    def proj(self):
        S = room3d.load(self.pdir())
        if not S["setups"]: S["setups"].append(self._new_setup("S1"))
        return S

    def _new_setup(self, name): return dict(name=name, cal={}, points=[], levels=[], surfaces=[], refs={})

    def save(self, S): json.dump(S, open(os.path.join(self.pdir(), "scan.json"), "w"))

    def cur(self, S): return S["setups"][-1]

    def model(self):
        p = os.path.join(self.pdir(), "model.json")
        return json.load(open(p)) if os.path.exists(p) else None

    def setup_T(self, name):
        """Кадр стоянки -> кадр проекта (R 3x3, t): свободная станция (если есть), иначе model.json."""
        with contextlib.suppress(Exception):
            for s in self.proj()["setups"]:
                if s["name"] == name and s.get("resect"): return np.array(s["resect"]["R"]), np.array(s["resect"]["t"])
        m = self.model()
        for s in (m or {}).get("setups", []):
            if s.get("name") == name and s.get("R"): return np.array(s["R"]), np.array(s["t"])
        return None

    def rebuild(self):
        try: room3d.build(self.pdir(), log=print)
        except Exception as e: print(f"  модель: {e}")

    def calibrated(self, st):
        return "tilt_x" in st["cal"]

    def job_calib(self, full=False, save_v0=True):
        st_ = self.station(); S = self.proj(); cur = self.cur(S); self.cfg["cal"].pop("imu_b", None); self.alert = None
        if self.cfg.get("hz_mark", True):                    # масштаб шнура Hz по метке TCRT5000 + ноль Hz
            try: st_.hz_scale()
            except RuntimeError as e: print(f"  {e}")
        self.progress = 0.05; st_.v_home(); st_.move_deg(st_.pos_deg()[0], 0)
        self.progress = 0.1; st_.level(); st_.v_home(); self.progress = 0.4
        if full or self.sim or "v0" not in self.file_cal: st_.v_index()
        else: print(f"  индекс V из config.json: {self.cfg['cal']['v0']:+.4f}° (полная калибровка — кнопка «Индекс V»)")
        st_.move_deg(0, 0); st_.tilt_arm(); print("  компенсатор включён: наклон контролируется в каждом замере")
        if cur.get("resect"):
            cur["resect"]["stale"] = True
            print("  свободная станция — от прошлой установки: если станцию двигали, повторите «Своб. станция» (проверка — «Проверка ст.»)")
        self.progress = 1.0
        cur["cal"] = dict(self.cfg["cal"]); self.save(S)
        if save_v0 and not self.sim:
            p = S_cfg_path(); c = json.load(open(p)) if os.path.exists(p) else {}
            c.setdefault("cal", {})["v0"] = round(self.cfg["cal"]["v0"], 5); json.dump(c, open(p, "w"), indent=1)
            print("  индекс V сохранён в config.json")

    def _wrap_point(self, st_, total):
        orig = st_.point; st_.point = self._counted(total, orig); return orig

    def _near_v(self, pts, hz):
        P = np.array([p for p in pts if p[3] == 0]); k = np.argmin(np.abs((P[:, 0] - hz + 180) % 360 - 180)); return float(P[k, 1])

    def job_scan(self):
        st_ = self.station(); S = self.proj(); cur = self.cur(S); c = self.cfg
        cur["mount"] = self.cfg["mount"]; cur["base_drop"] = c["base_drop_mm"]
        if not self.calibrated(cur): print("калибровка (наклон, индекс V)"); self.job_calib(); S = self.proj(); cur = self.cur(S)
        self.cfg["cal"].update(cur["cal"]); md = st_.mode()
        npl = len(md.get("plane_v_deg", c["plane_v_deg"])) * len(range(0, 360, int(c["plane_hz_step_deg"])))
        try:
            if self.cfg["mount"] == "tripod":
                total = int(round(360 / c["profile_step_deg"])) * len(c["profile_levels_deg"]) + npl
                orig = self._wrap_point(st_, total * 1.25)
                data = st_.scan(); cur["points"] = data["points"]
            else:
                # без штатива: сначала пол/потолок, затем профиль «по уровню» на высоте profile_z над полом
                step = md.get("step", 1.0); orig = self._wrap_point(st_, npl + 360/step*2.4)
                cur["points"] = st_.planes()
                if self.cfg["mount"] == "floor":                    # отвес: пол прямо под станцией
                    with contextlib.suppress(Exception): p, _ = st_.plumb(); cur["plumb"] = p; cur["floor_pts"] = [p]
                kf, kc = room3d.floor_ceiling(cur, *room3d.setup_points(cur))
                zf = kf[2] if kf is not None else -c["base_drop_mm"]
                if kf is None: print("  пол не найден — профиль от высоты опоры (замерьте «Пол» вручную)")
                z = zf + md.get("profile_z", 1000)
                print(f"  станция {-zf:.0f} мм над полом, профиль на {md.get('profile_z', 1000)} мм от пола")
                cur["points"] += [p + [0] for p in st_.trace_level(z, 0, 360, step)]
            cur["cal"] = dict(self.cfg["cal"]); self.save(S)
            A = room3d.analyze_setup(cur)
            print(f"  кромок для уточнения: {len(A['refine'])}")
            for rq in A["refine"]: cur["points"] += st_.refine_edge(rq, v=self._near_v(cur["points"], rq["hz_in"]))
            self.save(S); A = room3d.analyze_setup(cur)
            print(f"  ниш/выступов: {len(A['features'])} — ищу верх/низ")
            for f in A["features"]:
                s_, mid = room3d.face_of(f, A["segs"])
                if f["out"]: on = lambda X, f=f: bool(room3d.niche_masks(f, X[None])[0][0])       # внутри проёма
                else: on = lambda X, s_=s_: room3d.point_seg_dist(X[:2], s_) < room3d.TOL
                hz_m = st_.aim([mid[0], mid[1], 0])[0]
                cur["points"] += st_.vprobe(mid, on, v_start=self._near_v(cur["points"], hz_m))
            st_.ard.move(0, 0)
        finally:
            if "orig" in locals(): st_.point = orig
        self.save(S); self.rebuild(); self._slip(st_)

    def _slip(self, st_):
        d = st_.hz_check()
        if d is not None and abs(d) > self.cfg.get("slip_tol_deg", 0.02):
            self.alert = (f"ремень Hz проскочил ({d:+.3f}° за скан) — проверьте натяжение ремня (пазы мотора), повторите «Калибровку» и скан" if st_.belt()
                          else f"проскальзывание шнура Hz {d:+.3f}° за скан — подтяните шнур, повторите «Калибровку» и скан")

    def job_mount(self, m):
        if m not in self.cfg["mounts"]: raise ValueError("установка: tripod | floor | table")
        self.cfg["mount"] = m; S = self.proj(); cur = self.cur(S); cur["mount"] = m
        for k in ("tilt_x", "tilt_y", "imu_b"): cur["cal"].pop(k, None); self.cfg["cal"].pop(k, None)
        self.save(S); print(f"  установка: {dict(tripod='штатив', floor='пол (ножки)', table='стол/столешница')[m]} — нужна «Калибровка»")

    def _quick_xyz(self, cur, raw):
        from scan2dxf import to_xyz
        X = to_xyz(np.array([raw[:3]], float), cur["cal"] or self.cfg["cal"])[0]; T = self.setup_T(cur["name"])
        return (T[0] @ X + T[1]) if T is not None else X

    def job_qpoint(self, kind):
        """Быстрый замер без скана: точка (P2P) или точка пола."""
        st_ = self.station(); S = self.proj(); cur = self.cur(S); h, v = st_.pos_deg()
        if cur["cal"]: self.cfg["cal"].update(cur["cal"])
        ds = [st_.las.measure() for _ in range(3)]; raw = [h, v, float(np.median(ds))]
        cur.setdefault("quick" if kind == "p" else "floor_pts", []).append(raw); self.save(S)
        X = self._quick_xyz(cur, raw)
        print(f"  {'точка' if kind == 'p' else 'пол'}: X={X[0]:.0f} Y={X[1]:.0f} Z={X[2]:.1f}" + ("" if "tilt_x" in cur["cal"] else "  (без нивелира: ΔH неточна)"))
        if kind == "f": self.rebuild()

    def job_plumb(self):
        st_ = self.station(); S = self.proj(); cur = self.cur(S)
        if cur["cal"]: self.cfg["cal"].update(cur["cal"])
        p, X = st_.plumb(); cur["plumb"] = p
        if cur.get("mount", self.cfg["mount"]) == "floor": cur.setdefault("floor_pts", []).append(p)
        self.save(S); self.last = {"hz": p[0], "v": p[1], "d": p[2], "xyz": X.tolist(), "proj": False, "dh": None, "plumb": float(-X[2])}

    def job_qclear(self):
        S = self.proj(); cur = self.cur(S); cur["quick"] = []; self.save(S)

    def job_process(self):
        self.rebuild()

    def job_ref(self, rid):
        st_ = self.station(); S = self.proj(); cur = self.cur(S); h, v = st_.pos_deg()
        ds = [st_.las.measure() for _ in range(5)]; D = float(np.median(ds))
        cur["refs"][str(rid)] = [h, v, D]; self.save(S)
        print(f"  опорная точка {rid}: D={D:.1f} (разброс {max(ds) - min(ds):.1f} мм) на стоянке {cur['name']}")
        self.rebuild()

    def job_newsetup(self, name):
        S = self.proj(); name = name or f"S{len(S['setups']) + 1}"
        if any(s["name"] == name for s in S["setups"]): raise ValueError("имя занято")
        S["setups"].append(self._new_setup(name)); self.save(S)
        for k in ("tilt_x", "tilt_y", "imu_b", "hz_mark"): self.cfg["cal"].pop(k, None)
        self.stk = self.chk = None
        print(f"  новая стоянка {name}: перенесите станцию, «Калибровка», замерьте ≥2 (лучше 3) опорные точки, «Скан»")

    def job_level(self, h, hz0, hz1, step):
        st_ = self.station(); S = self.proj(); cur = self.cur(S); T = self.setup_T(cur["name"])
        if T is None: raise RuntimeError("сначала «Скан» этой стоянки (и привязка по опорным точкам)")
        self.cfg["cal"].update(cur["cal"])
        z = h - T[1][2]
        span = (hz1 - hz0) % 360 or 360; orig = self._wrap_point(st_, int(span/step) * 1.6)
        try:
            pts = st_.trace_level(z, hz0, hz1, step)
            if len(pts) > 10:                                          # точные кромки на уровне
                P = np.array(pts); X = room3d.to_xyz(P, self.cfg["cal"])
                R = room3d.analyze_profile(X[:, :2], P[:, 0], closed=span >= 359.9)
                print(f"  кромок на уровне: {len(R['refine'])}")
                for rq in R["refine"]:
                    v = P[np.argmin(np.abs((P[:, 0] - rq["hz_in"] + 180) % 360 - 180)), 1]
                    pts += [p[:3] for p in st_.refine_edge(rq, v=v)]
        finally: st_.point = orig
        st_.ard.move(0, 0)
        cur["levels"].append(dict(h=h, hz0=hz0, hz1=hz1, closed=span >= 359.9, points=pts)); self.save(S); self.rebuild()

    def job_surface(self, wall, kind, h0, h1, depth, step):
        st_ = self.station(); S = self.proj(); cur = self.cur(S); T = self.setup_T(cur["name"]); m = self.model()
        if T is None or not m: raise RuntimeError("сначала «Скан»")
        self.cfg["cal"].update(cur["cal"])
        room = next(r for r in m["rooms"] if r["name"] == cur["name"])
        w = next((x for x in room["walls"] if x["name"] == wall), None)
        if w is None: raise ValueError(f"нет стены {wall}")
        a, b = np.array(w["a"]), np.array(w["b"]); L = np.linalg.norm(b - a); d = (b - a) / L; nn = np.array([-d[1], d[0]])
        fl = {c["name"]: c["floor"] for c in room["corners"]}; zf = lambda s: fl[wall.split("-")[0]] + (fl[wall.split("-")[1]] - fl[wall.split("-")[0]]) * s / L
        S_ = np.arange(50, L - 49, step); P = []
        if kind == "wall":
            Z = np.arange(h0, h1 + 1e-6, step)
            for j, z in enumerate(Z):
                row = S_ if j % 2 == 0 else S_[::-1]
                P += [np.r_[a + s*d + nn*5, zf(s) + z] for s in row]
            ns, nt = len(S_), len(Z)
        else:
            Tt = np.arange(50, depth + 1e-6, step)
            for j, t in enumerate(Tt):
                row = S_ if j % 2 == 0 else S_[::-1]
                P += [np.r_[a + s*d + nn*t, zf(s)] for s in row]
            ns, nt = len(S_), len(Tt)
        R, t = T; Pst = [(R.T @ (p - t)) for p in P]
        orig = self._wrap_point(st_, len(Pst))
        try: pts = st_.measure_grid(Pst)
        finally: st_.point = orig
        st_.ard.move(0, 0)
        # змейка -> обратно в порядок сетки
        grid = []
        for j in range(nt):
            row = pts[j*ns:(j + 1)*ns]; grid += row if j % 2 == 0 else row[::-1]
        cur["surfaces"] = [x for x in cur["surfaces"] if not (x["wall"] == wall and x["kind"] == kind)]
        cur["surfaces"].append(dict(wall=wall, kind=kind, a=a.tolist(), b=b.tolist(), ns=ns, nt=nt, step=step, points=grid))
        self.save(S); self.rebuild()

    def job_photos(self):
        import photos
        st_ = self.station(); S = self.proj(); cur = self.cur(S); name = cur["name"]
        gj = os.path.join(self.pdir(), f"geom_{name}.json")
        if not os.path.exists(gj): raise RuntimeError("сначала «Скан»")
        geom = json.load(open(gj)); out = os.path.join(self.pdir(), f"photos_{name}"); cam = st_.cam()
        total = sum(len(photos.plan_shots(w, cam)) for w in photos.wall_geometry(geom))
        photos.shoot(st_, geom, out, cam, capture_fn=self._counted(total, st_.capture)); st_.ard.move(0, 0)
        sheets = photos.render_sheets(geom, out); json.dump(sheets, open(os.path.join(out, "sheets.json"), "w"))
        self.rebuild()

    def job_move(self, dh, dv):
        st_ = self.station(); h, v = st_.pos_deg(); h, v = st_.move_deg(h + dh, v + dv)
        self.say(f"Hz={h:.3f}° V={v:.3f}°")

    def job_measure(self, setref=False):
        st_ = self.station(); h, v = st_.pos_deg(); S = self.proj(); cur = self.cur(S)
        if cur["cal"]: self.cfg["cal"].update(cur["cal"])
        ds = [st_.las.measure() for _ in range(max(1, self.cfg["avg"]))]; D = float(np.mean(ds))
        X = st_.xyz([h, v, D]); T = self.setup_T(cur["name"]); P = (T[0] @ X + T[1]) if T is not None else X
        if setref: self.zref = float(P[2])
        self.last = {"hz": h, "v": v, "d": D, "xyz": P.tolist(), "proj": T is not None,
                     "dh": None if self.zref is None else float(P[2] - self.zref)}
        self.say(f"D={D:.1f} мм  X={P[0]:.0f} Y={P[1]:.0f} Z={P[2]:.1f}" + ("" if self.zref is None else f"  ΔH={P[2] - self.zref:+.1f}"))

    def job_home(self):
        st_ = self.station(); self.say(f"нуль Hz: {st_.ard.home()}")

    def job_zero(self):
        st_ = self.station(); st_.ard.zero(); self.say("текущее положение = 0")

    # ---------- самокалибровка круга Hz ----------
    def hzcal_poses(self):
        if self.sim: return getattr(self, "_hzcal", [])
        return json.load(open(HZCAL_PATH)) if os.path.exists(HZCAL_PATH) else []

    def hzcal_store(self, P):
        if self.sim: self._hzcal = P
        else: json.dump(P, open(HZCAL_PATH, "w"))

    def job_hzcal_pose(self):
        """Одно положение: нивелир + профиль по горизонту в сырых углах. Затем повернуть станцию целиком на ~90°."""
        st_ = self.station(); self.job_calib(save_v0=False)
        orig = self._wrap_point(st_, 720)
        try: pts = st_.hz_circle_profile(0.5)
        finally: st_.point = orig
        P = self.hzcal_poses(); P.append(dict(pts=pts, cal={k: v for k, v in self.cfg["cal"].items() if k != "imu_b"})); self.hzcal_store(P)
        print(f"  круг Hz: положение {len(P)} снято. Поверните станцию целиком на ~90° (штатив/пол) и снимите следующее; после 3–4 — «Рассчитать»")

    def job_hzcal_solve(self):
        P = self.hzcal_poses(); par, rep = hzcal.solve(P)
        self.cfg["hz_err"] = par
        print(f"  круг Hz: СКО до стен {rep['rms0']:.2f} -> {rep['rms']:.2f} мм; гармоники " +
              ", ".join(f"{n}: {a*3600:.0f}\"" for n, a in zip(par["n"], rep["amp"])))
        if not self.sim:
            p = S_cfg_path(); c = json.load(open(p)) if os.path.exists(p) else {}
            c["hz_err"] = par; json.dump(c, open(p, "w"), indent=1); print("  поправка круга Hz сохранена в config.json")
        self.hzcal_store([])

    def job_hzcal_reset(self):
        self.hzcal_store([]); self.cfg["hz_err"] = {}; print("  самокалибровка круга Hz сброшена (поправка выключена до нового расчёта)")
        if not self.sim:
            p = S_cfg_path(); c = json.load(open(p)) if os.path.exists(p) else {}; c["hz_err"] = {}; json.dump(c, open(p, "w"), indent=1)

    # ---------- шнур: пробег и замена ----------
    def cord_save(self, reset=False):
        c = self.cfg["cord"]
        if self.st is not None:
            c["hz_turns"] = c.get("hz_turns", 0) + self.st.odo[0]; c["v_turns"] = c.get("v_turns", 0) + self.st.odo[1]; self.st.odo = [0.0, 0.0]
        if reset:
            c.clear(); c.update(hz_turns=0.0, v_turns=0.0, spr0=None, since=time.strftime("%Y-%m-%d"))
            if self.st is not None: self.st.cord_warn = None
            self.alert = None; print("  новый шнур: пробег обнулён, исходные шаги/оборот — при следующей «Калибровке»")
        if not self.sim:
            p = S_cfg_path(); f = json.load(open(p)) if os.path.exists(p) else {}
            f["cord"] = c; json.dump(f, open(p, "w"), indent=1)

    def cord_state(self):
        c, L = self.cfg["cord"], self.cfg["cord_life"]; o = self.st.odo if self.st else [0, 0]
        return dict(hz=round(100*(c.get("hz_turns", 0) + o[0])/L["hz"], 1), v=round(100*(c.get("v_turns", 0) + o[1])/L["v"], 1),
                    drift=c.get("drift_ppm"), since=c.get("since", ""))

    # ---------- вынос проекта (как Leica iCON) ----------
    def load_layout(self):
        self.targets, self.lay, self.sel, self.wt = [], {}, None, None
        with contextlib.suppress(Exception): self.wt = json.load(open(os.path.join(self.pdir(), "worktop.json")))
        with contextlib.suppress(Exception):
            self.lay = json.load(open(os.path.join(self.pdir(), "layout.json")))
            if self.lay.get("file"): self.set_layout(self.lay, save=False)

    def upload(self, name, data):
        name = re.sub(r"[^\w\-.]+", "_", os.path.basename(name), flags=re.U)[:60] or "project.dxf"
        if not name.lower().endswith(".dxf"): raise ValueError("нужен .dxf")
        open(os.path.join(self.pdir(), name), "wb").write(data)
        return dict(file=name, layers=LY.dxf_info(os.path.join(self.pdir(), name)))

    def set_layout(self, p, save=True):
        f = os.path.join(self.pdir(), os.path.basename(p["file"]))
        self.targets = LY.targets(f, self.model(), p); self.lay = dict(p); self.sel = 1 if self.targets else None
        self.lay["layers_all"] = LY.dxf_info(f)
        if save: json.dump(self.lay, open(os.path.join(self.pdir(), "layout.json"), "w"), ensure_ascii=False)
        return len(self.targets)

    def _target(self, i):
        t = next((t for t in self.targets if t["id"] == int(i)), None)
        if t is None: raise ValueError("нет такой точки — загрузите DXF")
        return t

    def _ready(self):
        st_ = self.station(); S = self.proj(); cur = self.cur(S)
        if not self.calibrated(cur): raise RuntimeError("сначала «Калибровка» стоянки")
        self.cfg["cal"].update(cur["cal"]); T = self.setup_T(cur["name"])
        if T is None: raise RuntimeError("стоянка не привязана к проекту: «Скан» с опорными марками или «Свободная станция»")
        return st_, S, cur, T

    def _stake(self, st_, P, n):
        """Точка проекта -> луч точно на неё по реальной поверхности. -> (попадание в кадре проекта, отчёт)."""
        R, t = self._T; c = self.cfg["stake"]
        def meas(Q):
            p = st_.point(*st_.aim(Q)); return st_.xyz(p)
        Pst = R.T @ (np.asarray(P, float) - t); nst = None if n is None else R.T @ np.asarray(n, float)
        av = self.cfg["avg"]; self.cfg["avg"] = max(av, c.get("avg", 3))
        try: X, r = LY.stake(meas, Pst, nst, c["iters"], c["tol_mm"])
        finally: self.cfg["avg"] = av
        if nst is not None:                                           # угол падения луча на поверхность
            r["inc"] = float(np.degrees(np.arccos(min(1, abs(X @ nst)/np.linalg.norm(X)/np.linalg.norm(nst)))))
        return R @ X + t, r

    def job_stake(self, i):
        st_, S, cur, self._T = self._ready(); tg = self._target(i); self.sel = tg["id"]
        if tg["kind"] == "line": P = (np.array(tg["A"]) + np.array(tg["B"]))/2; print("  линия: наводка на середину (весь отрезок — «Линия»)")
        else: P = np.array(tg["P"])
        if (cur.get("resect") or {}).get("stale"): print("  ВНИМАНИЕ: свободная станция от прошлой установки — «Своб. станция» или «Проверка ст.»")
        st_.tilt_guard()
        try: H, r = self._stake(st_, P, tg.get("n"))
        except RuntimeError as e: raise RuntimeError(f"точка {tg['id']} не видна с этой стоянки ({e}) — переставьте станцию")
        st_.las.pointer(True)
        e = H - P; self.stk = dict(id=tg["id"], name=tg["name"], P=P.tolist(), hit=H.tolist(), **r)
        sv = "" if r["free"] else (f", поверхность {'выступает' if r['dev'] > 0 else 'утоплена'} на {abs(r['dev']):.1f} мм" if abs(r["dev"]) >= 0.5 else ", поверхность в проекте")
        print(f"  вынос {tg['id']} «{tg['name']}»: X{P[0]:.0f} Y{P[1]:.0f} Z{P[2]:.0f} — лазер на точке, остаток {r['lat']:.1f} мм ({r['it']} изм.){sv}")
        if r.get("inc", 0) > 70: print(f"  луч падает полого ({r['inc']:.0f}° к нормали) — точность хуже; лучше поставить станцию ближе")

    def job_tie(self, i=None, xyz=None):
        """Связь «где сейчас луч» <-> «известная точка проекта» (для свободной станции)."""
        st_ = self.station(); S = self.proj(); cur = self.cur(S)
        if cur["cal"]: self.cfg["cal"].update(cur["cal"])
        if xyz is not None: P = [float(x) for x in xyz]; nm = "XYZ"
        else:
            tg = self._target(i); nm = f"{tg['id']} {tg['name']}"
            if tg["kind"] != "pt": raise ValueError("привязка — к точке, не к линии")
            P = list(map(float, tg["P"]))
        h, v = st_.pos_deg(); D = float(np.median([st_.las.measure() for _ in range(5)]))
        cur.setdefault("ties", []).append(dict(name=nm, raw=[h, v, D], P=P)); self.save(S)
        print(f"  привязка: {nm} -> X{P[0]:.0f} Y{P[1]:.0f} Z{P[2]:.0f} (D={D:.1f}); всего {len(cur['ties'])}")

    def job_resect(self):
        """Свободная станция: ≥2 известные точки (опорные марки прошлых стоянок или точки проекта) -> положение станции."""
        from scan2dxf import to_xyz
        st_ = self.station(); S = self.proj(); cur = self.cur(S)
        if not self.calibrated(cur): raise RuntimeError("сначала «Калибровка»")
        A, B, ids = [], [], []
        known = {r["id"]: r for r in (self.model() or {}).get("refs", []) if r["setup"] != cur["name"]}
        for k, raw in cur.get("refs", {}).items():
            if k in known: A.append(to_xyz(np.array([raw[:3]], float), cur["cal"])[0]); B.append([known[k][q] for q in "xyz"]); ids.append("Т" + k)
        for tq in cur.get("ties", []):
            A.append(to_xyz(np.array([tq["raw"][:3]], float), cur["cal"])[0]); B.append(tq["P"]); ids.append(tq["name"])
        R, t, rep_ = LY.resect(A, B)
        cur["resect"] = dict(R=R.tolist(), t=t.tolist(), ids=ids, **rep_); self.save(S)
        print(f"  свободная станция по {rep_['n']} точкам: СКО {rep_['rms']:.1f} мм, max {rep_['max']:.1f} мм, по высоте {rep_['dz']:.1f} мм")
        for nm, e in zip(ids, rep_["err"]): print(f"    {nm}: {e:.1f} мм" + ("  <- проверьте точку" if e > 3*max(1.0, rep_["rms"]) and rep_["n"] > 2 else ""))
        print(f"  станция в проекте: X{t[0]:.0f} Y{t[1]:.0f} Z{t[2]:.0f}")

    def job_untie(self):
        S = self.proj(); cur = self.cur(S); cur["ties"] = []; cur.pop("resect", None); self.save(S); print("  привязки сброшены")

    def job_check(self):
        """Контроль стоянки: наклон (компенсатор) + повторный замер опорных марок/привязок с теми же углами."""
        st_ = self.station(); S = self.proj(); cur = self.cur(S)
        if not self.calibrated(cur): raise RuntimeError("сначала «Калибровка»")
        self.cfg["cal"].update(cur["cal"]); st_.move_deg(0, 0); dv = st_.tilt_dev(); tol = self.cfg["check_tol_mm"]; rows = []
        items = [("Т" + k, r) for k, r in cur.get("refs", {}).items()] + [(q["name"], q["raw"]) for q in cur.get("ties", [])]
        for nm, raw in items:
            if self.stop: raise Abort()
            st_.move_deg(raw[0], raw[1]); st_.las.pointer(True)
            if not self.sim: time.sleep(2.0)                                      # видно, где лазер относительно марки
            D = float(np.median([st_.las.measure() for _ in range(3)])); rows.append(dict(name=nm, dD=D - raw[2]))
            print(f"  {nm}: ΔD {D - raw[2]:+.1f} мм — лазер в центре марки?")
        bad = (dv is not None and dv > self.cfg["tilt_watch"]["tol_deg"]) or any(abs(r["dD"]) > tol for r in rows)
        self.chk = dict(tilt=dv, rows=rows, ok=not bad, t=time.strftime("%H:%M"))
        print(f"  наклон: {'—' if dv is None else f'{dv:.3f}°'}; " + ("СТАНЦИЯ СДВИНУТА — «Калибровка» и «Свободная станция»" if bad else "стоянка в порядке"))
        if bad: self.alert = "стоянка сдвинута — «Калибровка» и «Свободная станция»"
        elif not rows: print("  нет опорных марок на этой стоянке — проверен только наклон")

    def job_line(self, p):
        """Лазерная линия: точки по отрезку DXF или по уровню на стене; луч ходит туда-обратно до «Стоп»."""
        st_, S, cur, self._T = self._ready(); c = self.cfg["stake"]; step = float(p.get("step") or c["line_step_mm"])
        if p.get("id"):
            tg = self._target(p["id"])
            if tg["kind"] != "line": raise ValueError("выберите линию из DXF")
            Q = LY.line_points(tg["A"], tg["B"], step); n = tg.get("n"); nm = tg["name"]
        else:
            room = LY.room_at(self.model(), (0, 0), p.get("room")); fr = LY.wall_frame(room, p["wall"], int(p.get("corner", 0)))
            u0, u1, h = float(p.get("u0", 50)), float(p.get("u1", 0) or fr["L"] - 50), float(p["h"])
            Q = [np.r_[fr["o"] + u*fr["d"], fr["zo"] + h] for u in np.linspace(u0, u1, max(2, int(abs(u1 - u0)/step) + 1))]
            n = np.r_[fr["n"], 0.0]; nm = f"{p['wall']} H{h:.0f} от угла {fr['corner']}"
        R, t = self._T; exact = bool(p.get("exact", True)); ang, dev = [], []
        st_.tilt_guard(); orig = self._wrap_point(st_, len(Q)*(2.5 if exact else 0))
        try:
            for P in Q:
                if exact:
                    H, r = self._stake(st_, P, n); dev.append(r["dev"]); ang.append(st_.pos_deg())
                else: ang.append(st_.aim(R.T @ (np.asarray(P, float) - t)))
        finally: st_.point = orig
        self.lres = dict(name=nm, n=len(Q), dev=[min(dev), max(dev)] if dev else None)
        if dev: print(f"  линия «{nm}»: {len(Q)} точек, поверхность {min(dev):+.1f}…{max(dev):+.1f} мм от проекта")
        passes = int(p.get("passes", 0)) or 100000; st_.las.pointer(True)
        print("  лазер ведёт линию — отмечайте; «Стоп» — закончить")
        for k in range(passes):
            for a in (ang if k % 2 == 0 else ang[::-1]):
                if self.stop: raise Abort()
                st_.move_deg(*a)
                if not self.sim: time.sleep(c["line_dwell_s"])
            self.progress = (k + 1)/passes if passes < 100000 else 0.5

    def job_compare(self, file, layers):
        m = self.model()
        if not m: raise RuntimeError("сначала «Скан»")
        f = os.path.join(self.pdir(), os.path.basename(file))
        self.cmp = LY.compare(f, layers, m, os.path.join(self.pdir(), "compare.dxf"))
        json.dump(self.cmp, open(os.path.join(self.pdir(), "compare.json"), "w"), ensure_ascii=False)
        for w in self.cmp["walls"]:
            print(f"  {w['wall']}: " + ("нет пары в проекте" if w["off_a"] is None else f"{w['off_a']:+.1f} / {w['off_b']:+.1f} мм, угол {w['ang']:+.2f}°, L {w['len']:.0f} (проект {w['len_p']:.0f})"))
        print("  compare.dxf: PROJECT — проект, FACT — факт, DEVIATION — отклонения")

    # ---------- чертёж при замере (как Flexijet) ----------
    def cad(self):
        p = os.path.join(self.pdir(), "cad.json")
        C = json.load(open(p)) if os.path.exists(p) else {}
        for k, v in (("pts", []), ("els", []), ("tool", "wall"), ("multi", False), ("pending", []), ("next", 1)): C.setdefault(k, v)
        return C

    def cad_xyz(self, C):
        from scan2dxf import to_xyz
        S = self.proj(); cals = {s["name"]: s.get("cal", {}) for s in S["setups"]}; P = {}
        for q in C["pts"]:
            X = to_xyz(np.array([q["raw"]], float), q.get("cal") or cals.get(q["setup"], {}))[0]; T = self.setup_T(q["setup"])
            P[q["id"]] = (T[0] @ X + T[1]) if T is not None else X
        return P

    def cad_save(self, C):
        json.dump(C, open(os.path.join(self.pdir(), "cad.json"), "w"), ensure_ascii=False)
        with contextlib.suppress(Exception):
            P = self.cad_xyz(C); cadm.to_dxf(cadm.solve(P, C["els"]), P, os.path.join(self.pdir(), "cad.dxf"))

    def _cad_close(self, C):
        if not C["pending"]: return
        need = cadm.TOOLS[C["tool"]][1]
        if len(C["pending"]) < need: raise ValueError(f"{cadm.TOOLS[C['tool']][0]}: нужно точек ≥{need}, есть {len(C['pending'])}")
        C["els"].append(dict(id=C["next"], type=C["tool"], pts=list(C["pending"]))); C["next"] += 1; C["pending"] = []

    def job_cad_point(self):
        st_ = self.station(); S = self.proj(); cur = self.cur(S); C = self.cad()
        if cur["cal"]: self.cfg["cal"].update(cur["cal"])
        h, v = st_.pos_deg(); D = float(np.median([st_.las.measure() for _ in range(3)]))
        pid = 1 + max([q["id"] for q in C["pts"]], default=0)
        C["pts"].append(dict(id=pid, raw=[h, v, D], setup=cur["name"], cal=dict(cur["cal"]))); C["pending"].append(pid)
        if not C["multi"] and len(C["pending"]) >= cadm.TOOLS[C["tool"]][1]: self._cad_close(C)
        self.cad_save(C); X = self.cad_xyz(C)[pid]
        print(f"  {cadm.TOOLS[C['tool']][0].lower()}: точка {len(C['pending']) or 'готово'} — X{X[0]:.0f} Y{X[1]:.0f} Z{X[2]:.1f}")

    def cad_cmd(self, b):
        C = self.cad(); c = b["cmd"]
        if c == "cad_tool":
            if b["tool"] not in cadm.TOOLS: raise ValueError("инструмент?")
            C["tool"], C["multi"], C["pending"] = b["tool"], bool(b.get("multi")), []
        elif c == "cad_done": self._cad_close(C)
        elif c == "cad_undo":
            if C["pending"]: C["pending"].pop()
            elif C["els"]: C["els"].pop()
        elif c == "cad_del":
            ids = set(map(int, b["ids"])); C["els"] = [e for e in C["els"] if e["id"] not in ids and not ids & set(e.get("refs", []))]
        elif c == "cad_make":
            ids = list(map(int, b["ids"]))
            if b["op"] not in ("corner", "dist", "angle") or len(ids) < 2: raise ValueError("выберите 2 элемента (для угла комнаты — 2 стены, можно + плоскость пола/потолка)")
            C["els"].append(dict(id=C["next"], type=b["op"], refs=ids[:3])); C["next"] += 1
        elif c == "cad_clear": C = dict(pts=[], els=[], tool=C["tool"], multi=C["multi"], pending=[], next=1)
        self.cad_save(C); return {"ok": 1}

    def cad_state(self):
        with contextlib.suppress(Exception):
            C = self.cad(); P = self.cad_xyz(C); G = cadm.solve(P, C["els"])
            return dict(tool=C["tool"], multi=C["multi"], pending=len(C["pending"]), need=cadm.TOOLS[C["tool"]][1],
                        els=[dict(id=g["id"], type=g["type"], label=g["label"], ok=g["ok"]) for g in G], plan=cadm.plan(G),
                        pend=[np.round(P[i], 1).tolist() for i in C["pending"] if i in P])
        return None

    # ---------- шаблон столешницы (как Flexijet Stone) ----------
    def job_worktop(self, p):
        st_, S, cur, T = self._ready(); R, t = T
        h = float(p.get("h", 900)); D = float(p.get("depth", 600)); step = float(p.get("step", 0.5))
        hz0, hz1 = float(p.get("hz0", 0)), float(p.get("hz1", 360)); z = h - t[2]
        span = (hz1 - hz0) % 360 or 360; orig = self._wrap_point(st_, int(span/step)*1.6)
        try: pts = st_.trace_level(z, hz0, hz1, step)
        finally: st_.point = orig
        st_.ard.move(0, 0)
        if len(pts) < 10: raise RuntimeError("мало точек на трассе — проверьте сектор «Начало/Конец» и высоту")
        Pp = np.array(pts); X = room3d.to_xyz(Pp, self.cfg["cal"])
        W = WT.template(X[:, :2], Pp[:, 0], np.zeros(2), D, p.get("mode", "touch"), WT.parse_cutouts(p.get("cut", "")),
                        float(p.get("e0", 0)), float(p.get("e1", 0)))
        pr = lambda Q: (np.c_[np.asarray(Q, float), np.zeros(len(Q))] @ R.T + t)[:, :2]
        nm = p.get("name") or f"столешница H{h:.0f}"
        WT.to_dxf(W, os.path.join(self.pdir(), "worktop.dxf"), f"{nm}: глубина {D:.0f}, задняя кромка {'по выступу стены' if W['rep']['mode'] == 'touch' else 'по средней линии'}")
        rp = W["rep"]; loc = WT.to_local(W)
        self.wt = dict(name=nm, poly=np.round(pr(W["poly"]), 1).tolist(), cut=[np.round(pr(c["poly"]), 1).tolist() for c in W["cut"]],
                       local=np.round(loc(W["poly"]), 1).tolist(), **{k: rp[k] for k in ("back", "front", "angles", "walls", "area_m2", "depth", "mode")})
        json.dump(self.wt, open(os.path.join(self.pdir(), "worktop.json"), "w"), ensure_ascii=False)
        print(f"  {nm}: задняя кромка " + " + ".join(f"{x:.0f}" for x in rp["back"]) + ", фасад " + " + ".join(f"{x:.0f}" for x in rp["front"]) + f", {rp['area_m2']:.2f} м²")
        for i, w_ in enumerate(rp["walls"]): print(f"    стена {i + 1}: выступ {w_['pro']:.1f} мм, зазор за столешницей до {w_['gap']:.1f} мм")
        print("  worktop.dxf: CONTOUR, CUTOUTS, WALL_ACTUAL (стена по факту), DIM")

    # ---------- данные для экрана ----------
    def state(self):
        pos = None
        if self.st is not None and not self.busy:
            with contextlib.suppress(Exception): pos = self.st.pos_deg()
        setups = []; quick = []; batt = None
        if self.st is not None:
            with contextlib.suppress(Exception):
                if time.time() - getattr(self, "_bt", 0) > 5: self._bv = self.st.battery(); self._bt = time.time()
                batt = self._bv
        with contextlib.suppress(Exception):
            S_ = self.proj(); cur = self.cur(S_)
            quick = [self._quick_xyz(cur, q).round(1).tolist() for q in cur.get("quick", [])]
        with contextlib.suppress(Exception):
            setups = [dict(name=s["name"], refs=sorted(s.get("refs", {})), scanned=bool(s.get("points")), cal="tilt_x" in s.get("cal", {}))
                      for s in self.proj()["setups"]]
        return {"busy": self.busy, "progress": self.progress, "error": self.error, "log": self.log[-60:],
                "project": self.project, "projects": self.projects(), "pos": pos, "last": self.last,
                "sim": self.sim, "setups": setups, "zref": self.zref, "marks": self.marks, "mount": self.cfg["mount"],
                "quick": quick, "batt": batt, "alert": self.alert, "lay": self.lay_state(),
                "cad": self.cad_state() if self.project else None, "wt": self.wt, "cord": self.cord_state(),
                "hzcal": dict(poses=len(self.hzcal_poses()), on=bool(self.cfg.get("hz_err")))}

    def lay_state(self):
        r = None
        with contextlib.suppress(Exception):
            c = self.cur(self.proj()); rs = c.get("resect")
            r = dict(ties=[q["name"] for q in c.get("ties", [])], resect=None if not rs else {k: rs.get(k) for k in ("n", "rms", "max", "dz", "ids", "err", "stale")})
        f = lambda v: None if v is None else np.round(np.asarray(v, float), 1).tolist()
        T = [dict(id=t["id"], name=t["name"], kind=t["kind"], P=f(t.get("P")), A=f(t.get("A")), B=f(t.get("B")), src=f(t["src"]),
                  note=t["note"], layer=t["layer"]) for t in self.targets[:600]]
        return dict(p=self.lay, targets=T, sel=self.sel, stake=self.stk, check=self.chk, cmp=self.cmp, line=self.lres, st=r)

    def room(self, p=None):
        d = self.pdir(p); m = self.model() if p in (None, self.project) else None
        if m is None and os.path.exists(os.path.join(d, "model.json")): m = json.load(open(os.path.join(d, "model.json")))
        files = sorted(os.path.relpath(os.path.join(r, f), d) for r, _, fs in os.walk(d) for f in fs if not f.endswith(".jpg"))
        return dict(project=p or self.project, files=files, model=m)


def fusion_dxf(src, dst):
    """Копия DXF для Fusion 360 / мебельных программ: без облака точек и картинок."""
    import ezdxf
    doc = ezdxf.readfile(src); msp = doc.modelspace()
    for e in list(msp.query("*[layer=='CLOUD' | layer=='ELEVATIONS']")): msp.delete_entity(e)
    doc.saveas(dst)


class H(BaseHTTPRequestHandler):
    app: App = None

    def log_message(self, *a): pass

    def send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if isinstance(body, (dict, list)): body = json.dumps(body, ensure_ascii=False).encode()
        elif isinstance(body, str): body = body.encode()
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items(): self.send_header(k, v)
        self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path); q = parse_qs(u.query); A = self.app
        try:
            if u.path in ("/", "/index.html"):
                return self.send(200, open(os.path.join(HERE, "web", "index.html"), "rb").read(), "text/html; charset=utf-8")
            if u.path == "/api/state": return self.send(200, A.state())
            if u.path == "/api/room": return self.send(200, A.room(q.get("p", [None])[0]))
            if u.path.startswith("/f/"):                      # /f/<проект>/<файл>
                p, rel = unquote(u.path[3:]).split("/", 1)
                base = os.path.realpath(A.pdir(p)); f = os.path.realpath(os.path.join(base, rel))
                if not f.startswith(base + os.sep) or not os.path.isfile(f): return self.send(404, {"error": "нет файла"})
                ct = {".png": "image/png", ".jpg": "image/jpeg", ".json": "application/json",
                      ".dxf": "application/dxf", ".obj": "text/plain", ".stl": "model/stl"}.get(os.path.splitext(f)[1], "application/octet-stream")
                ex = {"Content-Disposition": f'attachment; filename="{os.path.basename(f)}"'} if "dl" in q else None
                return self.send(200, open(f, "rb").read(), ct, ex)
            if u.path.startswith("/zip/"):
                p = unquote(u.path[5:]); d = A.pdir(p); buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                    for root, _, fs in os.walk(d):
                        for f in fs:
                            if "full" in q or not f.endswith(".jpg"):   # сырые кадры — только по ?full
                                z.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), d))
                return self.send(200, buf.getvalue(), "application/zip",
                                 {"Content-Disposition": f'attachment; filename="{p}.zip"'})
            self.send(404, {"error": "нет"})
        except Exception as e:
            self.send(500, {"error": str(e)})

    def do_POST(self):
        A = self.app
        u = urlparse(self.path)
        if u.path == "/api/upload":                       # DXF проекта (тело — файл)
            try:
                n = int(self.headers.get("Content-Length", 0))
                if n > 30_000_000: raise ValueError("файл > 30 МБ")
                if not A.project: A.new_project("obj")
                return self.send(200, A.upload(parse_qs(u.query).get("name", ["project.dxf"])[0], self.rfile.read(n)))
            except Exception as e:
                return self.send(400, {"error": str(e)})
        try:
            n = int(self.headers.get("Content-Length", 0)); b = json.loads(self.rfile.read(n) or b"{}")
            c = b.get("cmd")
            if c == "stop": A.stop = True; return self.send(200, {"ok": 1})
            if c == "new": return self.send(200, {"project": A.new_project(b.get("name", ""))})
            if c == "open":
                if b.get("project") not in A.projects(): raise ValueError("нет проекта")
                A.project = b["project"]; return self.send(200, {"ok": 1})
            if not A.project: A.new_project("obj")
            if c == "layout": return self.send(200, {"n": A.set_layout(b)})
            if c == "sel": A.sel = int(b["id"]); return self.send(200, {"ok": 1})
            if c == "alert_ok": A.alert = None; return self.send(200, {"ok": 1})
            if c == "cord_new": A.cord_save(reset=True); return self.send(200, {"ok": 1})
            if c in ("cad_tool", "cad_done", "cad_undo", "cad_del", "cad_make", "cad_clear"):
                if A.busy: raise RuntimeError("занято")
                return self.send(200, A.cad_cmd(b))
            if c == "mark":                                  # метки сектора для трассы по уровню
                A.marks[b["which"]] = A.st.pos_deg()[0] if A.st else 0.0; return self.send(200, A.marks)
            f = lambda k, dflt: float(b.get(k, dflt))
            jobs = {"scan": (A.job_scan,), "photos": (A.job_photos,), "process": (A.job_process,),
                    "calib": (A.job_calib,), "vindex": (A.job_calib, True), "measure": (A.job_measure, bool(b.get("setref"))),
                    "home": (A.job_home,), "zero": (A.job_zero,), "ref": (A.job_ref, b.get("id", "1")),
                    "newsetup": (A.job_newsetup, b.get("name", "")),
                    "level": (A.job_level, f("h", 900), f("hz0", 0), f("hz1", 360), f("step", 0.5)),
                    "surface": (A.job_surface, b.get("wall", "A-B"), b.get("kind", "wall"), f("h0", 100), f("h1", 2400),
                                f("depth", 600), f("step", 100)),
                    "move": (A.job_move, f("dh", 0), f("dv", 0)), "mount": (A.job_mount, b.get("mount", "tripod")),
                    "qpoint": (A.job_qpoint, "p"), "floorpt": (A.job_qpoint, "f"), "qclear": (A.job_qclear,), "plumb": (A.job_plumb,),
                    "stake": (A.job_stake, b.get("id", A.sel)), "tie": (A.job_tie, b.get("id"), b.get("xyz")),
                    "resect": (A.job_resect,), "untie": (A.job_untie,), "check": (A.job_check,), "line": (A.job_line, b),
                    "cadpt": (A.job_cad_point,), "hzpose": (A.job_hzcal_pose,), "hzsolve": (A.job_hzcal_solve,), "hzreset": (A.job_hzcal_reset,), "worktop": (A.job_worktop, b),
                    "compare": (A.job_compare, b.get("file", A.lay.get("file", "")), b.get("layers") or [])}
            if c not in jobs: raise ValueError(f"команда? {c}")
            A.run(c, *jobs[c]); self.send(200, {"ok": 1})
        except Exception as e:
            self.send(400, {"error": str(e)})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sim", action="store_true"); ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--dir", default="~/scans")
    a = ap.parse_args()
    H.app = App(a.dir, a.sim)
    srv = ThreadingHTTPServer(("0.0.0.0", a.port), H)
    print(f"пульт: http://0.0.0.0:{a.port}  проекты: {H.app.root}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
