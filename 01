import streamlit as st
import pandas as pd
import trimesh
import numpy as np
import io
import hashlib
import json
from scipy.spatial import cKDTree

# --- 1. PreForm 專業 UI 配置 ---
st.set_page_config(page_title="SOLIDWIZARD | PreForm AI", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #f8fafc; border-right: 1px solid #e2e8f0; }
    .stButton>button { width: 100%; border-radius: 4px; font-weight: 600; background-color: #ffffff;
        border: 1px solid #cbd5e1; height: 36px; font-size: 12px; transition: all .15s; }
    .stButton>button:hover { background-color: #0081FF; color: white; border-color: #0081FF; }
    /* 主要動作按鈕 */
    div[data-testid="stButton"]:has(button[kind="primary"]) button {
        background:#0081FF; color:#fff; border-color:#0059b3; }
    .price-container { background-color: #ffffff; padding: 20px; border-radius: 8px;
        border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    .price-result { color: #1e293b; font-size: 32px; font-weight: 800;
        border-bottom: 2px solid #0081FF; display: inline-block; margin-bottom: 10px; }
    .data-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }
    .data-item { border-left: 3px solid #cbd5e1; padding-left: 10px; }
    .data-label { color: #64748b; font-size: 10px; font-weight: bold; text-transform: uppercase; }
    .data-value { color: #0f172a; font-size: 14px; font-weight: 700; }
    .cost-breakdown { background: #f8fafc; border-radius: 6px; padding: 12px 16px;
        margin-top: 12px; border: 1px solid #e2e8f0; }
    .cost-row { display: flex; justify-content: space-between; font-size: 12px; color: #475569; padding: 3px 0; }
    .cost-row.total { font-weight: 700; color: #0f172a; border-top: 1px solid #cbd5e1;
        margin-top: 6px; padding-top: 6px; font-size: 13px; }
    .priority-note { background: #eff6ff; color: #1d4ed8; border-left: 3px solid #3b82f6;
        padding: 8px 12px; font-size: 12px; border-radius: 0 4px 4px 0; margin-bottom: 8px; }
    /* 工具面板區塊標題 */
    h4 { font-size: 13px !important; margin: 4px 0 6px !important; color: #1e293b !important; }
    /* 方向鍵中間欄空白 */
    div[data-testid="column"]:nth-child(2) .stButton button { background: transparent !important;
        border-color: transparent !important; cursor: default !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心狀態初始化 ---
for k, v in [('offset', [0.0, 0.0]), ('mesh', None), ('mesh_hash', ""), ('thin_faces', None)]:
    if k not in st.session_state:
        st.session_state[k] = v

# --- 3. 材料與設備規格 ---
@st.cache_data
def load_materials():
    data = {
        "材料名稱": [
            "Clear Resin V4", "Grey Resin V4", "White Resin V4", "Black Resin V4",
            "Draft Resin V2", "Model Resin V3", "Tough 2000 Resin", "Tough 1500 Resin",
            "Durable Resin", "Grey Pro Resin", "Rigid 10K Resin", "Rigid 4000 Resin",
            "Flexible 80A Resin", "Elastic 50A Resin", "High Temp Resin", "Flame Retardant Resin",
            "ESD Resin", "BioMed Clear Resin", "BioMed Amber Resin", "BioMed White Resin",
            "BioMed Black Resin", "Custom Tray Resin", "IBT Resin", "Precision Model Resin",
            "Castable Wax 40 Resin", "Castable Wax Resin", "Silicone 40A Resin", "Alumina 4N Resin"
        ],
        "單價": [6900, 6900, 6900, 6900, 6900, 6900, 8500, 8500, 8500, 8500, 12000, 8500,
                 9500, 9500, 11000, 12000, 12000, 13500, 13500, 13500, 13500, 13500, 13500,
                 8500, 15000, 15000, 18000, 25000]
    }
    df = pd.DataFrame(data)
    df['每mm3成本'] = df['單價'] / 1000000
    return df

df_m = load_materials()

# 尺寸單位：mm
# Three.js 座標系：X=寬(W), Y=高(H，向上), Z=深(D)
# 框線：底面在 Y=0，中心在 XZ 原點
# 所以框線範圍：X ∈ [-W/2, W/2], Z ∈ [-D/2, D/2], Y ∈ [0, H]
PRINTERS = {
    "Form 4":  {"w": 200.0, "d": 125.0, "h": 210.0, "layer_time_sec": 5.0},
    "Form 4L": {"w": 353.0, "d": 196.0, "h": 350.0, "layer_time_sec": 6.0},
}


# --- 4. 產生給 Three.js 的幾何 JSON ---
# 座標轉換規則（trimesh → Three.js）:
#   Three.js X = trimesh X
#   Three.js Y = trimesh Z  (高度)
#   Three.js Z = trimesh Y  (深度，注意正負)
# 零件底部貼齊 Three.js Y=0（框線底部），XZ 置中在框線中心
def mesh_to_threejs_json(mesh, printer_box, qty, off_x, off_y, thin_faces=None):
    W = printer_box['w']
    D = printer_box['d']
    H = printer_box['h']

    cols = max(1, int(np.ceil(np.sqrt(qty))))
    rows = max(1, int(np.ceil(qty / cols)))

    # 間距用模型最大水平邊長 * 1.15
    sx = mesh.extents[0] * 1.15   # trimesh X 方向
    sy = mesh.extents[1] * 1.15   # trimesh Y 方向

    all_positions = []
    all_colors = []
    thin_set = set(thin_faces) if thin_faces else set()

    # 計算所有 instance 的 trimesh 座標，底部貼齊 Z=0，XY 陣列置中
    for i in range(qty):
        m = mesh.copy()
        r, c = divmod(i, cols)

        # 讓陣列在 trimesh XY 平面置中
        tx = (c - (cols - 1) / 2.0) * sx + off_x
        ty = (r - (rows - 1) / 2.0) * sy + off_y
        tz = -m.bounds[0][2]   # 底部貼齊 trimesh Z=0

        m.apply_translation([tx, ty, tz])
        verts = m.vertices
        faces = m.faces

        for fi, face in enumerate(faces):
            for vi in face:
                v = verts[vi]
                # trimesh(X,Y,Z) → Three.js(X, Z, -Y) 讓底部在 Three.js Y=0
                all_positions.extend([float(v[0]), float(v[2]), float(-v[1])])
                if fi in thin_set:
                    all_colors.extend([1.0, 0.18, 0.18])
                else:
                    all_colors.extend([0.0, 0.506, 1.0])

    # 邊界檢測（trimesh 空間，框線底面 trimesh Z=0, 頂面 Z=H, XY ±W/2, ±D/2）
    is_over = False
    for i in range(qty):
        m = mesh.copy()
        r, c = divmod(i, cols)
        tx = (c - (cols - 1) / 2.0) * sx + off_x
        ty = (r - (rows - 1) / 2.0) * sy + off_y
        tz = -m.bounds[0][2]
        m.apply_translation([tx, ty, tz])
        b = m.bounds
        if (b[0][0] < -W/2 or b[1][0] > W/2 or
                b[0][1] < -D/2 or b[1][1] > D/2 or
                b[1][2] > H):
            is_over = True
            break

    return {
        "positions": all_positions,
        "colors": all_colors,
        "printer": {"w": W, "d": D, "h": H},
        "is_over": is_over,
        "thin_count": len(thin_set)
    }


# --- 5. PreForm 風格 Three.js 渲染器 ---
def preform_viewer_html(geo_json: dict) -> str:
    data_str = json.dumps(geo_json)
    is_over = geo_json["is_over"]
    thin_count = geo_json.get("thin_count", 0)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#1a2235; font-family:'Segoe UI',system-ui,sans-serif; overflow:hidden; }}
#wrap {{ position:relative; width:100%; height:580px; }}
canvas {{ display:block; width:100%!important; height:100%!important; touch-action:none; }}

/* 頂部視角工具列 */
#viewbar {{
  position:absolute; top:8px; left:50%; transform:translateX(-50%);
  display:flex; gap:3px; background:rgba(10,18,35,0.92);
  border:1px solid #2d3f5a; border-radius:6px; padding:4px 6px;
  backdrop-filter:blur(6px); z-index:10; white-space:nowrap;
  max-width:calc(100% - 16px); overflow-x:auto;
}}
.vbtn {{
  background:transparent; border:1px solid transparent;
  color:#7a9cc0; font-size:clamp(10px,2.5vw,12px); font-weight:600;
  padding:4px 8px; border-radius:4px; cursor:pointer; transition:all .15s;
  min-height:28px; touch-action:manipulation;
}}
.vbtn:hover  {{ background:#1e3a6e; color:#fff; border-color:#3b82f6; }}
.vbtn.active {{ background:#0081FF; color:#fff; border-color:#0081FF; }}
.sep {{ width:1px; background:#2d3f5a; margin:2px 2px; flex-shrink:0; }}

/* 左上資訊面板 */
#info {{
  position:absolute; top:8px; left:8px;
  background:rgba(10,18,35,0.88); border:1px solid #1e3a5f;
  border-radius:6px; padding:7px 10px; font-size:clamp(10px,2.5vw,12px);
  color:#7dd3fc; line-height:1.8; pointer-events:none;
  backdrop-filter:blur(4px);
}}
#info .lbl {{
  color:#3d5a7a; font-size:clamp(9px,2vw,10px);
  text-transform:uppercase; letter-spacing:.06em;
}}

/* 右下操作提示（手機隱藏以節省空間）*/
#hint {{
  position:absolute; bottom:8px; right:10px;
  font-size:clamp(9px,2vw,11px); color:#3d5a7a; line-height:1.8;
  text-align:right; pointer-events:none;
}}
#hint b {{ color:#6b8fb5; }}
@media (max-width: 500px) {{ #hint {{ display:none; }} }}

/* 超出範圍警示 */
#over-badge {{
  display:none; position:absolute; bottom:8px; left:50%; transform:translateX(-50%);
  background:rgba(220,38,38,0.15); border:1px solid #f87171; border-radius:5px;
  color:#fca5a5; font-size:clamp(10px,2.5vw,12px); font-weight:700;
  padding:5px 14px; white-space:nowrap;
}}
#thin-badge {{
  display:none; position:absolute; bottom:40px; left:50%; transform:translateX(-50%);
  background:rgba(234,88,12,0.15); border:1px solid #fb923c; border-radius:5px;
  color:#fdba74; font-size:clamp(10px,2.5vw,12px); font-weight:600;
  padding:4px 12px; white-space:nowrap;
}}
</style>
</head>
<body>
<div id="wrap">
  <canvas id="c"></canvas>

  <div id="viewbar">
    <button class="vbtn" onclick="resetView()" title="重置 (F)">⌂</button>
    <div class="sep"></div>
    <button class="vbtn" id="b-iso"   onclick="setView('iso')">等角</button>
    <button class="vbtn" id="b-top"   onclick="setView('top')">俯</button>
    <button class="vbtn" id="b-front" onclick="setView('front')">前</button>
    <button class="vbtn" id="b-right" onclick="setView('right')">右</button>
    <div class="sep"></div>
    <button class="vbtn" id="b-wire"  onclick="toggleWire()">線框</button>
    <button class="vbtn" onclick="fitAll()">Fit</button>
  </div>

  <div id="info">
    <div class="lbl">Printer</div>
    <div id="i-printer">—</div>
    <div class="lbl" style="margin-top:3px">Volume (model)</div>
    <div id="i-vol">—</div>
  </div>

  <div id="over-badge">⚠ 零件超出列印範圍</div>
  <div id="thin-badge">🔴 薄壁標記顯示中</div>

  <div id="hint">
    <b>右鍵拖曳</b> 旋轉<br>
    <b>Shift＋右鍵</b> 平移<br>
    <b>滾輪</b> 縮放<br>
    <b>F</b> 重置視角
  </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script>
// ── 注入資料 ──────────────────────────────────────
const GEO = {data_str};
const W = GEO.printer.w;   // mm, Three.js X 方向
const D = GEO.printer.d;   // mm, Three.js Z 方向
const H = GEO.printer.h;   // mm, Three.js Y 方向（向上）

// ── Renderer ──────────────────────────────────────
const canvas = document.getElementById('c');
const renderer = new THREE.WebGLRenderer({{ canvas, antialias:true }});
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
scene.background = new THREE.Color(0x111827);

// ── Camera ────────────────────────────────────────
const camera = new THREE.PerspectiveCamera(32, 1, 0.5, 100000);

// ── 燈光 ──────────────────────────────────────────
scene.add(new THREE.AmbientLight(0xffffff, 0.50));
const sun = new THREE.DirectionalLight(0xffffff, 0.85);
sun.position.set(W, H * 2.5, D);
sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024);
scene.add(sun);
const fill = new THREE.DirectionalLight(0x9ab8e0, 0.40);
fill.position.set(-W * 0.8, H * 0.5, -D * 0.8);
scene.add(fill);
const bottom = new THREE.DirectionalLight(0x3a5070, 0.20);
bottom.position.set(0, -H, 0);
scene.add(bottom);

// ── 框線（Three.js 座標）────────────────────────
//    底面在 Y=0, 頂面在 Y=H
//    XZ 以原點置中：X ∈ [-W/2, W/2], Z ∈ [-D/2, D/2]
const hw = W / 2, hd = D / 2;

const isOver = GEO.is_over;
const boxHex = isOver ? 0xe11d48 : 0x4b6a8a;
const boxMat = new THREE.LineBasicMaterial({{ color: boxHex }});

// 12 條邊
const BV = [
  new THREE.Vector3(-hw, 0,  -hd), new THREE.Vector3( hw, 0,  -hd),
  new THREE.Vector3( hw, 0,   hd), new THREE.Vector3(-hw, 0,   hd),
  new THREE.Vector3(-hw, H,  -hd), new THREE.Vector3( hw, H,  -hd),
  new THREE.Vector3( hw, H,   hd), new THREE.Vector3(-hw, H,   hd),
];
[[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]]
  .forEach(([a,b]) => {{
    const g = new THREE.BufferGeometry().setFromPoints([BV[a], BV[b]]);
    scene.add(new THREE.Line(g, boxMat));
  }});

// 側面半透明填色（視覺輔助）
const sideMat = new THREE.MeshBasicMaterial({{
  color: boxHex, transparent:true, opacity: isOver ? 0.08 : 0.04,
  side: THREE.DoubleSide, depthWrite:false
}});
[[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]].forEach(([a,b,c,d]) => {{
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(
    new Float32Array([...BV[a].toArray(),...BV[b].toArray(),
                      ...BV[c].toArray(),...BV[d].toArray()]), 3));
  g.setIndex([0,1,2, 0,2,3]);
  scene.add(new THREE.Mesh(g, sideMat));
}});

// ── 底部格子（框線底面範圍內）────────────────────
// 格子線只在 X ∈ [-W/2,W/2], Z ∈ [-D/2,D/2], Y=0
const gridMat = new THREE.LineBasicMaterial({{ color:0x1e3a55, transparent:true, opacity:0.9 }});
const gridMajMat = new THREE.LineBasicMaterial({{ color:0x2a5a80, transparent:true, opacity:0.7 }});

function makeGrid() {{
  // 格線間距：讓格子數約 10~14 格
  const rawStep = Math.max(W, D) / 12;
  // 取整到 5mm 的倍數
  const step = Math.ceil(rawStep / 5) * 5;

  // X 方向線（沿 Z 延伸）
  for(let x = -hw; x <= hw + 0.01; x += step) {{
    const xc = Math.round(x / step) * step;
    if(xc < -hw || xc > hw) continue;
    const isMaj = Math.abs(xc % (step * 2)) < 0.01;
    const g = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(xc, 0, -hd),
      new THREE.Vector3(xc, 0,  hd)
    ]);
    scene.add(new THREE.Line(g, isMaj ? gridMajMat : gridMat));
  }}
  // Z 方向線（沿 X 延伸）
  for(let z = -hd; z <= hd + 0.01; z += step) {{
    const zc = Math.round(z / step) * step;
    if(zc < -hd || zc > hd) continue;
    const isMaj = Math.abs(zc % (step * 2)) < 0.01;
    const g = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(-hw, 0, zc),
      new THREE.Vector3( hw, 0, zc)
    ]);
    scene.add(new THREE.Line(g, isMaj ? gridMajMat : gridMat));
  }}

  // 底部填色平面
  const floorGeo = new THREE.PlaneGeometry(W, D);
  const floorMat = new THREE.MeshStandardMaterial({{
    color: 0x0a1628, transparent:true, opacity:0.70,
    roughness:1, metalness:0, depthWrite:false
  }});
  const floorMesh = new THREE.Mesh(floorGeo, floorMat);
  floorMesh.rotation.x = -Math.PI / 2;   // 水平
  floorMesh.position.y = 0.01;           // 略高於 Y=0 避免 z-fighting
  floorMesh.receiveShadow = true;
  scene.add(floorMesh);
}}
makeGrid();

// ── 零件 Mesh ─────────────────────────────────────
let partMesh = null, wireMesh = null;
let wireOn = false;

function buildPart() {{
  if(partMesh)  scene.remove(partMesh);
  if(wireMesh)  scene.remove(wireMesh);
  if(!GEO.positions || GEO.positions.length === 0) return;

  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(GEO.positions), 3));
  geo.setAttribute('color',    new THREE.BufferAttribute(new Float32Array(GEO.colors),    3));
  geo.computeVertexNormals();

  partMesh = new THREE.Mesh(geo, new THREE.MeshPhongMaterial({{
    vertexColors: true, transparent:true, opacity:0.90,
    shininess:55, specular:new THREE.Color(0x1a3a6a), side:THREE.DoubleSide
  }}));
  partMesh.castShadow = true;
  scene.add(partMesh);

  wireMesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({{
    color:0x7dd3fc, wireframe:true, transparent:true, opacity:0.10
  }}));
  wireMesh.visible = wireOn;
  scene.add(wireMesh);
}}
buildPart();

