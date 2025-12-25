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
# 1. 全局設定 & 產品目錄讀取
# ==========================================
st.set_page_config(page_title="興彰 x 默默｜線上設計估價", page_icon="👕", layout="wide")

# --- 嘗試讀取您原本的 products.py ---
try:
    from products import PRODUCT_CATALOG
except ImportError:
    # 萬一讀不到檔案，使用這個備用目錄 (避免報錯)
    # 這裡的結構已經統一，避免 KeyError
    st.warning("⚠️ 找不到 products.py，目前顯示測試資料。請確認檔案是否上傳。")
    PRODUCT_CATALOG = {
        "團體服系列": {
            "吸濕排汗 T-shirt": {
                "name": "吸濕排汗 T-shirt",
                "images": {"front": "https://placehold.co/600x800/EEE/31343C.png?text=Front+View", "back": "https://placehold.co/600x800/EEE/31343C.png?text=Back+View"},
                "pos_front": {"左胸 (Logo)": {"coords": (400, 250)}, "正中間 (大圖)": {"coords": (300, 400)}},
                "pos_back": {"背後大圖": {"coords": (300, 300)}}
            }
        }
    }

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

# 初始化狀態
if "user_role" not in st.session_state: st.session_state["user_role"] = "guest"
if "user_info" not in st.session_state: st.session_state["user_info"] = {}
if "designs" not in st.session_state: st.session_state["designs"] = {} 
if "site_locked" not in st.session_state: st.session_state["site_locked"] = True # 預設上鎖

# ==========================================
# 2. 密碼鎖定功能 (已隱藏提示)
# ==========================================
def check_lock():
    if st.session_state["site_locked"]:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<h2 style='text-align:center;'>🔒 網站維護中</h2>", unsafe_allow_html=True)
            # 這裡已經把 (預設: momo2025) 刪除了
            st.caption("目前網站進行內部調整，請輸入密碼進入")
            pwd = st.text_input("輸入密碼", type="password", label_visibility="collapsed")
            if st.button("解鎖登入", type="primary", use_container_width=True):
                # 這裡設定您的密碼
                if pwd == "momo2025": 
                    st.session_state["site_locked"] = False
                    st.rerun()
                else:
                    st.error("密碼錯誤")
        st.stop() 

# 執行檢查
check_lock()

