# -*- coding: utf-8 -*-
# main.py － 興彰 x 默默｜品牌級線上設計 & 自助估價系統
#
# ✅ 本版重點修正：
# 1) CP101 圖檔檔名大小寫相容（你的 assets 皆小寫也能抓到）
# 2) 若 back 圖缺失，先用 front 代替顯示（避免 Image Missing）
# 3) CP101 價格依你提供的價目表：10–30 / 30–100 / 100+；XS–2XL 與 3XL–5XL 不同價
# 4) CP101 尺寸輸入支援 XS～5XL；其餘商品維持 S～5XL
#
# ⚠️ 仍需確保：
# - products.py 在專案根目錄
# - 圖片在 assets/ 下，檔名例如：cp101_white_front.png、cp101_white_back.png（全小寫）
# - 如要生成詢價單中文正常，請放 NotoSansTC-Regular.ttf 到根目錄或 assets/

import io
import os
import json
import datetime
from pathlib import Path

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image, ImageDraw, ImageFont
from rembg import remove

# --- 從外部檔案匯入產品資料 ---
try:
    from products import PRODUCT_CATALOG
except Exception:
    st.set_page_config(page_title="興彰 x 默默｜線上設計估價", page_icon="👕", layout="wide")
    st.error("❌ Critical Error: 找不到或無法載入 products.py，請確認檔案在專案根目錄且語法正確。")
    st.stop()

# ==========================================
# 0. 基礎設定 & 路徑偵測
# ==========================================
st.set_page_config(
    page_title="興彰 x 默默｜品牌級線上設計估價系統",
    page_icon="👕",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

# 字型偵測（請準備 NotoSansTC-Regular.ttf）
FONT_FILENAME = "NotoSansTC-Regular.ttf"
font_path = None
for p in [BASE_DIR / FONT_FILENAME, ASSETS_DIR / FONT_FILENAME]:
    if p.exists():
        font_path = str(p)
        break

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# 正反袖口對應（AG21000 這類含袖口位置用）
SLEEVE_MAPPING = {
    "左臂 (Left Sleeve)": "左臂-後 (L.Sleeve Back)",
    "右臂 (Right Sleeve)": "右臂-後 (R.Sleeve Back)",
}

# ==========================================
# 連線 Google Sheet（支援 st.secrets 或環境變數）
# ==========================================
@st.cache_resource
def connect_to_gsheet():
    try:
        # Streamlit Cloud：st.secrets["gcp_service_account"]
        if "gcp_service_account" in st.secrets:
            info = st.secrets["gcp_service_account"]
        # 例如 Railway：環境變數 GCP_SERVICE_ACCOUNT（字串 JSON）
        elif "GCP_SERVICE_ACCOUNT" in os.environ:
            info = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
        else:
            return None

        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        gc = gspread.authorize(creds)
        return gc.open("momo_db")
    except Exception:
        return None


sh = connect_to_gsheet()

# Session state 初始化
if "designs" not in st.session_state:
    st.session_state["designs"] = {}
if "uploader_keys" not in st.session_state:
    st.session_state["uploader_keys"] = {}

# ==========================================
# 1. 影像處理引擎
# ==========================================
@st.cache_data(show_spinner=False)
def process_user_image(uploaded_file_bytes, apply_rb: bool):
    img = Image.open(io.BytesIO(uploaded_file_bytes)).convert("RGBA")
    max_width = 1200
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height))

    if apply_rb:
        img = remove(img)
    return img


def find_asset_image(base_name: str, color_code: str, side: str) -> str:
    """
    side: 'front' or 'back'
    會嘗試：原樣 / 全小寫 / 全大寫，避免 products.py 與 assets 檔名大小寫不一致導致抓不到
    """
    if not base_name or not color_code:
        return ""

    candidates = [
        f"{base_name}_{color_code}_{side}",
        f"{str(base_name).lower()}_{str(color_code).lower()}_{side}",
        f"{str(base_name).upper()}_{str(color_code).upper()}_{side}",
    ]
    for stem in candidates:
        for ext in [".png", ".jpg", ".jpeg"]:
            p = ASSETS_DIR / (stem + ext)
            if p.exists():
                return str(p)
    return ""


# ==========================================
# 2. 價格計算 + 品牌方案分級
# ==========================================
def calculate_unit_price(qty: int, is_double_sided: bool) -> int:
    """
    一般棉T（例如 AG21000）價格：按件數＆是否雙面計算單價
    """
    if qty < 20:
        return 0
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


