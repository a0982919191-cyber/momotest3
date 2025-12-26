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

# --- 從外部檔案匯入產品資料 ---
try:
    from products import PRODUCT_CATALOG
except ImportError:
    st.error("❌ Critical Error: products.py not found.")
    PRODUCT_CATALOG = {} 

# ==========================================
# 0. 設定與全域變數
# ==========================================
st.set_page_config(page_title="Hsing Chang x Momo | Design Quote", page_icon="👕", layout="wide")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
ASSETS_DIR = "assets"

# 袖子對應表
SLEEVE_MAPPING = {
    "左臂 (Left Sleeve)": "左臂-後 (L.Sleeve Back)",
    "右臂 (Right Sleeve)": "右臂-後 (R.Sleeve Back)"
}

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

# 初始化 Session State (已移除 site_locked)
if "designs" not in st.session_state: st.session_state["designs"] = {} 
if "uploader_keys" not in st.session_state: st.session_state["uploader_keys"] = {}

# ==========================================
# 核心加速引擎：圖片處理快取
# ==========================================
@st.cache_data(show_spinner=False)
def process_user_image(uploaded_file_bytes, apply_rb):
    img = Image.open(io.BytesIO(uploaded_file_bytes)).convert("RGBA")
    max_width = 1200
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height))
    
    if apply_rb:
        img = remove(img)
    return img

# ==========================================
# 1. 價格計算引擎
# ==========================================
def calculate_unit_price(qty, is_double_sided):
    if qty < 20: return 0 
    price_s, price_d = 410, 560
    if 30 <= qty < 50:
        price_s, price_d = 380, 530 
    elif 50 <= qty < 100:
        price_s, price_d = 360, 510
    elif 100 <= qty < 300:
        price_s, price_d = 340, 490
    elif qty >= 300:
        price_s, price_d = 320, 470
    return price_d if is_double_sided else price_s

