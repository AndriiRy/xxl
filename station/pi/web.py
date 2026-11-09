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
S_cfg_path = lambda: S.CFG_PATH


class Abort(Exception): pass


class App:
    def __init__(self, root, sim):
        self.root, self.sim = os.path.expanduser(root), sim
        os.makedirs(self.root, exist_ok=True)
        self.cfg = S.load_cfg(); self.st = None
        self.file_cal = (json.load(open(S.CFG_PATH)).get("cal", {}) if os.path.exists(S.CFG_PATH) else {})
        self.lock = threading.Lock()
        self.busy = None; self.progress = 0.0; self.error = None; self.stop = False
        self.log = []; self.last = {}; self.zref = None; self.marks = {}
        projs = self.projects(); self.project = projs[0] if projs else None

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
        self.project = p; return p

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
            except Exception as e:
                self.error = f"{type(e).__name__}: {e}"; self.say("ОШИБКА " + self.error)
                self.say(traceback.format_exc(limit=4))
            finally:
                self.busy = None
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
        """Кадр стоянки -> кадр проекта (R 3x3, t) из model.json."""
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
        st_ = self.station(); S = self.proj(); cur = self.cur(S)
        self.progress = 0.05; st_.v_home(); st_.move_deg(st_.pos_deg()[0], 0)
        self.progress = 0.1; st_.level(); st_.v_home(); self.progress = 0.4
        if full or self.sim or "v0" not in self.file_cal: st_.v_index()
        else: print(f"  индекс V из config.json: {self.cfg['cal']['v0']:+.4f}° (полная калибровка — кнопка «Индекс V»)")
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
        self.save(S); self.rebuild()

    def job_mount(self, m):
        if m not in self.cfg["mounts"]: raise ValueError("установка: tripod | floor | table")
        self.cfg["mount"] = m; S = self.proj(); cur = self.cur(S); cur["mount"] = m
        for k in ("tilt_x", "tilt_y"): cur["cal"].pop(k, None); self.cfg["cal"].pop(k, None)
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
        for k in ("tilt_x", "tilt_y"): self.cfg["cal"].pop(k, None)
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
                "quick": quick, "batt": batt}

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
        try:
            n = int(self.headers.get("Content-Length", 0)); b = json.loads(self.rfile.read(n) or b"{}")
            c = b.get("cmd")
            if c == "stop": A.stop = True; return self.send(200, {"ok": 1})
            if c == "new": return self.send(200, {"project": A.new_project(b.get("name", ""))})
            if c == "open":
                if b.get("project") not in A.projects(): raise ValueError("нет проекта")
                A.project = b["project"]; return self.send(200, {"ok": 1})
            if not A.project: A.new_project("obj")
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
                    "qpoint": (A.job_qpoint, "p"), "floorpt": (A.job_qpoint, "f"), "qclear": (A.job_qclear,), "plumb": (A.job_plumb,)}
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
