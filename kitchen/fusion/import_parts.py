# -*- coding: utf-8 -*-
"""Fusion 360: построение деталей кухни из kitchen-parts.json (кнопка «JSON → Fusion» в конфигураторе).
Каждый шкаф — отдельный компонент, каждая деталь — тело-параллелепипед с именем.
Вертикаль: Z (при Y-up спросит; обратный пересчёт: X=x, Y=z, Z=-y). Единицы: мм → см.
"""
import adsk.core, adsk.fusion, traceback, json


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
        root = design.rootComponent
        mgr = adsk.fusion.TemporaryBRepManager.get()
        parametric = design.designType == adsk.fusion.DesignTypes.ParametricDesignType
        comps = {}
        k = 0.1  # мм → см
        for p in data['parts']:
            cab = p['cab']
            if cab not in comps:
                occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
                occ.component.name = cab
                comps[cab] = occ.component
            comp = comps[cab]
            lo, hi = p['min'], p['max']
            if z_up:
                a, b = [lo[0] * k, lo[1] * k, lo[2] * k], [hi[0] * k, hi[1] * k, hi[2] * k]
            else:
                a, b = [lo[0] * k, lo[2] * k, -hi[1] * k], [hi[0] * k, hi[2] * k, -lo[1] * k]
            c = adsk.core.Point3D.create((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2)
            box = adsk.core.OrientedBoundingBox3D.create(
                c, adsk.core.Vector3D.create(1, 0, 0), adsk.core.Vector3D.create(0, 1, 0),
                b[0] - a[0], b[1] - a[1], b[2] - a[2])
            tmp = mgr.createBox(box)
            if parametric:
                bf = comp.features.baseFeatures.add()
                bf.startEdit()
                body = comp.bRepBodies.add(tmp, bf)
                bf.finishEdit()
            else:
                body = comp.bRepBodies.add(tmp)
            body.name = p['name']
        ui.messageBox('Создано деталей: %d, шкафов: %d' % (len(data['parts']), len(comps)))
    except Exception:
        ui.messageBox('Ошибка:\n' + traceback.format_exc())
