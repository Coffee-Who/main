import streamlit as st
import json
import hashlib
import datetime
import re
import io
import pandas as pd
from pathlib import Path
from urllib.parse import urljoin, urlparse

# ── 1. 頁面配置 ─────────────────────────────────────
st.set_page_config(
    page_title="SOLIDWIZARD | 技術文件資料庫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── 2. 核心 CSS 樣式 ──────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

/* 側邊欄深色主題 */
[data-testid="stSidebar"] { background: #0f172a; border-right: 1px solid #1e3a5f; }
[data-testid="stSidebar"] * { color: #94a3b8 !important; }
[data-testid="stSidebar"] h3 { 
    color: #e2e8f0 !important; font-size: 11px !important; 
    text-transform: uppercase; letter-spacing: .12em; 
    margin: 14px 0 6px !important; border-bottom: 1px solid #1e3a5f;
}

/* 文件卡片設計 */
.doc-card {
    background: #ffffff; border: 1px solid #e2e8f0;
    border-radius: 8px; padding: 14px 16px; margin-bottom: 10px;
    transition: all .2s ease; cursor: pointer;
}
.doc-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,.08); border-color: #3b82f6; }
.doc-card-title { font-size: 15px; font-weight: 600; color: #0f172a; margin-bottom: 6px; }

/* 標籤樣式 */
.tag { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; }
.tag-brand-formlabs  { background: #eff6ff; color: #2563eb; border: 1px solid #dbeafe; }
.tag-brand-scanology { background: #f0fdf4; color: #16a34a; border: 1px solid #dcfce7; }
.tag-type { background: #f1f5f9; color: #475569; }
.tag-new { background: #fefce8; color: #854d0e; border: 1px solid #fef08a; }

/* 統計資訊 */
.stat-bar { display: flex; gap: 12px; margin-bottom: 20px; }
.stat-item { 
    background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; 
    padding: 10px 16px; min-width: 100px;
}
.stat-item b { color: #0f172a; font-size: 18px; display: block; }
.stat-item span { color: #64748b; font-size: 11px; }
</style>
""", unsafe_allow_html=True)

# ── 3. 資料庫與 Session 管理 ────────────────────────────
DB_PATH = Path("doc_database.json")
PENDING_PATH = Path("doc_pending.json")

def init_db():
    if not DB_PATH.exists():
        # 種子資料 (範例)
        seed = [
            {"id":"fl_01","brand":"Formlabs","device":"Form 4","category":"Datasheet","title":"Form 4 技術規格表","url":"https://formlabs.com","date":"2024-05-01","verified":True},
            {"id":"sc_01","brand":"Scanology","device":"SIMSCAN30","category":"User Manual","title":"SIMSCAN 30 操作手冊","url":"https://scantech.com","date":"2024-04-20","verified":True}
        ]
        DB_PATH.write_text(json.dumps(seed, ensure_ascii=False))
    if not PENDING_PATH.exists():
        PENDING_PATH.write_text("[]")

init_db()

if "docs" not in st.session_state:
    st.session_state.docs = json.loads(DB_PATH.read_text(encoding="utf-8"))
if "pending" not in st.session_state:
    st.session_state.pending = json.loads(PENDING_PATH.read_text(encoding="utf-8"))

# ── 4. 工具函數 ──────────────────────────────────────
def save_data():
    DB_PATH.write_text(json.dumps(st.session_state.docs, ensure_ascii=False, indent=2), encoding="utf-8")
    PENDING_PATH.write_text(json.dumps(st.session_state.pending, ensure_ascii=False, indent=2), encoding="utf-8")

def make_id(url, title):
    return hashlib.md5((url + title).encode()).hexdigest()[:8]

# ── 5. 側邊欄篩選介面 ──────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 智能搜尋")
    search_q = st.text_input("關鍵字搜尋", placeholder="搜尋文件、型號...", label_visibility="collapsed")
    
    st.markdown("### 品牌與設備")
    sel_brands = []
    col1, col2 = st.columns(2)
    if col1.checkbox("Formlabs", value=True): sel_brands.append("Formlabs")
    if col2.checkbox("Scanology", value=True): sel_brands.append("Scanology")
    
    # 動態型號過濾
    device_options = []
    if "Formlabs" in sel_brands: device_options += ["Form 4", "Form 4L", "Fuse 1"]
    if "Scanology" in sel_brands: device_options += ["SIMSCAN30", "KSCANX"]
    
    sel_devices = st.multiselect("設備型號", device_options, default=device_options)
    
    st.markdown("### 文件分類")
    all_categories = ["Datasheet", "User Manual", "White Paper", "Application Note", "教學文件", "材料"]
    sel_cats = st.multiselect("分類過濾", all_categories, default=all_categories)

    st.divider()
    st.markdown("### ⚙️ 後台管理")
    if st.button("🕷️ 執行網站抓取更新", use_container_width=True):
        # 這裡模擬爬蟲邏輯，您可以串接原始碼中的 scrape_source
        new_item = {"id": make_id("test_url", "新發現文件"), "brand": "Formlabs", "device": "Form 4", "category": "Datasheet", "title": "自動偵測到的新文件", "url": "https://formlabs.com", "date": datetime.date.today().isoformat(), "verified": False}
        if new_item["id"] not in [d["id"] for d in st.session_state.docs]:
            st.session_state.pending.append(new_item)
            save_data()
            st.success("發現新文件，已加入待審區")

# ── 6. 主畫面顯示 ─────────────────────────────────────
st.title("📚 SOLIDWIZARD 文件總庫")

# 待審核區快顯
if st.session_state.pending:
    with st.expander(f"⚠️ 待審核項目 ({len(st.session_state.pending)})", expanded=True):
        for i, p in enumerate(st.session_state.pending):
            c1, c2, c3 = st.columns([5, 1, 1])
            c1.write(f"**{p['title']}** ({p['brand']} / {p['device']})")
            if c2.button("核准", key=f"app_{i}"):
                p["verified"] = True
                st.session_state.docs.append(p)
                st.session_state.pending.pop(i)
                save_data()
                st.rerun()
            if c3.button("略過", key=f"ign_{i}"):
                st.session_state.pending.pop(i)
                save_data()
                st.rerun()

# 數據過濾邏輯
filtered = [d for d in st.session_state.docs if 
            d["brand"] in sel_brands and 
            d["device"] in sel_devices and 
            d["category"] in sel_cats]

if search_q:
    filtered = [d for d in filtered if search_q.lower() in d["title"].lower() or search_q.lower() in d["device"].lower()]

# 統計條
st.markdown(f"""
<div class="stat-bar">
    <div class="stat-item"><b>{len(filtered)}</b><span>文件總數</span></div>
    <div class="stat-item"><b>{len(sel_brands)}</b><span>已選品牌</span></div>
    <div class="stat-item"><b>{datetime.date.today().strftime('%m/%d')}</b><span>最後更新</span></div>
</div>
""", unsafe_allow_html=True)

# 文件列表渲染
if not filtered:
    st.info("目前的篩選條件下沒有文件。")
else:
    for doc in filtered:
        brand_tag = "tag-brand-formlabs" if doc["brand"] == "Formlabs" else "tag-brand-scanology"
        st.markdown(f"""
        <div class="doc-card" onclick="window.open('{doc['url']}', '_blank')">
            <div style="display: flex; justify-content: space-between; align-items: start;">
                <div class="doc-card-title">{doc['title']}</div>
                <span style="font-size: 11px; color: #94a3b8;">{doc['date']}</span>
            </div>
            <div style="display: flex; gap: 8px; margin-top: 4px;">
                <span class="tag {brand_tag}">{doc['brand']}</span>
                <span class="tag tag-type">{doc['device']}</span>
                <span class="tag tag-type">{doc['category']}</span>
                {"<span class='tag tag-new'>New</span>" if "2024" in doc['date'] else ""}
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 功能按鈕
        col_btn1, col_btn2 = st.columns([1, 8])
        if col_btn1.button("🗑️ 移除", key=f"del_{doc['id']}", help="從資料庫永久刪除"):
            st.session_state.docs = [d for d in st.session_state.docs if d["id"] != doc["id"]]
            save_data()
            st.rerun()