function toggleWire() {{
  wireOn = !wireOn;
  if(wireMesh) wireMesh.visible = wireOn;
  document.getElementById('b-wire').classList.toggle('active', wireOn);
}}

// ── UI 標示 ────────────────────────────────────────
if(isOver) document.getElementById('over-badge').style.display = 'block';
if(GEO.thin_count > 0) document.getElementById('thin-badge').style.display = 'block';
document.getElementById('i-printer').textContent =
  W + ' × ' + D + ' × ' + H + ' mm';
// 用頂點數反推大概體積（僅用於顯示）
document.getElementById('i-vol').textContent =
  (GEO.positions.length / 9).toLocaleString() + ' faces';

// ── 視角控制 ──────────────────────────────────────
// 使用球座標 Spherical (r, phi, theta) 繞 TARGET 點
// TARGET = 框線中心 (0, H/2, 0)
const TARGET = new THREE.Vector3(0, H / 2, 0);
const sph = new THREE.Spherical();
let panOff = new THREE.Vector3();

function updateCam() {{
  const p = new THREE.Vector3().setFromSpherical(sph);
  p.add(TARGET).add(panOff);
  camera.position.copy(p);
  camera.lookAt(TARGET.clone().add(panOff));
}}

function calcR() {{
  // 讓框線完整出現在視野內的距離
  const diag = Math.sqrt(W*W + D*D + H*H);
  const fovRad = camera.fov * Math.PI / 180;
  return (diag / 2) / Math.sin(fovRad / 2) * 1.45;
}}

