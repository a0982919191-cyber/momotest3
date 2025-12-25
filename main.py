import streamlit as st
import io
import os
import requests
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from rembg import remove
from products import PRODUCT_CATALOG
import datetime

# ==========================================
# 1. 全局設定 & 模擬資料庫
# ==========================================
st.set_page_config(page_title="Momo Design Pro", page_icon="💎", layout="wide")

@st.cache_resource
def get_database():
    return {"members": []}

db = get_database()

if "user_role" not in st.session_state: st.session_state["user_role"] = "guest"
if "user_info" not in st.session_state: st.session_state["user_info"] = {}
if "site_locked" not in st.session_state: st.session_state["site_locked"] = True

# ==========================================
# 2. 全站密碼鎖
# ==========================================
def check_lock():
    if st.session_state["site_locked"]:
        st.markdown("<br><br><h2 style='text-align:center;'>🔒 Momo 內部系統</h2>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            pwd = st.text_input("請輸入密碼", type="password", label_visibility="collapsed")
            if st.button("進入系統", use_container_width=True):
                if pwd == "momo2025": 
                    st.session_state["site_locked"] = False
                    st.rerun()
                else:
                    st.error("密碼錯誤")
        st.stop()

check_lock()

# ==========================================
# 3. 字型處理 (防崩潰版)
# ==========================================
FONT_FILE = "NotoSansTC-Regular.ttf"
DEFAULT_FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanstc/NotoSansTC-Regular.ttf"

@st.cache_resource
def load_system_font():
    # 嘗試靜默下載，失敗不報錯
    if not os.path.exists(FONT_FILE):
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(DEFAULT_FONT_URL, headers=headers, timeout=10)
            if r.status_code == 200:
                with open(FONT_FILE, "wb") as f: f.write(r.content)
        except: 
            pass # 下載失敗就略過，不要卡住
    return FONT_FILE

load_system_font()

def get_font_obj(size):
    """取得字型，如果失敗絕對回傳預設值，防止 OSError"""
    try:
        # 1. 優先檢查手動救援的字型
        if "custom_font_bytes" in st.session_state:
            return ImageFont.truetype(io.BytesIO(st.session_state["custom_font_bytes"]), size)
        
        # 2. 檢查系統自動下載的字型
        if os.path.exists(FONT_FILE):
            return ImageFont.truetype(FONT_FILE, size)
            
    except Exception:
        pass # 發生任何錯誤(包含檔案損毀)都直接跳過
        
    # 3. 最後防線：使用預設字體 (雖然醜一點但不會當機)
    return ImageFont.load_default()

# ==========================================
# 4. CSS 美化
# ==========================================
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; font-family: "Microsoft JhengHei", sans-serif; }
    .block-container { padding-top: 1rem; padding-bottom: 3rem; }
    
    /* 會員條 */
    .member-bar {
        background: white; padding: 12px 20px; border-radius: 10px;
        margin-bottom: 20px; border-left: 6px solid #667eea;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        font-size: 15px; color: #4a5568;
    }
    
    /* 隱藏選單 */
    #MainMenu, footer, header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 5. 詢價單生成邏輯