# ==========================================
# 3. 詢價單生成 (圖片版)
# ==========================================
def generate_inquiry_image(base_img_front, data, design_list_text):
    w, h = 800, 1200
    card = Image.new("RGB", (w, h), "white")
    
    draw = ImageDraw.Draw(card)
    try: font = ImageFont.truetype("arial.ttf", 24)
    except: font = ImageFont.load_default()
    
    # 貼上正面合成圖
    t_w = 400; ratio = t_w/base_img_front.width; t_h = int(base_img_front.height*ratio)
    res = base_img_front.resize((t_w, t_h))
    card.paste(res, ((w-t_w)//2, 50), res if res.mode=='RGBA' else None)
    
    # 填寫資料
    start_y = 550
    fields = [
        f"Momo Design Quote - {datetime.date.today()}",
        "--------------------------------",
        f"Client: {data.get('name')} / {data.get('contact')}",
        f"Product: {data.get('series')} - {data.get('variant')}",
        f"Qty: {data.get('qty')} pcs",
        "--------------------------------",
        "Printing Details:",
    ]
    fields.extend(design_list_text)
    
    fields.append("--------------------------------")
    fields.append("!!! DISCOUNT ALERT !!!")
    fields.append("Send this image to LINE: @727jxovv")
    fields.append("To get 5% OFF (95折) immediately!")
    
    for line in fields:
        draw.text((100, start_y), line, fill="#333", font=font)
        start_y += 35
        
    return card

# ==========================================
# 4. 資料庫寫入函式
# ==========================================
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
# 5. 介面設計 - 阿默店面裝修
# ==========================================

# --- CSS 美化 ---
st.markdown("""
<style>
    .stApp {background-color: #F5F5F7;}
    div[data-testid="stSidebar"] {background-color: #FFFFFF;}
    h1, h2, h3 {font-family: 'Helvetica', sans-serif;}
</style>
""", unsafe_allow_html=True)

# --- 側邊欄：阿默的櫃台 ---
with st.sidebar:
    # 這裡放您的職人照片
    st.image("https://images.unsplash.com/photo-1556740738-b6a63e27c4df?w=300", caption="阿默｜興彰企業") 
    
    st.markdown("### 👨‍🔧 關於我們")
    st.info("""
    **興彰企業 x 默默文創**
    📍 彰化市中山路一段556巷23號之7
    專做：團體服 / 班系服 / 禮品
    """)
    
    st.markdown("---")
    st.success("🆔 **LINE ID: @727jxovv**")
    
    if st.button("🔒 鎖定網站"):
        st.session_state["site_locked"] = True
        st.rerun()

# --- 主畫面 ---
st.title("📝 線上設計 & 自助估價")
st.caption("🚀 免等業務，30秒預覽你的設計｜興彰企業 x 默默文創")

mode = st.radio("您是？", ["一般訪客 (快速估價)", "公司團體 (詳細訂製)"], horizontal=True)
ccode = st.session_state["user_info"].get("code", "THREADS_GUEST")

c1, c2 = st.columns([1.5, 1])

# --- 右欄：控制台 ---
with c2:
    st.markdown("### 1. 選擇產品")
    series_list = list(PRODUCT_CATALOG.keys())
    s = st.selectbox("系列", series_list)
    v = st.selectbox("款式", list(PRODUCT_CATALOG[s].keys()))
    
    # 取得產品資料 (加入防呆機制，避免 KeyError)
    item = PRODUCT_CATALOG[s][v]
    
    st.markdown("---")
    st.markdown("### 2. 創意設計")
    
    tab_f, tab_b = st.tabs(["👕 正面", "🔄 背面"])
    
    # 設計邏輯
    current_side = "front"
    # 防呆：如果資料裡沒寫 pos_front，就給一個空字典，這樣程式不會當掉
    current_positions = item.get("pos_front", {})
    
    with tab_f:
        current_side = "front"
        current_positions = item.get("pos_front", {})
        if not current_positions:
            st.info("此產品正面無可編輯位置")
        else:
            st.caption("點選下方位置上傳 Logo")
        
    with tab_b:
        current_side = "back"
        current_positions = item.get("pos_back", {})
        if not current_positions:
            st.info("此產品背面無可編輯位置")
        else:
            st.caption("支援背後大圖與領標")

    # 只有當該面有位置設定時，才顯示上傳介面
    if current_positions:
        pk = st.selectbox("印刷位置", list(current_positions.keys()))
        design_key = f"{current_side}_{pk}"
        
        uf = st.file_uploader(f"上傳圖片到: {pk}", type=["png", "jpg", "jpeg"], key=f"uploader_{design_key}")
        
        if uf:
            img = Image.open(uf).convert("RGBA")
            st.session_state["designs"][design_key] = st.session_state["designs"].get(design_key, {"img": img, "rb": False, "sz": 150, "rot": 0, "ox": 0, "oy": 0})
            st.session_state["designs"][design_key]["img"] = img 
            
        if design_key in st.session_state["designs"]:
            d_data = st.session_state["designs"][design_key]
            with st.expander("🛠 調整圖片參數", expanded=True):
                d_data["rb"] = st.checkbox("AI 去背", value=d_data["rb"], key=f"rb_{design_key}")
                d_data["sz"] = st.slider("大小缩放", 50, 400, d_data["sz"], key=f"sz_{design_key}")
                d_data["rot"] = st.slider("旋轉角度", -180, 180, d_data["rot"], key=f"rot_{design_key}")
                col_adj1, col_adj2 = st.columns(2)
                with col_adj1: d_data["ox"] = st.number_input("↔ 左右", -100, 100, d_data["ox"], key=f"ox_{design_key}")
                with col_adj2: d_data["oy"] = st.number_input("↕ 上下", -100, 100, d_data["oy"], key=f"oy_{design_key}")
                
                if st.button("🗑️ 清除此圖", key=f"del_{design_key}"):
                    del st.session_state["designs"][design_key]
                    st.rerun()

# --- 左欄：即時預覽 ---
with c1:
    st.markdown(f"#### 👁️ 預覽: {v} ({'正面' if current_side=='front' else '背面'})")
    try:
        # 防呆：確保 images key 存在
        img_dict = item.get("images", {})
        img_url = img_dict.get(current_side, "")
        
        if not img_url:
            st.warning("⚠️ 此面無預覽圖")
            base = Image.new("RGBA", (600, 800), (240, 240, 240))
        else:
            if os.path.exists(img_url): 
                base = Image.open(img_url).convert("RGBA")
            elif img_url.startswith("http"): 
                response = requests.get(img_url, stream=True)
                base = Image.open(response.raw).convert("RGBA")
            else:
                base = Image.new("RGBA", (600, 800), (240, 240, 240))
                st.warning(f"找不到圖片: {img_url}")

        final = base.copy()
        
        # 合成所有圖層
        for d_key, d_val in st.session_state["designs"].items():
            d_side, d_pos_name = d_key.split("_", 1)
            
            if d_side == current_side:
                # 取得該面位置設定
                pos_source = item.get("pos_front", {}) if current_side == "front" else item.get("pos_back", {})
                pos_config = pos_source.get(d_pos_name)
                
                if pos_config:
                    tx, ty = pos_config["coords"]
                    paste_img = d_val["img"].copy()
                    if d_val["rb"]: paste_img = remove(paste_img) 
                    
                    wr = d_val["sz"] / paste_img.width
                    paste_img = paste_img.resize((d_val["sz"], int(paste_img.height * wr)))
                    if d_val["rot"] != 0: paste_img = paste_img.rotate(d_val["rot"], expand=True)
                    
                    final_x = int(tx - paste_img.width/2 + d_val["ox"])
                    final_y = int(ty - paste_img.height/2 + d_val["oy"])
                    
                    final.paste(paste_img, (final_x, final_y), paste_img)

        st.image(final, use_container_width=True)

    except Exception as e:
        st.error(f"圖片載入錯誤: {e}")

# --- 下方送出區 ---
st.divider()
st.markdown("### 3. 完成與估價")

with st.container():
    col_submit1, col_submit2 = st.columns([1, 1])
    
    with col_submit1:
        inn = st.text_input("您的稱呼 / 單位名稱")
        inq = st.number_input("預計數量", value=30)
    
    with col_submit2:
        st.info("💡 **阿默小提醒**：數量滿 30 件免版費，滿 100 件再打折！")
        
        if st.button("🚀 生成詢價單 (領取 95 折)", type="primary", use_container_width=True):
            design_list = [f"• {k}" for k in st.session_state["designs"].keys()]
            
            dt = {"name": inn, "contact": inn, "phone": "Online", "line": "Online", 
                  "qty": inq, "note": "Threads Lead", "series": s, "variant": v, "promo_code": ccode}
            
            if sh: add_order_to_db(dt)
            
            receipt_img = generate_inquiry_image(final.convert("RGB"), dt, design_list)
            
            st.success("✅ 詢價單已生成！請長按下方圖片儲存，並傳給阿默。")
            st.image(receipt_img, caption="請截圖此畫面傳 LINE: @727jxovv")
            st.link_button("👉 點此開啟 LINE 傳送截圖", "https://line.me/ti/p/~@727jxovv")