// 標準等角視角：從右前上方看，phi≈54.7°, theta≈-45°（真正等角投影角度）
function resetView() {{
  sph.set(calcR(), Math.PI / 2 - Math.atan(1 / Math.sqrt(2)), -Math.PI / 4);
  panOff.set(0, 0, 0);
  setActive('b-iso');
  updateCam();
}}

function setView(name) {{
  const R = calcR();
  panOff.set(0, 0, 0);
  switch(name) {{
    case 'iso':
      sph.set(R, Math.PI/2 - Math.atan(1/Math.sqrt(2)), -Math.PI/4); break;
    case 'top':
      sph.set(R, 0.001, 0); break;
    case 'front':
      sph.set(R, Math.PI/2, 0); break;
    case 'right':
      sph.set(R, Math.PI/2, -Math.PI/2); break;
  }}
  setActive('b-'+name);
  updateCam();
}}

function fitAll() {{
  sph.radius = calcR();
  panOff.set(0, 0, 0);
  updateCam();
}}

function setActive(id) {{
  document.querySelectorAll('.vbtn[id^=b-]').forEach(b => b.classList.remove('active'));
  const el = document.getElementById(id);
  if(el) el.classList.add('active');
}}

// 初始視角
resetView();

// ── 滑鼠操作 ──────────────────────────────────────
let dragging = false, shiftDown = false, lastX = 0, lastY = 0;

