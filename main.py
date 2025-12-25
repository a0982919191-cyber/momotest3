import streamlit as st
import io
import os
import requests
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from rembg import remove
import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- 關鍵修改：從 products.py 匯入產品目錄 ---
from products import PRODUCT_CATALOG 

# ==========================================
# 1. 全局設定 & 資料庫連線
# ==========================================
st.set_page_config(page_title="Momo Design Pro", page_icon="💎", layout="wide")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def connect_to_gsheet():
    try:
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
            gc = gspread.authorize(creds)
            return gc.open("momo_db")
        return None
    except: return None

sh = connect_to_gsheet()

if "user_role" not in st.session_state: st.session_state["user_role"] = "guest"
if "user_info" not in st.session_state: st.session_state["user_info"] = {}
if "site_locked" not in st.session_state: st.session_state["site_locked"] = True

# ==========================================
# 2. 字型處理 (智慧防崩潰)
# ==========================================
FONT_SAVE_PATH = "temp_font.ttf" 
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/notosanstc/NotoSansTC-Regular.ttf"

def get_font(size):
    font = None
    if not os.path.exists(FONT_SAVE_PATH) or os.path.getsize(FONT_SAVE_PATH) < 1000000:
        try:
            r = requests.get(FONT_URL, timeout=5)
            if r.status_code == 200:
                with open(FONT_SAVE_PATH, "wb") as f: f.write(r.content)
        except: pass

    try:
        if os.path.exists(FONT_SAVE_PATH):
            font = ImageFont.truetype(FONT_SAVE_PATH, size)
    except:
        try: os.remove(FONT_SAVE_PATH)
        except: pass
    
    if font is None: font = ImageFont.load_default()
    return font

# ==========================================
# 3. 詢價單生成 (底圖套用版)
# ==========================================
def generate_inquiry(img, data):
    w, h = 800, 1200 
    
    # 載入底圖 (如果有 template.png)
    if os.path.exists("template.png"):
        try:
            card = Image.open("template.png").convert("RGB").resize((w, h))
        except:
            card = Image.new("RGB", (w, h), "white")
    else:
        card = Image.new("RGB", (w, h), "white")

    draw = ImageDraw.Draw(card)
    
    # 字型設定
    f_title = get_font(40)
    f_label = get_font(24)
    f_text = get_font(22)
    f_small = get_font(18)
    
    # 貼上衣服圖案
    t_w = 400
    ratio = t_w / img.width
    t_h = int(img.height * ratio)
    res = img.resize((t_w, t_h))
    
    img_x = (w - t_w) // 2
    img_y = 150
    
    # 白底框 (避免底圖干擾)
    draw.rectangle([(img_x-10, img_y-10), (img_x+t_w+10, img_y+t_h+10)], fill="white")
    card.paste(res, (img_x, img_y), res if res.mode=='RGBA' else None)
    
    # 填寫文字
    if not os.path.exists("template.png"):
        draw.rectangle([(0,0), (w, 120)], fill="#2c3e50")
        draw.text((30, 40), "Momo Design 詢價單", fill="white", font=f_title)
    
    draw.text((600, 60), f"日期: {datetime.date.today()}", fill="#333", font=f_small)

    start_y = 650 
    line_height = 50
    
    fields = [
        ("訂購單位", data.get('name')),
        ("聯絡姓名", data.get('contact')),
        ("聯絡電話", data.get('phone')),
        ("LINE ID", data.get('line')),
        ("產品系列", data.get('series')),
        ("產品款式", data.get('variant')),
        ("訂購數量", f"{data.get('qty')} 件"),
        ("備註事項", data.get('note')),
        ("推廣代碼", data.get('promo_code') if data.get('promo_code') != "GUEST" else "無")
    ]
    
    for label, content in fields:
        if not os.path.exists("template.png"):
             draw.line([(50, start_y + 35), (750, start_y + 35)], fill="#ddd", width=1)
        
        draw.text((80, start_y), f"{label}：", fill="#555", font=f_label)
        draw.text((250, start_y), str(content), fill="black", font=f_text)
        start_y += line_height

    return card

# ==========================================
# 4. 資料庫寫入
# ==========================================
def add_member_to_db(name, phone, code, is_amb):
    if sh:
        try:
            sh.worksheet("members").append_row([name, phone, code, "TRUE" if is_amb else "FALSE", str(datetime.date.today())])
            return True
        except: return False
    return False

def add_order_to_db(data):
    if sh:
        try:
            oid = f"ORD-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            sh.worksheet("orders").append_row([oid, data['name'], data['contact'], data['phone'], data['line'], 
                                             f"{data['series']}-{data['variant']}", data['qty'], data['note'], 
                                             data['promo_code'], str(datetime.date.today())])
            return True
        except: return False
    return False

