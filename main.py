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
# 0. 產品目錄與設定 (AG21000 重磅棉T)
# ==========================================
st.set_page_config(page_title="興彰 x 默默｜線上設計估價", page_icon="👕", layout="wide")

PRODUCT_CATALOG = {
    "團體服系列": {
        "AG21000 重磅棉T": {
            "name": "AG21000 重磅棉T",
            "colors": ["白 (White)", "黑 (Black)", "丈青 (Navy)"],
            "color_map": {
                "白 (White)": "White",
                "黑 (Black)": "Black",
                "丈青 (Navy)": "Navy"
            },
            "image_base": "AG21000",
            # --- 正面印刷位置 ---
            "pos_front": {
                "正中間 (Center)": {"coords": (300, 400)},
                "左胸 (Left Chest)": {"coords": (420, 280)},
                "右胸 (Right Chest)": {"coords": (180, 280)},
                "左臂 (Left Sleeve)": {"coords": (520, 320)},
                "右臂 (Right Sleeve)": {"coords": (80, 320)}
            },
            # --- 背面印刷位置 ---
            "pos_back": {
                "背後正中 (Center)": {"coords": (300, 350)},
                "左臂-後 (L.Sleeve Back)": {"coords": (520, 320)},
                "右臂-後 (R.Sleeve Back)": {"coords": (80, 320)}
            }
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

# 初始化 Session State
if "designs" not in st.session_state: st.session_state["designs"] = {} 
if "site_locked" not in st.session_state: st.session_state["site_locked"] = True 

# ==========================================
# 1. 價格計算引擎 (Pricing Engine)
# ==========================================
def calculate_unit_price(qty, is_double_sided):
    """
    根據 AG21000 價格表計算單價 (包含 20 件起訂規則)
    """
    if qty < 20:
        return 0 # 未達起訂量
    
    # 定義價格區間 (單面價格, 雙面價格)
    # 20件起訂：單面410 / 雙面560
    if 20 <= qty < 30:
        price_s, price_d = 410, 560
    elif 30 <= qty < 50:
        price_s, price_d = 380, 530  # 依照圖片 -30
    elif 50 <= qty < 100:
        price_s, price_d = 360, 510
    elif 100 <= qty < 300:
        price_s, price_d = 340, 490
    else: # 300件以上
        price_s, price_d = 320, 470
        
    return price_d if is_double_sided else price_s

# ==========================================
# 2. 詢價單生成 (含正反面雙圖)
# ==========================================
def generate_inquiry_image(img_front, img_back, data, design_list_text, unit_price):
    # 畫布變大，左右並排
    w, h = 1200, 1000 
    card = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(card)
    
    try: font_L = ImageFont.truetype("arial.ttf", 36)
    except: font_L = ImageFont.load_default()
    try: font_M = ImageFont.truetype("arial.ttf", 28)
    except: font_M = ImageFont.load_default()
    
    # --- 貼上衣服圖 (左正、右反) ---
    t_w = 400
    ratio = t_w / img_front.width
    t_h = int(img_front.height * ratio)
    
    res_f = img_front.resize((t_w, t_h))
    res_b = img_back.resize((t_w, t_h))
    
    # 定位 (左邊放正面，右邊放背面)
    card.paste(res_f, (100, 150), res_f if res_f.mode=='RGBA' else None)
    card.paste(res_b, (600, 150), res_b if res_b.mode=='RGBA' else None)
    
    # 標示文字
    draw.text((250, 100), "Front View", fill="#555", font=font_M)
    draw.text((750, 100), "Back View", fill="#555", font=font_M)

    # --- 填寫訂單資料 (下方區域) ---
    start_y = 150 + t_h + 50
    col1_x = 100
    col2_x = 600
    
    # 標題
    draw.text((col1_x, 40), f"Momo Design Quote - {datetime.date.today()}", fill="black", font=font_L)

    # 左欄：客戶與產品
    fields_L = [
        f"Client: {data.get('name')}",
        f"Contact: {data.get('phone')} / {data.get('line')}",
        "--------------------------------",
        f"Product: {data.get('series')}",
        f"Style: {data.get('variant')}",
        f"Total Qty: {data.get('qty')} pcs",
        f"Est. Unit Price: NT$ {unit_price}",
        f"Est. Total: NT$ {unit_price * data.get('qty'):,}", 
    ]
    
    curr_y = start_y
    for line in fields_L:
        draw.text((col1_x, curr_y), line, fill="#333", font=font_M)
        curr_y += 40

    # 右欄：尺寸與印刷
    fields_R = [
        "Size Breakdown:",
        f"{data.get('size_breakdown')}",
        "--------------------------------",
        "Printing Locations:",
    ]
    fields_R.extend(design_list_text)
    
    curr_y = start_y
    for line in fields_R:
        draw.text((col2_x, curr_y), line, fill="#333", font=font_M)
        curr_y += 40
        
    # 底部折扣碼
    draw.rectangle([(0, h-80), (w, h)], fill="#ff4b4b")
    draw.text((300, h-60), "Sent to LINE @727jxovv to confirm order & get discount!", fill="white", font=font_M)
        
    return card

def add_order_to_db(data):
    if sh:
        try:
            oid = f"ORD-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            sh.worksheet("orders").append_row([oid, data['name'], data['contact'], data['phone'], data['line'], 
                                             f"{data['series']}-{data['variant']}", data['qty'], 
                                             f"{data['size_breakdown']} | ${data['price']}", 
                                             data['promo_code'], str(datetime.date.today())])
            return True
        except: return False
    return False

# ==========================================
# 3. 密碼鎖 (隱藏提示)
# ==========================================
def check_lock():
    if st.session_state["site_locked"]:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<h2 style='text-align:center;'>🔒 網站維護中</h2>", unsafe_allow_html=True)
            st.caption("請輸入權限密碼進入")
            pwd = st.text_input("輸入密碼", type="password", label_visibility="collapsed")
            if st.button("解鎖登入", type="primary", use_container_width=True):
                if pwd == "momo2025": 
                    st.session_state["site_locked"] = False
                    st.rerun()
                else:
                    st.error("密碼錯誤")
        st.stop() 
check_lock()

# ==========================================
# 4. 主介面設計
# ==========================================
st.markdown("""
<style>
    .stApp {background-color: #F5F5F7;}
    div[data-testid="stSidebar"] {background-color: #FFFFFF;}
    h1, h2, h3 {font-family: 'Helvetica', sans-serif;}
</style>
""", unsafe_allow_html=True)

# --- 側邊欄 ---
with st.sidebar:
    if os.path.exists("owner.jpg"):
        st.image("owner.jpg", caption="阿默｜興彰企業")
    else:
        st.info("💡 請上傳 owner.jpg")
        
    st.markdown("### 👨‍🔧 關於我們")
    st.info("**興彰企業 x 默默文創**\n📍 彰化市中山路一段556巷23號之7")
    st.success("🆔 **LINE ID: @727jxovv**")
    
    with st.expander("🛠 檔案檢查員"):
        st.write("雲端檔案列表：")
        st.code(os.listdir("."))
        if st.button("重新整理"): st.rerun()
    
    if st.button("🔒 鎖定網站"):
        st.session_state["site_locked"] = True
        st.rerun()

# --- 主畫面 ---
st.title("📝 線上設計 & 自助估價")
st.caption("🚀 AG21000 重磅棉T｜興彰企業 x 默默文創")

# --- 1. 選擇產品與尺寸 ---
c1, c2 = st.columns([1.5, 1])

with c2:
    st.markdown("### 1. 選擇產品 & 數量")
    series_list = list(PRODUCT_CATALOG.keys())
    s = st.selectbox("系列", series_list)
    v = st.selectbox("款式", list(PRODUCT_CATALOG[s].keys()))
    
    item = PRODUCT_CATALOG.get(s, {}).get(v, {})

    # 顏色選擇
    color_options = item.get("colors", ["預設"]) 
    selected_color_name = st.selectbox("顏色", color_options)
    color_code = item.get("color_map", {}).get(selected_color_name, "")
    
    # 圖片路徑邏輯 (智慧偵測 JPG/PNG)
    base_name = item.get("image_base", "")
    img_url_front = ""
    img_url_back = ""
    
    if base_name and color_code:
        f_try = f"{base_name}_{color_code}_front"
        b_try = f"{base_name}_{color_code}_back"
        if os.path.exists(f"{f_try}.jpg"): img_url_front = f"{f_try}.jpg"
        elif os.path.exists(f"{f_try}.png"): img_url_front = f"{f_try}.png"
        if os.path.exists(f"{b_try}.jpg"): img_url_back = f"{b_try}.jpg"
        elif os.path.exists(f"{b_try}.png"): img_url_back = f"{b_try}.png"

    # --- 尺寸表與輸入 ---
    st.markdown("---")
    with st.expander("📏 查看尺寸表 (Size Chart)"):
        if os.path.exists("size_chart.jpg"): st.image("size_chart.jpg")
        elif os.path.exists("size_chart.png"): st.image("size_chart.png")
        else: st.warning("請上傳尺寸表 size_chart.jpg")

    # 尺寸輸入 (S-5XL 順序)
    sizes = ["S", "M", "L", "XL", "2XL", "3XL", "4XL", "5XL"]
    size_inputs = {}
    st.caption("請輸入各尺寸件數 (最低訂購 20 件)：")
    
    cols_size = st.columns(4)
    for i, size in enumerate(sizes):
        with cols_size[i % 4]:
            size_inputs[size] = st.number_input(f"{size}", min_value=0, step=1, key=f"qty_{size}")
    
    total_qty = sum(size_inputs.values())
    
    # --- 2. 創意設計區 (切換正反面) ---
    st.markdown("### 2. 創意設計 & 上傳")
    
    # Tab 切換
    tab_f, tab_b = st.tabs(["👕 正面設計", "🔄 背面設計"])
    
    with tab_f:
        st.info("可編輯：正中間、左胸、右胸、左臂、右臂")
        pk_f = st.selectbox("正面位置", list(item.get("pos_front", {}).keys()), key="sel_f")
        design_key_f = f"front_{pk_f}"
        uf_f = st.file_uploader(f"上傳正面圖片 ({pk_f})", type=["png","jpg"], key=f"u_{design_key_f}")
        if uf_f:
            img = Image.open(uf_f).convert("RGBA")
            st.session_state["designs"][design_key_f] = st.session_state["designs"].get(design_key_f, {"img": img, "rb": False, "sz": 150, "rot": 0, "ox": 0, "oy": 0})
            st.session_state["designs"][design_key_f]["img"] = img

    with tab_b:
        st.info("可編輯：背後正中、左臂(後)、右臂(後)")
        pk_b = st.selectbox("背面位置", list(item.get("pos_back", {}).keys()), key="sel_b")
        design_key_b = f"back_{pk_b}"
        uf_b = st.file_uploader(f"上傳背面圖片 ({pk_b})", type=["png","jpg"], key=f"u_{design_key_b}")
        if uf_b:
            img = Image.open(uf_b).convert("RGBA")
            st.session_state["designs"][design_key_b] = st.session_state["designs"].get(design_key_b, {"img": img, "rb": False, "sz": 150, "rot": 0, "ox": 0, "oy": 0})
            st.session_state["designs"][design_key_b]["img"] = img

    # --- 判斷單雙面與價格 ---
    has_front_design = any(k.startswith("front_") for k in st.session_state["designs"].keys())
    has_back_design = any(k.startswith("back_") for k in st.session_state["designs"].keys())
    is_double_sided = has_front_design and has_back_design
    
    # 計算單價
    unit_price = calculate_unit_price(total_qty, is_double_sided)
    total_price = unit_price * total_qty

# --- 左欄：即時預覽 (含切換功能) ---
with c1:
    view_side = st.radio("👁️ 預覽視角", ["正面 Front", "背面 Back"], horizontal=True, label_visibility="collapsed")
    current_side = "front" if "正面" in view_side else "back"

    st.markdown(f"#### 預覽: {v} ({'黑色' if 'Black' in color_code else color_code})")
    
    target_img_path = img_url_front if current_side == "front" else img_url_back
    
    # 產生底圖
    if target_img_path and os.path.exists(target_img_path):
        base = Image.open(target_img_path).convert("RGBA")
    else:
        base = Image.new("RGBA", (600, 800), (240, 240, 240))
        draw_tmp = ImageDraw.Draw(base)
        draw_tmp.text((50, 300), f"No Image: {target_img_path}", fill="red")

    final = base.copy()
    
    # 貼上設計圖
    for d_key, d_val in st.session_state["designs"].items():
        d_side, d_pos_name = d_key.split("_", 1)
        if d_side == current_side:
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
    
    # 顯示該面已上傳的圖片調整器
    st.markdown("---")
    st.caption(f"調整 {current_side} 的設計：")
    for d_key in list(st.session_state["designs"].keys()):
        if d_key.startswith(current_side + "_"):
            d_val = st.session_state["designs"][d_key]
            with st.expander(f"🔧 {d_key.split('_')[1]}", expanded=False):
                d_val["sz"] = st.slider("大小", 50, 400, d_val["sz"], key=f"sz_{d_key}")
                d_val["rot"] = st.slider("旋轉", -180, 180, d_val["rot"], key=f"rot_{d_key}")
                c1a, c2a = st.columns(2)
                with c1a: d_val["ox"] = st.number_input("X軸", -100, 100, d_val["ox"], key=f"ox_{d_key}")
                with c2a: d_val["oy"] = st.number_input("Y軸", -100, 100, d_val["oy"], key=f"oy_{d_key}")
                if st.button("🗑️ 刪除", key=f"del_{d_key}"):
                    del st.session_state["designs"][d_key]
                    st.rerun()

# --- 下方：報價與結帳區 ---
st.divider()
st.markdown("### 3. 興彰嚴選報價 & 服務承諾")

if total_qty < 20:
    st.warning(f"⚠️ 為確保製作印刷品質，最低訂製量為 20 件 (目前: {total_qty} 件)。")
else:
    col_price, col_value = st.columns([1, 1.5])
    
    with col_price:
        side_text = "雙面設計" if is_double_sided else "單面設計"
        st.markdown(f"""
        <div style="background-color: #f8f9fa; border: 1px solid #ddd; padding: 20px; border-radius: 10px; text-align: center;">
            <p style="color: #666; font-size: 14px; margin-bottom: 5px;">預估單價 ({side_text})</p>
            <h2 style="color: #2c3e50; margin: 0;">NT$ {unit_price}</h2>
            <p style="color: #888; font-size: 12px; margin-top: 5px;">x {total_qty} 件</p>
            <hr style="margin: 10px 0;">
            <h3 style="color: #d63031; margin: 0;">總計：NT$ {total_price:,}</h3>
        </div>
        """, unsafe_allow_html=True)
        
    with col_value:
        st.markdown("#### ✅ 報價包含以下職人服務：")
        st.markdown("""
        - 🛡️ **品質保證**：使用 AG21000 重磅棉，縮水率控制在 3% 內。
        - 🎨 **圖檔健檢**：設計師親自檢查解析度，確保印刷清晰。
        - 📦 **獨立包裝**：每件衣服皆含透明防塵袋包裝。
        - 🚚 **安心出貨**：彰化在地工廠直營，售後有保障。
        """)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.checkbox("我接受此品質與報價，填寫聯絡資料 (下一步)", value=False):
        with st.container():
            st.info("💡 **阿默小提醒**：送出後不會立刻扣款，我們會有專人與您最後確認圖檔細節。")
            col_sub1, col_sub2 = st.columns(2)
            with col_sub1:
                c_name = st.text_input("您的稱呼 / 單位名稱")
                c_line = st.text_input("LINE ID (重要！傳送圖檔用)")
            with col_sub2:
                c_phone = st.text_input("手機號碼")
                c_note = st.text_input("特殊需求備註 (例如: 急單、特殊包裝)")

            if st.button("🚀 生成正式報價單 (鎖定優惠)", type="primary", use_container_width=True):
                if not c_name or not c_line:
                    st.error("請填寫稱呼與 LINE ID 以便我們為您保留產能！")
                else:
                    design_list = [f"• {k}" for k in st.session_state["designs"].keys()]
                    size_str_list = [f"{k}*{v}" for k, v in size_inputs.items() if v > 0]
                    size_breakdown = ", ".join(size_str_list)
                    
                    dt = {
                        "name": c_name, "contact": c_name, "phone": c_phone, "line": c_line,
                        "qty": total_qty, "size_breakdown": size_breakdown,
                        "series": s, "variant": v, "price": unit_price, "promo_code": "ProQuote"
                    }
                    
                    if sh: add_order_to_db(dt)
                    
                    # 生成雙面預覽圖 (合成背面)
                    base_b = Image.open(img_url_back).convert("RGBA") if img_url_back and os.path.exists(img_url_back) else Image.new("RGBA", (600,800), (240,240,240))
                    final_back = base_b.copy()
                    for d_key, d_val in st.session_state["designs"].items():
                        if d_key.startswith("back_"):
                            pk = d_key.split("_", 1)[1]
                            pos = item.get("pos_back", {}).get(pk)
                            if pos:
                                tx, ty = pos["coords"]
                                pi = d_val["img"].copy()
                                if d_val["rb"]: pi = remove(pi)
                                wr = d_val["sz"]/pi.width
                                pi = pi.resize((d_val["sz"], int(pi.height*wr)))
                                if d_val["rot"]!=0: pi=pi.rotate(d_val["rot"], expand=True)
                                final_back.paste(pi, (int(tx-pi.width/2+d_val["ox"]), int(ty-pi.height/2+d_val["oy"])), pi)

                    receipt_img = generate_inquiry_image(final.convert("RGB"), final_back.convert("RGB"), dt, design_list, unit_price)
                    
                    st.success("✅ 正式報價單已生成！")
                    st.image(receipt_img, caption="請長按儲存圖片，並傳給阿默 LINE: @727jxovv")
                    st.link_button("👉 點此開啟 LINE 進行圖檔確認", "https://line.me/ti/p/~@727jxovv")