canvas.addEventListener('contextmenu', e => e.preventDefault());

canvas.addEventListener('mousedown', e => {{
  if(e.button === 2) {{
    dragging = true;
    shiftDown = e.shiftKey;
    lastX = e.clientX; lastY = e.clientY;
  }}
}});
window.addEventListener('mouseup', () => {{ dragging = false; }});

window.addEventListener('mousemove', e => {{
  if(!dragging) return;
  const dx = e.clientX - lastX;
  const dy = e.clientY - lastY;
  lastX = e.clientX; lastY = e.clientY;

  if(shiftDown || e.shiftKey) {{
    // Pan：沿相機的 right / up 方向移動 TARGET
    const speed = sph.radius * 0.0012;
    const right = new THREE.Vector3();
    right.crossVectors(
      camera.getWorldDirection(new THREE.Vector3()), camera.up
    ).normalize();
    panOff.addScaledVector(right, -dx * speed);
    panOff.addScaledVector(camera.up, dy * speed);
  }} else {{
    // Orbit：右鍵拖曳旋轉
    sph.theta += dx * 0.007;
    sph.phi   -= dy * 0.007;
    sph.phi = Math.max(0.02, Math.min(Math.PI - 0.02, sph.phi));
  }}
  updateCam();
}});

// 滾輪縮放
canvas.addEventListener('wheel', e => {{
  e.preventDefault();
  sph.radius *= e.deltaY > 0 ? 1.10 : 0.91;
  sph.radius = Math.max(10, Math.min(sph.radius, 200000));
  updateCam();
}}, {{ passive:false }});

// ── 觸控操作（手機）──────────────────────────────
let touches = {{}};
let lastPinchDist = 0;
let lastTouchX = 0, lastTouchY = 0;
let lastMidX = 0, lastMidY = 0;

