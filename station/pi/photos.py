"""Фото стен с привязкой к координатам станции -> развёртки стен в масштабе -> вставка в DXF.
Камера на V-барабане, оптическая ось параллельна лучу дальномера.
Система координат станции: начало в пересечении осей, X/Y — горизонт, Z — вверх.
"""
import json, math, os, subprocess, time
import numpy as np
from PIL import Image, ImageDraw

CAM_DEFAULT = {
    # Pi Camera v2 (IMX219) в режиме 1640x1232 (полное поле зрения). Уточнить командой camalign / калибровкой.
    "width": 1640, "height": 1232, "fx": 1357.0, "fy": 1357.0, "cx": 820.0, "cy": 616.0,
    "k1": 0.0, "k2": 0.0,
    "offset_mm": [0.0, 13.0, 10.0],   # [вправо, вверх, вперёд] от точки пересечения осей, в системе V-барабана
    "yaw_deg": 0.0, "pitch_deg": 0.0, "roll_deg": 0.0,
    "overlap": 0.3, "mm_per_px": 2.0,
    "backend": "rpicam",             # rpicam: Pi Camera (CSI) | v4l2: USB веб-камера | rtsp: Wi-Fi IP-камера
    "device": "/dev/video0",
    "rtsp_url": "rtsp://user:pass@192.168.1.50:554/stream1",   # Tapo: stream1; Imou: /cam/realmonitor?channel=1&subtype=0
    "still_args": ["-n", "-t", "800"],
    # USB-камера: зафиксировать фокус/экспозицию, иначе кадры стыкуются пятнами, напр.:
    # v4l2-ctl -d /dev/video0 -c focus_automatic_continuous=0 -c focus_absolute=0 -c auto_exposure=1
}


def basis(hz, v, cam):
    """Ортонормированный базис камеры (r, up, f) и центр проекции при положении станции hz, v (градусы)."""
    h, w = math.radians(hz), math.radians(v)
    f = np.array([math.cos(w)*math.cos(h), math.cos(w)*math.sin(h), math.sin(w)])
    r = np.array([math.sin(h), -math.cos(h), 0.0])
    up = np.cross(r, f)
    o = cam["offset_mm"]; C = o[0]*r + o[1]*up + o[2]*f
    # малые повороты камеры относительно луча
    ya, pi_, ro = (math.radians(cam[k]) for k in ("yaw_deg", "pitch_deg", "roll_deg"))
    f2 = f + ya*r + pi_*up; f2 /= np.linalg.norm(f2)
    r2 = r - ya*f; r2 = r2 - (r2 @ f2)*f2; r2 /= np.linalg.norm(r2)
    up2 = np.cross(r2, f2)
    r3 = math.cos(ro)*r2 + math.sin(ro)*up2; up3 = np.cross(r3, f2)
    return r3, up3, f2, C


def project(P, hz, v, cam):
    """P (N,3) -> пиксели (N,2), глубина (N,), норм. радиус (N,)."""
    r, up, f, C = basis(hz, v, cam)
    d = P - C
    X, Y, Z = d @ r, -(d @ up), d @ f
    Zs = np.where(Z > 1, Z, np.nan)
    xn, yn = X / Zs, Y / Zs
    r2 = xn*xn + yn*yn; k = 1 + cam["k1"]*r2 + cam["k2"]*r2*r2
    u = cam["cx"] + cam["fx"]*xn*k; w = cam["cy"] + cam["fy"]*yn*k
    return np.c_[u, w], Z, np.sqrt(r2)


def wall_geometry(geom):
    """Стены из *_geom.json: список (имя, P1, P2, zf(x,y), zc(x,y))."""
    C = np.array(geom["corners"]); n = len(C); names = geom["names"]
    kf, kc = np.array(geom["floor"]), np.array(geom["ceiling"])
    walls = []
    for k in range(n):
        a, b = C[k], C[(k+1) % n]
        walls.append((f"{names[k]}-{names[(k+1) % n]}", a, b, kf, kc))
    return walls


def zplane(k, xy): return k[0]*xy[..., 0] + k[1]*xy[..., 1] + k[2]


