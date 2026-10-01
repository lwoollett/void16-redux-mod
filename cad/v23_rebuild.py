import adsk.core, adsk.fusion, json, traceback, math
MM = 0.1
C6 = math.cos(math.radians(6)); S6 = math.sin(math.radians(6)); T6 = math.tan(math.radians(6))
log = []
def V(x): return adsk.core.ValueInput.createByReal(x)
def P(x, y, z=0.0): return adsk.core.Point3D.create(x*MM, y*MM, z*MM)
def OC(items):
    c = adsk.core.ObjectCollection.create()
    for i in items: c.add(i)
    return c
def body_names():
    return [b.name for b in root.bRepBodies]
try:
    app = adsk.core.Application.get()
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    voids = json.load(open('/tmp/to_voids.json'))
    insets = json.load(open('/tmp/to_inset.json'))
    polys = voids['polygons']; inset = insets['inset']
    def ext(profiles, op, dist_mm, start_mm=None, participants=None, sym_cm=None, taper_deg=None):
        ei = root.features.extrudeFeatures.createInput(profiles, op)
        if start_mm is not None:
            ei.startExtent = adsk.fusion.OffsetStartDefinition.create(V(start_mm*MM))
        if sym_cm is not None:
            ei.setSymmetricExtent(V(sym_cm), True)
        else:
            ei.setDistanceExtent(False, V(dist_mm*MM))
        if taper_deg is not None:
            ei.taperAngle = V(math.radians(taper_deg))
        if participants is not None:
            ei.participantBodies = list(participants)
        return root.features.extrudeFeatures.add(ei)
    def combine(target, tools, op):
        ci = root.features.combineFeatures.createInput(target, OC(tools))
        ci.operation = op
        return root.features.combineFeatures.add(ci)
    def all_profiles(sk):
        return OC([sk.profiles.item(i) for i in range(sk.profiles.count)])
    def sliver_at(sk, x0, y0, x1, y1, r):
        L = sk.sketchCurves.sketchLines
        L.addByTwoPoints(P(x0, y0+r), P(x0, y0)); L.addByTwoPoints(P(x0, y0), P(x0+r, y0))
        sk.sketchCurves.sketchArcs.addByCenterStartSweep(P(x0+r, y0+r), P(x0+r, y0), -math.pi/2)
        L.addByTwoPoints(P(x1-r, y0), P(x1, y0)); L.addByTwoPoints(P(x1, y0), P(x1, y0+r))
        sk.sketchCurves.sketchArcs.addByCenterStartSweep(P(x1-r, y0+r), P(x1, y0+r), -math.pi/2)
        L.addByTwoPoints(P(x0, y1-r), P(x0, y1)); L.addByTwoPoints(P(x0, y1), P(x0+r, y1))
        sk.sketchCurves.sketchArcs.addByCenterStartSweep(P(x0+r, y1-r), P(x0+r, y1), math.pi/2)
        L.addByTwoPoints(P(x1, y1-r), P(x1, y1)); L.addByTwoPoints(P(x1, y1), P(x1-r, y1))
        sk.sketchCurves.sketchArcs.addByCenterStartSweep(P(x1-r, y1-r), P(x1-r, y1), -math.pi/2)
    def spline_loop(sk, pts):
        coll = OC([adsk.core.Point3D.create(p[0]*MM, p[1]*MM, 0) for p in pts])
        spl = sk.sketchCurves.sketchFittedSplines.add(coll)
        sk.sketchCurves.sketchLines.addByTwoPoints(coll.item(coll.count-1), coll.item(0))
        return spl
    W, T, FT, WT, R = 84.45, 2.5, 3.0, 2.5, 2.0
    Y0, Y1 = -3.5, 110.5
    PLX0, PLX1 = 2.725, 81.725
    PLY0, PLY1 = -0.78, 107.75
    COLS = [13.65, 32.7, 51.75, 70.8]; ROWS = [13.63, 32.68, 51.73, 70.78]
    ENC = [(13.65, 89.83), (70.8, 89.83)]
    INS_XY = [(20.0, 102.4), (64.0, 102.4), (4.5, 89.0), (79.95, 89.0)]
    PROP_XY = [(23.175, 0.9), (42.225, 0.9), (61.275, 0.9)]
    USB_X = (25.5, 34.5)
    sk = root.sketches.add(root.xYConstructionPlane)
    sk.sketchCurves.sketchLines.addTwoPointRectangle(P(0,Y0), P(W,Y1))
    ext(all_profiles(sk), adsk.fusion.FeatureOperations.NewBodyFeatureOperation, 28.0)
    bottom = root.bRepBodies.item(0); bottom.name = 'Bottom Plate'
    sk2 = root.sketches.add(root.xYConstructionPlane)
    sliver_at(sk2, 0, Y0, W, Y1, R)
    assert sk2.profiles.count == 4
    ext(all_profiles(sk2), adsk.fusion.FeatureOperations.CutFeatureOperation, 29, start_mm=-0.5, participants=[bottom])
    sk3 = root.sketches.add(root.xYConstructionPlane)
    sk3.sketchCurves.sketchLines.addTwoPointRectangle(P(WT, Y0+WT), P(W-WT, Y1-WT))
    ext(all_profiles(sk3), adsk.fusion.FeatureOperations.CutFeatureOperation, 32, start_mm=FT, participants=[bottom])
    skto = root.sketches.add(root.xYConstructionPlane)
    n_spl = 0
    for poly in polys:
        step = max(1, len(poly)//85)
        spline_loop(skto, poly[::step])
        n_spl += 1
    assert skto.profiles.count == n_spl
    try:
        ext(all_profiles(skto), adsk.fusion.FeatureOperations.CutFeatureOperation, 10.6, start_mm=-1, participants=[bottom], taper_deg=4)
        log.append('spline void cut ok (tapered)')
    except:
        ext(all_profiles(skto), adsk.fusion.FeatureOperations.CutFeatureOperation, 10.6, start_mm=-1, participants=[bottom])
        log.append('spline void cut ok (no taper)')
    ski = root.sketches.add(root.xYConstructionPlane)
    n_ins = 0
    for poly in inset:
        spline_loop(ski, poly)
        n_ins += 1
    assert ski.profiles.count == n_ins
    ext(all_profiles(ski), adsk.fusion.FeatureOperations.CutFeatureOperation, 2.5, start_mm=7.2, participants=[bottom])
    log.append('inset top-step ok')
    def post_bodies(points, r_mm, h_mm):
        skp = root.sketches.add(root.xYConstructionPlane)
        for (x, y) in points:
            skp.sketchCurves.sketchCircles.addByCenterRadius(P(x, y), r_mm*MM)
        before = set(body_names())
        ext(all_profiles(skp), adsk.fusion.FeatureOperations.NewBodyFeatureOperation, h_mm, start_mm=0)
        ps = [b for b in root.bRepBodies if b.name not in before]
        assert len(ps) == len(points)
        combine(bottom, ps, adsk.fusion.FeatureOperations.JoinFeatureOperation)
        assert len(root.bRepBodies) == 1
    post_bodies(INS_XY, 3.5, 30)
    post_bodies(PROP_XY, 3.25, 30)
    sk5 = root.sketches.add(root.xYConstructionPlane)
    sk5.sketchCurves.sketchLines.addTwoPointRectangle(P(19.0,67.7), P(21.0,108.5))
    sk5.sketchCurves.sketchLines.addTwoPointRectangle(P(39.0,67.7), P(41.0,108.5))
    before = set(body_names())
    ext(all_profiles(sk5), adsk.fusion.FeatureOperations.NewBodyFeatureOperation, 4.5, start_mm=0)
    rails = [b for b in root.bRepBodies if b.name not in before]
    assert len(rails) == 2
    combine(bottom, rails, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    skped = root.sketches.add(root.xYConstructionPlane)
    skped.sketchCurves.sketchLines.addTwoPointRectangle(P(21.0,67.7), P(39.0,108.5))
    before = set(body_names())
    ext(all_profiles(skped), adsk.fusion.FeatureOperations.NewBodyFeatureOperation, 4.5, start_mm=0)
    ped = [b for b in root.bRepBodies if b.name not in before][0]
    combine(bottom, [ped], adsk.fusion.FeatureOperations.JoinFeatureOperation)
    skg = root.sketches.add(root.xYConstructionPlane)
    skg.sketchCurves.sketchLines.addTwoPointRectangle(P(19.0,67.7), P(21.0,108.5))
    skg.sketchCurves.sketchLines.addTwoPointRectangle(P(39.0,67.7), P(41.0,108.5))
    before = set(body_names())
    ext(all_profiles(skg), adsk.fusion.FeatureOperations.NewBodyFeatureOperation, 1.6, start_mm=4.4)
    guides = [b for b in root.bRepBodies if b.name not in before]
    assert len(guides) == 2
    combine(bottom, guides, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    assert len(root.bRepBodies) == 1
    log.append('posts+pedestal+guides ok')
    skbc = root.sketches.add(root.xYConstructionPlane)
    skbc.sketchCurves.sketchLines.addTwoPointRectangle(P(41.2, 67.4), P(65.6, 98.6))
    skbc.sketchCurves.sketchLines.addTwoPointRectangle(P(41.2, 98.6), P(60.4, 107.9))
    assert skbc.profiles.count == 2
    ext(all_profiles(skbc), adsk.fusion.FeatureOperations.CutFeatureOperation, 11.0, start_mm=-1, participants=[bottom])
    skbp = root.sketches.add(root.xYConstructionPlane)
    skbp.sketchCurves.sketchLines.addTwoPointRectangle(P(39.8, 67.4), P(65.6, 108.5))
    before = set(body_names())
    ext(all_profiles(skbp), adsk.fusion.FeatureOperations.NewBodyFeatureOperation, 4.5, start_mm=0)
    pad = [b for b in root.bRepBodies if b.name not in before][0]
    combine(bottom, [pad], adsk.fusion.FeatureOperations.JoinFeatureOperation)
    assert len(root.bRepBodies) == 1
    skbl = root.sketches.add(root.xYConstructionPlane)
    skbl.sketchCurves.sketchLines.addTwoPointRectangle(P(39.8, 67.4), P(42.4, 108.5))
    skbl.sketchCurves.sketchLines.addTwoPointRectangle(P(63.4, 67.4), P(65.6, 108.5))
    skbl.sketchCurves.sketchLines.addTwoPointRectangle(P(42.4, 106.5), P(63.4, 108.5))
    assert skbl.profiles.count == 3
    before = set(body_names())
    ext(all_profiles(skbl), adsk.fusion.FeatureOperations.NewBodyFeatureOperation, 3.5, start_mm=4.5)
    lips = [b for b in root.bRepBodies if b.name not in before]
    combine(bottom, lips, adsk.fusion.FeatureOperations.JoinFeatureOperation)
    assert len(root.bRepBodies) == 1
    log.append('battery bay ok (pad = clearance blanket)')
    # MCU relief: void everything above the MCU footprint up to +1mm over the USB-C port
    # (clears the back-left post corner that runs through the board's back-left corner)
    skmcu = root.sketches.add(root.xYConstructionPlane)
    skmcu.sketchCurves.sketchLines.addTwoPointRectangle(P(20.7, 67.6), P(39.3, 107.9))
    assert skmcu.profiles.count == 1
    eimcu = root.features.extrudeFeatures.createInput(OC([skmcu.profiles.item(0)]), adsk.fusion.FeatureOperations.CutFeatureOperation)
    eimcu.startExtent = adsk.fusion.OffsetStartDefinition.create(V(0.445))
    eimcu.setDistanceExtent(False, V(0.505))
    eimcu.participantBodies = [bottom]
    root.features.extrudeFeatures.add(eimcu)
    log.append('MCU relief ok (x 20.7-39.3, y 67.6-107.9, z 4.45-9.5)')

    def wedge_sketch(base_z):
        skw = root.sketches.add(root.yZConstructionPlane)
        ya = Y0 - 2; yb = Y1 + 2.5
        zt = base_z + ya*T6; zb = base_z + yb*T6
        pts = [(-zt, ya), (-zb, yb), (-40.0, yb), (-40.0, ya)]
        lw = skw.sketchCurves.sketchLines
        for i in range(4):
            a = pts[i]; b = pts[(i+1)%4]
            lw.addByTwoPoints(adsk.core.Point3D.create(a[0]*MM, a[1]*MM, 0), adsk.core.Point3D.create(b[0]*MM, b[1]*MM, 0))
        assert skw.profiles.count == 1
        return skw
    ext(OC([wedge_sketch(14.5).profiles.item(0)]), adsk.fusion.FeatureOperations.CutFeatureOperation, 0, sym_cm=20.0, participants=[bottom])
    skc0 = root.sketches.add(root.xYConstructionPlane)
    skc0.sketchCurves.sketchLines.addTwoPointRectangle(P(0.1, Y0+0.1), P(W-0.1, Y1-0.1))
    skc0.sketchCurves.sketchLines.addTwoPointRectangle(P(2.5, Y0+2.5), P(W-2.5, Y1-2.5))
    assert skc0.profiles.count == 2
    cp = None
    for i in range(2):
        a = skc0.profiles.item(i).areaProperties().area
        if 5.0 < a < 22.0:
            cp = skc0.profiles.item(i); break
    assert cp is not None
    ext(OC([cp]), adsk.fusion.FeatureOperations.NewBodyFeatureOperation, 20.0, start_mm=13.4)
    collar = [b for b in root.bRepBodies if b.name != bottom.name][0]
    assert collar.boundingBox.maxPoint.z*10 > 31
    ext(OC([wedge_sketch(17.5).profiles.item(0)]), adsk.fusion.FeatureOperations.CutFeatureOperation, 0, sym_cm=20.0, participants=[collar])
    ct = collar.boundingBox.maxPoint.z*10
    log.append('collar top %.2f' % ct)
    combine(bottom, [collar], adsk.fusion.FeatureOperations.JoinFeatureOperation)
    assert len(root.bRepBodies) == 1
    log.append('wedge+collar ok')
    def circ_cuts(points, r_mm, start_mm, depth_mm):
        skc3 = root.sketches.add(root.xYConstructionPlane)
        for (x, y) in points:
            skc3.sketchCurves.sketchCircles.addByCenterRadius(P(x, y), r_mm*MM)
        ext(all_profiles(skc3), adsk.fusion.FeatureOperations.CutFeatureOperation, depth_mm, start_mm=start_mm, participants=[bottom])
    gA = [(x, y) for (x, y) in INS_XY if abs(y - 102.4) < 0.01]
    gB = [(x, y) for (x, y) in INS_XY if abs(y - 89.0) < 0.01]
    plA = 14.5 + 102.4*T6; plB = 14.5 + 89.0*T6
    circ_cuts(gA, 2.1, 0.0, 2.5)
    circ_cuts(gB, 2.1, 0.0, 2.5)
    circ_cuts(gA, 1.2, 2.3, (plA - 4.5) - 2.3 + 0.1)
    circ_cuts(gB, 1.2, 2.3, (plB - 4.5) - 2.3 + 0.1)
    circ_cuts(gA, 1.75, plA - 4.5, 5.2)
    circ_cuts(gB, 1.75, plB - 4.5, 5.2)
    plC = 14.5 + 0.9*T6
    circ_cuts(PROP_XY, 2.1, 0.0, 2.5)
    circ_cuts(PROP_XY, 1.2, 2.3, (plC - 4.5) - 2.3 + 0.1)
    circ_cuts(PROP_XY, 1.75, plC - 4.5, 5.2)
    sku = root.sketches.add(root.xYConstructionPlane)
    sku.sketchCurves.sketchLines.addTwoPointRectangle(P(USB_X[0],107.0), P(USB_X[1],113.5))
    ext(all_profiles(sku), adsk.fusion.FeatureOperations.CutFeatureOperation, 4.0, start_mm=4.5, participants=[bottom])
    skl = root.sketches.add(root.xYConstructionPlane)
    skl.sketchCurves.sketchLines.addTwoPointRectangle(P(-1.0,36.05), P(3.5,44.95))
    ext(all_profiles(skl), adsk.fusion.FeatureOperations.CutFeatureOperation, 4.2, start_mm=6.0, participants=[bottom])
    # reset button pinhole: O2.5 through right wall at y=75, z=7.5
    skph = root.sketches.add(root.yZConstructionPlane)
    skph.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(-0.75, 7.5, 0), 0.125)
    assert skph.profiles.count == 1
    eiph = root.features.extrudeFeatures.createInput(OC([skph.profiles.item(0)]), adsk.fusion.FeatureOperations.CutFeatureOperation)
    eiph.startExtent = adsk.fusion.OffsetStartDefinition.create(V(8.1))
    eiph.setDistanceExtent(False, V(0.45))
    eiph.participantBodies = [bottom]
    root.features.extrudeFeatures.add(eiph)
    log.append('reset pinhole ok (O2.5 right wall y75 z7.5)')
    log.append('bottom done: %s' % [(b.name, round(b.volume,3)) for b in root.bRepBodies])
    skt = root.sketches.add(root.xYConstructionPlane)
    skt.sketchCurves.sketchLines.addTwoPointRectangle(P(PLX0,PLY0), P(PLX1,PLY1))
    ext(all_profiles(skt), adsk.fusion.FeatureOperations.NewBodyFeatureOperation, T)
    plate = None
    for b in root.bRepBodies:
        if b.name != bottom.name:
            zbx = b.boundingBox
            if zbx.maxPoint.z*10 < 3.5:
                plate = b; break
    assert plate is not None
    plate.name = 'Top Plate'
    skc = root.sketches.add(root.xYConstructionPlane)
    for cx in COLS:
        for cy in ROWS:
            skc.sketchCurves.sketchLines.addTwoPointRectangle(P(cx-7, cy-7), P(cx+7, cy+7))
    for (hx, hy) in [(20.0, 102.4/C6), (64.0, 102.4/C6), (4.5, 89/C6), (79.95, 89/C6)]:
        skc.sketchCurves.sketchCircles.addByCenterRadius(P(hx, hy), 1.2*MM)
    for (hx, hy) in [(23.175, 0.9/C6), (42.225, 0.9/C6), (61.275, 0.9/C6)]:
        skc.sketchCurves.sketchCircles.addByCenterRadius(P(hx, hy), 1.2*MM)
    for (ex, ey) in ENC:
        skc.sketchCurves.sketchCircles.addByCenterRadius(P(ex, ey), 3.6*MM)
    skc.sketchCurves.sketchLines.addTwoPointRectangle(P(29.725, 83.83), P(54.725, 101.33))
    sliver_at(skc, PLX0, PLY0, PLX1, PLY1, R)
    assert skc.profiles.count == 30
    ext(all_profiles(skc), adsk.fusion.FeatureOperations.CutFeatureOperation, 3.0, start_mm=-0.5, participants=[plate])
    skch = root.sketches.add(root.xYConstructionPlane)
    skch.sketchCurves.sketchLines.addTwoPointRectangle(P(26.725, 79.83), P(57.725, 83.83))
    skch.sketchCurves.sketchLines.addTwoPointRectangle(P(26.725, 101.33), P(57.725, 105.33))
    assert skch.profiles.count == 2
    ext(all_profiles(skch), adsk.fusion.FeatureOperations.CutFeatureOperation, 1.5, start_mm=-0.5, participants=[plate])
    sks = root.sketches.add(root.xYConstructionPlane)
    sks.sketchCurves.sketchLines.addTwoPointRectangle(P(12.35, 93.33), P(14.95, 95.95))
    sks.sketchCurves.sketchLines.addTwoPointRectangle(P(69.5, 93.33), P(72.1, 95.95))
    assert sks.profiles.count == 2
    ext(all_profiles(sks), adsk.fusion.FeatureOperations.CutFeatureOperation, 3.0, start_mm=-0.5, participants=[plate])
    m = adsk.core.Matrix3D.create()
    m.setWithCoordinateSystem(adsk.core.Point3D.create(0,0,14.5*MM),
        adsk.core.Vector3D.create(1,0,0), adsk.core.Vector3D.create(0,C6,S6), adsk.core.Vector3D.create(0,-S6,C6))
    root.features.moveFeatures.add(root.features.moveFeatures.createInput(OC([plate]), m))
    def bbmm(b):
        z = b.boundingBox
        return [round(v*10,2) for v in (z.minPoint.x,z.minPoint.y,z.minPoint.z,z.maxPoint.x,z.maxPoint.y,z.maxPoint.z)]
    def cylhist(b):
        h = {}
        for f in b.faces:
            g = f.geometry
            if g.objectType == adsk.core.Cylinder.classType():
                k = str(round(g.radius*10,2)); h[k] = h.get(k,0)+1
        return h
    res = {}
    for b in root.bRepBodies:
        res[b.name] = {'vol_cm3': round(b.volume,4), 'bbox': bbmm(b), 'cyl': cylhist(b)}
    assert len(root.bRepBodies) == 2
    bb = res.get('Bottom Plate'); tp = res.get('Top Plate')
    assert bb and tp
    assert abs(bb['bbox'][5] - (17.5 + Y1*T6)) < 0.15, 'bottom zmax %s' % bb['bbox']
    assert abs(bb['bbox'][1] - Y0) < 0.1
    assert 43.5 < bb['vol_cm3'] < 46.5, 'bottom vol %s' % bb['vol_cm3']
    pv = (79.0*(PLY1-PLY0)*2.5 - 4*0.858*2.5 - 16*196*2.5 - 2*math.pi*12.96*2.5 - 25*17.5*2.5 - (31*4+31*4)*1.0 - 7*math.pi*1.44*2.5 - 2*2.6*2.62*2.5)/1000.0
    assert abs(tp['vol_cm3'] - pv) < 0.03, 'top vol %s != %.4f' % (tp['vol_cm3'], pv)
    assert abs(tp['bbox'][5] - (14.5 + PLY1*S6 + 2.5*C6)) < 0.12, 'plate zmax %s' % tp['bbox']
    assert tp['cyl'].get('1.2') == 7 and tp['cyl'].get('3.6') == 2
    assert bb['cyl'].get('1.75', 0) >= 7 and bb['cyl'].get('1.2', 0) >= 7 and bb['cyl'].get('2.1', 0) >= 7
    sliver_check = []
    for fc in bottom.faces:
        g = fc.geometry
        if g.objectType == adsk.core.Plane.classType() and abs(g.normal.x) > 0.95:
            b2 = fc.boundingBox
            x = round(b2.minPoint.x*10,2)
            if 65.3 < x < 66.0 and b2.minPoint.y*10 > 67 and b2.maxPoint.y*10 < 98.8 and b2.maxPoint.z*10 < 4.6:
                sliver_check.append([x, round(fc.area*100,1)])
    log.append('base sliver faces (should be none): %s' % sliver_check)
    assert not sliver_check, 'slivers: %s' % sliver_check
    for p in design.userParameters:
        if p.name == 'plate_t': p.expression = '2.5 mm'
        if p.name == 'case_l': p.expression = '114.0 mm'
    em = design.exportManager
    e1 = em.execute(em.createSTLExportOptions(plate, '/Users/luke/Documents/void16-redux-mod/top-plate.stl'))
    e2 = em.execute(em.createSTLExportOptions(bottom, '/Users/luke/Documents/void16-redux-mod/bottom-plate.stl'))
    e3 = em.execute(em.createSTEPExportOptions('/Users/luke/Documents/void16-redux-mod/void16-redux-mod.step'))
    X0 = 100.0
    skq = root.sketches.add(root.xYConstructionPlane)
    skq.sketchCurves.sketchLines.addTwoPointRectangle(P(6+X0, 77.0), P(78.45+X0, 108.0))
    ext(all_profiles(skq), adsk.fusion.FeatureOperations.NewBodyFeatureOperation, 2.5, 0.0)
    coupon = [b for b in root.bRepBodies if b.name not in ('Bottom Plate', 'Top Plate')][0]
    coupon.name = 'Screen Encoder Slice'
    skh = root.sketches.add(root.xYConstructionPlane)
    skh.sketchCurves.sketchLines.addTwoPointRectangle(P(129.725, 83.83), P(154.725, 101.33))
    for (ex, ey) in ENC:
        skh.sketchCurves.sketchCircles.addByCenterRadius(P(ex+X0, ey), 3.6*MM)
    for (hx, hy) in [(120.0, 102.4/C6), (164.0, 102.4/C6)]:
        skh.sketchCurves.sketchCircles.addByCenterRadius(P(hx, hy), 1.2*MM)
    for cx2 in (113.65, 170.8, 132.7, 151.75):
        skh.sketchCurves.sketchLines.addTwoPointRectangle(P(cx2-7, 77.0), P(cx2+7, 77.78))
    assert skh.profiles.count == 9
    ext(all_profiles(skh), adsk.fusion.FeatureOperations.CutFeatureOperation, 3.0, start_mm=-0.5, participants=[coupon])
    skt2 = root.sketches.add(root.xYConstructionPlane)
    skt2.sketchCurves.sketchLines.addTwoPointRectangle(P(112.35, 93.33), P(114.95, 95.95))
    skt2.sketchCurves.sketchLines.addTwoPointRectangle(P(169.5, 93.33), P(172.1, 95.95))
    ext(all_profiles(skt2), adsk.fusion.FeatureOperations.CutFeatureOperation, 3.0, start_mm=-0.5, participants=[coupon])
    skch2 = root.sketches.add(root.xYConstructionPlane)
    skch2.sketchCurves.sketchLines.addTwoPointRectangle(P(126.725, 79.83), P(157.725, 83.83))
    skch2.sketchCurves.sketchLines.addTwoPointRectangle(P(126.725, 101.33), P(157.725, 105.33))
    assert skch2.profiles.count == 2
    ext(all_profiles(skch2), adsk.fusion.FeatureOperations.CutFeatureOperation, 1.5, start_mm=-0.5, participants=[coupon])
    cv = round(coupon.volume, 3)
    assert 3.1 < cv < 3.95
    e4 = em.execute(em.createSTLExportOptions(coupon, '/Users/luke/Documents/void16-redux-mod/screen-encoder-slice.stl'))
    root.features.removeFeatures.add(coupon)
    assert len(root.bRepBodies) == 2
    vp = app.activeViewport
    def shot(path, eye, target, up):
        c = vp.camera
        c.isSmoothTransition = False
        c.eye = adsk.core.Point3D.create(eye[0]*0.1, eye[1]*0.1, eye[2]*0.1)
        c.target = adsk.core.Point3D.create(target[0]*0.1, target[1]*0.1, target[2]*0.1)
        c.upVector = adsk.core.Vector3D.create(*up)
        vp.camera = c
        vp.fit()
        return vp.saveAsImageFile(path, 1200, 900)
    s1 = shot('/tmp/void16_v21_bottom.png', (42.2, 53.5, -560), (42.2, 53.5, 0), (0,1,0))
    s2 = shot('/tmp/void16_v21_bay.png', (95, 88, -25), (55, 88, 3), (0,0,1))
    RES = json.dumps({'log': log, 'verify': res, 'exports': [bool(e1), bool(e2), bool(e3), bool(e4)], 'coupon': cv, 'shots': [bool(s1), bool(s2)]})
except:
    RES = json.dumps({'error': traceback.format_exc(), 'log': log})
RES