canvas.addEventListener('touchstart', e => {{
  e.preventDefault();
  for(const t of e.changedTouches) touches[t.identifier] = t;
  const pts = Object.values(touches);
  if(pts.length === 1) {{
    lastTouchX = pts[0].clientX;
    lastTouchY = pts[0].clientY;
  }} else if(pts.length === 2) {{
    lastPinchDist = Math.hypot(pts[1].clientX - pts[0].clientX,
                               pts[1].clientY - pts[0].clientY);
    lastMidX = (pts[0].clientX + pts[1].clientX) / 2;
    lastMidY = (pts[0].clientY + pts[1].clientY) / 2;
  }}
}}, {{ passive:false }});

canvas.addEventListener('touchmove', e => {{
  e.preventDefault();
  for(const t of e.changedTouches) touches[t.identifier] = t;
  const pts = Object.values(touches);

  if(pts.length === 1) {{
    // 單指：旋轉（等同右鍵拖曳）
    const dx = pts[0].clientX - lastTouchX;
    const dy = pts[0].clientY - lastTouchY;
    lastTouchX = pts[0].clientX;
    lastTouchY = pts[0].clientY;
    sph.theta += dx * 0.007;
    sph.phi   -= dy * 0.007;
    sph.phi = Math.max(0.02, Math.min(Math.PI - 0.02, sph.phi));
    updateCam();
  }} else if(pts.length === 2) {{
    // 雙指縮放
    const dist = Math.hypot(pts[1].clientX - pts[0].clientX,
                            pts[1].clientY - pts[0].clientY);
    if(lastPinchDist > 0) {{
      const factor = lastPinchDist / dist;
      sph.radius = Math.max(10, Math.min(sph.radius * factor, 200000));
    }}
    lastPinchDist = dist;

    // 雙指平移（中心點移動）
    const midX = (pts[0].clientX + pts[1].clientX) / 2;
    const midY = (pts[0].clientY + pts[1].clientY) / 2;
    const dx = midX - lastMidX;
    const dy = midY - lastMidY;
    lastMidX = midX; lastMidY = midY;
    const speed = sph.radius * 0.0012;
    const right = new THREE.Vector3();
    right.crossVectors(
      camera.getWorldDirection(new THREE.Vector3()), camera.up
    ).normalize();
    panOff.addScaledVector(right, -dx * speed);
    panOff.addScaledVector(camera.up, dy * speed);
    updateCam();
  }}
}}, {{ passive:false }});

canvas.addEventListener('touchend', e => {{
  for(const t of e.changedTouches) delete touches[t.identifier];
  lastPinchDist = 0;
}}, {{ passive:false }});

// 鍵盤快捷鍵
window.addEventListener('keydown', e => {{
  const k = e.key.toLowerCase();
  if(k === 'f') resetView();
  if(k === 't') setView('top');
  if(k === 'r') setView('right');
  if(k === 'i') setView('iso');
}});

// ── Resize ────────────────────────────────────────
function onResize() {{
  const w = canvas.parentElement.clientWidth;
  const h = canvas.parentElement.clientHeight;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}}
window.addEventListener('resize', onResize);
onResize();

