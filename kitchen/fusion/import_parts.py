# -*- coding: utf-8 -*-
"""Fusion 360: построение деталей кухни из kitchen-parts.json (кнопка «JSON → Fusion» в конфигураторе).
Каждый шкаф — отдельный компонент, каждая деталь — тело с именем.
Прямоугольные детали (в т.ч. повёрнутые на любой угол) — ориентированный бокс; фигурные
(столешницы с подрезкой, треугольники угловых вставок) — эскиз контура + выдавливание.
Вертикаль: Z (при Y-up спросит; обратный пересчёт: X=x, Y=z, Z=-y). Единицы: мм → см.
"""
import adsk.core, adsk.fusion, traceback, json, math

K = 0.1  # мм → см


def is_rect(p):
    if len(p) != 4:
        return False
    for i in range(4):
        a, b, c = p[i - 1], p[i], p[(i + 1) % 4]
        if abs((a[0] - b[0]) * (c[0] - b[0]) + (a[1] - b[1]) * (c[1] - b[1])) > 1.0:
            return False
    return True


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        dlg = ui.createFileDialog()
        dlg.title = 'kitchen-parts.json'
        dlg.filter = 'JSON (*.json)'
        if dlg.showOpen() != adsk.core.DialogResults.DialogOK:
            return
        with open(dlg.filename, encoding='utf-8') as f:
            data = json.load(f)
        z_up = ui.messageBox('Вертикальная ось модели — Z?\n(Да = Z вверх, Нет = Y вверх)', 'Импорт деталей',
                             adsk.core.MessageBoxButtonTypes.YesNoButtonType) == adsk.core.DialogResults.DialogYes

        def M(x, y, z):  # план (мм) → модель (см)
            return adsk.core.Point3D.create(x * K, y * K, z * K) if z_up else adsk.core.Point3D.create(x * K, z * K, -y * K)

        def Vd(x, y):  # направление на плане → вектор модели
            return adsk.core.Vector3D.create(x, y, 0) if z_up else adsk.core.Vector3D.create(x, 0, -y)

        upv = adsk.core.Vector3D.create(0, 0, 1) if z_up else adsk.core.Vector3D.create(0, 1, 0)
        root = design.rootComponent
        mgr = adsk.fusion.TemporaryBRepManager.get()
        parametric = design.designType == adsk.fusion.DesignTypes.ParametricDesignType
        comps, n = {}, 0
        for p in data['parts']:
            cab = p['cab']
            if cab not in comps:
                occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
                occ.component.name = cab
                comps[cab] = occ.component
            comp = comps[cab]
            poly = p.get('poly') or [[p['min'][0], p['min'][1]], [p['max'][0], p['min'][1]], [p['max'][0], p['max'][1]], [p['min'][0], p['max'][1]]]
            z0 = p.get('z0', p['min'][2])
            z1 = p.get('z1', p['max'][2])
            if is_rect(poly):
                a, b, c = poly[0], poly[1], poly[2]
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                W = math.hypot(c[0] - b[0], c[1] - b[1])
                cx = sum(q[0] for q in poly) / 4.0
                cy = sum(q[1] for q in poly) / 4.0
                box = adsk.core.OrientedBoundingBox3D.create(
                    M(cx, cy, (z0 + z1) / 2.0), Vd((b[0] - a[0]) / L, (b[1] - a[1]) / L), Vd((c[0] - b[0]) / W, (c[1] - b[1]) / W),
                    L * K, W * K, (z1 - z0) * K)
                tmp = mgr.createBox(box)
                if parametric:
                    bf = comp.features.baseFeatures.add()
                    bf.startEdit()
                    body = comp.bRepBodies.add(tmp, bf)
                    bf.finishEdit()
                else:
                    body = comp.bRepBodies.add(tmp)
            else:
                sk = comp.sketches.add(comp.xYConstructionPlane if z_up else comp.xZConstructionPlane)
                pts = [sk.modelToSketchSpace(M(q[0], q[1], 0)) for q in poly]
                lines = sk.sketchCurves.sketchLines
                first = prev = lines.addByTwoPoints(pts[0], pts[1])
                for q in pts[2:]:
                    prev = lines.addByTwoPoints(prev.endSketchPoint, q)
                lines.addByTwoPoints(prev.endSketchPoint, first.startSketchPoint)
                normal = sk.xDirection.crossProduct(sk.yDirection)
                sgn = 1.0 if normal.dotProduct(upv) > 0 else -1.0
                ext = comp.features.extrudeFeatures
                inp = ext.createInput(sk.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                inp.startExtent = adsk.fusion.OffsetStartDefinition.create(adsk.core.ValueInput.createByReal(sgn * z0 * K))
                inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(sgn * (z1 - z0) * K))
                body = ext.add(inp).bodies.item(0)
            body.name = p['name']
            n += 1
        ui.messageBox('Создано деталей: %d, шкафов: %d' % (n, len(comps)))
    except Exception:
        ui.messageBox('Ошибка:\n' + traceback.format_exc())