def plan_shots(wall, cam):
    """Сетка положений (hz, v), покрывающая стену от пола до потолка с перекрытием."""
    _, a, b, kf, kc = wall
    s = np.linspace(0, 1, 41)[:, None]; xy = a + s*(b - a)
    hz = np.degrees(np.unwrap(np.arctan2(xy[:, 1], xy[:, 0])))
    dist = np.linalg.norm(xy, axis=1)
    vlo = np.degrees(np.arctan2(zplane(kf, xy), dist)).min()
    vhi = np.degrees(np.arctan2(zplane(kc, xy), dist)).max()
    fov_h = 2*math.degrees(math.atan(cam["width"]/2/cam["fx"]))
    fov_v = 2*math.degrees(math.atan(cam["height"]/2/cam["fy"]))
    sh, sv = fov_h*(1 - cam["overlap"]), fov_v*(1 - cam["overlap"])
    h0, h1 = min(hz[0], hz[-1]), max(hz[0], hz[-1])
    nh = max(1, math.ceil((h1 - h0 - fov_h*0.9)/sh) + 1); nv = max(1, math.ceil((vhi - vlo - fov_v*0.9)/sv) + 1)
    H = np.linspace(h0 + min(fov_h*0.45, (h1-h0)/2), h1 - min(fov_h*0.45, (h1-h0)/2), nh) if nh > 1 else [(h0+h1)/2]
    V = np.linspace(vlo + min(fov_v*0.45, (vhi-vlo)/2), vhi - min(fov_v*0.45, (vhi-vlo)/2), nv) if nv > 1 else [(vlo+vhi)/2]
    return [(float(h % 360), float(v)) for v in V for h in H]


