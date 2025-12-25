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
# 1. 全局設定 (最簡化)
# ==========================================
st.set_page_config(page_title="Momo Design", page_icon="👕", layout="wide")

# 模擬資料庫
@st.cache_resource
def get_database():
    return {"members": []}
db = get_database()

# 狀態初始化
if "user_role" not in st.session_state: st.session_state["user_role"] = "guest"
if "user_info" not in st.session_state: st.session_state["user_info"] = {}
if "site_locked" not in st.session_state: st.session_state["site_locked"] = True

# ==========================================
# 2. 全站密碼鎖
# ==========================================
def check_lock():
    if st.session_state["site_locked"]:
        st.markdown("<br><h2 style='text-align:center;'>🔒 系統鎖定中</h2>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            pwd = st.text_input("輸入密碼", type="password", label_visibility="collapsed")
            if st.button("登入", use_container_width=True):
                if pwd == "momo2025":
                    st.session_state["site_locked"] = False
                    st.rerun()
                else:
                    st.error("密碼錯誤")
        st.stop()

check_lock()

# ==========================================
# 3. 字型處理 (安全防崩潰版)
# ==========================================
FONT_FILE = "NotoSansTC-Regular.ttf"
# 使用 Google Fonts 的穩定連結
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/notosanstc/NotoSansTC-Regular.ttf"

def get_safe_font(size):
    """
    取得字型：優先嘗試下載中文，失敗則回傳預設 (不會崩潰)
    """
    font = None
    
    # 1. 檢查並下載 (如果檔案不存在或太小，就下載)
    if not os.path.exists(FONT_FILE) or os.path.getsize(FONT_FILE) < 1000000:
        try:
            print("正在下載字型...")
            r = requests.get(FONT_URL, timeout=5) # 設定超時，避免卡太久
            if r.status_code == 200:
                with open(FONT_FILE, "wb") as f:
                    f.write(r.content)
        except:
            pass # 下載失敗就算了，不要報錯

    # 2. 嘗試讀取字型檔
    try:
        if os.path.exists(FONT_FILE):
            font = ImageFont.truetype(FONT_FILE, size)
    except Exception:
        # 如果讀取失敗 (例如檔案壞掉)，刪除它以便下次重試
        try: os.remove(FONT_FILE) 
        except: pass
    
    # 3. 如果上面都失敗，使用醜但安全的預設字體
    if font is None:
        font = ImageFont.load_default()
        
    return font

# ==========================================
# 4. CSS 美化
# ==========================================
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; font-family: sans-serif; }
    .block-container { padding-top: 1rem; padding-bottom: 3rem; }
    .member-bar {
        background: white; padding: 12px 20px; border-radius: 10px;
        margin-bottom: 20px; border-left: 6px solid #667eea;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08); font-size: 15px;
    }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 5. 詢價單生成
# ==========================================
def generate_inquiry(img, data):
    w, h = 800, 1300
    card = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(card)
    
    # 取得字型 (絕對不會報錯)
    f_xl = get_safe_font(40)
    f_l = get_safe_font(30)
    f_m = get_safe_font(24)
    f_s = get_safe_font(20)
    
    # 繪製內容
    draw.rectangle([(0,0), (w, 140)], fill="#2c3e50")
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
    
    # 推廣碼
    if data.get('promo_code') and data.get('promo_code') != "GUEST":
        draw.rectangle([(50, y), (750, y+60)], fill="#fff3cd")
        draw.text((70, y+15), f"★ 分潤代碼：{data.get('promo_code')}", fill="#856404", font=f_l)
        y += 90
    
    # 欄位
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
        draw.text((60, y), f"[{k}]", fill="#2c3e50", font=f_m) # 括號避免方塊字太醜
        val = str(v) if v else "-"
        # 簡單換行
        for i in range(0, len(val), 22):
            draw.text((250, y), val[i:i+22], fill="#333", font=f_m)
            y += 40
        y += 10

    draw.rectangle([(0, h-80), (w, h)], fill="#f8f9fa")
    draw.text((200, h-50), "此單據僅供詢價，正式報價以業務回傳為主", fill="#999", font=f_s)
    return card

