import streamlit as st
import io
import os
import requests
import platform
from PIL import Image, ImageDraw, ImageFont
from rembg import remove
from products import PRODUCT_CATALOG
import datetime

# ==========================================
# 1. 全局設定 & 狀態管理
# ==========================================
st.set_page_config(
    page_title="Momo Design Pro",
    page_icon="✨",
    layout="wide"
)

if "user_role" not in st.session_state: st.session_state["user_role"] = "guest"
if "user_info" not in st.session_state: st.session_state["user_info"] = {"name": "", "code": "GUEST", "is_ambassador": False}

# ==========================================
# 2. 字型強制修復
# ==========================================
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanstc/NotoSansTC-Regular.ttf"
FONT_FILE = "NotoSansTC-Regular.ttf"

@st.cache_resource
def load_font_file():
    if not os.path.exists(FONT_FILE) or os.path.getsize(FONT_FILE) < 1000000:
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(FONT_URL, headers=headers, timeout=45)
            if r.status_code == 200:
                with open(FONT_FILE, "wb") as f: f.write(r.content)
        except: pass
    return FONT_FILE

load_font_file()

def get_font_obj(size):
    try: return ImageFont.truetype(FONT_FILE, size)
    except: return ImageFont.load_default()

# ==========================================
# 3. CSS 美化
# ==========================================
st.markdown("""
    <style>
    .stApp { background-color: #f4f7f6; font-family: "Microsoft JhengHei", sans-serif; }
    .block-container { padding-top: 2rem; padding-bottom: 3rem; }
    .banner-box { padding: 25px; border-radius: 16px; margin-bottom: 25px; text-align: center; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1); color: white; }
    .theme-default { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .theme-corp { background: linear-gradient(135deg, #0ba360 0%, #3cba92 100%); }
    .banner-title { font-size: 28px; font-weight: 800; margin-bottom: 8px; letter-spacing: 1px; }
    .price-card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #eee; text-align: center; margin-top: 10px; }
    .price-val { font-size: 32px; font-weight: 800; color: #2d3748; }
    .tools-container { background: white; padding: 20px; border-radius: 16px; box-shadow: 0 2px 10px rgba(0,0,0,0.03); border: 1px solid #f0f0f0; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 4. 詢價單生成 (含聯絡人資訊)
# ==========================================
def generate_inquiry_card(img, data):
    # 加高畫布以容納更多資訊
    w, h = 800, 1250 
    card = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(card)
    
    f_title = get_font_obj(40)
    f_head = get_font_obj(24)
    f_norm = get_font_obj(20)
    f_small = get_font_obj(16)
    
    header_color = "#0ba360"
    
    # 1. 標題區
    draw.rectangle([(0,0), (w, 130)], fill=header_color)
    draw.text((40, 45), "Momo Design 需求詢價單", fill="white", font=f_title)
    draw.text((w-250, 60), str(datetime.date.today()), fill="#e2e8f0", font=f_norm)
    
    # 2. 產品示意圖
    t_w = 400
    ratio = t_w / img.width
    t_h = int(img.height * ratio)
    res = img.resize((t_w, t_h))
    draw.rectangle([( (w-t_w)//2 - 5, 160 - 5), ( (w-t_w)//2 + t_w + 5, 160 + t_h + 5)], fill="#f0f0f0")
    card.paste(res, ((w-t_w)//2, 160), res if res.mode=='RGBA' else None)
    
    # 3. 資料區開始
    y = 160 + t_h + 50
    draw.line([(50, y), (750, y)], fill="#e2e8f0", width=2)
    y += 30
    
    # --- 區塊 A: 聯絡資料 ---
    draw.text((50, y), "【聯絡資料】", fill=header_color, font=f_head)
    y += 40
    
    contact_infos = [
        ("單位名稱", data.get('name', '-')),
        ("聯絡姓名", data.get('contact', '-')),
        ("聯絡電話", data.get('phone', '-')),
        ("LINE ID", data.get('line', '-'))
    ]
    
    # 雙欄排列聯絡資訊 (左右各兩項)
    col1_x, col2_x = 60, 420
    for i, (k, v) in enumerate(contact_infos):
        # 決定畫在左欄還是右欄
        curr_x = col1_x if i % 2 == 0 else col2_x
        draw.text((curr_x, y), f"{k}：", fill="#718096", font=f_norm)
        draw.text((curr_x + 100, y), str(v), fill="#2d3748", font=f_norm)
        if i % 2 == 1: y += 40 # 每畫完兩個換下一行
            
    y += 20 # 區塊間距
    
    # --- 區塊 B: 訂購需求 ---
    draw.text((50, y), "【訂購需求】", fill=header_color, font=f_head)
    y += 40
    
    order_infos = [
        ("產品系列", data.get('series', '-')),
        ("款式顏色", data.get('variant', '-')),
        ("預計數量", f"{data.get('qty', '-')} 件"),
        ("備註需求", data.get('note', '無'))
    ]
    
    for k, v in order_infos:
        draw.text((60, y), f"{k}：", fill="#718096", font=f_norm)
        
        # 備註自動換行處理
        content_str = str(v)
        max_char = 28
        first_line = True
        for i in range(0, len(content_str), max_char):
            line = content_str[i:i+max_char]
            draw.text((160, y), line, fill="#2d3748", font=f_norm)
            y += 35
            first_line = False
        if first_line: y += 35 # 如果只有一行，也要加高度

    # Footer
    draw.rectangle([(0, h-60), (w, h)], fill="#f7fafc")
    draw.text((240, h-40), "此單據僅供詢價參考，正式報價以業務回傳為主", fill="#718096", font=f_small)
    return card

def add_watermark(base, text):
    wm = Image.new("RGBA", base.size, (0,0,0,0))
    d = ImageDraw.Draw(wm)
    w, h = base.size
    fs = int(h * 0.04)
    f = get_font_obj(fs)
    label = f"Promo: {text}"
    d.rectangle([(w-fs*12, h-fs*3.2), (w, h)], fill=(255,255,255,220))
    d.text((w-fs*11, h-fs*2.5), label, fill=(255,80,80,255), font=f)
    d.text((w-fs*11, h-fs*1.2), "Momo Design Studio", fill="#718096", font=get_font_obj(int(fs*0.7)))
    return Image.alpha_composite(base, wm)

# ==========================================
# 5. 側邊欄
# ==========================================
with st.sidebar:
    st.title("👤 會員中心")
    if st.session_state["user_role"] == "guest":
        st.info("訪客模式")
        with st.expander("登入 / 註冊推廣大使", expanded=True):
            name = st.text_input("暱稱")
            phone = st.text_input("手機")
            is_amb = st.checkbox("我要開啟分潤功能", value=False)
            if st.button("確認身分", type="primary"):
                if name:
                    code = f"{name.upper()}{phone[-3:]}" if phone and is_amb else "MEMBER"
                    st.session_state.update({"user_role": "member", "user_info": {"name":name, "code":code, "is_ambassador":is_amb}})
                    st.rerun()
    else:
        info = st.session_state["user_info"]
        st.success(f"Hi, {info['name']}")
        if info["is_ambassador"]: st.markdown(f"推廣碼: **`{info['code']}`**")
        if st.button("登出"):
            st.session_state.update({"user_role": "guest", "user_info": {"name":"", "code":"GUEST", "is_ambassador":False}})
            st.rerun()

# ==========================================
# 6. 主畫面
# ==========================================
mode_cols = st.columns([2, 1])
with mode_cols[0]:
    mode = st.radio("服務模式", ["設計訂製 / 推廣", "公司團體 (詢價)"], horizontal=True, label_visibility="collapsed")

if mode == "公司團體 (詢價)":
    banner_class, b_title, b_sub = "theme-corp", "Momo 團體訂購中心", "企業制服 · 活動團服 · 專人報價服務"
    partner_id = "Corporate"
else:
    banner_class, b_title, b_sub = "theme-default", "Momo 創意設計工坊", "打造專屬商品 · 享受設計樂趣"
    partner_id = st.session_state["user_info"]["code"] if st.session_state["user_role"] == "member" and st.session_state["user_info"]["is_ambassador"] else st.session_state["user_info"]["name"] or "GUEST"

st.markdown(f"""
    <div class="banner-box {banner_class}">
        <div class="banner-title">{b_title}</div>
        <div class="banner-sub">{b_sub}</div>
    </div>
""", unsafe_allow_html=True)

col_preview, col_tools = st.columns([1.6, 1], gap="large")

# --- 右側工具欄 ---
with col_tools:
    st.markdown('<div class="tools-container">', unsafe_allow_html=True)
    st.markdown("### 📦 1. 選擇產品")
    c1, c2 = st.columns(2)
    with c1: series = st.selectbox("系列", list(PRODUCT_CATALOG.keys()))
    with c2: variant = st.selectbox("款式", list(PRODUCT_CATALOG[series].keys()))
    
    item = PRODUCT_CATALOG[series][variant]
    price = item.get("price", 0)
    pos = item.get("positions", {"中":[150,150]})
    
    st.divider()
    st.markdown("### 🛠️ 2. 設計調整")
    
    uploaded_file = st.file_uploader("上傳圖片 (PNG/JPG)", type=["png", "jpg", "jpeg"])
    if uploaded_file:
        with st.expander("細部參數設定", expanded=True):
            remove_bg = st.toggle("✨ AI 自動去背", value=False)
            pos_key = st.selectbox("印製位置", list(pos.keys()))
            size_val = st.slider("圖案大小", 50, 450, 180)
            c_x, c_y = st.columns(2)
            with c_x: off_x = st.slider("↔️ 左右微調", -60, 60, 0)
            with c_y: off_y = st.slider("↕️ 上下微調", -60, 60, 0)
            rotate = st.slider("🔄 旋轉角度", -180, 180, 0)
    else:
        pos_key, size_val, off_x, off_y, rotate, remove_bg = list(pos.keys())[0], 150, 0, 0, 0, False
    st.markdown('</div>', unsafe_allow_html=True)

# --- 左側預覽 ---
with col_preview:
    try:
        st.markdown('<div style="background:white; padding:20px; border-radius:16px; box-shadow:0 4px 20px rgba(0,0,0,0.06);">', unsafe_allow_html=True)
        base_img = Image.open(item["image"]).convert("RGBA")
        final_img = base_img.copy()
        
        if uploaded_file:
            design = Image.open(uploaded_file).convert("RGBA")
            if remove_bg: design = remove(design)
            w_rat = size_val / design.width
            design = design.resize((size_val, int(design.height * w_rat)))
            if rotate: design = design.rotate(rotate, expand=True)
            tx, ty = pos[pos_key]
            final_img.paste(design, (int(tx - design.width/2 + off_x), int(ty - design.height/2 + off_y)), design)
        
        final_view = add_watermark(final_img, partner_id) if mode != "公司團體 (詢價)" else final_img
        st.image(final_view, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"圖片載入錯誤: {e}")

# --- 底部行動區 (詢價/下載) ---
with col_tools:
    if mode == "公司團體 (詢價)":
        st.markdown('<div class="tools-container" style="margin-top:20px; border-left:4px solid #0ba360;">', unsafe_allow_html=True)
        st.markdown("### 📋 3. 填寫詢價資料")
        
        # [新增] 聯絡資料輸入區
        nm = st.text_input("單位/公司名稱")
        
        # 分欄讓版面更整齊
        cc1, cc2 = st.columns(2)
        with cc1: contact_person = st.text_input("聯絡人姓名")
        with cc2: contact_phone = st.text_input("聯絡電話")
        
        contact_line = st.text_input("LINE ID (選填)")
        
        c_q, c_n = st.columns([1, 2])
        with c_q: qt = st.number_input("數量", value=20, min_value=1)
        with c_n: nt = st.text_input("備註")
        
        if st.button("📄 生成並下載詢價單", type="primary", use_container_width=True):
            # 打包資料
            inquiry_data = {
                "name": nm or "Guest",
                "contact": contact_person,
                "phone": contact_phone,
                "line": contact_line,
                "series": series,
                "variant": variant,
                "qty": qt,
                "note": nt
            }
            
            with st.spinner("正在生成詢價單..."):
                card = generate_inquiry_card(final_img, inquiry_data)
                buf = io.BytesIO(); card.save(buf, format="PNG")
            
            st.success("詢價單已生成！")
            st.download_button("📥 點擊下載圖片", data=buf.getvalue(), file_name=f"Inquiry_{nm or 'Guest'}.png", mime="image/png", use_container_width=True, type="primary")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="price-card">
            <div class="price-label">建議售價</div>
            <div class="price-val"><span class="price-currency">NT$</span>{price}</div>
        </div>
        """, unsafe_allow_html=True)
        buf = io.BytesIO(); final_view.save(buf, format="PNG")
        if st.session_state["user_role"] == "member" and st.session_state["user_info"]["is_ambassador"]:
            st.download_button("✨ 下載專屬推廣圖", data=buf.getvalue(), file_name=f"Promo_{partner_id}.png", mime="image/png", type="primary", use_container_width=True)
        else:
            st.download_button("📥 下載設計預覽圖", data=buf.getvalue(), file_name="Design.png", mime="image/png", use_container_width=True)
