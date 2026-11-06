# -*- coding: utf-8 -*-
"""Fusion 360: экспорт стен/окон/дверей/коммуникаций в JSON для конфигуратора кухни.

Установка: Fusion → Utilities → Add-Ins → Scripts and Add-Ins → «+» → выбрать эту папку/файл.
Именование тел (регистр не важен, достаточно начала имени):
  Стена*/Wall*, Окно*/Window*, Дверь*/Door*, Вода*/Water*, Канализ*/Sewer*, Газ*/Gas*,
  Розетк*/Socket*, Вытяж*/Vent*, Колонн*/Column*. Остальные тела → тип «other».
Экспортируются только ВИДИМЫЕ тела (лампочка включена).
Для каждого тела: габарит (min/max) и контур на плане (poly) — внешний контур нижней плоской грани,
поэтому наклонные стены, парапеты эркера (8-угольник) и т.п. передаются точно. Дуги — ломаной по 8 точкам.
Парапет эркера: тело «Парапет…» высотой до подоконника, над ним — «Окно…».
Единицы: мм. Вертикаль — Z (при Y-up спросит и пересчитает: x=X, y=-Z, z=Y).
"""
import adsk.core, adsk.fusion, traceback, json

KEYS = [
    ('wall', ['стена', 'wall']), ('parapet', ['парапет', 'parapet', 'подоконн']), ('window', ['окно', 'window']), ('door', ['дверь', 'door']),
    ('water', ['вода', 'water']), ('sewer', ['канализ', 'sewer', 'drain']), ('gas', ['газ', 'gas']),
    ('socket', ['розетк', 'socket', 'outlet']), ('vent', ['вытяж', 'vent', 'hood']),
    ('column', ['колонн', 'column', 'pillar']),
]


def kind(name):
    n = name.lower().strip()
    for k, prefixes in KEYS:
        for p in prefixes:
            if n.startswith(p):
                return k
    return 'other'


def footprint(body, plan, up):
    """Внешний контур самой нижней плоской грани с нормалью вниз → [[x,y],...] в мм плана."""
    best = None
    for face in body.faces:
        if face.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        ok, n = face.evaluator.getNormalAtPoint(face.pointOnFace)
        if not ok or n.x * up[0] + n.y * up[1] + n.z * up[2] > -0.999:
            continue
        p = face.pointOnFace
        h = p.x * up[0] + p.y * up[1] + p.z * up[2]
        if best is None or h < best[0]:
            best = (h, face)
    if best is None:
        return None
    for loop in best[1].loops:
        if not loop.isOuter:
            continue
        pts = []
        for ce in loop.coEdges:
            e = ce.edge
            if e.geometry.curveType == adsk.core.Curve3DTypes.Line3DCurveType:
                v = e.endVertex if ce.isOpposedToEdge else e.startVertex
                pts.append(plan(v.geometry))
            else:
                ev = e.evaluator
                ok, t0, t1 = ev.getParameterExtents()
                ts = [t0 + (t1 - t0) * k / 8.0 for k in range(8)]
                if ce.isOpposedToEdge:
                    ts = [t1 - (t1 - t0) * k / 8.0 for k in range(8)]
                ok, ps = ev.getPointsAtParameters(ts)
                pts.extend(plan(q) for q in ps)
        return pts if len(pts) >= 3 else None
    return None


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('Откройте дизайн (Design).')
            return
        z_up = ui.messageBox('Вертикальная ось модели — Z?\n(Да = Z вверх, Нет = Y вверх)', 'Экспорт стен',
                             adsk.core.MessageBoxButtonTypes.YesNoButtonType) == adsk.core.DialogResults.DialogYes
        root = design.rootComponent
        bodies = list(root.bRepBodies)
        for occ in root.allOccurrences:
            bodies.extend(list(occ.bRepBodies))   # прокси-тела в контексте сборки
        up = (0, 0, 1) if z_up else (0, 1, 0)

        def plan(p):  # точка модели (см) → [x, y] плана (мм)
            return [round(p.x * 10.0, 1), round((p.y if z_up else -p.z) * 10.0, 1)]

        out, zmax = [], 0.0
        for b in bodies:
            if not b.isVisible:
                continue
            bb = b.boundingBox
            mn, mx = bb.minPoint, bb.maxPoint
            k = 10.0  # см → мм
            if z_up:
                lo = [mn.x * k, mn.y * k, mn.z * k]
                hi = [mx.x * k, mx.y * k, mx.z * k]
            else:
                lo = [mn.x * k, -mx.z * k, mn.y * k]
                hi = [mx.x * k, -mn.z * k, mx.y * k]
            t = kind(b.name)
            if t in ('wall', 'parapet'):
                zmax = max(zmax, hi[2])
            item = {'name': b.name, 'type': t, 'min': [round(v, 1) for v in lo], 'max': [round(v, 1) for v in hi]}
            try:
                poly = footprint(b, plan, up)
                if poly:
                    item['poly'] = poly
            except Exception:
                pass  # останется габарит
            out.append(item)
        dlg = ui.createFileDialog()
        dlg.title = 'Сохранить стены'
        dlg.filter = 'JSON (*.json)'
        dlg.initialFilename = 'walls.json'
        if dlg.showSave() != adsk.core.DialogResults.DialogOK:
            return
        with open(dlg.filename, 'w', encoding='utf-8') as f:
            json.dump({'format': 'kitchen-walls/1', 'units': 'mm', 'height': round(zmax or 2700, 1), 'bodies': out}, f, ensure_ascii=False, indent=1)
        ui.messageBox('Экспортировано тел: %d\n%s' % (len(out), dlg.filename))
    except Exception:
        ui.messageBox('Ошибка:\n' + traceback.format_exc())