# ==========================================
# 6. 介面 (去除所有雜項)
# ==========================================
with st.sidebar:
    st.title("👤 會員中心")
    
    if st.session_state["user_role"] == "guest":
        st.info("尚未登入")
        with st.expander("登入 / 註冊推廣大使", expanded=True):
            r_name = st.text_input("姓名")
            r_phone = st.text_input("電話")
            is_amb = st.checkbox("開啟分潤功能")
            if st.button("確認", type="primary", use_container_width=True):
                if r_name and r_phone:
                    code = f"{r_name.upper()}{r_phone[-3:]}" if is_amb else "MEMBER"
                    db["members"].append({"Name":r_name, "Phone":r_phone, "Code":code})
                    st.session_state["user_role"] = "member"
                    st.session_state["user_info"] = {"name":r_name, "code":code, "is_ambassador":is_amb}
                    st.rerun()
    else:
        u = st.session_state["user_info"]
        st.success(f"Hi, {u['name']}")
        if u["is_ambassador"]: st.markdown(f"推廣碼: **`{u['code']}`**")
        if st.button("登出", use_container_width=True):
            st.session_state["user_role"] = "guest"
            st.session_state["user_info"] = {}
            st.rerun()

# 主畫面
st.markdown("#### 🛍️ 選擇模式")
mode = st.radio("mode", ["一般訂製", "公司團體 (詢價)"], horizontal=True, label_visibility="collapsed")
current_code = st.session_state["user_info"].get("code", "GUEST")

col_pre, col_tools = st.columns([1.5, 1], gap="medium")

with col_tools:
    c1, c2 = st.columns(2)
    with c1: series = st.selectbox("系列", list(PRODUCT_CATALOG.keys()))
    with c2: variant = st.selectbox("款式", list(PRODUCT_CATALOG[series].keys()))
    item = PRODUCT_CATALOG[series][variant]
    pos = item.get("positions", {"中":[150,150]})
    
    up_file = st.file_uploader("上傳圖案", type=["png","jpg","jpeg"])
    if up_file:
        with st.expander("調整", expanded=True):
            rm_bg = st.toggle("AI 去背")
            pos_k = st.selectbox("位置", list(pos.keys()))
            sz = st.slider("大小", 50, 450, 180)
            ox = st.slider("左右", -60, 60, 0)
            oy = st.slider("上下", -60, 60, 0)
            rot = st.slider("旋轉", -180, 180, 0)
    else:
        pos_k, sz, ox, oy, rot, rm_bg = list(pos.keys())[0], 150, 0, 0, 0, False

with col_pre:
    try:
        base = Image.open(item["image"]).convert("RGBA")
        final = base.copy()
        if up_file:
            d = Image.open(up_file).convert("RGBA")
            if rm_bg: d = remove(d)
            wr = sz / d.width
            d = d.resize((sz, int(d.height * wr)))
            if rot: d = d.rotate(rot, expand=True)
            tx, ty = pos[pos_k]
            final.paste(d, (int(tx-d.width/2+ox), int(ty-d.height/2+oy)), d)
        st.image(final, use_container_width=True)
    except: st.error("圖片載入失敗")

with col_tools:
    st.markdown("---")
    if mode == "公司團體 (詢價)":
        st.markdown("### 詢價資料")
        with st.container(border=True):
            in_name = st.text_input("單位名稱")
            in_contact = st.text_input("聯絡人")
            in_phone = st.text_input("電話")
            in_line = st.text_input("LINE ID")
            in_qty = st.number_input("數量", value=20)
            in_note = st.text_input("備註")
            
            if st.button("📄 生成詢價單", type="primary", use_container_width=True):
                data = {
                    "name": in_name, "contact": in_contact, "phone": in_phone, 
                    "line": in_line, "qty": in_qty, "note": in_note,
                    "series": series, "variant": variant, "promo_code": current_code
                }
                with st.spinner("生成中..."):
                    card = generate_inquiry(final, data)
                    buf = io.BytesIO(); card.save(buf, format="PNG")
                st.download_button("📥 下載圖片", data=buf.getvalue(), file_name="Inquiry.png", mime="image/png", use_container_width=True)
    else:
        st.markdown(f"#### 建議售價：NT$ {item.get('price', 0)}")
        buf = io.BytesIO(); final.save(buf, format="PNG")
        label = "✨ 下載分潤圖" if st.session_state["user_info"].get("is_ambassador") else "📥 下載設計圖"
        st.download_button(label, data=buf.getvalue(), file_name="Design.png", mime="image/png", use_container_width=True)
