import streamlit as st
import pandas as pd
import trimesh
import numpy as np
import io
import hashlib
import json

# --- 1. PreForm 專業 UI 配置 ---
st.set_page_config(page_title="SOLIDWIZARD | PreForm AI & Sales Hub", layout="wide")

st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #f8fafc; border-right: 1px solid #e2e8f0; }
    .stButton>button { width: 100%; border-radius: 4px; font-weight: 600; background-color: #ffffff;
        border: 1px solid #cbd5e1; height: 36px; font-size: 12px; transition: all .15s; }
    .stButton>button:hover { background-color: #0081FF; color: white; border-color: #0081FF; }
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
    h4 { font-size: 13px !important; margin: 10px 0 6px !important; color: #1e293b !important; font-weight: bold !important; }
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

PRINTERS = {
    "Form 4":  {"w": 200.0, "d": 125.0, "h": 210.0, "layer_time_sec": 5.0},
    "Form 4L": {"w": 353.0, "d": 196.0, "h": 350.0, "layer_time_sec": 6.0},
    "FUSE 1+": {"w": 165.0, "d": 165.0, "h": 300.0, "layer_time_sec": 8.0},
}

SCAN_DEVICES = ["SIMSCAN 30", "KSCAN-X", "AXE-B17", "TrackScan-Sharp"]

# --- 4. 側邊欄：多層級業務分類查詢系統 ---
with st.sidebar:
    st.image("https://formlabs.com/favicon.ico", width=24)
    st.title("業務內部分類查詢系統")
    
    st.markdown('<div class="priority-note">請勾選品牌與設備型號，系統將自動過濾對應文件。</div>', unsafe_allow_html=True)
    
    # 第一層：品牌
    st.markdown("#### 1. 品牌選擇")
    col1, col2 = st.columns(2)
    with col1:
        f_brand = st.checkbox("Formlabs", value=True)
    with col2:
        s_brand = st.checkbox("Scanology", value=False)
    
    # 第二層：設備類型 (Checkbox 動態展開)
    st.markdown("#### 2. 設備型號")
    selected_models = []
    
    if f_brand:
        with st.expander("Formlabs 列印設備", expanded=True):
            for model in PRINTERS.keys():
                if st.checkbox(model, key=f"check_{model}", value=(model == "Form 4")):
                    selected_models.append(model)
                    
    if s_brand:
        with st.expander("Scanology 掃描設備", expanded=True):
            for device in SCAN_DEVICES:
                if st.checkbox(device, key=f"check_{device}"):
                    selected_models.append(device)
    
    # 第三層：文件分類
    st.markdown("#### 3. 技術資料庫")
    with st.expander("技術文件分類", expanded=False):
        doc_types = ["Datasheet (規格表)", "White Paper", "Application Note", 
                     "User Manual", "Case Study", "Tutorial", "Comparison"]
        selected_docs = []
        for dt in doc_types:
            if st.checkbox(dt, key=f"doc_{dt}"):
                selected_docs.append(dt)
                
    with st.expander("材料與科學規格"):
        m_choice = st.selectbox("材料選擇", df_m["材料名稱"].tolist())
    
    st.divider()
    
    # 報價系統參數 (收納至進階設定)
    with st.expander("💰 報價參數設定"):
        qty = st.number_input("數量", min_value=1, value=1)
        markup = st.number_input("報價加成倍率", min_value=1.0, value=2.0, step=0.1)
        layer_thickness = st.selectbox("層厚 (mm)", [0.05, 0.1, 0.2], index=1)
        handling_fee = st.number_input("處理費 / 件 (NT$)", min_value=0, value=200)

    if st.button("🔄 清除所有過濾"):
        st.rerun()

# --- 5. 主畫面邏輯 ---
# 為了兼容原本 3D 報價邏輯，我們取 selected_models 的第一個作為當前渲染機型
active_printer = "Form 4"
if selected_models:
    for m in selected_models:
        if m in PRINTERS:
            active_printer = m
            break

printer_spec = PRINTERS[active_printer]
u_cost = df_m.loc[df_m["材料名稱"] == m_choice, "每mm3成本"].values[0]

# 顯示分區
tab_quote, tab_docs = st.tabs(["🚀 3D 報價模擬器", "📂 技術文件查詢"])

with tab_quote:
    # --- 檔案上傳區 ---
    st.subheader("STL 模型上傳")
    up_file = st.file_uploader("上傳零件進行體積分析 (支援多件陣列計算)", type=["stl"])
    
    # 原本的 3D 計算與渲染邏輯 (簡化呈現核心)
    if up_file:
        file_bytes = up_file.read()
        file_hash = hashlib.md5(file_bytes).hexdigest()
        
        # 載入 Mesh 邏輯 (此處承接您原本的 trimesh 代碼)
        if st.session_state.mesh_hash != file_hash:
            try:
                loaded = trimesh.load(io.BytesIO(file_bytes), file_type='stl')
                if isinstance(loaded, trimesh.Scene):
                    meshes = [g for g in loaded.geometry.values() if isinstance(g, trimesh.Trimesh)]
                    raw = trimesh.util.concatenate(meshes)
                else:
                    raw = loaded
                raw.apply_translation(-raw.bounds[0]) # 置中
                st.session_state.mesh = raw
                st.session_state.mesh_hash = file_hash
            except:
                st.error("檔案載入失敗")
    
    if st.session_state.mesh:
        mesh = st.session_state.mesh
        model_vol = abs(mesh.volume)
        
        # 成本計算看板
        total_vol = model_vol * 1.2 * qty # 預設 20% 支撐
        material_cost = total_vol * u_cost
        final_price = (material_cost + (handling_fee * qty)) * markup
        
        st.markdown(f"""
        <div class="price-container">
            <div class="price-result">預估報價 NT$ {final_price:,.0f}</div>
            <div class="data-grid">
                <div class="data-item"><div class="data-label">使用機型</div><div class="data-value">{active_printer}</div></div>
                <div class="data-item"><div class="data-label">材料</div><div class="data-value">{m_choice}</div></div>
                <div class="data-item"><div class="data-label">單件體積</div><div class="data-value">{model_vol/1000:,.1f} cm³</div></div>
                <div class="data-item"><div class="data-label">加成倍率</div><div class="data-value">{markup}x</div></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 這裡會放入您原本的 preform_viewer_html 函數生成的 3D View
        # 為保持範例簡潔，僅預留位置
        st.info(f"3D 視圖載入中... 目前機型範圍: {printer_spec['w']}x{printer_spec['d']}x{printer_spec['h']} mm")

with tab_docs:
    st.subheader("內部分享文件")
    if not selected_models:
        st.warning("請在左側選單至少勾選一個型號來過濾文件。")
    else:
        # 模擬文件查詢結果
        st.write(f"正在顯示：{', '.join(selected_models)} 的相關文件")
        
        # 範例表格呈現
        results = []
        for m in selected_models:
            for d in (selected_docs if selected_docs else ["預設清單"]):
                results.append({"型號": m, "文件類型": d, "更新日期": "2024-05", "連結": "🔗 下載"})
        
        st.table(results)

# 註：這裡原本的 Three.js 渲染 HTML 函數 preform_viewer_html 與相關邏輯可直接貼在上方繼續運行。