# ==========================================
# 2. 詢價單生成 (英文專業版)
# ==========================================
def generate_inquiry_image(img_front, img_back, data, design_list_text, unit_price):
    w, h = 1200, 1100 
    card = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(card)
    
    font_path = "NotoSansTC-Regular.ttf"
    if not os.path.exists(font_path):
        font_path = os.path.join(ASSETS_DIR, "NotoSansTC-Regular.ttf")
    
    try:
        font_Title = ImageFont.truetype(font_path, 48) if os.path.exists(font_path) else ImageFont.load_default()
        font_L = ImageFont.truetype(font_path, 32) if os.path.exists(font_path) else ImageFont.load_default()
        font_M = ImageFont.truetype(font_path, 24) if os.path.exists(font_path) else ImageFont.load_default()
        font_S = ImageFont.truetype(font_path, 20) if os.path.exists(font_path) else ImageFont.load_default()
    except:
        font_Title = ImageFont.load_default()
        font_L = ImageFont.load_default()
        font_M = ImageFont.load_default()
        font_S = ImageFont.load_default()

    # --- Header ---
    draw.rectangle([(0, 0), (w, 120)], fill="#2c3e50")
    draw.text((50, 35), "HSINN ZHANG x MOMO | PROFESSIONAL ESTIMATE", fill="white", font=font_Title)
    draw.text((w - 350, 45), f"Date: {datetime.date.today()}", fill="#ecf0f1", font=font_L)

    # --- Images ---
    t_w = 420
    ratio = t_w / img_front.width
    t_h = int(img_front.height * ratio)
    
    res_f = img_front.resize((t_w, t_h))
    res_b = img_back.resize((t_w, t_h))
    
    y_img = 150
    x_f = 120
    x_b = 660
    
    card.paste(res_f, (x_f, y_img), res_f if res_f.mode=='RGBA' else None)
    card.paste(res_b, (x_b, y_img), res_b if res_b.mode=='RGBA' else None)
    
    draw.text((x_f + 160, y_img - 30), "FRONT VIEW", fill="#7f8c8d", font=font_L)
    draw.text((x_b + 160, y_img - 30), "BACK VIEW", fill="#7f8c8d", font=font_L)

    # --- Info Section ---
    y_info = y_img + t_h + 40
    draw.line([(50, y_info), (w-50, y_info)], fill="#bdc3c7", width=2)
    
    col1_x = 80
    curr_y = y_info + 40
    
    fields_L = [
        ("CLIENT NAME", data.get('name')),
        ("CONTACT INFO", f"{data.get('phone')} / {data.get('line')}"),
        ("PRODUCT SERIES", data.get('series')),
        ("STYLE & COLOR", data.get('variant')),
        ("PRINTING METHOD", "DTF (Direct to Film)"),
    ]
    
    for label, val in fields_L:
        draw.text((col1_x, curr_y), label, fill="#95a5a6", font=font_S)
        draw.text((col1_x, curr_y + 25), str(val), fill="#2c3e50", font=font_L)
        curr_y += 70

    col2_x = 660
    curr_y = y_info + 40
    
    # Price Box
    draw.rectangle([(col2_x - 20, curr_y - 10), (w - 50, curr_y + 160)], fill="#f7f9f9")
    draw.text((col2_x, curr_y), "ESTIMATED TOTAL", fill="#e74c3c", font=font_L)
    draw.text((col2_x, curr_y + 40), f"NT$ {unit_price * data.get('qty'):,}", fill="#c0392b", font=font_Title)
    draw.text((col2_x + 300, curr_y + 55), f"(@ NT$ {unit_price} x {data.get('qty')} pcs)", fill="#7f8c8d", font=font_M)
    
    curr_y += 180
    
    draw.text((col2_x, curr_y), "SIZE BREAKDOWN", fill="#95a5a6", font=font_S)
    draw.text((col2_x, curr_y + 25), str(data.get('size_breakdown')), fill="#2c3e50", font=font_M)
    
    curr_y += 70
    draw.text((col2_x, curr_y), "PRINT LOCATIONS", fill="#95a5a6", font=font_S)
    
    loc_y = curr_y + 25
    for item in design_list_text:
        draw.text((col2_x, loc_y), item, fill="#2c3e50", font=font_M)
        loc_y += 30

    # --- Footer ---
    draw.rectangle([(0, h-60), (w, h)], fill="#c0392b")
    footer_text = "CONFIRMATION: Please send this image to LINE: @727jxovv to finalize your order."
    draw.text((220, h-45), footer_text, fill="white", font=font_M)
        
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
# 4. 主介面設計
# ==========================================
st.markdown("""
<style>
    .stApp {background-color: #F5F5F7;}
    div[data-testid="stSidebar"] {background-color: #FFFFFF;}
    h1, h2, h3 {font-family: 'Helvetica', sans-serif;}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    owner_path = os.path.join(ASSETS_DIR, "owner.jpg")
    if os.path.exists(owner_path):
        st.image(owner_path, caption="Hsing Chang Enterprise")
    else:
        st.info("💡 Please upload owner.jpg")
        
    st.markdown("### 👨‍🔧 About Us")
    st.info("**Hsing Chang x Momo**\n📍 Changhua City")
    st.success("🆔 **LINE ID: @727jxovv**")
    
    with st.expander("🛠 File Checker"):
        if os.path.exists(ASSETS_DIR):
            st.code(os.listdir(ASSETS_DIR))
        else:
            st.error(f"❌ {ASSETS_DIR} not found")
        if st.button("Refresh"): st.rerun()

st.title("📝 Online Design & Quote System")
st.caption("🚀 AG21000 Heavyweight Cotton T-Shirt | Professional Customization")

# --- 1. 選擇產品與尺寸 ---
c1, c2 = st.columns([1.5, 1])

with c2:
    st.markdown("### 1. Product & Quantity")
    if not PRODUCT_CATALOG:
        st.warning("⚠️ Database Error: products.py not found.")
        st.stop()

    series_list = list(PRODUCT_CATALOG.keys())
    s = st.selectbox("Series", series_list)
    v = st.selectbox("Style", list(PRODUCT_CATALOG[s].keys()))
    
    item = PRODUCT_CATALOG.get(s, {}).get(v, {})

    color_options = item.get("colors", ["Default"]) 
    selected_color_name = st.selectbox("Color", color_options)
    color_code = item.get("color_map", {}).get(selected_color_name, "")
    
    base_name = item.get("image_base", "")
    img_url_front = ""
    img_url_back = ""
    
    if base_name and color_code:
        f_try = f"{base_name}_{color_code}_front"
        b_try = f"{base_name}_{color_code}_back"
        f_path_jpg = os.path.join(ASSETS_DIR, f"{f_try}.jpg")
        f_path_png = os.path.join(ASSETS_DIR, f"{f_try}.png")
        b_path_jpg = os.path.join(ASSETS_DIR, f"{b_try}.jpg")
        b_path_png = os.path.join(ASSETS_DIR, f"{b_try}.png")

        if os.path.exists(f_path_jpg): img_url_front = f_path_jpg
        elif os.path.exists(f_path_png): img_url_front = f_path_png
        if os.path.exists(b_path_jpg): img_url_back = b_path_jpg
        elif os.path.exists(b_path_png): img_url_back = b_path_png

    st.markdown("---")
    with st.expander("📏 Size Chart"):
        size_chart_jpg = os.path.join(ASSETS_DIR, "size_chart.jpg")
        size_chart_png = os.path.join(ASSETS_DIR, "size_chart.png")
        if os.path.exists(size_chart_jpg): st.image(size_chart_jpg)
        elif os.path.exists(size_chart_png): st.image(size_chart_png)
        else: st.warning("Please upload size_chart.jpg")

    sizes = ["S", "M", "L", "XL", "2XL", "3XL", "4XL", "5XL"]
    size_inputs = {}
    st.caption("Enter quantity for each size (Min Order: 20):")
    
    cols_size = st.columns(4)
    for i, size in enumerate(sizes):
        with cols_size[i % 4]:
            size_inputs[size] = st.number_input(f"{size}", min_value=0, step=1, key=f"qty_{size}")
    
    total_qty = sum(size_inputs.values())
    
    # --- 2. 創意設計區 ---
    st.markdown("### 2. Design & Upload")
    
    tab_f, tab_b = st.tabs(["👕 Front Design", "🔄 Back Design"])
    
    def render_upload_ui(pos_dict, side_prefix):
        if not pos_dict:
            st.warning("No editable positions.")
            return
        
        pk = st.selectbox(f"Position ({side_prefix})", list(pos_dict.keys()), key=f"sel_{side_prefix}")
        design_key = f"{side_prefix}_{pk}"
        
        if design_key not in st.session_state["uploader_keys"]:
            st.session_state["uploader_keys"][design_key] = 0
            
        uploader_key_version = st.session_state["uploader_keys"][design_key]
        
        uf = st.file_uploader(f"Upload Image for {pk}", type=["png","jpg"], key=f"u_{design_key}_{uploader_key_version}")
        
        if uf:
            file_bytes = uf.getvalue()
            if design_key not in st.session_state["designs"]:
                default_rotation = pos_dict[pk].get("default_rot", 0)
                st.session_state["designs"][design_key] = {
                    "bytes": file_bytes,
                    "rb": False, 
                    "sz": 150, 
                    "rot": default_rotation,
                    "ox": 0, "oy": 0
                }
            else:
                st.session_state["designs"][design_key]["bytes"] = file_bytes
        
        if design_key in st.session_state["designs"]:
            st.success(f"✅ Image uploaded for {pk}")
            if st.button(f"🗑️ Remove Image ({pk})", key=f"btn_clear_{design_key}"):
                del st.session_state["designs"][design_key]
                st.session_state["uploader_keys"][design_key] += 1
                st.rerun()

    with tab_f:
        render_upload_ui(item.get("pos_front", {}), "front")

    with tab_b:
        render_upload_ui(item.get("pos_back", {}), "back")

    has_front_design = any(k.startswith("front_") for k in st.session_state["designs"].keys())
    has_back_design = any(k.startswith("back_") for k in st.session_state["designs"].keys())
    is_double_sided = has_front_design and has_back_design
    unit_price = calculate_unit_price(total_qty, is_double_sided)
    total_price = unit_price * total_qty

# --- 左欄：即時預覽 ---
with c1:
    view_side = st.radio("👁️ View Angle", ["Front", "Back"], horizontal=True, label_visibility="collapsed")
    current_side = "front" if "Front" in view_side else "back"

    st.markdown(f"#### Preview: {v} ({'Black' if 'Black' in color_code else color_code})")
    
    target_img_path = img_url_front if current_side == "front" else img_url_back
    
    if target_img_path and os.path.exists(target_img_path):
        base = Image.open(target_img_path).convert("RGBA")
    else:
        base = Image.new("RGBA", (600, 800), (220, 220, 220))
        draw_tmp = ImageDraw.Draw(base)
        msg = f"No Image in {ASSETS_DIR}:\n{f_try if current_side=='front' else b_try}.jpg"
        draw_tmp.text((50, 350), msg, fill="red")

    final = base.copy()
    
    for d_key, d_val in st.session_state["designs"].items():
        d_side, d_pos_name = d_key.split("_", 1)
        
        should_draw = False
        target_pos_config = None
        
        if d_side == current_side:
            should_draw = True
            if current_side == "front":
                target_pos_config = item.get("pos_front", {}).get(d_pos_name)
            else:
                target_pos_config = item.get("pos_back", {}).get(d_pos_name)
        
        elif current_side == "back" and d_side == "front":
            if d_pos_name in SLEEVE_MAPPING:
                back_pos_name = SLEEVE_MAPPING[d_pos_name]
                target_pos_config = item.get("pos_back", {}).get(back_pos_name)
                should_draw = True
        
        if should_draw and target_pos_config:
            tx, ty = target_pos_config["coords"]
            
            with st.spinner("Processing..." if d_val["rb"] else None):
                paste_img = process_user_image(d_val["bytes"], d_val["rb"])
            
            wr = d_val["sz"] / paste_img.width
            paste_img = paste_img.resize((d_val["sz"], int(paste_img.height * wr)))
            if d_val["rot"] != 0: paste_img = paste_img.rotate(d_val["rot"], expand=True)
            
            final_x = int(tx - paste_img.width/2 + d_val["ox"])
            final_y = int(ty - paste_img.height/2 + d_val["oy"])
            final.paste(paste_img, (final_x, final_y), paste_img)

    st.image(final, use_container_width=True)
    
    # 調整工具區
    st.markdown("---")
    st.caption(f"Adjust {current_side} Design:")
    for d_key in list(st.session_state["designs"].keys()):
        if d_key.startswith(current_side + "_"):
            d_val = st.session_state["designs"][d_key]
            
            with st.expander(f"🔧 Adjust: {d_key.split('_')[1]}", expanded=True):
                with st.form(key=f"form_{d_key}"):
                    st.caption("Click 'Apply Changes' to update preview")
                    
                    new_rb = st.checkbox("✨ AI Remove Background", value=d_val["rb"])
                    new_sz = st.slider("Size", 50, 400, d_val["sz"])
                    new_rot = st.slider("Rotate", -180, 180, d_val["rot"])
                    
                    c1a, c2a = st.columns(2)
                    with c1a: new_ox = st.number_input("Move X", -100, 100, d_val["ox"])
                    with c2a: new_oy = st.number_input("Move Y", -100, 100, d_val["oy"])
                    
                    submitted = st.form_submit_button("✅ Apply Changes")
                    
                    if submitted:
                        d_val["rb"] = new_rb
                        d_val["sz"] = new_sz
                        d_val["rot"] = new_rot
                        d_val["ox"] = new_ox
                        d_val["oy"] = new_oy
                        st.rerun()

                if st.button("🗑️ Delete Image", key=f"del_{d_key}"):
                    del st.session_state["designs"][d_key]
                    if d_key in st.session_state["uploader_keys"]:
                        st.session_state["uploader_keys"][d_key] += 1
                    st.rerun()

# --- 下方：報價與結帳區 ---
st.divider()
st.markdown("### 3. Quote & Checkout")

if total_qty < 20:
    st.warning(f"⚠️ Minimum Order Quantity is 20 pcs (Current: {total_qty}).")
else:
    col_price, col_value = st.columns([1, 1.5])
    
    with col_price:
        side_text = "Double Sided" if is_double_sided else "Single Sided"
        st.markdown(f"""
        <div style="background-color: #f8f9fa; border: 1px solid #ddd; padding: 20px; border-radius: 10px; text-align: center;">
            <p style="color: #666; font-size: 14px; margin-bottom: 5px;">Unit Price ({side_text})</p>
            <h2 style="color: #2c3e50; margin: 0;">NT$ {unit_price}</h2>
            <p style="color: #888; font-size: 12px; margin-top: 5px;">x {total_qty} pcs</p>
            <hr style="margin: 10px 0;">
            <h3 style="color: #d63031; margin: 0;">Total: NT$ {total_price:,}</h3>
        </div>
        """, unsafe_allow_html=True)
        
    with col_value:
        st.markdown("#### ✅ Premium Service Included:")
        st.markdown("""
        - 🌈 **Full Color DTF**: No limit on colors, perfect for gradients.
        - 🛡️ **No Setup Fee**: Printing cost included.
        - 📦 **Individual Packaging**: Each shirt comes in a dust bag.
        - 🚚 **Direct from Factory**: Quality guaranteed by Hsing Chang.
        """)

    st.markdown("<br>", unsafe_allow_html=True)
    if st.checkbox("I accept the price, proceed to contact info.", value=False):
        with st.container():
            st.info("💡 Note: Metallic or Fluorescent colors are not supported in standard DTF.")
            col_sub1, col_sub2 = st.columns(2)
            with col_sub1:
                c_name = st.text_input("Name / Company")
                c_line = st.text_input("LINE ID (Required for artwork confirmation)")
            with col_sub2:
                c_phone = st.text_input("Phone Number")
                c_note = st.text_input("Notes (e.g., Rush Order)")

            if st.button("🚀 Generate Official Quote (Lock Price)", type="primary", use_container_width=True):
                if not c_name or not c_line:
                    st.error("Please fill in Name and LINE ID.")
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
                    
                    base_b = Image.open(img_url_back).convert("RGBA") if img_url_back and os.path.exists(img_url_back) else Image.new("RGBA", (600,800), (240,240,240))
                    final_back = base_b.copy()
                    
                    for d_key, d_val in st.session_state["designs"].items():
                        d_side, d_pos_name = d_key.split("_", 1)
                        
                        should_draw_b = False
                        target_pos_config_b = None
                        
                        if d_side == "back":
                            should_draw_b = True
                            target_pos_config_b = item.get("pos_back", {}).get(d_pos_name)
                        elif d_side == "front" and d_pos_name in SLEEVE_MAPPING:
                            should_draw_b = True
                            back_pos_name = SLEEVE_MAPPING[d_pos_name]
                            target_pos_config_b = item.get("pos_back", {}).get(back_pos_name)
                        
                        if should_draw_b and target_pos_config_b:
                            tx, ty = target_pos_config_b["coords"]
                            pi = process_user_image(d_val["bytes"], d_val["rb"])
                            wr = d_val["sz"]/pi.width
                            pi = pi.resize((d_val["sz"], int(pi.height*wr)))
                            if d_val["rot"]!=0: pi=pi.rotate(d_val["rot"], expand=True)
                            final_back.paste(pi, (int(tx-pi.width/2+d_val["ox"]), int(ty-pi.height/2+d_val["oy"])), pi)

                    receipt_img = generate_inquiry_image(final, final_back, dt, design_list, unit_price)
                    
                    st.success("✅ Official Quote Generated!")
                    st.image(receipt_img, caption="Please save this image and send to LINE: @727jxovv")
                    st.link_button("👉 Open LINE to Confirm Order", "https://line.me/ti/p/~@727jxovv")