# ==========================================
# 5. 介面 & 密碼鎖
# ==========================================
def check_lock():
    if st.session_state["site_locked"]:
        st.markdown("<br><h2 style='text-align:center;'>🔒 Momo 內部系統</h2>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            if st.text_input("密碼", type="password", label_visibility="collapsed") == "momo2025":
                st.session_state["site_locked"] = False
                st.rerun()
        st.stop()
check_lock()

st.markdown("<style>.stApp{font-family:sans-serif} #MainMenu{visibility:hidden}</style>", unsafe_allow_html=True)

with st.sidebar:
    st.title("👤 會員中心")
    if st.session_state["user_role"] == "guest":
        with st.expander("登入 / 註冊", expanded=True):
            rn = st.text_input("姓名"); rp = st.text_input("電話"); amb = st.checkbox("開啟分潤")
            if st.button("確認", type="primary"):
                if rn and rp:
                    code = f"{rn.upper()}{rp[-3:]}" if amb else "MEMBER"
                    if sh: 
                        with st.spinner("連線中..."):
                            add_member_to_db(rn, rp, code, amb)
                    st.session_state.update({"user_role":"member", "user_info":{"name":rn, "code":code, "is_ambassador":amb}})
                    st.rerun()
    else:
        u = st.session_state["user_info"]
        st.success(f"Hi, {u['name']}")
        if u["is_ambassador"]: st.markdown(f"推廣碼: **`{u['code']}`**")
        if st.button("登出"): st.session_state.update({"user_role":"guest", "user_info":{}}); st.rerun()

st.markdown("#### 🛍️ 選擇模式")
mode = st.radio("mode", ["一般訂製", "公司團體 (詢價)"], horizontal=True, label_visibility="collapsed")
ccode = st.session_state["user_info"].get("code", "GUEST")

c1, c2 = st.columns([1.5, 1])
with c2:
    # --- 這裡開始使用外部匯入的 PRODUCT_CATALOG ---
    s = st.selectbox("系列", list(PRODUCT_CATALOG.keys()))
    v = st.selectbox("款式", list(PRODUCT_CATALOG[s].keys()))
    item = PRODUCT_CATALOG[s][v]
    
    # 讀取位置設定
    pos = item.get("positions", {"正中間":[300, 400]})
    
    uf = st.file_uploader("上傳圖案")
    if uf:
        with st.expander("調整", expanded=True):
            rb = st.toggle("去背"); pk = st.selectbox("位置", list(pos.keys())); sz = st.slider("大小",50,450,180)
            ox = st.slider("X",-60,60,0); oy = st.slider("Y",-60,60,0); rot = st.slider("轉",-180,180,0)
    else: pk,sz,ox,oy,rot,rb = list(pos.keys())[0],150,0,0,0,False

with c1:
    try:
        # 檢查圖片是否存在
        if not os.path.exists(item["image"]):
             st.error(f"⚠️ 找不到圖片：{item['image']}")
             if os.path.exists("assets"):
                 st.caption(f"assets 目錄內容: {os.listdir('assets')}")
             base = Image.new("RGBA", (600, 800), (240, 240, 240))
        else:
             base = Image.open(item["image"]).convert("RGBA")

        final = base.copy()
        if uf:
            d = Image.open(uf).convert("RGBA"); 
            if rb: d = remove(d)
            wr=sz/d.width; d=d.resize((sz,int(d.height*wr))); 
            if rot: d=d.rotate(rot, expand=True)
            tx,ty=pos[pk]; final.paste(d, (int(tx-d.width/2+ox), int(ty-d.height/2+oy)), d)
        st.image(final, use_container_width=True)
    except Exception as e: st.error(f"Error: {e}")

with c2:
    st.divider()
    if mode == "公司團體 (詢價)":
        st.markdown("### 詢價資料")
        inn = st.text_input("單位名稱"); inc = st.text_input("聯絡人"); inp = st.text_input("電話"); inl = st.text_input("LINE")
        inq = st.number_input("數量", value=20); innote = st.text_input("備註")
        if st.button("📄 生成詢價單", type="primary"):
            dt = {"name":inn, "contact":inc, "phone":inp, "line":inl, "qty":inq, "note":innote, "series":s, "variant":v, "promo_code":ccode}
            if sh: 
                with st.spinner("訂單處理中..."): add_order_to_db(dt)
            with st.spinner("生成圖片中..."):
                card = generate_inquiry(final, dt)
                buf = io.BytesIO(); card.save(buf, format="PNG")
            st.download_button("📥 下載", data=buf.getvalue(), file_name="Inquiry.png", mime="image/png")
            if sh: st.success("✅ 訂單已自動傳送至雲端")
    else:
        buf = io.BytesIO(); final.save(buf, format="PNG")
        st.download_button("📥 下載圖", data=buf.getvalue(), file_name="Design.png", mime="image/png")
