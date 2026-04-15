"""
SOLIDWIZARD — 文件資料庫
多層級篩選（Faceted Navigation）+ 手動更新機制
"""

import streamlit as st
import json
import hashlib
import datetime
import time
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

# ── 頁面設定 ─────────────────────────────────────
st.set_page_config(
    page_title="SOLIDWIZARD | 文件資料庫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── 樣式 ──────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

/* 側邊欄 */
[data-testid="stSidebar"] {
    background: #0f172a;
    border-right: 1px solid #1e3a5f;
}
[data-testid="stSidebar"] * { color: #94a3b8 !important; }
[data-testid="stSidebar"] h3 {
    color: #e2e8f0 !important; font-size: 11px !important;
    text-transform: uppercase; letter-spacing: .12em;
    margin: 14px 0 6px !important; padding-bottom: 4px;
    border-bottom: 1px solid #1e3a5f;
}
[data-testid="stSidebar"] label { font-size: 12px !important; }
[data-testid="stSidebar"] .stCheckbox label { color: #cbd5e1 !important; }
[data-testid="stSidebar"] .stCheckbox:has(input:checked) label {
    color: #7dd3fc !important; font-weight: 600;
}

/* 主標題 */
.page-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
    border: 1px solid #1e3a5f; border-radius: 10px;
    padding: 20px 28px; margin-bottom: 20px;
    display: flex; align-items: center; gap: 16px;
}
.page-header h1 {
    font-family: 'DM Mono', monospace; font-size: 22px;
    color: #f8fafc; margin: 0; letter-spacing: -.01em;
}
.page-header p { color: #64748b; font-size: 13px; margin: 2px 0 0; }

/* 文件卡片 */
.doc-card {
    background: #ffffff; border: 1px solid #e2e8f0;
    border-radius: 8px; padding: 14px 16px; margin-bottom: 10px;
    transition: box-shadow .15s, border-color .15s;
    cursor: pointer;
}
.doc-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,.08); border-color: #93c5fd; }
.doc-card-title { font-size: 14px; font-weight: 600; color: #0f172a; margin-bottom: 4px; }
.doc-card-meta { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.tag {
    font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 99px;
    text-transform: uppercase; letter-spacing: .06em;
}
.tag-brand-formlabs  { background: #dbeafe; color: #1d4ed8; }
.tag-brand-scanology { background: #dcfce7; color: #15803d; }
.tag-type { background: #f1f5f9; color: #475569; }
.tag-new  { background: #fef9c3; color: #a16207; }
.doc-card-url { font-size: 11px; color: #94a3b8; margin-top: 5px;
    font-family: 'DM Mono', monospace; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis; }

/* 更新候選面板 */
.update-panel {
    background: #fffbeb; border: 1px solid #fcd34d;
    border-radius: 8px; padding: 14px 18px; margin-bottom: 16px;
}
.update-panel h4 { color: #92400e; font-size: 13px; margin: 0 0 8px; }

/* 統計條 */
.stat-bar {
    display: flex; gap: 16px; margin-bottom: 16px; flex-wrap: wrap;
}
.stat-item {
    background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
    padding: 8px 14px; font-size: 12px; color: #64748b;
}
.stat-item b { color: #0f172a; font-size: 16px; display: block; }

/* 搜尋 */
.stTextInput input {
    border-radius: 6px !important; border: 1px solid #cbd5e1 !important;
    font-size: 13px !important;
}
.stTextInput input:focus { border-color: #3b82f6 !important; box-shadow: 0 0 0 2px #bfdbfe !important; }
</style>
""", unsafe_allow_html=True)

# ── 資料庫路徑 ────────────────────────────────────
DB_PATH = Path("doc_database.json")
PENDING_PATH = Path("doc_pending.json")

# ── 預設文件資料（種子資料，初次運行時使用）──────
DEFAULT_DOCS = [
    # ── Formlabs Form 4 ─────────────────────────
    {"id":"fl001","brand":"Formlabs","device":"Form 4","category":"Datasheet",
     "title":"Form 4 技術規格表","url":"https://formlabs.com/3d-printers/form-4/","lang":"zh",
     "date":"2024-01-01","verified":True},
    {"id":"fl002","brand":"Formlabs","device":"Form 4","category":"User Manual",
     "title":"Form 4 操作手冊","url":"https://support.formlabs.com/s/?language=zh_CN","lang":"zh",
     "date":"2024-01-01","verified":True},
    {"id":"fl003","brand":"Formlabs","device":"Form 4","category":"材料",
     "title":"Form 4 材料相容性清單","url":"https://formlabs.com/materials/","lang":"zh",
     "date":"2024-03-01","verified":True},
    {"id":"fl004","brand":"Formlabs","device":"Form 4","category":"Application Note",
     "title":"Form 4 SLA 列印應用說明 — 工業原型","url":"https://formlabs.com/applications/","lang":"zh",
     "date":"2024-02-15","verified":True},
    # ── Formlabs Form 4L ─────────────────────────
    {"id":"fl005","brand":"Formlabs","device":"Form 4L","category":"Datasheet",
     "title":"Form 4L 大型列印規格表","url":"https://formlabs.com/3d-printers/form-4l/","lang":"zh",
     "date":"2024-01-01","verified":True},
    {"id":"fl006","brand":"Formlabs","device":"Form 4L","category":"Case Study",
     "title":"Form 4L 案例：航太零件快速原型","url":"https://formlabs.com/blog/","lang":"zh",
     "date":"2024-04-01","verified":True},
    {"id":"fl007","brand":"Formlabs","device":"Form 4L","category":"White Paper",
     "title":"大型 SLA 列印白皮書：Form 4L 精度驗證","url":"https://formlabs.com/blog/","lang":"zh",
     "date":"2024-02-01","verified":True},
    # ── Formlabs Fuse 1 ──────────────────────────
    {"id":"fl008","brand":"Formlabs","device":"Fuse 1","category":"Datasheet",
     "title":"Fuse 1 SLS 技術規格表","url":"https://formlabs.com/3d-printers/fuse-1/","lang":"zh",
     "date":"2024-01-01","verified":True},
    {"id":"fl009","brand":"Formlabs","device":"Fuse 1","category":"User Manual",
     "title":"Fuse 1 操作與維護手冊","url":"https://support.formlabs.com/s/?language=zh_CN","lang":"zh",
     "date":"2024-01-01","verified":True},
    {"id":"fl010","brand":"Formlabs","device":"Fuse 1","category":"材料",
     "title":"Nylon 12 粉末材料規格（Fuse 1）","url":"https://formlabs.com/materials/","lang":"zh",
     "date":"2024-03-15","verified":True},
    {"id":"fl011","brand":"Formlabs","device":"Fuse 1","category":"比較分析",
     "title":"SLA vs SLS：Form 4 vs Fuse 1 技術對比","url":"https://formlabs.com/blog/","lang":"zh",
     "date":"2024-05-01","verified":True},
    {"id":"fl012","brand":"Formlabs","device":"Fuse 1","category":"教學文件",
     "title":"Fuse 1 PreForm 切片設定教學","url":"https://support.formlabs.com/s/?language=zh_CN","lang":"zh",
     "date":"2024-04-10","verified":True},
    # ── Scanology SIMSCAN 30 ─────────────────────
    {"id":"sc001","brand":"Scanology","device":"SIMSCAN30","category":"Datasheet",
     "title":"SIMSCAN 30 手持式 3D 掃描規格表","url":"https://www.3d-scantech.com/","lang":"zh",
     "date":"2024-01-01","verified":True},
    {"id":"sc002","brand":"Scanology","device":"SIMSCAN30","category":"User Manual",
     "title":"SIMSCAN 30 操作手冊 v2.1","url":"https://www.3d-scantech.com/","lang":"zh",
     "date":"2024-02-01","verified":True},
    {"id":"sc003","brand":"Scanology","device":"SIMSCAN30","category":"Application Note",
     "title":"SIMSCAN 30 逆向工程應用說明","url":"https://www.3d-scantech.com/","lang":"zh",
     "date":"2024-03-01","verified":True},
    {"id":"sc004","brand":"Scanology","device":"SIMSCAN30","category":"Case Study",
     "title":"SIMSCAN 30 汽車覆蓋件掃描案例","url":"https://www.3d-scantech.com/","lang":"zh",
     "date":"2024-04-01","verified":True},
    {"id":"sc005","brand":"Scanology","device":"SIMSCAN30","category":"教學文件",
     "title":"SIMSCAN 30 快速上手掃描教學（10 分鐘）","url":"https://www.3d-scantech.com/","lang":"zh",
     "date":"2024-04-20","verified":True},
    # ── Scanology KSCAN X ────────────────────────
    {"id":"sc006","brand":"Scanology","device":"KSCANX","category":"Datasheet",
     "title":"KSCAN X 高精度 3D 掃描規格表","url":"https://www.3d-scantech.com/","lang":"zh",
     "date":"2024-01-01","verified":True},
    {"id":"sc007","brand":"Scanology","device":"KSCANX","category":"White Paper",
     "title":"KSCAN X 精度白皮書：光柵投影技術分析","url":"https://www.3d-scantech.com/","lang":"zh",
     "date":"2024-03-01","verified":True},
    {"id":"sc008","brand":"Scanology","device":"KSCANX","category":"比較分析",
     "title":"KSCAN X vs SIMSCAN 30：精度與場景對比","url":"https://www.3d-scantech.com/","lang":"zh",
     "date":"2024-05-10","verified":True},
    {"id":"sc009","brand":"Scanology","device":"KSCANX","category":"材料",
     "title":"KSCAN X 掃描標靶與校準板規格","url":"https://www.3d-scantech.com/","lang":"zh",
     "date":"2024-02-15","verified":True},
]

# ── 資料庫讀寫 ────────────────────────────────────
def load_db() -> list:
    if DB_PATH.exists():
        try:
            return json.loads(DB_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    DB_PATH.write_text(json.dumps(DEFAULT_DOCS, ensure_ascii=False, indent=2), encoding="utf-8")
    return DEFAULT_DOCS

def save_db(docs: list):
    DB_PATH.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")

def load_pending() -> list:
    if PENDING_PATH.exists():
        try:
            return json.loads(PENDING_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []

def save_pending(items: list):
    PENDING_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

# ── Session state 初始化 ──────────────────────────
if "docs" not in st.session_state:
    st.session_state.docs = load_db()
if "pending" not in st.session_state:
    st.session_state.pending = load_pending()
if "scrape_running" not in st.session_state:
    st.session_state.scrape_running = False
if "selected_doc" not in st.session_state:
    st.session_state.selected_doc = None

docs: list = st.session_state.docs
pending: list = st.session_state.pending

# ── 爬蟲邏輯（手動觸發）────────────────────────────
SOURCES = [
    {"name":"Formlabs 官網",    "url":"https://formlabs.com/blog/",            "brand":"Formlabs"},
    {"name":"Formlabs 支援中心", "url":"https://support.formlabs.com/s/?language=zh_CN","brand":"Formlabs"},
    {"name":"Scantech 官網",    "url":"https://www.3d-scantech.com/",          "brand":"Scanology"},
]

CATEGORY_KEYWORDS = {
    "Datasheet":        ["datasheet","規格","spec","specification","技術規格"],
    "White Paper":      ["white paper","whitepaper","白皮書","paper"],
    "Application Note": ["application","應用","note","說明"],
    "User Manual":      ["manual","手冊","操作","guide","指南"],
    "Case Study":       ["case","案例","study","客戶"],
    "教學文件":          ["tutorial","教學","入門","quick start","how to"],
    "比較分析":          ["compare","對比","comparison","vs","versus","分析"],
    "材料":             ["material","材料","resin","powder","nylon","樹脂"],
}

DEVICE_KEYWORDS = {
    "Form 4":    ["form 4","form4"],
    "Form 4L":   ["form 4l","form4l"],
    "Fuse 1":    ["fuse 1","fuse1","sls"],
    "SIMSCAN30": ["simscan","simscan30","simscan 30"],
    "KSCANX":    ["kscan","kscan x","kscanx"],
}

def guess_category(text: str) -> str:
    text_l = text.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        if any(k in text_l for k in kws):
            return cat
    return "其他"

def guess_device(text: str, brand: str) -> str:
    text_l = text.lower()
    fl_devs = ["Form 4", "Form 4L", "Fuse 1"]
    sc_devs = ["SIMSCAN30", "KSCANX"]
    pool = fl_devs if brand == "Formlabs" else sc_devs
    for dev in pool:
        kws = DEVICE_KEYWORDS.get(dev, [])
        if any(k in text_l for k in kws):
            return dev
    return pool[0]  # 預設第一個

def make_id(url: str, title: str) -> str:
    return hashlib.md5((url + title).encode()).hexdigest()[:8]

def scrape_source(source: dict) -> list:
    """嘗試抓取頁面連結，回傳候選文件清單"""
    try:
        import urllib.request
        req = urllib.request.Request(
            source["url"],
            headers={"User-Agent": "Mozilla/5.0 (compatible; SolidWizardBot/1.0)"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return [{"_error": str(e), "_source": source["name"]}]

    # 用 regex 抽取 <a> 連結
    pattern = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)
    found = []
    existing_urls = {d["url"] for d in docs}
    existing_ids  = {d["id"]  for d in docs}

    for match in pattern.finditer(html):
        href = match.group(1).strip()
        text = re.sub(r'<[^>]+>', '', match.group(2)).strip()

        if not text or len(text) < 5 or len(text) > 200:
            continue
        if href.startswith("#") or href.startswith("javascript"):
            continue

        # 補全相對 URL
        if href.startswith("/"):
            parsed = urlparse(source["url"])
            href = f"{parsed.scheme}://{parsed.netloc}{href}"
        elif not href.startswith("http"):
            href = urljoin(source["url"], href)

        # 跳過已存在
        if href in existing_urls:
            continue

        cat    = guess_category(text + " " + href)
        device = guess_device(text + " " + href, source["brand"])
        doc_id = make_id(href, text)

        if doc_id in existing_ids:
            continue

        # 過濾掉無意義連結（首頁、登入等）
        skip_kw = ["login","signup","cart","cookie","privacy","terms",
                   "account","pricing","contact","about","careers","#"]
        if any(k in href.lower() for k in skip_kw):
            continue

        found.append({
            "id": doc_id,
            "brand": source["brand"],
            "device": device,
            "category": cat,
            "title": text[:120],
            "url": href,
            "lang": "zh" if any(c > '\u4e00' for c in text) else "en",
            "date": datetime.date.today().isoformat(),
            "verified": False,
            "_source": source["name"],
            "_is_new": True,
        })

        if len(found) >= 30:  # 每次來源最多取 30 筆避免洪水
            break

    return found


# ════════════════════════════════════════════════
#  側邊欄：多層級篩選
# ════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🔍 文件篩選")

    # 搜尋框
    search_q = st.text_input("關鍵字搜尋", placeholder="輸入文件名稱、型號…", label_visibility="collapsed")

    # ── 第一層：品牌 ──────────────────────────────
    st.markdown("### 品牌")
    sel_brands = set()
    col_fl, col_sc = st.columns(2)
    if col_fl.checkbox("Formlabs", value=True, key="cb_fl"):
        sel_brands.add("Formlabs")
    if col_sc.checkbox("Scanology", value=True, key="cb_sc"):
        sel_brands.add("Scanology")

    # ── 第二層：設備（依品牌聯動）────────────────
    st.markdown("### 設備型號")
    sel_devices = set()
    DEVICE_MAP = {
        "Formlabs":  ["Form 4", "Form 4L", "Fuse 1"],
        "Scanology": ["SIMSCAN30", "KSCANX"],
    }
    for brand in ["Formlabs", "Scanology"]:
        if brand not in sel_brands:
            continue
        st.markdown(f"<div style='font-size:10px;color:#475569;text-transform:uppercase;"
                    f"letter-spacing:.08em;margin:4px 0 2px'>{brand}</div>",
                    unsafe_allow_html=True)
        for dev in DEVICE_MAP[brand]:
            if st.checkbox(dev, value=True, key=f"cb_{dev.replace(' ','_')}"):
                sel_devices.add(dev)

    # ── 第三層：文件分類 ──────────────────────────
    st.markdown("### 文件分類")
    ALL_CATS = ["Datasheet","White Paper","Application Note",
                "User Manual","Case Study","教學文件","比較分析","材料","其他"]
    sel_cats = set()
    # 全選快捷
    _all_cat = st.checkbox("全選分類", value=True, key="cb_all_cats")
    for cat in ALL_CATS:
        if st.checkbox(cat, value=_all_cat, key=f"cb_cat_{cat}"):
            sel_cats.add(cat)

    st.divider()
    # ── 只顯示已驗證 ─────────────────────────────
    only_verified = st.checkbox("僅顯示已驗證", value=False)
    only_new = st.checkbox("僅顯示新項目", value=False)

    st.divider()
    # ── 手動更新觸發 ──────────────────────────────
    st.markdown("### 🔄 後台資料更新")
    st.caption("來源：Formlabs 官網、支援中心、Scantech 官網")

    update_btn = st.button("🕷️ 立即抓取更新", use_container_width=True,
                           help="從三個來源網站搜尋新文件，結果需手動確認才會加入資料庫")
    st.caption(f"現有文件：{len(docs)} 筆　待審：{len(pending)} 筆")


# ════════════════════════════════════════════════
#  主畫面
# ════════════════════════════════════════════════

# 頁首
st.markdown("""
<div class="page-header">
  <div style="font-size:36px">📚</div>
  <div>
    <h1>文件資料庫</h1>
    <p>Formlabs &amp; Scanology 技術文件 · 多層級篩選 · 手動審核更新</p>
  </div>
</div>
""", unsafe_allow_html=True)

# ── 爬蟲執行 ─────────────────────────────────────
if update_btn:
    with st.status("🕷️ 正在抓取資料來源…", expanded=True) as status_box:
        new_candidates = []
        for src in SOURCES:
            st.write(f"▸ 抓取 {src['name']}…")
            results = scrape_source(src)
            errors  = [r for r in results if "_error" in r]
            valid   = [r for r in results if "_error" not in r]
            if errors:
                st.write(f"  ⚠️ {src['name']} 連線失敗：{errors[0]['_error']}")
            else:
                st.write(f"  ✅ 找到 {len(valid)} 筆候選")
            new_candidates.extend(valid)

        # 去重（已在 pending 裡的不重複加）
        pending_ids = {p["id"] for p in pending}
        fresh = [c for c in new_candidates if c["id"] not in pending_ids]
        pending.extend(fresh)
        save_pending(pending)
        st.session_state.pending = pending

        status_box.update(
            label=f"✅ 抓取完成：新增 {len(fresh)} 筆待審項目",
            state="complete"
        )

# ── 待審面板 ─────────────────────────────────────
if pending:
    with st.expander(f"⏳ 待審核項目（{len(pending)} 筆）— 點選確認或略過", expanded=True):
        st.markdown('<div class="update-panel"><h4>以下文件已從來源網站抓取，請逐一確認是否加入資料庫。</h4></div>',
                    unsafe_allow_html=True)

        accept_all = st.button("✅ 全部接受", key="accept_all")
        dismiss_all = st.button("❌ 全部略過", key="dismiss_all")

        if accept_all:
            for item in pending:
                item.pop("_is_new", None)
                item.pop("_source", None)
                item["verified"] = True
                docs.append(item)
            save_db(docs)
            st.session_state.docs = docs
            pending.clear()
            save_pending(pending)
            st.session_state.pending = pending
            st.success(f"已加入 {len(docs)} 筆")
            st.rerun()

        if dismiss_all:
            pending.clear()
            save_pending(pending)
            st.session_state.pending = pending
            st.rerun()

        to_remove = []
        for i, item in enumerate(pending):
            c1, c2, c3 = st.columns([4, 1, 1])
            with c1:
                st.markdown(
                    f"**{item['title']}**  \n"
                    f"<span style='font-size:11px;color:#64748b'>"
                    f"{item['brand']} · {item['device']} · {item['category']} · "
                    f"<a href='{item['url']}' target='_blank'>🔗 來源</a></span>",
                    unsafe_allow_html=True
                )
            with c2:
                if st.button("✅ 接受", key=f"acc_{i}"):
                    item_copy = {k: v for k, v in item.items()
                                 if k not in ("_is_new", "_source")}
                    item_copy["verified"] = True
                    docs.append(item_copy)
                    save_db(docs)
                    st.session_state.docs = docs
                    to_remove.append(i)
            with c3:
                if st.button("❌ 略過", key=f"dis_{i}"):
                    to_remove.append(i)

        if to_remove:
            for idx in sorted(set(to_remove), reverse=True):
                pending.pop(idx)
            save_pending(pending)
            st.session_state.pending = pending
            st.rerun()

st.divider()

# ── 篩選邏輯 ─────────────────────────────────────
filtered = docs

if sel_brands:
    filtered = [d for d in filtered if d.get("brand") in sel_brands]
if sel_devices:
    filtered = [d for d in filtered if d.get("device") in sel_devices]
if sel_cats:
    filtered = [d for d in filtered if d.get("category") in sel_cats]
if search_q:
    q = search_q.lower()
    filtered = [d for d in filtered
                if q in d.get("title","").lower()
                or q in d.get("device","").lower()
                or q in d.get("category","").lower()
                or q in d.get("url","").lower()]
if only_verified:
    filtered = [d for d in filtered if d.get("verified")]
if only_new:
    today = datetime.date.today().isoformat()
    week_ago = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    filtered = [d for d in filtered if d.get("date","") >= week_ago]

# ── 統計條 ────────────────────────────────────────
brands_in = {}
for d in filtered:
    brands_in[d.get("brand","?")] = brands_in.get(d.get("brand","?"), 0) + 1

stat_html = '<div class="stat-bar">'
stat_html += f'<div class="stat-item"><b>{len(filtered)}</b>篩選結果</div>'
for br, cnt in brands_in.items():
    stat_html += f'<div class="stat-item"><b>{cnt}</b>{br}</div>'
cats_cnt = {}
for d in filtered:
    cats_cnt[d.get("category","?")] = cats_cnt.get(d.get("category","?"),0)+1
top_cats = sorted(cats_cnt.items(), key=lambda x:-x[1])[:3]
for cat, cnt in top_cats:
    stat_html += f'<div class="stat-item"><b>{cnt}</b>{cat}</div>'
stat_html += '</div>'
st.markdown(stat_html, unsafe_allow_html=True)

# ── 排序選項 ──────────────────────────────────────
sort_col, add_col = st.columns([3, 1])
with sort_col:
    sort_by = st.selectbox("排序", ["日期（新→舊）","日期（舊→新）","品牌","型號","分類"],
                           label_visibility="collapsed")
with add_col:
    if st.button("＋ 手動新增文件", use_container_width=True):
        st.session_state.show_add_form = not st.session_state.get("show_add_form", False)

if sort_by == "日期（新→舊）":
    filtered = sorted(filtered, key=lambda x: x.get("date",""), reverse=True)
elif sort_by == "日期（舊→新）":
    filtered = sorted(filtered, key=lambda x: x.get("date",""))
elif sort_by == "品牌":
    filtered = sorted(filtered, key=lambda x: x.get("brand",""))
elif sort_by == "型號":
    filtered = sorted(filtered, key=lambda x: x.get("device",""))
elif sort_by == "分類":
    filtered = sorted(filtered, key=lambda x: x.get("category",""))

# ── 手動新增表單 ──────────────────────────────────
if st.session_state.get("show_add_form", False):
    with st.form("add_doc_form"):
        st.markdown("#### ＋ 手動新增文件")
        fc1, fc2 = st.columns(2)
        nb = fc1.selectbox("品牌", ["Formlabs","Scanology"])
        nd = fc2.selectbox("設備", ["Form 4","Form 4L","Fuse 1","SIMSCAN30","KSCANX"])
        nc = st.selectbox("分類", ALL_CATS)
        nt = st.text_input("文件標題")
        nu = st.text_input("文件 URL")
        submitted = st.form_submit_button("新增")
        if submitted and nt and nu:
            new_doc = {
                "id": make_id(nu, nt),
                "brand": nb, "device": nd, "category": nc,
                "title": nt, "url": nu, "lang": "zh",
                "date": datetime.date.today().isoformat(), "verified": True
            }
            if new_doc["id"] not in {d["id"] for d in docs}:
                docs.append(new_doc)
                save_db(docs)
                st.session_state.docs = docs
                st.success("✅ 已新增")
                st.session_state.show_add_form = False
                st.rerun()
            else:
                st.warning("此文件已存在")

# ── 文件卡片列表 ──────────────────────────────────
if not filtered:
    st.info("沒有符合篩選條件的文件。請調整左側篩選選項。")
else:
    for i, doc in enumerate(filtered):
        brand = doc.get("brand","")
        device = doc.get("device","")
        cat = doc.get("category","")
        title = doc.get("title","（無標題）")
        url = doc.get("url","#")
        date_str = doc.get("date","")
        verified = doc.get("verified", False)
        is_new_flag = (doc.get("date","") >= (datetime.date.today() -
                        datetime.timedelta(days=7)).isoformat())

        brand_cls = "tag-brand-formlabs" if brand == "Formlabs" else "tag-brand-scanology"

        new_badge = '<span class="tag tag-new">NEW</span>' if is_new_flag else ""
        verified_badge = '<span style="font-size:11px;color:#16a34a">✔ 已驗證</span>' if verified else \
                         '<span style="font-size:11px;color:#d97706">⚠ 待驗證</span>'

        st.markdown(f"""
        <div class="doc-card" onclick="window.open('{url}','_blank')">
          <div class="doc-card-title">{title}</div>
          <div class="doc-card-meta">
            <span class="tag {brand_cls}">{brand}</span>
            <span class="tag tag-type">{device}</span>
            <span class="tag tag-type">{cat}</span>
            {new_badge}
            {verified_badge}
            <span style="font-size:11px;color:#94a3b8;margin-left:auto">{date_str}</span>
          </div>
          <div class="doc-card-url">{url}</div>
        </div>
        """, unsafe_allow_html=True)

        # 刪除按鈕（小、低調）
        del_key = f"del_{doc['id']}_{i}"
        if st.button("🗑 移除", key=del_key, help="從資料庫移除此文件"):
            docs = [d for d in docs if d["id"] != doc["id"]]
            save_db(docs)
            st.session_state.docs = docs
            st.rerun()