# ==========================================
def generate_inquiry(img, data):
    w, h = 800, 1300
    card = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(card)
    
    c_primary = "#2c3e50"
    
    # 取得字型 (不會報錯)
    f_xl = get_font_obj(40)
    f_l = get_font_obj(30)
    f_m = get_font_obj(24)
    f_s = get_font_obj(20)
    
    # Header
    draw.rectangle([(0,0), (w, 140)], fill=c_primary)
    draw.text((40, 50), "Momo Design 需求詢價單", fill="white", font=f_xl)
    draw.text((w-250, 60), str(datetime.date.today()), fill="#ccc", font=f_s)
    
    # 圖片
    t_w = 400
    ratio = t_w / img.width
    t_h = int(img.height * ratio)
    res = img.resize((t_w, t_h))
    draw.rectangle([((w-t_w)//2-5, 170-5), ((w-t_w)//2+t_w+5, 170+t_h+5)], fill="#eee")
    card.paste(res, ((w-t_w)//2, 170), res if res.mode=='RGBA' else None)
    
    y = 170 + t_h + 50
    draw.line([(50,y), (750,y)], fill="#ddd", width=2)
    y += 30
    
    # 推廣碼區塊
    promo_code = data.get('promo_code')
    if promo_code and promo_code != "GUEST":
        draw.rectangle([(50, y), (750, y+60)], fill="#fff3cd")
        draw.text((70, y+15), f"★ 分潤/推薦代碼：{promo_code}", fill="#856404", font=f_l)
        y += 90
    
    # 資料欄位
    fields = [
        ("詢價單位", data.get('name')), ("聯絡人", data.get('contact')),
        ("電話", data.get('phone')), ("LINE ID", data.get('line')),
        ("---", "---"),
        ("產品系列", data.get('series')), ("款式", data.get('variant')),
        ("數量", f"{data.get('qty')} 件"), ("備註", data.get('note'))
    ]
    
    for k, v in fields:
        if k == "---":
            y += 15; draw.line([(50,y), (750,y)], fill="#eee", width=1); y += 25
            continue
        draw.text((60, y), f"【{k}】", fill=c_primary, font=f_m)
        val = str(v) if v else "-"
        # 自動換行
        max_char = 22
        for i in range(0, len(val), max_char):
            draw.text((250, y), val[i:i+max_char], fill="#333", font=f_m)
            y += 40
        y += 10

    draw.rectangle([(0, h-80), (w, h)], fill="#f8f9fa")
    draw.text((200, h-50), "此單據僅供詢價，正式報價以業務回傳為主", fill="#999", font=f_s)
    return card

# ==========================================
# 6. 側邊欄 (會員中心 + 隱藏後台)
# ==========================================
with st.sidebar:
    st.title("👤 會員中心")
    
    # 一般會員 / 訪客邏輯
    if st.session_state["user_role"] == "guest":
        st.info("尚未登入")
        with st.expander("🚀 登入 / 註冊推廣大使", expanded=True):
            r_name = st.text_input("姓名/暱稱")
            r_phone = st.text_input("手機號碼")
            is_amb = st.checkbox("開啟分潤功能 (成為大使)")
            
            if st.button("確認進入", type="primary", use_container_width=True):
                if r_name and r_phone:
                    code = f"{r_name.upper()}{r_phone[-3:]}" if is_amb else "MEMBER"
                    # 寫入資料庫
                    db["members"].append({"Name": r_name, "Phone": r_phone, "Type": "大使" if is_amb else "會員", "Code": code, "Date": str(datetime.date.today())})
                    st.session_state["user_role"] = "member"
                    st.session_state["user_info"] = {"name": r_name, "code": code, "is_ambassador": is_amb}
                    st.rerun()
                else:
                    st.error("請輸入資料")
    else:
        # 已登入顯示
        u = st.session_state["user_info"]
        st.success(f"Hi, {u['name']}")
        if u["is_ambassador"]:
            st.markdown(f"推廣碼: **`{u['code']}`**")
        if st.button("登出", use_container_width=True):
            st.session_state["user_role"] = "guest"
            st.session_state["user_info"] = {}
            st.rerun()

    st.markdown("---")
    
    # --- [隱藏後台] 只有勾選才會出現 ---
    show_admin = st.checkbox("⚙️ 系統管理", value=False, help="管理員/字型修復")
    
    if show_admin:
        st.markdown("#### 🔐 管理員後台")
        ad_pwd = st.text_input("Admin Password", type="password")
        if ad_pwd == "admin888":
            st.success("Access Granted")
            if db["members"]:
                st.dataframe(pd.DataFrame(db["members"]), use_container_width=True)
            else:
                st.info("尚無會員資料")
        
        st.markdown("#### 🔤 字型救援")
        st.caption("若詢價單文字異常，請上傳 .ttf 檔")
        cf = st.file_uploader("上傳字型", type=["ttf"])
        if cf:
            st.session_state["custom_font_bytes"] = cf.getvalue()
            st.success("字型已套用")

# ==========================================
# 7. 主畫面
# ==========================================
# 頂部狀態條
if st.session_state["user_role"] == "member":
    u = st.session_state["user_info"]
    code_msg = f"｜推廣碼：**{u['code']}**" if u['is_ambassador'] else ""
    st.markdown(f"""<div class="member-bar">👋 歡迎回來，{u['name']} {code_msg}</div>""", unsafe_allow_html=True)

# 模式選擇
st.markdown("#### 🛍️ 選擇模式")
mode = st.radio("mode", ["一般訂製 / 推廣", "公司團體 (詢價)"], horizontal=True, label_visibility="collapsed")

current_code = st.session_state["user_info"].get("code", "GUEST") if st.session_state["user_role"] == "member" else "GUEST"

col_preview, col_tools = st.columns([1.5, 1], gap="medium")

with col_tools:
    st.markdown("### 1. 產品")
    c1, c2 = st.columns(2)
    with c1: series = st.selectbox("系列", list(PRODUCT_CATALOG.keys()))
    with c2: variant = st.selectbox("款式", list(PRODUCT_CATALOG[series].keys()))
    item = PRODUCT_CATALOG[series][variant]
    pos_opts = item.get("positions", {"中":[150,150]})
    
    st.markdown("### 2. 設計")
    up_file = st.file_uploader("上傳圖案", type=["png","jpg","jpeg"])
    if up_file:
        with st.expander("參數調整", expanded=True):
            rm_bg = st.toggle("AI 去背")
            pos_k = st.selectbox("位置", list(pos_opts.keys()))
            sz = st.slider("大小", 50, 450, 180)
            ox = st.slider("左右", -60, 60, 0)
            oy = st.slider("上下", -60, 60, 0)
            rot = st.slider("旋轉", -180, 180, 0)
    else:
        pos_k, sz, ox, oy, rot, rm_bg = list(pos_opts.keys())[0], 150, 0, 0, 0, False

with col_preview:
    try:
        base = Image.open(item["image"]).convert("RGBA")
        final = base.copy()
        if up_file:
            d = Image.open(up_file).convert("RGBA")
            if rm_bg: d = remove(d)
            wr = sz / d.width
            d = d.resize((sz, int(d.height * wr)))
            if rot: d = d.rotate(rot, expand=True)
            tx, ty = pos_opts[pos_k]
            final.paste(d, (int(tx-d.width/2+ox), int(ty-d.height/2+oy)), d)
        
        st.image(final, use_container_width=True)
    except Exception as e:
        st.error("圖片載入失敗，請重新整理")

with col_tools:
    st.markdown("---")
    if mode == "公司團體 (詢價)":
        st.markdown("### 3. 詢價資料")
        with st.container(border=True):
            in_name = st.text_input("單位名稱")
            cc1, cc2 = st.columns(2)
            with cc1: in_contact = st.text_input("聯絡人")
            with cc2: in_phone = st.text_input("電話")
            in_line = st.text_input("LINE ID")
            cq, cn = st.columns([1,2])
            with cq: in_qty = st.number_input("數量", value=20)
            with cn: in_note = st.text_input("備註")
            
            if st.button("📄 生成詢價單", type="primary", use_container_width=True):
                data = {
                    "name": in_name, "contact": in_contact, "phone": in_phone, 
                    "line": in_line, "qty": in_qty, "note": in_note,
                    "series": series, "variant": variant, "promo_code": current_code
                }
                with st.spinner("生成中..."):
                    card = generate_inquiry(final, data)
                    buf = io.BytesIO(); card.save(buf, format="PNG")
                st.download_button("📥 下載圖片", data=buf.getvalue(), file_name=f"Inquiry.png", mime="image/png", use_container_width=True, type="primary")
    else:
        st.markdown(f"#### 建議售價：NT$ {item.get('price', 0)}")
        buf = io.BytesIO(); final.save(buf, format="PNG")
        btn_label = "✨ 下載分潤推廣圖" if st.session_state["user_info"].get("is_ambassador") else "📥 下載設計圖"
        st.download_button(btn_label, data=buf.getvalue(), file_name="Design.png", mime="image/png", use_container_width=True, type="primary")