def capture(path, cam):
    if cam.get("backend") == "rtsp":
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-rtsp_transport", "tcp", "-i", cam["rtsp_url"],
                        "-vf", "select=gte(n\\,15)", "-frames:v", "1", "-q:v", "2", path], check=True)
        return
    if cam.get("backend") == "v4l2":
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "v4l2", "-video_size",
                        f"{cam['width']}x{cam['height']}", "-i", cam["device"],
                        "-vf", "select=gte(n\\,10)", "-frames:v", "1", path], check=True)   # 10 кадров на автоэкспозицию
        return
    for exe in ("rpicam-still", "libcamera-still"):
        try:
            subprocess.run([exe, *cam["still_args"], "--width", str(cam["width"]),
                            "--height", str(cam["height"]), "-o", path], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except FileNotFoundError:
            continue
    raise RuntimeError("нет rpicam-still/libcamera-still: sudo apt install rpicam-apps")


def shoot(station, geom, outdir, cam, capture_fn=capture):
    """Съёмка всех стен. station.move_deg(hz, v) — поворот. Возвращает список кадров."""
    os.makedirs(outdir, exist_ok=True); shots = []
    for wall in wall_geometry(geom):
        for i, (hz, v) in enumerate(plan_shots(wall, cam)):
            hz_r, v_r = station.move_deg(hz, v)                 # фактическое положение после хода
            fn = f"{wall[0]}_{i:02d}.jpg"
            capture_fn(os.path.join(outdir, fn), cam)
            shots.append({"wall": wall[0], "file": fn, "hz": hz_r, "v": v_r})
            print(f"  {wall[0]} кадр {i}: Hz={hz_r:.2f} V={v_r:.2f}", flush=True)
    json.dump({"cam": cam, "shots": shots}, open(os.path.join(outdir, "shots.json"), "w"), indent=1)
    return shots


def bilinear(img, uv):
    h, w = img.shape[:2]
    u = np.clip(uv[:, 0] - 0.5, 0, w - 1.001); v = np.clip(uv[:, 1] - 0.5, 0, h - 1.001)
    u0, v0 = u.astype(int), v.astype(int); du, dv = (u - u0)[:, None], (v - v0)[:, None]
    return (img[v0, u0]*(1-du)*(1-dv) + img[v0, u0+1]*du*(1-dv) +
            img[v0+1, u0]*(1-du)*dv + img[v0+1, u0+1]*du*dv)


def render_sheets(geom, outdir):
    """Развёртки стен (PNG, масштаб mm_per_px) из shots.json. Возвращает [(имя, png, L, z0, z1)]."""
    meta = json.load(open(os.path.join(outdir, "shots.json"))); cam = meta["cam"]; mpp = cam["mm_per_px"]
    res = []
    for name, a, b, kf, kc in wall_geometry(geom):
        L = float(np.linalg.norm(b - a)); t = (b - a) / L
        z0 = float(min(zplane(kf, a), zplane(kf, b))) - 20; z1 = float(max(zplane(kc, a), zplane(kc, b))) + 20
        W, H = int(L / mpp), int((z1 - z0) / mpp)
        s = (np.arange(W) + 0.5) * mpp; z = z1 - (np.arange(H) + 0.5) * mpp
        S, Z = np.meshgrid(s, z); P = np.c_[(a[0] + S*t[0]).ravel(), (a[1] + S*t[1]).ravel(), Z.ravel()]
        out = np.full((len(P), 3), 235.0); best = np.full(len(P), np.inf)
        for sh in (x for x in meta["shots"] if x["wall"] == name):
            img = np.asarray(Image.open(os.path.join(outdir, sh["file"])).convert("RGB"), float)
            uv, depth, rn = project(P, sh["hz"], sh["v"], cam)
            ok = (uv[:, 0] >= 1) & (uv[:, 0] < img.shape[1] - 1) & (uv[:, 1] >= 1) & (uv[:, 1] < img.shape[0] - 1) & (rn < best)
            out[ok] = bilinear(img, uv[ok]); best[ok] = rn[ok]
        im = Image.fromarray(out.reshape(H, W, 3).clip(0, 255).astype(np.uint8))
        d = ImageDraw.Draw(im)
        for x in range(0, int(L) + 1, 100):                     # сетка 100 мм, жирная 500 мм
            X = x / mpp; d.line([(X, H - 12), (X, H)], fill=(255, 0, 0), width=1 + (x % 500 == 0))
            if x % 500 == 0: d.text((X + 3, H - 26), str(x), fill=(255, 0, 0))
        zfa = float(zplane(kf, a))                               # высоты — от пола в начале стены
        for zz in range(0, int(z1 - zfa), 100):
            Y = (z1 - zfa - zz) / mpp; d.line([(0, Y), (12, Y)], fill=(255, 0, 0), width=1 + (zz % 500 == 0))
            if zz % 500 == 0: d.text((15, Y - 6), str(zz), fill=(255, 0, 0))
        d.text((W/2 - 60, 6), f"{name}  L={L:.0f}  1px={mpp:g}mm", fill=(255, 0, 0))
        fn = f"sheet_{name}.png"; im.save(os.path.join(outdir, fn))
        res.append((name, fn, L, z0, z1)); print(f"  развёртка {name}: {W}x{H} px")
    return res


def add_to_dxf(dxf_path, sheets, outdir):
    """Вставка развёрток под план (слой ELEVATIONS), 1 ед. = 1 мм."""
    import ezdxf
    doc = ezdxf.readfile(dxf_path); msp = doc.modelspace()
    if "ELEVATIONS" not in doc.layers: doc.layers.add("ELEVATIONS", color=6)
    ext = [e for e in msp.query("LWPOLYLINE[layer=='WALLS']")]
    pts = np.array([p[:2] for p in ext[0].get_points()]) if ext else np.zeros((1, 2))
    x, y = pts[:, 0].min(), pts[:, 1].min() - 1500
    for name, fn, L, z0, z1 in sheets:
        Hh = z1 - z0; img = Image.open(os.path.join(outdir, fn))
        idef = doc.add_image_def(filename=os.path.relpath(os.path.join(outdir, fn), os.path.dirname(os.path.abspath(dxf_path))),
                                 size_in_pixel=img.size)
        msp.add_image(idef, insert=(x, y - Hh), size_in_units=(L, Hh), dxfattribs={"layer": "ELEVATIONS"})
        msp.add_lwpolyline([(x, y - Hh), (x + L, y - Hh), (x + L, y), (x, y)], close=True, dxfattribs={"layer": "ELEVATIONS"})
        msp.add_text(f"Развёртка {name}", height=100, dxfattribs={"layer": "ELEVATIONS"}).set_placement((x, y + 60))
        x += L + 600
    doc.saveas(dxf_path)


def find_dark_mark(path, near=None, win=220):
    """Центр тёмной метки (чёрный кружок Ø40 мм на белом листе А4). near — прогноз пикселя."""
    a = np.asarray(Image.open(path).convert("L"), float); x0 = y0 = 0
    if near is not None:
        x0, y0 = int(max(0, near[0] - win)), int(max(0, near[1] - win))
        a = a[y0:int(near[1] + win), x0:int(near[0] + win)]
    if a.size == 0: return None
    m = a < (a.min() + 0.35*(np.median(a) - a.min()))
    yy, xx = np.nonzero(m)
    if len(xx) < 6: return None
    return float(xx.mean() + x0), float(yy.mean() + y0)


def camcal(P, obs, cam):
    """Калибровка камеры по наблюдениям одной метки P (мм, сист. станции) с разных (hz, v).
    obs: [(hz, v, u, w)]. Уточняет fx, fy, k1, k2, yaw, pitch (cx, cy — центр кадра)."""
    keys = ["fx", "fy", "k1", "k2", "yaw_deg", "pitch_deg"]; scale = np.array([100, 100, 0.05, 0.05, 0.5, 0.5])
    x = np.array([cam[k] for k in keys], float)
    def res(x):
        c = dict(cam); c.update(dict(zip(keys, x)))
        return np.concatenate([project(P[None], h, v, c)[0][0] - [u, w] for h, v, u, w in obs])
    for _ in range(15):
        r0 = res(x); J = np.stack([(res(x + e*s*1e-3) - r0)/(s*1e-3) for e, s in zip(np.eye(6), scale)], 1)
        dx = np.linalg.lstsq(J, -r0, rcond=None)[0]; x += dx
        if np.all(np.abs(dx) < scale*1e-5): break
    rms = float(np.sqrt(np.mean(res(x)**2)))
    out = dict(zip(keys, map(float, x))); return out, rms


def find_laser_dot(path):
    """Пиксель лазерной точки: максимум «красноты»."""
    a = np.asarray(Image.open(path).convert("RGB"), float)
    red = a[..., 0] - 0.5*(a[..., 1] + a[..., 2])
    y, x = np.unravel_index(np.argmax(red), red.shape)
    m = red[max(0, y-6):y+7, max(0, x-6):x+7]; yy, xx = np.mgrid[max(0, y-6):y+7, max(0, x-6):x+7]
    w = np.clip(m - m.max()*0.5, 0, None)
    return float((xx*w).sum()/w.sum()), float((yy*w).sum()/w.sum())


# ---------------- симулятор камеры (тест без железа) ----------------
def sim_capture_factory(room_min, room_max, origin):
    """Рендер кадра в виртуальной коробке-комнате: шахматка 100 мм + чёрные «розетки» 80x80."""
    room_min, room_max, O = np.array(room_min, float), np.array(room_max, float), np.array(origin, float)
    sockets = [(0, 4000, 1000, 300), (1, 3200, 2500, 1100), (0, 0, 600, 900)]   # (ось, коорд. стены, вдоль, z)

    def cap(path, cam, hz=None, v=None):
        W, H = cam["width"], cam["height"]
        r, up, f, C = basis(hz, v, cam)
        uu, vv = np.meshgrid(np.arange(W) + 0.5, np.arange(H) + 0.5)
        xn = (uu - cam["cx"]) / cam["fx"]; yn = (vv - cam["cy"]) / cam["fy"]
        xd, yd = xn.copy(), yn.copy()
        for _ in range(8):                                  # обратная дисторсия
            r2 = xn*xn + yn*yn; k = 1 + cam["k1"]*r2 + cam["k2"]*r2*r2
            xn, yn = xd / k, yd / k
        D = (xn[..., None]*r - yn[..., None]*up + f).reshape(-1, 3); Cw = C + O
        t = np.full(len(D), np.inf); hit_ax = np.zeros(len(D), int)
        for ax in range(3):
            for lim in (room_min[ax], room_max[ax]):
                with np.errstate(divide="ignore", invalid="ignore"):
                    tt = (lim - Cw[ax]) / D[:, ax]
                ok = (tt > 0) & (tt < t)
                t[ok] = tt[ok]; hit_ax[ok] = ax
        P = Cw + D * t[:, None]
        q = np.floor(P / 100).astype(int)
        chk = (q[:, 0] + q[:, 1] + q[:, 2]) % 2
        col = np.where(chk[:, None] == 1, [[200, 190, 170]], [[120, 140, 160]]).astype(float)
        col[hit_ax == 2] = [[180, 180, 180]]
        for ax, c, along, z in sockets:
            o = 1 - ax
            m = (hit_ax == ax) & (np.abs(P[:, ax] - c) < 1) & (P[:, o] >= along) & (P[:, o] <= along + 80) & (P[:, 2] >= z) & (P[:, 2] <= z + 80)
            col[m] = 0
        Image.fromarray(col.reshape(H, W, 3).astype(np.uint8)).save(path, quality=92)
    return cap
