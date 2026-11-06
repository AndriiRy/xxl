# -*- coding: utf-8 -*-
"""Fusion 360: построение деталей кухни из kitchen-parts.json (кнопка «JSON → Fusion» в конфигураторе).
Формат kitchen-parts/3: каждая деталь — призма: плоский контур P (точки x,y,z, мм) + вектор выдавливания e.
Деталь строится эскизом на XY в своём компоненте шкафа, выдавливается на |e| и переносится матрицей
в мировое положение (подходит для любых углов, скосов и вырезов).
Вертикаль: Z (при Y-up спросит; пересчёт: X=x, Y=z, Z=-y). Единицы: мм → см.
"""
import adsk.core, adsk.fusion, traceback, json, math

K = 0.1  # мм → см


def v3(a):
    return adsk.core.Vector3D.create(a[0], a[1], a[2])


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

        def M(p):  # мм план → см модели
            return [p[0] * K, p[1] * K, p[2] * K] if z_up else [p[0] * K, p[2] * K, -p[1] * K]

        root = design.rootComponent
        comps, n = {}, 0
        for p in data['parts']:
            cab = p['cab']
            if cab not in comps:
                occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
                occ.component.name = cab
                comps[cab] = occ.component
            comp = comps[cab]
            if 'P' in p:
                P, e = p['P'], p['e']
            else:  # старый формат — бокс
                a, b = p['min'], p['max']
                P = [[a[0], a[1], a[2]], [b[0], a[1], a[2]], [b[0], b[1], a[2]], [a[0], b[1], a[2]]]
                e = [0, 0, b[2] - a[2]]
            W = [M(q) for q in P]
            E = M([e[0], e[1], e[2]])
            if not z_up:  # для вектора — без сдвига, тот же поворот
                E = [e[0] * K, e[2] * K, -e[1] * K]
            o = W[0]
            U = [W[1][i] - o[i] for i in range(3)]
            lu = math.sqrt(sum(x * x for x in U))
            U = [x / lu for x in U]
            le = math.sqrt(sum(x * x for x in E))
            N = [x / le for x in E]
            # V = N × U  (правая тройка U, V, N)
            Vv = [N[1] * U[2] - N[2] * U[1], N[2] * U[0] - N[0] * U[2], N[0] * U[1] - N[1] * U[0]]
            # U может быть не ⟂ N, если контур не перпендикулярен e — ортогонализуем
            dUN = sum(U[i] * N[i] for i in range(3))
            U = [U[i] - dUN * N[i] for i in range(3)]
            lu = math.sqrt(sum(x * x for x in U))
            U = [x / lu for x in U]
            Vv = [N[1] * U[2] - N[2] * U[1], N[2] * U[0] - N[0] * U[2], N[0] * U[1] - N[1] * U[0]]
            loc = [[sum((q[i] - o[i]) * U[i] for i in range(3)), sum((q[i] - o[i]) * Vv[i] for i in range(3))] for q in W]
            sk = comp.sketches.add(comp.xYConstructionPlane)
            lines = sk.sketchCurves.sketchLines
            pts = [adsk.core.Point3D.create(x, y, 0) for x, y in loc]
            first = prev = lines.addByTwoPoints(pts[0], pts[1])
            for q in pts[2:]:
                prev = lines.addByTwoPoints(prev.endSketchPoint, q)
            lines.addByTwoPoints(prev.endSketchPoint, first.startSketchPoint)
            ext = comp.features.extrudeFeatures
            inp = ext.createInput(sk.profiles.item(0), adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            # высота вдоль N (контур может быть не перпендикулярен e — тогда берётся проекция)
            h = sum(E[i] * N[i] for i in range(3))
            inp.setDistanceExtent(False, adsk.core.ValueInput.createByReal(h))
            feat = ext.add(inp)
            body = feat.bodies.item(0)
            body.name = p['name']
            sk.isVisible = False
            mtx = adsk.core.Matrix3D.create()
            mtx.setWithCoordinateSystem(adsk.core.Point3D.create(o[0], o[1], o[2]), v3(U), v3(Vv), v3(N))
            col = adsk.core.ObjectCollection.create()
            col.add(body)
            mv = comp.features.moveFeatures
            mv.add(mv.createInput(col, mtx))
            n += 1
        ui.messageBox('Создано деталей: %d, шкафов: %d' % (n, len(comps)))
    except Exception:
        ui.messageBox('Ошибка:\n' + traceback.format_exc())
