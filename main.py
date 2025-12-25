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

# ==========================================
# 1. 產品目錄 (位置數值已全數校正)
# ==========================================
STD_POSITIONS = {
    "正中間": [300, 400], 
    "左胸": [450, 250], 
    "背後大圖": [300, 350]
}

PRODUCT_CATALOG = {
    "品牌聯名系列": {
        "MakeWorld 客製棉T (黑)": {"image": "assets/AG21000_Black.png", "price": 590, "positions": STD_POSITIONS},
        "MakeWorld 客製棉T (白)": {"image": "assets/AG21000_white.png", "price": 590, "positions": STD_POSITIONS},
        "MakeWorld 客製棉T (藍)": {"image": "assets/AG21000_Blue.png", "price": 590, "positions": STD_POSITIONS},
        "MakeWorld 客製棉T (卡其)": {"image": "assets/AG21000_Khaki.png", "price": 590, "positions": STD_POSITIONS},
        "MakeWorld 客製棉T (灰)": {"image": "assets/AG21000_grey.png", "price": 590, "positions": STD_POSITIONS},
    }
}

# ==========================================
# 2. 全局設定 & 資料庫連線
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
# 3. 字型處理 (智慧型防崩潰系統)
# ==========================================
# 這裡我們不使用 assets 裡的字型，改用自動下載的暫存檔，避免您上傳到壞掉的檔案
FONT_SAVE_PATH = "temp_font.ttf" 
FONT_URL = "https://github.com/google/fonts/raw/main/ofl/notosanstc/NotoSansTC-Regular.ttf"

def get_font(size):
    """
    嘗試取得中文字型，如果失敗則使用系統預設 (方塊字)，
    保證永遠不會讓程式崩潰。
    """
    font = None
    
    # 1. 檢查暫存檔是否存在且完整 (大於 1MB)
    if not os.path.exists(FONT_SAVE_PATH) or os.path.getsize(FONT_SAVE_PATH) < 1000000:
        try:
            # 嘗試下載
            r = requests.get(FONT_URL, timeout=5)
            if r.status_code == 200:
                with open(FONT_SAVE_PATH, "wb") as f:
                    f.write(r.content)
        except:
            pass # 下載失敗就略過

    # 2. 嘗試讀取字型
    try:
        if os.path.exists(FONT_SAVE_PATH):
            font = ImageFont.truetype(FONT_SAVE_PATH, size)
    except Exception:
        # 如果檔案壞掉，刪除它以便下次重試
        try: os.remove(FONT_SAVE_PATH)
        except: pass
    
    # 3. 【最後防線】如果上面都失敗，使用系統預設字體
    # 這就是您要求的「內建字體」，雖然中文會變方塊，但至少程式能跑
    if font is None:
        font = ImageFont.load_default()
        
    return font

# ==========================================
# 4. 詢價單生成
# ==========================================
def generate_inquiry(img, data):
    w, h = 800, 1300
    card = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(card)
    
    # 使用安全字型取得器
    f_xl = get_font(40)
    f_l = get_font(30)
    f_m = get_font(24)
    f_s = get_font(20)
    
    draw.rectangle([(0,0), (w, 140)], fill="#2c3e50")
    # 這裡如果是方塊字，代表下載失敗，但至少不會 Error
    draw.text((40, 50), "Momo Design 需求詢價單", fill="white", font=f_xl)
    draw.text((w-250, 60), str(datetime.date.today()), fill="#ccc", font=f_s)
    
    t_w = 400; ratio = t_w/img.width; t_h = int(img.height*ratio)
    res = img.resize((t_w, t_h))
    draw.rectangle([((w-t_w)//2-5, 170-5), ((w-t_w)//2+t_w+5, 170+t_h+5)], fill="#eee")
    card.paste(res, ((w-t_w)//2, 170), res if res.mode=='RGBA' else None)
    
    y = 170 + t_h + 50
    draw.line([(50,y), (750,y)], fill="#ddd", width=2); y += 30
    
    if data.get('promo_code') not in [None, "GUEST"]:
        draw.rectangle([(50, y), (750, y+60)], fill="#fff3cd")
        draw.text((70, y+15), f"★ 分潤代碼：{data.get('promo_code')}", fill="#856404", font=f_l); y += 90
    
    fields = [("詢價單位", data.get('name')), ("聯絡人", data.get('contact')), ("電話", data.get('phone')), ("LINE ID", data.get('line')),
              ("---", "---"), ("系列", data.get('series')), ("款式", data.get('variant')), ("數量", f"{data.get('qty')} 件"), ("備註", data.get('note'))]
    
    for k, v in fields:
        if k == "---":
            y+=15; draw.line([(50,y), (750,y)], fill="#eee", width=1); y+=25; continue
        draw.text((60, y), f"【{k}】", fill="#2c3e50", font=f_m)
        val = str(v) if v else "-"
        for i in range(0, len(val), 22):
            draw.text((250, y), val[i:i+22], fill="#333", font=f_m); y += 40
        y += 10

    draw.rectangle([(0, h-80), (w, h)], fill="#f8f9fa")
    draw.text((200, h-50), "正式報價以業務回傳為主", fill="#999", font=f_s)
    return card

# ==========================================
# 5. 資料庫寫入
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
# 6. 介面 & 密碼鎖
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
    s = st.selectbox("系列", list(PRODUCT_CATALOG.keys()))
    v = st.selectbox("款式", list(PRODUCT_CATALOG[s].keys()))
    item = PRODUCT_CATALOG[s][v]
    
    # 讀取校正後的位置
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
