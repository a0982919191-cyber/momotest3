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
# 1. 全局設定
# ==========================================
st.set_page_config(
    page_title="Momo Design System",
    page_icon="🎨",
    layout="wide"
)
# --- 全站存取密碼設定 ---
def check_password():
    """如果輸入正確密碼則回傳 True"""
    if "password_correct" not in st.session_state:
        # 顯示輸入框
        st.markdown("### 🔒 歡迎試用 Momo 系統")
        password = st.text_input("請輸入存取密碼以繼續：", type="password")
        if st.button("登入"):
            if password == "momo2025": # 👈 在這裡設定您要給別人的密碼
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ 密碼錯誤，請洽管理員")
        return False
    return True

if not check_password():
    st.stop() # 密碼不正確就停止執行後面的程式碼

# ==========================================
# 2. 字型修復 (修正下載連結)
# ==========================================
# 使用正確的 raw.githubusercontent.com 連結
FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanstc/NotoSansTC-Regular.ttf"
FONT_FILE = "NotoSansTC-Regular.ttf"

@st.cache_resource
def get_best_font_path():
    """
    智慧尋找最佳中文字型路徑：
    1. Windows 本地 -> 微軟正黑體
    2. Mac 本地 -> 蘋方體
    3. Linux/Cloud -> 自動下載 NotoSansTC (從正確的網址)
    """
    system_name = platform.system()
    
    # 1. 嘗試 Windows 內建字型 (優先使用，速度最快)
    if system_name == "Windows":
        if os.path.exists("C:/Windows/Fonts/msjh.ttc"):
            return "C:/Windows/Fonts/msjh.ttc"
        if os.path.exists("C:/Windows/Fonts/msjh.ttf"):
            return "C:/Windows/Fonts/msjh.ttf"
            
    # 2. 嘗試 Mac 內建字型
    if system_name == "Darwin": # macOS
        if os.path.exists("/System/Library/Fonts/PingFang.ttc"):
            return "/System/Library/Fonts/PingFang.ttc"
    
    # 3. 雲端/Linux 環境 -> 下載 Google Font
    # 如果檔案不存在或太小 (下載失敗過)，就重新下載
    if not os.path.exists(FONT_FILE) or os.path.getsize(FONT_FILE) < 1000000:
        print(f"📥 正在從 {FONT_URL} 下載字型...")
        try:
            response = requests.get(FONT_URL, timeout=30)
            if response.status_code == 200:
                with open(FONT_FILE, "wb") as f:
                    f.write(response.content)
                print("✅ 字型下載成功")
            else:
                print(f"❌ 下載失敗，狀態碼: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ 下載錯誤: {e}")
            return None

    return FONT_FILE

# 取得全域字型路徑
font_path_global = get_best_font_path()

def get_font(size):
    """載入字型物件"""
    try:
        if font_path_global:
            return ImageFont.truetype(font_path_global, size)
    except:
        pass
    # 真的失敗時回傳預設
    return ImageFont.load_default()

