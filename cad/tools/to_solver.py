"""SIMP topology optimisation for the void16-redux-mod case floor web. v2 (fixed KE)."""
import json, math
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla
from scipy.ndimage import gaussian_filter

W, Y0, Y1 = 84.45, -3.5, 110.5
NELX, NELY = 56, 76
dx = W / NELX; dy = (Y1 - Y0) / NELY
POSTS = [(20.0, 102.4), (64.0, 102.4), (4.5, 89.0), (79.95, 89.0),
         (23.175, 0.9), (42.225, 0.9), (61.275, 0.9)]

def elem_centre(ex, ey):
    return ((ex+0.5)*dx, Y0+(ey+0.5)*dy)

solid = np.zeros((NELY, NELX), dtype=bool)
for ey in range(NELY):
    for ex in range(NELX):
        cx, cy = elem_centre(ex, ey)
        if min(cx, W-cx, cy-Y0, Y1-cy) < 6.0:
            solid[ey, ex] = True; continue
        for (px, py) in POSTS:
            if math.hypot(cx-px, cy-py) < 4.2:
                solid[ey, ex] = True; break
design = ~solid
design_flat = design.ravel()

NNX, NNY = NELX+1, NELY+1
EDOF_MAP = np.zeros((NELY*NELX, 8), dtype=int)
for ey in range(NELY):
    for ex in range(NELX):
        n = ex + NNX*ey
        EDOF_MAP[ey*NELX+ex] = [2*n, 2*n+1, 2*(n+1), 2*(n+1)+1,
                                2*(n+NNX), 2*(n+NNX)+1, 2*(n+NNX+1), 2*(n+NNX+1)+1]

# integrated bilinear quad KE (BL,BR,TL,TR), plane stress, scaled by detJ
E_, nu = 1.0, 0.3
D = E_/(1-nu**2)*np.array([[1,nu,0],[nu,1,0],[0,0,(1-nu)/2]])
gp = [-1/np.sqrt(3), 1/np.sqrt(3)]
nodes = [(-1,-1),(1,-1),(-1,1),(1,1)]
KE = np.zeros((8,8))
for xi in gp:
    for eta in gp:
        dNdx = [0.25*n[0]*(1+eta*n[1]) for n in nodes]
        dNdy = [0.25*n[1]*(1+xi*n[0]) for n in nodes]
        B = np.zeros((3,8))
        for i in range(4):
            B[0,2*i] = dNdx[i]; B[1,2*i+1] = dNdy[i]
            B[2,2*i] = dNdy[i]; B[2,2*i+1] = dNdx[i]
        KE += B.T @ D @ B
KE *= (dx*dy/4.0)

fixed = set()
for ey in range(NNY):
    for ex in [0,1,2,3, NNX-4, NNX-3, NNX-2, NNX-1]:
        n = ex + NNX*ey
        fixed.add(2*n); fixed.add(2*n+1)
free = np.array(sorted(set(range(2*NNX*NNY)) - fixed))

F = np.zeros(2*NNX*NNY)
for (px, py) in POSTS:
    ex = int(px/dx); ey = int((py-Y0)/dy)
    n = ex + NNX*ey
    F[2*n+1] -= 1.0

VOLFRAC, PENAL, RMIN_E, MOVE = 0.32, 3.0, 5.0/dx, 0.1
nel = NELX*NELY
x = np.full(nel, VOLFRAC); x[solid.ravel()] = 1.0
rad = int(math.ceil(RMIN_E))
rows, cols, vals = [], [], []
for ey in range(NELY):
    for ex in range(NELX):
        a = ey*NELX+ex
        for sy in range(max(0,ey-rad), min(NELY,ey+rad+1)):
            for sx in range(max(0,ex-rad), min(NELX,ex+rad+1)):
                b = sy*NELX+sx
                w = max(0.0, RMIN_E - math.hypot(sx-ex, sy-ey))
                if w > 0: rows.append(a); cols.append(b); vals.append(w)
H = sp.csr_matrix((vals,(rows,cols)), shape=(nel,nel))
Hs = np.asarray(H.sum(axis=1)).ravel()

edof_rows = EDOF_MAP  # (nel,8)

def solve_state(xe_flat):
    kvals = np.tile(KE.flatten(), nel)
    rowsm = np.repeat(edof_rows, 8, axis=1).ravel()
    colsm = np.tile(edof_rows, (1, 8)).ravel()
    kscale = np.repeat(xe_flat, 64)
    K = sp.csr_matrix((kvals*kscale, (rowsm, colsm)), shape=(2*NNX*NNY,)*2)
    Kff = K[free][:, free].tocsc()
    Uf = spla.spsolve(Kff, F[free])
    U = np.zeros(2*NNX*NNY); U[free] = Uf
    return U

