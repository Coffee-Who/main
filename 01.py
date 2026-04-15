import streamlit as st
import pandas as pd
import json
import hashlib
import datetime
import re
import io
from pathlib import Path
from urllib.parse import urljoin, urlparse

# ── 1. 頁面配置 ─────────────────────────────────────
st.set_page_config(
    page_title="SOLIDWIZARD | 業務技術資源庫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── 2. 核心樣式 (CSS) ──────────────────────────────────
st.markdown("""
<style>
/* 側邊欄樣式 */
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
.doc-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08); border-color: #3b82f6; }
.doc-card-title { font-size: 15px; font-weight: 600; color: #1e293b; margin-bottom: 4px; }

/* 標籤 */
.tag { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; }
.tag-fl { background: #eff6ff; color: #2563eb; }
.tag-sc { background: #f0fdf4; color: #16a34a; }
.tag-cat { background: #f1f5f9; color: #475569; }
</style>
""", unsafe_allow_html=True)

# ── 3. 資料庫初始化 ──────────────────────────────────
DB_PATH = Path("doc_db.json")
PENDING_PATH = Path("pending_db.json")

def init_db():
    if not DB_PATH.exists():
        DB_PATH.write_text(json.dumps([
            {"id":"seed1","brand":"Formlabs","device":"Form 4","category":"User Manual","title":"Form 4 快速入門指南","url":"https://support.formlabs.com","date":"2024-01-01"},
            {"id":"seed2","brand":"Scanology","device":"SIMSCAN30","category":"Datasheet","title":"SIMSCAN 30 技術規格手冊","url":"https://www.3d-scantech.com","date":"2024-02-15"}
        ], ensure_ascii=False))
    if not PENDING_PATH.exists():
        PENDING_PATH.write_text("[]")

init_db()

if "docs" not in st.session_state:
    st.session_state.docs = json.loads(DB_PATH.read_text(encoding="utf-8"))
if "pending" not in st.session_state:
    st.session_state.pending = json.loads(PENDING_PATH.read_text(encoding="utf-8"))

def save_all():
    DB_PATH.write_text(json.dumps(st.session_state.docs, ensure_ascii=False, indent=2), encoding="utf-8")
    PENDING_PATH.write_text(json.dumps(st.session_state.pending, ensure_ascii=False, indent=2), encoding="utf-8")

# ── 4. 側邊欄：多層級篩選選單 (Faceted Navigation) ──────────
with st.sidebar:
    st.title("SOLIDWIZARD")
    st.subheader("文件篩選系統")
    
    # 第一層：品牌
    st.markdown("### 品牌 (Brand)")
    sel_brands = []
    if st.checkbox("Formlabs", value=True): sel_brands.append("Formlabs")
    if st.checkbox("Scanology", value=True): sel_brands.append("Scanology")
    
    # 第二層：設備類型 (連動第一層)
    st.markdown("### 設備型號 (Device)")
    dev_map = {
        "Formlabs": ["Form 4", "Form 4L", "Fuse 1"],
        "Scanology": ["SIMSCAN30", "KSCANX"]
    }
    selectable_devs = []
    for b in sel_brands:
        selectable_devs.extend(dev_map[b])
    
    sel_devices = []
    for d in selectable_devs:
        if st.checkbox(d, value=True):
            sel_devices.append(d)
            
    # 第三層：文件分類
    st.markdown("### 內容分類 (Category)")
    cats = ["Datasheet", "White Paper", "Application Note", "User Manual", "Case Study", "教學文件", "比較分析", "材料"]
    sel_cats = []
    for c in cats:
        if st.checkbox(c, value=True):
            sel_cats.append(c)

    st.divider()
    # 後台手動更新觸發器
    if st.button("🕷️ 掃描來源網站更新"):
        # 模擬爬蟲發現新文件
        new_id = hashlib.md5(str(datetime.datetime.now()).encode()).hexdigest()[:6]
        mock_item = {
            "id": new_id,
            "brand": "Formlabs",
            "device": "Form 4L",
            "category": "White Paper",
            "title": f"新發現：SLA 精度驗證白皮書 ({datetime.date.today()})",
            "url": "https://formlabs.com/white-paper",
            "date": str(datetime.date.today())
        }
        st.session_state.pending.append(mock_item)
        save_all()
        st.success("掃描完成，請至待審區確認。")

# ── 5. 主畫面邏輯 ─────────────────────────────────────
tab_main, tab_admin = st.tabs(["📂 文件檢索庫", "⚙️ 後台審核更新"])

with tab_main:
    # 搜尋框
    q = st.text_input("🔍 輸入關鍵字搜尋文件...", placeholder="例如：操作手冊、Fuse 1...")
    
    # 篩選邏輯
    filtered = [d for d in st.session_state.docs if 
                d["brand"] in sel_brands and 
                d["device"] in sel_devices and 
                d["category"] in sel_cats]
    
    if q:
        filtered = [d for d in filtered if q.lower() in d["title"].lower() or q.lower() in d["device"].lower()]

    # 顯示統計
    st.caption(f"找到 {len(filtered)} 份符合條件的文件")
    
    # 渲染卡片
    for doc in filtered:
        tag_color = "tag-fl" if doc["brand"] == "Formlabs" else "tag-sc"
        st.markdown(f"""
        <div class="doc-card" onclick="window.open('{doc['url']}', '_blank')">
            <div class="doc-card-title">{doc['title']}</div>
            <div style="display: flex; gap: 8px;">
                <span class="tag {tag_color}">{doc['brand']}</span>
                <span class="tag tag-cat">{doc['device']}</span>
                <span class="tag tag-cat">{doc['category']}</span>
                <span style="font-size: 11px; color: #94a3b8; margin-left: auto;">{doc['date']}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

with tab_admin:
    st.subheader("待審核更新項目")
    if not st.session_state.pending:
        st.write("目前沒有待處理的更新。")
    else:
        for i, p in enumerate(st.session_state.pending):
            with st.expander(f"🆕 新文件: {p['title']}", expanded=True):
                col1, col2, col3 = st.columns([4, 1, 1])
                col1.write(f"品牌: {p['brand']} | 分類: {p['category']} | 日期: {p['date']}")
                if col2.button("✅ 批准加入", key=f"acc_{i}"):
                    st.session_state.docs.append(p)
                    st.session_state.pending.pop(i)
                    save_all()
                    st.rerun()
                if col3.button("❌ 略過", key=f"ign_{i}"):
                    st.session_state.pending.pop(i)
                    save_all()
                    st.rerun()