# ==========================================
# 3. CSS 美化
# ==========================================
st.markdown("""
    <style>
    .stApp { 
        background-color: #F8F9FA; 
        font-family: -apple-system, BlinkMacSystemFont, "Microsoft JhengHei", "Segoe UI", Roboto, sans-serif;
        color: #333; font-size: 14px; 
    }
    .banner-box {
        padding: 20px 25px; border-radius: 12px; margin-bottom: 20px; text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    .theme-promo { background: linear-gradient(120deg, #FF8008 0%, #FFC837 100%); }
    .theme-corp { background: linear-gradient(120deg, #11998e 0%, #38ef7d 100%); }
    .theme-b2b { background: linear-gradient(135deg, #2C3E50 0%, #4CA1AF 100%); }
    
    .banner-title { color: #FFF !important; font-size: 28px !important; font-weight: 700 !important; margin-bottom: 5px !important; text-shadow: 0 1px 3px rgba(0,0,0,0.2); }
    .banner-sub { color: #F0F0F0 !important; font-size: 14px !important; opacity: 0.9; }
    
    .price-card { background: white; padding: 15px 20px; border-radius: 10px; border-left: 4px solid #ccc; box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-bottom: 20px; }
    .border-promo { border-left-color: #FF8008; }
    .border-corp { border-left-color: #11998e; }
    .border-b2b { border-left-color: #2C3E50; }
    
    .price-label { font-size: 12px; color: #777; margin-bottom: 5px; }
    .price-big { font-size: 24px; font-weight: 700; margin-bottom: 5px; }
    .price-small { font-size: 12px; color: #999; }
    .text-promo { color: #e67e22; }
    .text-corp { color: #27ae60; }
    .text-b2b { color: #c0392b; }
    
    .info-box { background-color: #fff; border: 1px solid #eee; border-radius: 10px; padding: 15px; margin-bottom: 20px; }
    #MainMenu, footer, header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 4. 圖片生成邏輯 (含詢價單)
# ==========================================

def add_watermark(base_image, text, mode="promo"):
    watermark = Image.new("RGBA", base_image.size, (0,0,0,0))
    draw = ImageDraw.Draw(watermark)
    w, h = base_image.size
    
    font_size = int(h * 0.035) 
    if font_size < 20: font_size = 20
    font = get_font(font_size)
    
    box_h = font_size * 2.5
    
    if mode == "b2b":
        label = f"PO Ref: {text}"
        draw.text((w - (font_size*10), h - (font_size*2)), label, fill=(50, 50, 50, 150), font=font)
    elif mode == "corp":
        label = f"Inquiry: {text}"
        draw.rectangle([(0, h - box_h), (w, h)], fill=(255, 255, 255, 200))
        draw.text((20, h - box_h + 10), label, fill=(17, 153, 142, 255), font=font)
    else:
        label = f"Promo: {text}"
        x = w - (font_size*12)
        y = h - box_h - 20
        draw.rectangle([(x-10, y), (w-20, h-20)], fill=(255, 255, 255, 220))
        draw.text((x, y+5), label, fill=(255, 80, 80, 255), font=font)
        
    return Image.alpha_composite(base_image, watermark)

def generate_inquiry_card(product_image, data_dict):
    """生成完整詢價單 (確保字型載入)"""
    canvas_w, canvas_h = 800, 1100
    card = Image.new("RGB", (canvas_w, canvas_h), "white")
    draw = ImageDraw.Draw(card)
    
    font_title = get_font(40)
    font_header = get_font(24)
    font_text = get_font(20)
    font_small = get_font(16)
    
    # 標題
    draw.rectangle([(0, 0), (canvas_w, 120)], fill="#11998e")
    draw.text((40, 40), "Momo Design 團體詢價單", fill="white", font=font_title)
    draw.text((550, 55), f"日期: {datetime.date.today()}", fill="white", font=font_text)
    
    # 產品圖
    target_img_w = 400
    ratio = target_img_w / product_image.width
    target_img_h = int(product_image.height * ratio)
    resized_product = product_image.resize((target_img_w, target_img_h))
    paste_x = (canvas_w - target_img_w) // 2
    paste_y = 150
    card.paste(resized_product, (paste_x, paste_y), resized_product)
    
    # 分隔線
    info_start_y = paste_y + target_img_h + 40
    draw.line([(50, info_start_y), (750, info_start_y)], fill="#ccc", width=2)
    
    y = info_start_y + 40
    line_height = 45
    
    # 內容填寫
    draw.text((50, y), "【詢價單位資料】", fill="#11998e", font=font_header)
    y += 50
    draw.text((60, y), f"單位名稱： {data_dict.get('comp_name', '-')}", fill="#333", font=font_text)
    y += line_height
    draw.text((60, y), f"統一編號： {data_dict.get('tax_id', '-')}", fill="#333", font=font_text)
    
    y += 60
    draw.text((50, y), "【訂購需求明細】", fill="#11998e", font=font_header)
    y += 50
    draw.text((60, y), f"產品系列： {data_dict.get('series', '-')}", fill="#333", font=font_text)
    y += line_height
    draw.text((60, y), f"款式顏色： {data_dict.get('variant', '-')}", fill="#333", font=font_text)
    y += line_height
    draw.text((60, y), f"預計數量： {data_dict.get('qty', '-')} 件", fill="#d35400", font=font_header)
    
    y += 60
    draw.text((50, y), "【備註需求 / 交期】", fill="#11998e", font=font_header)
    y += 50
    note_text = data_dict.get('note', '無')
    
    # 自動換行
    max_char = 28
    for i in range(0, len(note_text), max_char):
        line = note_text[i:i+max_char]
        draw.text((60, y), line, fill="#555", font=font_text)
        y += 30
    
    # Footer
    draw.rectangle([(0, canvas_h-60), (canvas_w, canvas_h)], fill="#f0f0f0")
    draw.text((220, canvas_h-40), "此單據僅供詢價使用，正式報價以業務回傳為主", fill="#999", font=font_small)
    
    return card

# ==========================================
# 5. 側邊欄狀態
# ==========================================
with st.sidebar:
    st.header("⚙️ 系統狀態")
    if font_path_global and "Noto" in font_path_global:
        st.success("✅ 雲端中文字型已下載")
    elif font_path_global:
        st.success("✅ 使用本機系統字型")
    else:
        st.error("⚠️ 字型下載失敗，使用預設")
    st.write("---")

# ==========================================
# 6. 頂部身份切換
# ==========================================
st.markdown("### 🚀 請先選擇您的身份")
col_role, col_pwd = st.columns([2.5, 1])

with col_role:
    role = st.radio("身份選擇", ["🎁 分潤推廣大使 (一般會員)", "🏢 公司/團體訂購 (填表詢價)", "🔐 經銷合作夥伴 (B2B)"], horizontal=True, label_visibility="collapsed")

user_mode = "promo"
partner_id = "GUEST"

if "公司/團體" in role:
    user_mode = "corp"
    banner_class = "theme-corp"
    banner_title = "Momo 團體訂購中心"
    banner_sub = "企業制服 · 活動團服 · 專人報價服務"
elif "經銷合作夥伴" in role:
    with col_pwd:
        pwd = st.text_input("🔐 夥伴密碼", type="password", label_visibility="collapsed", placeholder="請輸入密碼...")
    if pwd == "momo888":
        user_mode = "b2b"
        banner_class = "theme-b2b"
        banner_title = "Momo 經銷採購系統"
        banner_sub = "B2B Partner Portal · 成本計算 · 批量採購"
    else:
        if pwd: st.error("密碼錯誤")
        st.info("👈 請輸入密碼解鎖經銷功能")
        st.stop()
else: 
    user_mode = "promo"
    banner_class = "theme-promo"
    banner_title = "Momo 創意推廣中心"
    banner_sub = "加入會員 · 設計專屬商品 · 分享賺分潤"

st.markdown(f"""
    <div class="banner-box {banner_class}">
        <div class="banner-title">{banner_title}</div>
        <div class="banner-sub">{banner_sub}</div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 7. 主操作區
# ==========================================
col_preview, col_tools = st.columns([1.6, 1], gap="large")

with col_tools:
    req_data = {} 
    
    if user_mode == "corp":
        st.markdown('<div class="info-box" style="border-left: 4px solid #11998e;">', unsafe_allow_html=True)
        st.markdown("#### 📝 詢價需求單")
        c1, c2 = st.columns(2)
        with c1: comp_name = st.text_input("公司/團體名稱", placeholder="例: 某某科技")
        with c2: tax_id = st.text_input("統一編號 (選填)")
        req_data['comp_name'] = comp_name
        req_data['tax_id'] = tax_id
        if comp_name: partner_id = comp_name
        else: partner_id = "Guest"
        st.caption("請填寫資料，以便生成完整需求單。")
        st.markdown('</div>', unsafe_allow_html=True)
        
    elif user_mode == "b2b":
        st.markdown("#### 👤 夥伴識別")
        partner_id = st.text_input("夥伴代號 (Partner ID)", value="Partner01")
        
    else:
        st.markdown('<div class="info-box" style="border-left: 4px solid #FF8008;">', unsafe_allow_html=True)
        st.markdown("#### 📝 會員註冊")
        c1, c2 = st.columns(2)
        with c1: m_name = st.text_input("您的暱稱", placeholder="例: Andy")
        with c2: m_phone = st.text_input("手機後3碼", placeholder="例: 888")
        if m_name and m_phone:
            partner_id = f"{m_name.upper()}{m_phone}"
            st.success(f"✅ 推廣碼：{partner_id}")
        else: partner_id = "MOMO-GUEST"
        st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("📦 產品選擇")
    selected_series = st.selectbox("系列", list(PRODUCT_CATALOG.keys()))
    series_data = PRODUCT_CATALOG[selected_series]
    selected_variant = st.selectbox("款式", list(series_data.keys()))
    
    req_data['series'] = selected_series
    req_data['variant'] = selected_variant
    
    current_item = series_data[selected_variant]
    bg_path = current_item["image"]
    retail_price = current_item.get("price", 0)
    
    if retail_price >= 600: wholesale_rate = 0.55
    else: wholesale_rate = 0.7
    wholesale_price = int(retail_price * wholesale_rate)
    
    positions_dict = current_item.get("positions", {"正中": [150, 150]})

    if user_mode == "b2b":
        st.markdown(f"""<div class="price-card border-b2b"><div class="price-label">建議售價 ${retail_price}</div><div class="price-big text-b2b">批發成本 NT$ {wholesale_price}</div><div class="price-small">含稅價，不含運費</div></div>""", unsafe_allow_html=True)
    elif user_mode == "corp":
        st.markdown(f"""<div class="price-card border-corp"><div class="price-label">建議售價 (MSRP)</div><div class="price-big text-corp">NT$ {retail_price}</div><div style="margin-top:10px; padding:12px; background:#e8f5e9; border-radius:8px;"><span style="font-size:13px; color:#2e7d32; font-weight:600;">ℹ️ 實際報價說明：</span><br><span style="font-size:12px; color:#1b5e20;">請填寫下方需求，系統將生成完整詢價單，請下載後回傳。</span></div></div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div class="price-card border-promo"><div class="price-label">建議售價</div><div class="price-big text-promo">NT$ {retail_price} 起</div><div class="price-small">憑代碼【{partner_id}】分享賺分潤</div></div>""", unsafe_allow_html=True)

    st.write("---")
    with st.expander("🎨 設計圖上傳與調整", expanded=True):
        uploaded_file = st.file_uploader("上傳圖片", type=["png", "jpg", "jpeg"])
        target_center_x, target_center_y = positions_dict[list(positions_dict.keys())[0]]
        width_slider, offset_x, offset_y, rotate_slider = 150, 0, 0, 0
        if uploaded_file:
            remove_bg = st.toggle("✨ AI 自動去背", value=False)
            selected_pos_name = st.selectbox("印製位置", list(positions_dict.keys()))
            target_center_x, target_center_y = positions_dict[selected_pos_name]
            width_slider = st.slider("圖案大小", 50, 400, 150)
            c1, c2 = st.columns(2)
            with c1: offset_x = st.slider("↔️ X 微調", -50, 50, 0)
            with c2: offset_y = st.slider("↕️ Y 微調", -50, 50, 0)
            rotate_slider = st.slider("🔄 旋轉", -180, 180, 0)

# ==========================================
# 8. 圖片處理 (後端)
# ==========================================
try: template_image = Image.open(bg_path).convert("RGBA")
except: st.stop()

final_image = template_image.copy()

if uploaded_file:
    design_image = Image.open(uploaded_file).convert("RGBA")
    if remove_bg:
        try: design_image = remove(design_image)
        except: pass
    
    w_percent = (width_slider / float(design_image.size[0]))
    h_size = int((float(design_image.size[1]) * float(w_percent)))
    design_image_resized = design_image.resize((width_slider, h_size))
    if rotate_slider != 0:
        design_image_resized = design_image_resized.rotate(rotate_slider, expand=True)
    
    img_w, img_h = design_image_resized.size
    paste_x = int(target_center_x - (img_w / 2) + offset_x)
    paste_y = int(target_center_y - (img_h / 2) + offset_y)
    final_image.paste(design_image_resized, (paste_x, paste_y), design_image_resized)

watermarked_image = add_watermark(final_image, partner_id, mode=user_mode)

with col_preview:
    st.subheader("👀 效果預覽")
    st.image(watermarked_image, use_container_width=True)

# ==========================================
# 9. 輸出行動區
# ==========================================
with col_tools:
    st.write("---")

    if user_mode == "corp":
        st.markdown("### 📋 填寫需求並下載")
        qty = st.number_input("預計訂購數量 (件)", min_value=10, value=30, step=5)
        note = st.text_area("備註需求 (如: 希望交期、特殊印刷)", placeholder="例: 需要加上手臂印刷，希望 10/20 前到貨", height=80)
        req_data['qty'] = qty
        req_data['note'] = note
        
        if st.button("🔄 生成需求詢價單"):
            with st.spinner("生成中..."):
                inquiry_sheet = generate_inquiry_card(final_image, req_data)
                buf = io.BytesIO()
                inquiry_sheet.save(buf, format="PNG")
                byte_im = buf.getvalue()
            st.success("✅ 詢價單已生成！")
            st.download_button(label="📄 下載完整需求詢價單", data=byte_im, file_name=f"Inquiry_{partner_id}.png", mime="image/png", use_container_width=True)

    elif user_mode == "b2b":
        buf = io.BytesIO()
        watermarked_image.save(buf, format="PNG")
        byte_im = buf.getvalue()
        st.markdown("### 🚚 進貨採購")
        qty = st.number_input("進貨數量", value=10)
        st.info(f"💰 總進貨成本: NT$ {qty * wholesale_price:,}")
        st.download_button("📥 下載採購單 (PO)", data=byte_im, file_name=f"PO_{partner_id}.png", mime="image/png", use_container_width=True)

    else:
        buf = io.BytesIO()
        watermarked_image.save(buf, format="PNG")
        byte_im = buf.getvalue()
        st.markdown("### 🚀 分享賺分潤")
        txt = f"我設計的 {selected_variant}！輸入代碼【{partner_id}】享優惠！"
        st.text_area("文案", value=txt, height=80)
        if partner_id == "MOMO-GUEST": st.warning("⚠️ 請先輸入暱稱領取推廣碼")
        else: st.download_button("✨ 下載推廣圖", data=byte_im, file_name=f"Promo_{partner_id}.png", mime="image/png", use_container_width=True)