history = []
for it in range(150):
    xf = (H @ x) / Hs
    xphys = np.maximum(1e-3, xf); xphys[solid.ravel()] = 1.0
    xe = xphys**PENAL
    U = solve_state(xe)
    ue_all = U[EDOF_MAP]
    energies = np.einsum('ij,jk,ik->i', ue_all, KE, ue_all)
    c = float(np.sum(xe * energies))
    if not np.isfinite(c) or c <= 0:
        print("DIVERGED at", it); break
    dc = -PENAL * (xphys**(PENAL-1)) * energies
    dc = H @ (dc / Hs * xphys)
    L1, L2 = 0.0, 1e5
    while (L2-L1)/(L1+L2+1e-12) > 1e-4:
        Lmid = 0.5*(L2+L1)
        cand = x * np.sqrt(np.maximum(-dc, 1e-16)/(Lmid+1e-16))
        xn = np.clip(cand, np.maximum(0.001, x-MOVE), np.minimum(1.0, x+MOVE))
        xn[~design_flat] = 1.0
        if xn[design_flat].sum() - VOLFRAC*design_flat.sum() > 0: L1 = Lmid
        else: L2 = Lmid
    change = float(np.abs(xn - x).max())
    x = xn
    history.append(c)
    if it % 10 == 0 or it == 149:
        print(f"it {it:3d} c {c:10.5f} vol {x[design_flat].mean():.3f} chg {change:.3f}")
    if it > 20 and change < 0.005:
        print("converged at", it); break

# ---------------- extraction ----------------
field = xphys.reshape(NELY, NELX).copy()
field[~design] = 1.0
field[solid] = 1.0
for _ in range(3):
    field = gaussian_filter(field, sigma=1.6)
    field[solid] = 1.0
fmin, fmax = field.min(), field.max()
field = np.clip((field-fmin)/(fmax-fmin+1e-12), 0, 1)

def find_contours_basic(f, lvl):
    segs = []
    H_, W_ = f.shape
    for ey in range(H_-1):
        for ex in range(W_-1):
            a, b, c, d = f[ey,ex], f[ey,ex+1], f[ey+1,ex+1], f[ey+1,ex]
            pts = []
            for (p, q, x0, y0, x1, y1) in [
                (a,b, ex,ey, ex+1,ey), (b,c, ex+1,ey, ex+1,ey+1),
                (c,d, ex+1,ey+1, ex,ey+1), (d,a, ex,ey+1, ex,ey)]:
                if (p-lvl)*(q-lvl) < 0:
                    t = (lvl-p)/(q-p)
                    pts.append((x0+(x1-x0)*t, y0+(y1-y0)*t))
            if len(pts) == 2:
                segs.append((pts[0], pts[1]))
            elif len(pts) == 4:
                segs.append((pts[0], pts[1])); segs.append((pts[2], pts[3]))
    adj = {}
    for i,(p,q) in enumerate(segs):
        adj.setdefault((round(p[0],3),round(p[1],3)), []).append((i,0))
        adj.setdefault((round(q[0],3),round(q[1],3)), []).append((i,1))
    used = [False]*len(segs); loops = []
    for i in range(len(segs)):
        if used[i]: continue
        loop = [segs[i][0]]; used[i] = True; cur = segs[i][1]
        for _ in range(len(segs)+2):
            key = (round(cur[0],3), round(cur[1],3))
            nxt = None
            for (j, side) in adj.get(key, []):
                if not used[j]:
                    nxt = (segs[j][0], segs[j][1], j); break
            if nxt is None: break
            used[nxt[2]] = True
            loop.append(nxt[0]); cur = nxt[1]
        if len(loop) >= 8:
            loops.append(loop)
    return loops

contours = find_contours_basic(field, 0.5)
def to_mm(pt):
    cx, ry = pt
    return [round(cx*dx, 3), round(Y0+ry*dy, 3)]

polys = []
for cnt in contours:
    poly = [to_mm(pt) for pt in cnt]
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    if min(xs) < 1.0 or max(xs) > W-1.0 or min(ys) < Y0+1.0 or max(ys) > Y1-1.0:
        continue
    per = sum(math.hypot(poly[i][0]-poly[(i+1)%len(poly)][0],
                         poly[i][1]-poly[(i+1)%len(poly)][1]) for i in range(len(poly)))
    if per < 30.0:
        continue
    polys.append(poly)

for _ in range(2):
    for pi, poly in enumerate(polys):
        n = len(poly); newp = []
        for i in range(n):
            ax, ay = poly[(i-1)%n]; bx, by = poly[(i+1)%n]; cx2, cy2 = poly[i]
            newp.append([0.25*ax+0.5*cx2+0.25*bx, 0.25*ay+0.5*cy2+0.25*by])
        polys[pi] = newp

area_void = 0.0
for poly in polys:
    a = 0.0
    for i in range(len(poly)):
        a += poly[i][0]*poly[(i+1)%len(poly)][1] - poly[(i+1)%len(poly)][0]*poly[i][1]
    area_void += abs(a/2)

meta = {'iterations': len(history), 'c_first': round(history[0],4), 'c_last': round(history[-1],4),
        'n_voids': len(polys), 'void_area_mm2': round(area_void,1),
        'design_area_mm2': round(design.sum()*dx*dy,1),
        'solid_frac_design': round(1-area_void/(design.sum()*dx*dy),3)}
print(json.dumps(meta, indent=1))
with open('/tmp/to_voids.json','w') as f:
    json.dump({'polygons': polys, 'meta': meta}, f)
print('vertices total:', sum(len(p) for p in polys))