// ── Render Loop ───────────────────────────────────
(function loop() {{
  requestAnimationFrame(loop);
  renderer.render(scene, camera);
}})();
</script>
</body>
</html>"""


# ════════════════════════════════════════════════
#  側邊欄
# ════════════════════════════════════════════════
with st.sidebar:
    st.image("https://formlabs.com/favicon.ico", width=20)
    st.title("PreForm 模擬報價")

    st.markdown(
        '<div class="priority-note">📌 上傳 STL 優先；未上傳時使用手動體積估算。</div>',
        unsafe_allow_html=True
    )

    with st.container():
        st.subheader("⌨️ 手動估價")
        m_unit = st.radio("單位", ["mm³", "cm³"], horizontal=True)
        manual_v = st.number_input("體積值", min_value=0.0, step=100.0)

    with st.container():
        st.subheader("📂 上傳 STL 檔案")
        up_file = st.file_uploader("STL 檔案（優先使用）", type=["stl"])

    st.divider()
    m_choice = st.selectbox("Formlabs 材料選擇", df_m["材料名稱"].tolist())
    p_choice = st.selectbox("列印機型範圍", list(PRINTERS.keys()))
    qty = st.number_input("數量", min_value=1, value=1)
    markup = st.number_input("報價加成倍率", min_value=1.0, value=2.0)

    st.divider()
    st.subheader("⚙️ 進階設定")
    support_ratio = st.slider("支撐結構體積係數 (%)", 0, 50, 20, 5,
                               help="SLA 通常需要額外 15~30% 支撐材料。")
    layer_thickness = st.selectbox("層厚 (mm)", [0.05, 0.1, 0.2], index=1)
    min_t_val = st.slider("薄度偵測閾值 (mm)", 0.0, 5.0, 0.5, 0.5)
    handling_fee = st.number_input("基本處理費 / 件 (NT$)", min_value=0, value=200, step=50,
                                    help="含清洗、後固化等後處理成本。")


# ════════════════════════════════════════════════
#  主畫面
# ════════════════════════════════════════════════
u_cost = df_m.loc[df_m["材料名稱"] == m_choice, "每mm3成本"].values[0]
printer_spec = PRINTERS[p_choice]

# MD5 hash 判斷檔案是否真的改變
if up_file:
    file_bytes = up_file.read()
    file_hash = hashlib.md5(file_bytes).hexdigest()
    if st.session_state.mesh_hash != file_hash:
        load_error = None
        raw = None
        try:
            # 嘗試載入（同時支援 binary 與 ASCII STL）
            loaded = trimesh.load(io.BytesIO(file_bytes), file_type='stl')

            # trimesh 有時回傳 Scene（多物件）而非單一 Mesh
            if isinstance(loaded, trimesh.Scene):
                meshes = [g for g in loaded.geometry.values()
                          if isinstance(g, trimesh.Trimesh) and len(g.faces) > 0]
                if not meshes:
                    raise ValueError("STL 內沒有有效的 mesh 物件")
                raw = trimesh.util.concatenate(meshes)
            elif isinstance(loaded, trimesh.Trimesh):
                raw = loaded
            else:
                raise ValueError(f"不支援的物件類型：{type(loaded)}")

            # 檢查基本有效性
            if len(raw.faces) == 0:
                raise ValueError("模型沒有任何面（可能是空的 STL）")
            if np.any(np.isnan(raw.vertices)) or np.any(np.isinf(raw.vertices)):
                raise ValueError("模型頂點含有 NaN 或 Inf，檔案可能損毀")

            # 自動修復：修正法線方向、填補破面
            raw.fix_normals()
            trimesh.repair.fill_holes(raw)
            trimesh.repair.fix_winding(raw)

            # 若體積仍為負（法線全部反轉），強制翻轉
            try:
                if raw.volume < 0:
                    raw.invert()
            except Exception:
                pass  # 非 watertight mesh 的 volume 可能拋出例外，忽略

            # 尺寸保護：避免 extents=0 導致除以零
            if np.any(raw.extents < 1e-6):
                raise ValueError(
                    f"模型尺寸過小或為零（extents: {raw.extents}），"
                    "請確認單位是否正確（應為 mm）"
                )

            # 置中：底部貼齊 Z=0，XY 置中
            raw.apply_translation(-raw.bounds[0])
            raw.apply_translation([-raw.extents[0] / 2, -raw.extents[1] / 2, 0])

        except Exception as e:
            load_error = str(e)
            raw = None

        if load_error:
            st.error(f"❌ 無法載入此 STL 檔案：{load_error}")
            st.info("💡 建議：用 Meshmixer 或 PrusaSlicer 的「修復」功能先處理此檔案，再重新上傳。")
            st.session_state.mesh = None
            st.session_state.mesh_hash = ""
        else:
            st.session_state.mesh = raw
            st.session_state.mesh_hash = file_hash
            st.session_state.offset = [0.0, 0.0]
            st.session_state.thin_faces = None

use_stl = up_file and st.session_state.mesh is not None
use_manual = not use_stl and manual_v > 0

if use_stl or use_manual:
    if use_stl:
        try:
            vol = st.session_state.mesh.volume
            if not np.isfinite(vol) or vol <= 0:
                vol = st.session_state.mesh.convex_hull.volume
                st.caption("⚠️ 模型非封閉（非 watertight），體積以凸包近似計算。")
        except Exception:
            vol = st.session_state.mesh.convex_hull.volume
            st.caption("⚠️ 體積計算失敗，以凸包近似。")
        model_vol = abs(vol)
    else:
        model_vol = manual_v if m_unit == "mm³" else manual_v * 1000

    # 成本計算
    support_vol = model_vol * (support_ratio / 100)
    total_vol_per_unit = model_vol + support_vol
    material_cost_total = total_vol_per_unit * u_cost * qty
    handling_total = handling_fee * qty
    subtotal = material_cost_total + handling_total
    final_price = subtotal * markup

    # 材料每公升成本（原始未加成）
    mat_price_per_liter = df_m.loc[df_m["材料名稱"] == m_choice, "單價"].values[0]  # NT$/L

    # 列印時間估算
    model_h = st.session_state.mesh.extents[2] if use_stl else model_vol ** (1 / 3)
    n_layers = int(np.ceil(model_h / layer_thickness))
    print_time = (n_layers * printer_spec["layer_time_sec"]) / 60

    # 報價看板
    st.markdown(f"""
    <div class="price-container">
        <div style="font-size:13px;color:#64748b;font-weight:bold;margin-bottom:4px;">PREFORM 預估總列印成本</div>
        <div class="price-result">NT$ {final_price:,.0f}</div>
        <div class="data-grid">
            <div class="data-item"><div class="data-label">模型體積</div><div class="data-value">{model_vol:,.1f} mm³</div></div>
            <div class="data-item"><div class="data-label">使用材料</div><div class="data-value">{m_choice}</div></div>
            <div class="data-item"><div class="data-label">含支撐消耗 (mL)</div><div class="data-value">{total_vol_per_unit * qty / 1000:,.2f} mL</div></div>
            <div class="data-item"><div class="data-label">列印機型</div><div class="data-value">{p_choice}</div></div>
            <div class="data-item"><div class="data-label">預估列印時間</div><div class="data-value">≈ {print_time:.0f} 分鐘</div></div>
            <div class="data-item"><div class="data-label">層數（{layer_thickness}mm）</div><div class="data-value">{n_layers:,} 層</div></div>
            <div class="data-item"><div class="data-label">材料單價</div><div class="data-value">NT$ {mat_price_per_liter:,} / L</div></div>
            <div class="data-item"><div class="data-label">材料單價換算</div><div class="data-value">NT$ {mat_price_per_liter/1000:.2f} / mL</div></div>
        </div>
        <div class="cost-breakdown">
            <div class="cost-row">
                <span>材料費（含支撐 {support_ratio}%，{total_vol_per_unit / 1000:.2f} mL/件 × NT${mat_price_per_liter/1000:.2f}/mL）× {qty} 件</span>
                <span>NT$ {material_cost_total:,.0f}</span>
            </div>
            <div class="cost-row">
                <span>後處理費（NT$ {handling_fee}/件）× {qty} 件</span>
                <span>NT$ {handling_total:,.0f}</span>
            </div>
            <div class="cost-row"><span>小計</span><span>NT$ {subtotal:,.0f}</span></div>
            <div class="cost-row total"><span>× 加成 {markup}x　→　最終報價</span><span>NT$ {final_price:,.0f}</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3D 操作區
    if use_stl:
        st.divider()
        col_tool, col_view = st.columns([1, 3])

        with col_tool:
            # ── 區塊 1：擺放優化 ──────────────────────────
            st.markdown("#### 🎯 擺放優化")

            if st.button("⚡ 最佳列印位置", use_container_width=True,
                         help="綜合評估支撐面積、截面積、列印高度，自動找出最佳擺放方向"):
                with st.spinner("正在計算最佳方向..."):
                    mesh_orig = st.session_state.mesh.copy()

                    # ── SLA 最佳方向演算法 ──────────────────
                    # 取樣方向：均勻分布在上半球（法線朝上的方向作為底面朝向）
                    # 使用 Fibonacci sphere 取樣
                    def fibonacci_directions(n=120):
                        """均勻分布在球面的方向向量"""
                        indices = np.arange(n)
                        phi = np.pi * (3 - np.sqrt(5))  # 黃金角
                        y = 1 - (indices / (n - 1)) * 2
                        radius = np.sqrt(1 - y * y)
                        theta = phi * indices
                        x = np.cos(theta) * radius
                        z = np.sin(theta) * radius
                        dirs = np.column_stack([x, y, z])
                        # 只取上半球（底面朝上方向 = 零件朝下旋轉）
                        return dirs[dirs[:, 2] >= -0.1]

                    directions = fibonacci_directions(160)
                    face_areas = mesh_orig.area_faces
                    face_normals = mesh_orig.face_normals
                    total_area = mesh_orig.area

                    best_score = np.inf
                    best_rot = None
                    best_meta = {}

                    for up_dir in directions:
                        up_dir = up_dir / np.linalg.norm(up_dir)

                        # 旋轉矩陣：讓 up_dir 對齊 +Z（trimesh Z = 高度向上）
                        z = np.array([0, 0, 1.0])
                        axis = np.cross(up_dir, z)
                        axis_len = np.linalg.norm(axis)
                        if axis_len < 1e-8:
                            # 已經對齊或完全相反
                            if np.dot(up_dir, z) > 0:
                                rot_mat = np.eye(4)
                            else:
                                rot_mat = trimesh.transformations.rotation_matrix(
                                    np.pi, [1, 0, 0])
                        else:
                            angle = np.arctan2(axis_len, np.dot(up_dir, z))
                            rot_mat = trimesh.transformations.rotation_matrix(
                                angle, axis / axis_len)

                        # 旋轉後的法線
                        rot3 = rot_mat[:3, :3]
                        rotated_normals = face_normals @ rot3.T

                        # ① 支撐面積分數：朝下的面積（法線 Z < -cos45°）越少越好
                        down_mask = rotated_normals[:, 2] < -0.707
                        support_area = np.sum(face_areas[down_mask])
                        score_support = support_area / total_area  # 0~1

                        # ② 截面積分數：底面朝下時的 XY 截面積越小越好
                        #    用旋轉後的頂點估算底部 10% 高度的截面積
                        rotated_verts = (mesh_orig.vertices @ rot3.T)
                        z_min = rotated_verts[:, 2].min()
                        z_range = rotated_verts[:, 2].max() - z_min
                        bottom_mask = rotated_verts[:, 2] < z_min + z_range * 0.1
                        if bottom_mask.sum() > 0:
                            bv = rotated_verts[bottom_mask]
                            cross_area = (bv[:, 0].max() - bv[:, 0].min()) * \
                                         (bv[:, 1].max() - bv[:, 1].min())
                            bbox_xy = (rotated_verts[:, 0].max() - rotated_verts[:, 0].min()) * \
                                      (rotated_verts[:, 1].max() - rotated_verts[:, 1].min())
                            score_cross = cross_area / (bbox_xy + 1e-6)
                        else:
                            score_cross = 1.0

                        # ③ 高度分數：Z 方向高度越低，層數越少，列印越快
                        height = z_range
                        bbox_diag = np.sqrt(
                            (rotated_verts[:, 0].max() - rotated_verts[:, 0].min())**2 +
                            (rotated_verts[:, 1].max() - rotated_verts[:, 1].min())**2 +
                            (rotated_verts[:, 2].max() - rotated_verts[:, 2].min())**2
                        )
                        score_height = height / (bbox_diag + 1e-6)

                        # 綜合評分（權重：支撐面積 50%、截面積 30%、高度 20%）
                        score = 0.50 * score_support + 0.30 * score_cross + 0.20 * score_height

                        if score < best_score:
                            best_score = score
                            best_rot = rot_mat
                            best_meta = {
                                "support_pct": score_support * 100,
                                "height": height,
                                "score": score
                            }

                    # 套用最佳旋轉
                    if best_rot is not None:
                        m = st.session_state.mesh
                        m.apply_transform(best_rot)
                        m.apply_translation(-m.bounds[0])
                        m.apply_translation([-m.extents[0]/2, -m.extents[1]/2, 0])
                        st.session_state.thin_faces = None
                        pct = best_meta['support_pct']
                        ht  = best_meta['height']
                        st.success(
                            f"✅ 最佳方向已套用｜"
                            f"支撐面積 {pct:.1f}%｜"
                            f"列印高度 {ht:.1f} mm"
                        )
                        st.rerun()

            # 快速旋轉
            st.markdown("<div style='font-size:11px;color:#64748b;margin:6px 0 2px;font-weight:600;'>快速旋轉</div>",
                        unsafe_allow_html=True)
            rca, rcb, rcc = st.columns(3)
            if rca.button("X 90°", use_container_width=True):
                m = st.session_state.mesh
                m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(90), [1,0,0]))
                m.apply_translation(-m.bounds[0]); m.apply_translation([-m.extents[0]/2,-m.extents[1]/2,0])
                st.session_state.thin_faces = None; st.rerun()
            if rcb.button("Y 90°", use_container_width=True):
                m = st.session_state.mesh
                m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(90), [0,1,0]))
                m.apply_translation(-m.bounds[0]); m.apply_translation([-m.extents[0]/2,-m.extents[1]/2,0])
                st.session_state.thin_faces = None; st.rerun()
            if rcc.button("Z 90°", use_container_width=True):
                m = st.session_state.mesh
                m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(90), [0,0,1]))
                m.apply_translation(-m.bounds[0]); m.apply_translation([-m.extents[0]/2,-m.extents[1]/2,0])
                st.session_state.thin_faces = None; st.rerun()

            if st.button("↩ 重置旋轉＋位置", use_container_width=True):
                # 重新從原始 hash 載入
                st.session_state.offset = [0.0, 0.0]
                st.session_state.mesh_hash = ""   # 強制下次重新載入
                st.session_state.thin_faces = None
                st.rerun()

            st.divider()

            # ── 區塊 2：位置微調 ──────────────────────────
            st.markdown("#### 📏 位置微調")
            step_mm = st.select_slider("步距 (mm)", options=[1, 5, 10, 20], value=10)

            # 方向鍵佈局
            _, mc, _ = st.columns([1, 2, 1])
            mc.button("▲ Y+", use_container_width=True, key="y_plus",
                      on_click=lambda: st.session_state.update({"offset": [st.session_state.offset[0], st.session_state.offset[1]+step_mm]}))
            lc, _, rc = st.columns([1, 1, 1])
            lc.button("◀ X-", use_container_width=True, key="x_minus",
                      on_click=lambda: st.session_state.update({"offset": [st.session_state.offset[0]-step_mm, st.session_state.offset[1]]}))
            rc.button("▶ X+", use_container_width=True, key="x_plus",
                      on_click=lambda: st.session_state.update({"offset": [st.session_state.offset[0]+step_mm, st.session_state.offset[1]]}))
            _, mc2, _ = st.columns([1, 2, 1])
            mc2.button("▼ Y-", use_container_width=True, key="y_minus",
                       on_click=lambda: st.session_state.update({"offset": [st.session_state.offset[0], st.session_state.offset[1]-step_mm]}))

            ox, oy = st.session_state.offset
            st.markdown(
                f"<div style='text-align:center;font-size:11px;color:#64748b;margin-top:4px'>"
                f"偏移　X: <b>{ox:+.0f}</b> mm　Y: <b>{oy:+.0f}</b> mm</div>",
                unsafe_allow_html=True
            )
            if st.button("⊙ 歸零", use_container_width=True):
                st.session_state.offset = [0.0, 0.0]; st.rerun()

            st.divider()

            # ── 區塊 3：薄度偵測 ──────────────────────────
            st.markdown("#### 🔍 品質檢測")
            if st.button("🔴 薄壁偵測", use_container_width=True,
                         help=f"標記厚度 < {min_t_val} mm 的區域"):
                mesh_q = st.session_state.mesh
                tree = cKDTree(mesh_q.triangles_center)
                thin_set = set()
                for fi, (center, normal) in enumerate(zip(mesh_q.triangles_center, mesh_q.face_normals)):
                    dists, idxs = tree.query(center, k=6)
                    for dist, nfi in zip(dists[1:], idxs[1:]):
                        if dist < min_t_val and np.dot(normal, mesh_q.face_normals[nfi]) < -0.5:
                            thin_set.add(fi); break
                st.session_state.thin_faces = thin_set
                if thin_set:
                    st.warning(f"⚠️ {len(thin_set)} 個薄壁面（< {min_t_val} mm）")
                else:
                    st.success("✅ 無薄壁問題")

            if st.button("✕ 清除標記", use_container_width=True):
                st.session_state.thin_faces = None; st.rerun()

            # 模型資訊
            m = st.session_state.mesh
            st.markdown(
                f"""<div style='background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;
                padding:8px 10px;margin-top:8px;font-size:11px;color:#475569;line-height:1.9'>
                <b style='color:#0f172a'>模型資訊</b><br>
                尺寸：{m.extents[0]:.1f} × {m.extents[1]:.1f} × {m.extents[2]:.1f} mm<br>
                面數：{len(m.faces):,}<br>
                封閉：{'✅ 是' if m.is_watertight else '⚠️ 否'}</div>""",
                unsafe_allow_html=True
            )

        with col_view:
            geo_json = mesh_to_threejs_json(
                st.session_state.mesh,
                printer_spec, qty,
                st.session_state.offset[0],
                st.session_state.offset[1],
                thin_faces=st.session_state.thin_faces
            )
            if geo_json["is_over"]:
                st.error("⚠️ 零件超出設備列印範圍！請調整位置或數量。")

            html_code = preform_viewer_html(geo_json)
            st.components.v1.html(html_code, height=620, scrolling=False)

else:
    st.info("💡 請上傳 STL 模型（左側），或手動輸入體積，開始 PreForm 專業模擬。")
    st.markdown("""
**使用說明：**
- 📂 **上傳 STL**：自動計算體積，支援 3D 排版與薄度偵測（優先使用）
- ⌨️ **手動輸入**：僅輸入體積時使用，適合快速估算

**3D 視窗操作：**

| 操作 | 效果 |
|------|------|
| 右鍵拖曳 | 旋轉視角 |
| Shift＋右鍵 | 平移畫面 |
| 滾輪 | 縮放 |
| F | 重置視角 |
| T / R / I | 俯視 / 右視 / 等角 |
    """)