def calculate_cp101_price(size_counts: dict):
    """
    CP101 吸濕排汗團體服價格（依你提供的圖表）：
    - 10–30：XS～2XL=255；3XL～5XL=265
    - 30–100：XS～2XL=245；3XL～5XL=255
    - 100+：XS～2XL=240；3XL～5XL=250
    系統最低訂購量：20 件（沿用你的規則）
    回傳：(平均單價, 總價)
    """
    total_qty = int(sum(size_counts.values()))
    if total_qty < 20:
        return 0, 0

    small_sizes = ["XS", "S", "M", "L", "XL", "2XL"]
    big_sizes = ["3XL", "4XL", "5XL"]

    small_qty = sum(int(size_counts.get(s, 0)) for s in small_sizes)
    big_qty = sum(int(size_counts.get(s, 0)) for s in big_sizes)

    if total_qty <= 30:
        small_price, big_price = 255, 265
    elif total_qty <= 100:
        small_price, big_price = 245, 255
    else:
        small_price, big_price = 240, 250

    total_price = small_qty * small_price + big_qty * big_price
    avg_unit_price = round(total_price / total_qty) if total_qty > 0 else 0
    return avg_unit_price, total_price


def classify_plan(qty: int, is_double_sided: bool):
    """
    品牌分級：
    - 20–49：團體款 Team Edition
    - 50–99：企業款 Corporate Edition
    - 100+ 或 雙面印刷：品牌款 Brand Edition
    """
    if qty < 20:
        return None, None

    if qty >= 100 or is_double_sided:
        name = "品牌款 Brand Edition"
        desc = "適合有明確品牌定位、需要一體化形象與高識別度的企業 / 品牌專案。"
    elif qty >= 50:
        name = "企業款 Corporate Edition"
        desc = "適合公司制服、活動識別服，重視團隊感與一致的品牌觀感。"
    else:
        name = "團體款 Team Edition"
        desc = "適合班服、社團、活動紀念服，以高 CP 值完成一次性專案。"
    return name, desc


# ==========================================
# 3. 詢價單生成（圖片）
# ==========================================
def get_fonts():
    """取得四種字級的字型物件"""
    if not font_path:
        return (
            ImageFont.load_default(),
            ImageFont.load_default(),
            ImageFont.load_default(),
            ImageFont.load_default(),
        )
    try:
        font_Title = ImageFont.truetype(font_path, 48)
        font_L = ImageFont.truetype(font_path, 32)
        font_M = ImageFont.truetype(font_path, 24)
        font_S = ImageFont.truetype(font_path, 20)
        return font_Title, font_L, font_M, font_S
    except Exception:
        return (
            ImageFont.load_default(),
            ImageFont.load_default(),
            ImageFont.load_default(),
            ImageFont.load_default(),
        )


def load_logo():
    """從 assets 目錄載入 LOGO 做浮水印"""
    candidates = ["LOGO.png", "logo.png", "logo.jpg", "logo.jpeg"]
    for fn in candidates:
        p = ASSETS_DIR / fn
        if p.exists():
            try:
                return Image.open(p).convert("RGBA")
            except Exception:
                continue
    return None


def generate_inquiry_image(img_front, img_back, data, design_list_text, unit_price):
    """
    日系文創質感版詢價單 + 品牌浮水印
    """
    w, h = 1400, 1200
    card = Image.new("RGB", (w, h), "#F7F4EE")  # 暖米白
    draw = ImageDraw.Draw(card)

    font_Title, font_L, font_M, font_S = get_fonts()

    # ========= Header =========
    header_h = 140
    draw.rectangle([(0, 0), (w, header_h)], fill="#F0E6D8")

    draw.text((70, 35), "HSINN ZHANG × MOMO", fill="#4A4A4A", font=font_Title)

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    draw.text((w - 260, 45), f"DATE  {today_str}", fill="#8A7E6A", font=font_M)

    draw.text(
        (72, 95),
        "ORIGINAL TEE ESTIMATE ｜ 客製服飾設計估價",
        fill="#8A7E6A",
        font=font_M,
    )

    # ========= 商品預覽區 =========
    card_y = header_h + 10
    img_box = (80, card_y, w - 80, card_y + 380)
    draw.rounded_rectangle(img_box, radius=26, fill="#FFFFFF")

    draw.text((w // 2 - 70, card_y + 16), "DESIGN PREVIEW", fill="#A1A7AD", font=font_M)

    # 前後圖
    fw = 520
    ratio = fw / img_front.width if img_front.width else 1
    fh = int(img_front.height * ratio) if img_front.height else 1
    res_f = img_front.resize((fw, fh))
    res_b = img_back.resize((fw, int(img_back.height * (fw / img_back.width)))) if img_back.width else img_back

    front_x = 140
    back_x = w - 140 - fw
    img_top = card_y + 50

    card.paste(res_f, (front_x, img_top), res_f)
    card.paste(res_b, (back_x, img_top), res_b)

    # FRONT / BACK 標示
    label_font = font_M

    front_text = "FRONT VIEW"
    fb = draw.textbbox((0, 0), front_text, font=label_font)
    front_label_x = front_x + fw // 2 - (fb[2] - fb[0]) // 2
    front_label_y = img_top - 30
    draw.text((front_label_x, front_label_y), front_text, fill="#939FA8", font=label_font)

    back_text = "BACK VIEW"
    bb = draw.textbbox((0, 0), back_text, font=label_font)
    back_label_x = back_x + fw // 2 - (bb[2] - bb[0]) // 2
    back_label_y = img_top - 30
    draw.text((back_label_x, back_label_y), back_text, fill="#939FA8", font=label_font)

    # ========= 下半部雙欄資訊卡 =========
    left_box = (80, 560, 740, h - 90)
    right_box = (760, 560, w - 80, h - 90)
    draw.rounded_rectangle(left_box, radius=24, fill="#FFFFFF")
    draw.rounded_rectangle(right_box, radius=24, fill="#FFFFFF")

    # LEFT：客戶 & 產品資訊
    lx, cy = 115, 595
    fields = [
        ("CLIENT NAME（客戶稱呼）", data.get("name")),
        ("CONTACT INFO（聯絡方式）", f"{data.get('phone')} / {data.get('line')}"),
        ("PRODUCT SERIES（產品系列）", data.get("series")),
        ("STYLE & COLOR（款式顏色）", data.get("variant")),
        ("PRINTING METHOD（印刷工藝）", "DTF 數位膠膜印製"),
    ]
    for label, value in fields:
        draw.text((lx, cy), label, fill="#9BA3AC", font=font_S)
        draw.text((lx, cy + 26), str(value), fill="#3C434A", font=font_L)
        cy += 86

    # RIGHT：價格＋尺寸＋位置
    rx = 795
    py = 595
    price_box = (rx - 10, py - 6, w - 95, py + 160)
    draw.rounded_rectangle(price_box, radius=18, fill="#FFF3EC")

    draw.text((rx, py), "ESTIMATED TOTAL（預估總計）", fill="#D4684C", font=font_L)
    draw.text((rx, py + 40), f"NT$ {unit_price * int(data['qty']):,}", fill="#C0392B", font=font_Title)
    draw.text(
        (rx, py + 100),
        f"＠ NT$ {data['price']} × {data['qty']} pcs",
        fill="#A27E6F",
        font=font_M,
    )

    py += 190
    draw.text((rx, py), "SIZE BREAKDOWN（尺寸分佈）", fill="#9BA3AC", font=font_S)
    draw.text((rx, py + 26), str(data.get("size_breakdown")), fill="#3C434A", font=font_M)

    py += 80
    draw.text((rx, py), "PRINT LOCATIONS（印刷位置）", fill="#9BA3AC", font=font_S)
    for t in design_list_text:
        py += 30
        draw.text((rx, py), f"• {t}", fill="#3C434A", font=font_M)

    # Footer
    draw.rectangle([(0, h - 70), (w, h)], fill="#C8443B")
    footer_text = "CONFIRMATION｜請將此圖片傳送至 LINE：@727jxovv 完成最終確認與下單"
    draw.text((w // 2 - 380, h - 50), footer_text, fill="white", font=font_M)

    # 浮水印 LOGO
    logo = load_logo()
    if logo is not None:
        max_logo_w = 260
        ratio = max_logo_w / logo.width
        logo_h = int(logo.height * ratio)
        logo = logo.resize((max_logo_w, logo_h))

        if logo.mode != "RGBA":
            logo = logo.convert("RGBA")
        alpha = logo.split()[3]
        alpha = alpha.point(lambda p: int(p * 0.18))  # 約 18% 不透明
        logo.putalpha(alpha)

        lx_logo = w - max_logo_w - 60
        ly_logo = h - logo_h - 130
        card.paste(logo, (lx_logo, ly_logo), logo)

    return card


# ==========================================
# 4. 寫入訂單資料
# ==========================================
def add_order_to_db(data):
    if sh:
        try:
            oid = f"ORD-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            sh.worksheet("orders").append_row(
                [
                    oid,
                    data["name"],
                    data["contact"],
                    data["phone"],
                    data["line"],
                    f"{data['series']}-{data['variant']}",
                    data["qty"],
                    f"{data['size_breakdown']} | ${data['price']}",
                    data.get("promo_code", ""),
                    str(datetime.date.today()),
                ]
            )
            return True
        except Exception:
            return False
    return False


# ==========================================
# 5. UI 佈局與品牌化呈現
# ==========================================
st.markdown(
    """
<style>
    .stApp {background-color: #F5F5F7;}
    div[data-testid="stSidebar"] {background-color: #FFFFFF;}
    h1, h2, h3 {font-family: 'Helvetica', sans-serif;}
</style>
""",
    unsafe_allow_html=True,
)

# Sidebar：品牌資訊＆系統診斷
with st.sidebar:
    owner_path = ASSETS_DIR / "owner.jpg"
    if owner_path.exists():
        st.image(str(owner_path), caption="阿默｜興彰企業")
    else:
        st.info("💡 請上傳 owner.jpg 到 assets 資料夾")

    st.markdown("### 👨‍🔧 關於我們")
    st.info("**興彰企業 x 默默文創**\n📍 彰化市中山路一段556巷23號之7")
    st.success("🆔 **LINE ID: @727jxovv**")

    if not font_path:
        st.error(
            "⚠ 找不到中文字型 NotoSansTC-Regular.ttf，詢價單中的中文字可能顯示異常，"
            "請將字型檔放到專案根目錄或 assets 資料夾。"
        )

    with st.expander("🛠 系統診斷 (System Debug)"):
        st.write(f"字型路徑: `{font_path}`")
        if os.path.exists(str(ASSETS_DIR)):
            st.write("📁 assets 資料夾狀態：")
            st.code(os.listdir(str(ASSETS_DIR)))
        if st.button("手動重新整理網頁"):
            st.rerun()

# Hero 區：品牌定位 & 操作步驟
st.markdown(
    """
# 👕 興彰企業 x 默默文創｜品牌級旗艦版
  
> 從班服、社團服，到企業制服、聯名企劃，都用同一套高標準，穩定輸出你的品牌感。

---

### 💡 為什麼要用這套系統？

- **設計導向，不只是報價表**：先看到成品長什麼樣，再談單價與數量。  
- **品牌一致性控管**：款式、顏色、印刷位置都有紀錄，下次追加不會「長得不一樣」。  
- **溝通更有效率**：版型示意＋正式詢價單，一張圖就能和夥伴、長官、客戶說明企劃。  
- **價格透明可預期**：依件數與正反面印製，自動對應團體款 / 企業款 / 品牌款級距，不用猜。 

---

### 🎯 適用對象

- 想做 **班服 / 社團服 / 活動服**，希望照片、實體都能呈現品牌感的你  
- 公司行號、品牌團隊，希望 **制服與形象服** 有一致的視覺語言與質感  
- 創作者 / IP / 自媒體，希望用 **限量 TEE / 週邊服飾** 做一波有記憶點的策展企劃 

---

### ✅ 使用流程（4 個步驟）

1. **選擇產品 & 數量**  
2. **上傳設計圖檔（可選 AI 去背）**  
3. **查看預估報價與方案分級**  
4. **生成正式詢價單（品牌級版面）並傳給 LINE：@727jxovv**

---
"""
)

st.caption("🚀 興彰企業 x 默默文創｜工廠直營．品牌級品質．透明估價")

# 主體兩欄：左預覽，右設定
c1, c2 = st.columns([1.5, 1])

# =========================
# 右側：產品、尺寸、上傳
# =========================
with c2:
    st.markdown("### 1️⃣ 選擇產品 & 數量")

    if not PRODUCT_CATALOG:
        st.error("⚠️ 資料庫讀取失敗，請確認 products.py 是否在根目錄且 PRODUCT_CATALOG 結構正確。")
        st.stop()

    series_list = list(PRODUCT_CATALOG.keys())
    s = st.selectbox("系列", series_list)
    v = st.selectbox("款式", list(PRODUCT_CATALOG[s].keys()))
    item = PRODUCT_CATALOG.get(s, {}).get(v, {})

    st.caption(f"🚀 {s}｜{v}｜興彰企業 x 默默文創")

    color_options = item.get("colors", ["預設"])
    selected_color_name = st.selectbox("顏色", color_options)
    color_code = item.get("color_map", {}).get(selected_color_name, "")

    base_name = item.get("image_base", "")
    img_url_front = ""
    img_url_back = ""

    if base_name and color_code:
        img_url_front = find_asset_image(base_name, color_code, "front")
        img_url_back = find_asset_image(base_name, color_code, "back")
        # 若 back 找不到，先用 front 頂著顯示（避免 Missing）
        if img_url_front and not img_url_back:
            img_url_back = img_url_front

    st.markdown("---")
    with st.expander("📏 查看尺寸表 (Size Chart)"):
        sz_path = ASSETS_DIR / "size_chart.png"
        if not sz_path.exists():
            sz_path = ASSETS_DIR / "size_chart.jpg"
        if sz_path.exists():
            st.image(str(sz_path))
        else:
            st.warning("請上傳 size_chart 圖檔到 assets 資料夾。")

    # 尺寸輸入（CP101 含 XS）
    size_inputs = {}
    st.markdown("### 尺寸件數設定")
    st.caption("請依實際需求輸入各尺寸件數（**最低總數 20 件**）：")

    is_cp101 = "CP101" in str(v)
    if is_cp101:
        rows = [("XS", "S"), ("M", "L"), ("XL", "2XL"), ("3XL", "4XL"), ("5XL", None)]
    else:
        rows = [("S", "M"), ("L", "XL"), ("2XL", "3XL"), ("4XL", "5XL")]

    for left_size, right_size in rows:
        if right_size is None:
            cols = st.columns(1)
            pair = (left_size,)
        else:
            cols = st.columns(2)
            pair = (left_size, right_size)

        for col, size in zip(cols, pair):
            with col:
                st.markdown(
                    f"""
<div style="
    background-color:#F9FAFB;
    border-radius:8px;
    padding:6px 10px;
    margin-bottom:4px;
    border:1px solid #E1E4EA;
">
  <div style="font-size:10px;color:#A3A8B3;">SIZE</div>
  <div style="font-size:16px;font-weight:600;">{size}</div>
</div>
""",
                    unsafe_allow_html=True,
                )

                size_inputs[size] = st.number_input(
                    label="",
                    min_value=0,
                    step=1,
                    key=f"qty_{size}",
                    label_visibility="collapsed",
                )

    total_qty = int(sum(size_inputs.values()))

    # 2 創意設計 & 上傳
    st.markdown("### 2️⃣ 創意設計 & 上傳")

    tab_f, tab_b = st.tabs(["👕 正面設計", "🔄 背面設計"])

    def render_upload_ui(pos_dict, side_prefix: str):
        """上傳介面 + 刪除按鈕"""
        if not pos_dict:
            st.info("此款式尚未設定印刷位置。")
            return

        pk = st.selectbox(
            f"{'正面' if side_prefix=='front' else '背面'}位置",
            list(pos_dict.keys()),
            key=f"sel_{side_prefix}",
        )
        design_key = f"{side_prefix}_{pk}"

        if design_key not in st.session_state["uploader_keys"]:
            st.session_state["uploader_keys"][design_key] = 0
        uk = st.session_state["uploader_keys"][design_key]

        uf = st.file_uploader(
            f"上傳圖片（{pk}）",
            type=["png", "jpg", "jpeg"],
            key=f"u_{design_key}_{uk}",
        )
        if uf:
            file_bytes = uf.getvalue()
            if design_key not in st.session_state["designs"]:
                d_rot = pos_dict[pk].get("default_rot", 0)
                st.session_state["designs"][design_key] = {
                    "bytes": file_bytes,
                    "rb": False,
                    "sz": 150,
                    "rot": d_rot,
                    "ox": 0,
                    "oy": 0,
                }
            else:
                st.session_state["designs"][design_key]["bytes"] = file_bytes

        if design_key in st.session_state["designs"]:
            if st.button(f"🗑️ 刪除圖片（{pk}）", key=f"btn_clear_{design_key}"):
                del st.session_state["designs"][design_key]
                st.session_state["uploader_keys"][design_key] += 1
                st.rerun()

    with tab_f:
        render_upload_ui(item.get("pos_front", {}), "front")
    with tab_b:
        render_upload_ui(item.get("pos_back", {}), "back")

    has_f = any(k.startswith("front_") for k in st.session_state["designs"].keys())
    has_b = any(k.startswith("back_") for k in st.session_state["designs"].keys())
    is_ds = has_f and has_b

    # CP101 用專屬價，其餘用一般價
    if is_cp101:
        unit_price, total_price = calculate_cp101_price(size_inputs)
    else:
        unit_price = calculate_unit_price(total_qty, is_ds)
        total_price = unit_price * total_qty

    plan_name, plan_desc = classify_plan(total_qty, is_ds)

# =========================
# 左側：即時預覽
# =========================
with c1:
    view_side = st.radio(
        "👁️ 預覽視角",
        ["正面 Front", "背面 Back"],
        horizontal=True,
        label_visibility="collapsed",
    )
    curr_side = "front" if "正面" in view_side else "back"
    st.markdown(f"#### 即時預覽：{v}｜{selected_color_name}")

    target_path = img_url_front if curr_side == "front" else img_url_back
    if target_path and os.path.exists(target_path):
        base = Image.open(target_path).convert("RGBA")
    else:
        base = Image.new("RGBA", (900, 1100), (220, 220, 220))
        draw_tmp = ImageDraw.Draw(base)
        draw_tmp.text((50, 520), "Image Missing in Assets", fill="red")

    final = base.copy()

    for d_key, d_val in st.session_state["designs"].items():
        d_side, d_pos_name = d_key.split("_", 1)
        should_draw = False
        target_pos = None

        if d_side == curr_side:
            should_draw = True
            target_pos = item.get(f"pos_{curr_side}", {}).get(d_pos_name)
        elif curr_side == "back" and d_side == "front" and d_pos_name in SLEEVE_MAPPING:
            target_pos = item.get("pos_back", {}).get(SLEEVE_MAPPING[d_pos_name])
            should_draw = True

        if should_draw and target_pos:
            tx, ty = target_pos["coords"]
            p_img = process_user_image(d_val["bytes"], d_val["rb"])
            wr = d_val["sz"] / p_img.width
            p_img = p_img.resize((d_val["sz"], int(p_img.height * wr)))

            if d_val["rot"] != 0:
                p_img = p_img.rotate(d_val["rot"], expand=True)

            final.paste(
                p_img,
                (
                    int(tx - p_img.width / 2 + d_val["ox"]),
                    int(ty - p_img.height / 2 + d_val["oy"]),
                ),
                p_img,
            )

    st.image(final, use_container_width=True)
    st.markdown("---")

    for d_key in list(st.session_state["designs"].keys()):
        if d_key.startswith(curr_side + "_"):
            d_val = st.session_state["designs"][d_key]
            with st.expander(f"🔧 調整：{d_key.split('_', 1)[1]}", expanded=True):
                with st.form(key=f"form_{d_key}"):
                    new_rb = st.checkbox("✨ AI 智能去背", value=d_val["rb"])
                    new_sz = st.slider("縮放大小", 50, 400, int(d_val["sz"]))
                    new_rot = st.slider("旋轉角度", -180, 180, int(d_val["rot"]))
                    c1a, c2a = st.columns(2)
                    with c1a:
                        new_ox = st.number_input("左右微調 X", -200, 200, int(d_val["ox"]))
                    with c2a:
                        new_oy = st.number_input("上下微調 Y", -200, 200, int(d_val["oy"]))
                    if st.form_submit_button("✅ 確認套用"):
                        d_val.update({"rb": new_rb, "sz": new_sz, "rot": new_rot, "ox": new_ox, "oy": new_oy})
                        st.rerun()

# =========================
# 報價區
# =========================
st.divider()
st.markdown("### 3️⃣ 興彰嚴選報價 & 品牌分級")

if total_qty < 20:
    st.warning("⚠️ 最低訂製量為 20 件，請調整各尺寸件數。")
else:
    cp, cv = st.columns([1, 1.5])

    with cp:
        st.markdown(
            f"""
<div style="background-color:#f8f9fa;padding:20px;border-radius:10px;text-align:center;">
  <p>本次估價所屬方案</p>
  <h4>{plan_name}</h4>
  <hr>
  <p>預估單價</p>
  <h2>NT$ {unit_price}</h2>
  <hr>
  <h3>總計：NT$ {int(total_price):,}</h3>
  <p style="font-size:12px;color:#666;">（依件數與尺寸級距自動計算，實際金額以專人確認為準）</p>
</div>
""",
            unsafe_allow_html=True,
        )

    with cv:
        st.markdown(
            f"""
- 🧩 **方案定位**：{plan_desc}
- 🌈 **全彩印製**：高品質 DTF 數位膠膜，不限色數。
- 🛡️ **免開版費**：報價已含基本印製費，適合少量多樣設計。
- 📦 **獨立包裝**：每件含透明防塵袋，方便倉儲與發放。
- 🚚 **工廠直營**：彰化在地生產，交期可控、品質穩定。
"""
        )

    st.markdown("---")
    st.markdown("#### 4️⃣ 填寫聯絡資料，一鍵生成「品牌級正式詢價單」")

    if st.checkbox("我接受此預估報價，並希望由專人協助確認與優化設計", value=False):
        c1b, c2b = st.columns(2)
        with c1b:
            c_name = st.text_input("您的稱呼 / 單位名稱")
            c_line = st.text_input("LINE ID（用於傳圖與聯絡）")
        with c2b:
            c_phone = st.text_input("手機號碼")
            c_note = st.text_input("需求備註（顏色、風格、希望感覺等）")

        if st.button("🚀 生成正式詢價單（品牌專業版）", type="primary", use_container_width=True):
            if not c_name or not c_line:
                st.error("請至少填寫「稱呼 / 單位名稱」與「LINE ID」。")
            elif not font_path:
                st.error(
                    "目前缺少中文字型檔（NotoSansTC-Regular.ttf），為避免詢價單中文字錯誤，請先補上字型再重新生成。"
                )
            else:
                sz_br = ", ".join([f"{k}*{int(v)}" for k, v in size_inputs.items() if int(v) > 0])

                dt = {
                    "name": c_name,
                    "contact": c_name,
                    "phone": c_phone,
                    "line": c_line,
                    "qty": total_qty,
                    "size_breakdown": sz_br,
                    "series": s,
                    "variant": f"{v} / {selected_color_name}",
                    "price": unit_price,
                    "promo_code": "MomoPro",
                    "note": c_note,
                }

                if sh:
                    add_order_to_db(dt)

                # 背面合成
                if img_url_back and os.path.exists(img_url_back):
                    base_b = Image.open(img_url_back).convert("RGBA")
                else:
                    base_b = Image.new("RGBA", base.size, (240, 240, 240))

                final_b = base_b.copy()
                for dk, dv in st.session_state["designs"].items():
                    ds, dpn = dk.split("_", 1)
                    tp = None
                    if ds == "back":
                        tp = item.get("pos_back", {}).get(dpn)
                    elif ds == "front" and dpn in SLEEVE_MAPPING:
                        tp = item.get("pos_back", {}).get(SLEEVE_MAPPING[dpn])

                    if tp:
                        tx, ty = tp["coords"]
                        pimg = process_user_image(dv["bytes"], dv["rb"])
                        wr = dv["sz"] / pimg.width
                        pimg = pimg.resize((dv["sz"], int(pimg.height * wr)))
                        if dv["rot"] != 0:
                            pimg = pimg.rotate(dv["rot"], expand=True)
                        final_b.paste(
                            pimg,
                            (
                                int(tx - pimg.width / 2 + dv["ox"]),
                                int(ty - pimg.height / 2 + dv["oy"]),
                            ),
                            pimg,
                        )

                design_list = []
                for dk in st.session_state["designs"].keys():
                    ds, dpn = dk.split("_", 1)
                    side_label = "正面" if ds == "front" else "背面"
                    design_list.append(f"{side_label}｜{dpn}")

                receipt = generate_inquiry_image(final, final_b, dt, design_list, unit_price)

                st.success("✅ 品牌級正式詢價單已生成！")
                st.image(receipt, caption="📩 請長按儲存此圖片，並傳給阿默 LINE: @727jxovv")

                st.link_button("👉 立即開啟 LINE 傳送圖檔給阿默", "https://line.me/ti/p/~@727jxovv")
