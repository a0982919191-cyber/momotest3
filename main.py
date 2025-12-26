# -*- coding: utf-8 -*-
# main.py

import streamlit as st
import io
import os
import datetime
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials
from PIL import Image, ImageDraw, ImageFont
from rembg import remove

# --- 從外部檔案匯入產品資料 ---
try:
    from products import PRODUCT_CATALOG
except ImportError:
    st.error("❌ Critical Error: products.py not found.")
    PRODUCT_CATALOG = {}

# ==========================================
# 0. 基礎設定 & 路徑偵測
# ==========================================
st.set_page_config(
    page_title="興彰 x 默默｜品牌級線上設計估價系統",
    page_icon="👕",
    layout="wide"
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

# 正反袖口對應
SLEEVE_MAPPING = {
    "左臂 (Left Sleeve)": "左臂-後 (L.Sleeve Back)",
    "右臂 (Right Sleeve)": "右臂-後 (R.Sleeve Back)",
}

# ==========================================
# 連線 Google Sheet
# ==========================================
@st.cache_resource
def connect_to_gsheet():
    try:
        if "gcp_service_account" in st.secrets:
            creds = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=SCOPES,
            )
            gc = gspread.authorize(creds)
            return gc.open("momo_db")
        return None
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
# 2. 價格計算 + 品牌方案分級
# ==========================================
def calculate_unit_price(qty, is_double_sided):
    """按件數＆是否雙面計算單價"""
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


def classify_plan(qty, is_double_sided):
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
        # 若真的找不到中文字型，就回退預設英文字型
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


def generate_inquiry_image(img_front, img_back, data, design_list_text, unit_price):
    """
    產生最終詢價單圖片
    data: 包含 name, phone, line, qty, size_breakdown, series, variant 等
    design_list_text: 位置清單（已整理好的文字陣列）
    """
    w, h = 1200, 1100
    card = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(card)

    font_Title, font_L, font_M, font_S = get_fonts()

    # Header
    draw.rectangle([(0, 0), (w, 120)], fill="#2c3e50")
    draw.text(
        (50, 35),
        "HSINN ZHANG x MOMO | BRAND ESTIMATE",
        fill="white",
        font=font_Title,
    )
    draw.text(
        (w - 350, 45),
        f"Date: {datetime.date.today()}",
        fill="#ecf0f1",
        font=font_L,
    )

    # 商品預覽
    t_w = 420
    ratio = t_w / img_front.width
    t_h = int(img_front.height * ratio)
    res_f = img_front.resize((t_w, t_h))
    res_b = img_back.resize((t_w, t_h))

    card.paste(res_f, (120, 150), res_f if res_f.mode == "RGBA" else None)
    card.paste(res_b, (660, 150), res_b if res_b.mode == "RGBA" else None)

    draw.text((280, 120), "FRONT VIEW", fill="#7f8c8d", font=font_L)
    draw.text((820, 120), "BACK VIEW", fill="#7f8c8d", font=font_L)

    # Info 分隔線
    y_info = 150 + t_h + 40
    draw.line([(50, y_info), (w - 50, y_info)], fill="#bdc3c7", width=2)

    # 左欄：客戶＋產品資訊
    col1_x = 80
    curr_y = y_info + 40

    fields_L = [
        ("CLIENT NAME (客戶稱呼)", data.get("name")),
        ("CONTACT INFO (聯絡方式)", f"{data.get('phone')} / {data.get('line')}"),
        ("PRODUCT SERIES (產品系列)", data.get("series")),
        ("STYLE & COLOR (款式顏色)", data.get("variant")),
        ("PRINTING METHOD (印刷工藝)", "DTF (Direct to Film 數位膠膜)"),
    ]

    for label, val in fields_L:
        draw.text((col1_x, curr_y), label, fill="#95a5a6", font=font_S)
        draw.text((col1_x, curr_y + 25), str(val), fill="#2c3e50", font=font_L)
        curr_y += 75

    # 右欄：價格、尺寸、位置
    col2_x = 660
    curr_y = y_info + 40

    # 價格框
    draw.rectangle(
        [(col2_x - 20, curr_y - 10), (w - 50, curr_y + 160)],
        fill="#f7f9f9",
    )
    draw.text(
        (col2_x, curr_y),
        "ESTIMATED TOTAL (預估總計)",
        fill="#e74c3c",
        font=font_L,
    )
    draw.text(
        (col2_x, curr_y + 40),
        f"NT$ {unit_price * data.get('qty'):,}",
        fill="#c0392b",
        font=font_Title,
    )
    draw.text(
        (col2_x, curr_y + 100),
        f"(@ NT$ {unit_price} x {data.get('qty')} pcs)",
        fill="#7f8c8d",
        font=font_M,
    )

    curr_y += 180
    draw.text(
        (col2_x, curr_y),
        "SIZE BREAKDOWN (尺寸分佈)",
        fill="#95a5a6",
        font=font_S,
    )
    draw.text(
        (col2_x, curr_y + 25),
        str(data.get("size_breakdown")),
        fill="#2c3e50",
        font=font_M,
    )

    curr_y += 70
    draw.text(
        (col2_x, curr_y),
        "PRINT LOCATIONS (印刷位置)",
        fill="#95a5a6",
        font=font_S,
    )

    loc_y = curr_y + 25
    for item in design_list_text:
        draw.text((col2_x, loc_y), item, fill="#2c3e50", font=font_M)
        loc_y += 30

    # Footer
    draw.rectangle([(0, h - 60), (w, h)], fill="#c0392b")
    footer_text = (
        "CONFIRMATION: 請將此圖片傳送至 LINE: @727jxovv 完成詢價確認。"
    )
    draw.text((120, h - 45), footer_text, fill="white", font=font_M)

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
                    data["promo_code"],
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
# 全局樣式
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
    st.info(
        "**興彰企業 x 默默文創**\n"
        "📍 彰化市中山路一段556巷23號之7"
    )
    st.success("🆔 **LINE ID: @727jxovv**")

    if not font_path:
        st.error(
            "⚠ 找不到中文字型 NotoSansTC-Regular.ttf，"
            "詢價單中的中文字可能顯示異常，"
            "請將字型檔放到專案根目錄或 assets 資料夾。"
        )

    with st.expander("🛠 系統診斷 (System Debug)"):
        st.write(f"專人字型路徑: `{font_path}`")
        if os.path.exists(str(ASSETS_DIR)):
            st.write("📁 assets 資料夾狀態：")
            st.code(os.listdir(str(ASSETS_DIR)))
        if st.button("手動重新整理網頁"):
            st.rerun()

# Hero 區：品牌定位 & 操作步驟
st.markdown(
    """
# 👕 興彰企業 x 默默文創｜品牌級線上設計 & 自助估價

> 從「印製單價」升級為「品牌體驗方案」。  
> 這套系統不只是幫你算價格，而是幫你把團體服、企業服、品牌合作專案，  
> 都用 **同一套專業標準** 做出來。

---

### 🔍 適用對象
- 想做 **班服 / 社團服 / 活動服**，希望質感與照片成品漂亮的你  
- 公司行號、企業品牌，希望 **制服與形象服** 有一體化設計感  
- 創作者 / IP / 品牌，希望用 **限量服飾** 做一波亮眼的品牌企劃

---

### ☑ 使用流程（4 個步驟）
1. **選擇產品 & 數量**：先決定 AG21000 款式與各尺寸件數  
2. **上傳設計圖檔**：可勾選「AI 智能去背」，即時預覽排版位置  
3. **查看預估報價**：系統依件數與印刷面，對應品牌分級與單價  
4. **生成正式詢價單**：一鍵輸出專業版報價圖，直接傳給阿默確認

---
""",
    unsafe_allow_html=False,
)

st.caption(
    "🚀 AG21000 重磅棉T｜興彰企業 x 默默文創｜工廠直營．品牌級品質．透明估價"
)

# 主體兩欄：左預覽，右設定
c1, c2 = st.columns([1.5, 1])

# =========================
# 右側：產品、尺寸、上傳
# =========================
with c2:
    st.markdown("### 1️⃣ 選擇產品 & 數量")

    if not PRODUCT_CATALOG:
        st.error("⚠️ 資料庫讀取失敗，請確認 products.py 是否在根目錄。")
        st.stop()

    series_list = list(PRODUCT_CATALOG.keys())
    s = st.selectbox("系列", series_list)
    v = st.selectbox("款式", list(PRODUCT_CATALOG[s].keys()))
    item = PRODUCT_CATALOG.get(s, {}).get(v, {})

    color_options = item.get("colors", ["預設"])
    selected_color_name = st.selectbox("顏色", color_options)
    color_code = item.get("color_map", {}).get(selected_color_name, "")

    base_name = item.get("image_base", "")
    img_url_front = ""
    img_url_back = ""

    if base_name and color_code:
        f_try = f"{base_name}_{color_code}_front"
        b_try = f"{base_name}_{color_code}_back"
        for ext in [".png", ".jpg"]:
            fp = ASSETS_DIR / (f_try + ext)
            bp = ASSETS_DIR / (b_try + ext)
            if fp.exists():
                img_url_front = str(fp)
            if bp.exists():
                img_url_back = str(bp)

    st.markdown("---")
    with st.expander("📏 查看尺寸表 (Size Chart)"):
        sz_path = ASSETS_DIR / "size_chart.png"
        if not sz_path.exists():
            sz_path = ASSETS_DIR / "size_chart.jpg"
        if sz_path.exists():
            st.image(str(sz_path))
        else:
            st.warning("請上傳 size_chart 圖檔到 assets 資料夾。")

    sizes = ["S", "M", "L", "XL", "2XL", "3XL", "4XL", "5XL"]
    size_inputs = {}
    st.caption("請輸入各尺寸件數（最低訂購 20 件）：")
    cols_size = st.columns(4)
    for i, size in enumerate(sizes):
        with cols_size[i % 4]:
            size_inputs[size] = st.number_input(
                size, min_value=0, step=1, key=f"qty_{size}"
            )
    total_qty = sum(size_inputs.values())

    # 上傳設計
    st.markdown("### 2️⃣ 創意設計 & 上傳")

    tab_f, tab_b = st.tabs(["👕 正面設計", "🔄 背面設計"])

    def render_upload_ui(pos_dict, side_prefix: str):
        """上傳介面 + 刪除按鈕"""
        if not pos_dict:
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
            type=["png", "jpg"],
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
            if st.button(
                f"🗑️ 刪除圖片（{pk}）", key=f"btn_clear_{design_key}"
            ):
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
        base = Image.new("RGBA", (600, 800), (220, 220, 220))
        draw_tmp = ImageDraw.Draw(base)
        draw_tmp.text((50, 350), "Image Missing in Assets", fill="red")

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
            with st.spinner("Processing..."):
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

    # 當前視角可調整的設計區
    for d_key in list(st.session_state["designs"].keys()):
        if d_key.startswith(curr_side + "_"):
            d_val = st.session_state["designs"][d_key]
            with st.expander(f"🔧 調整：{d_key.split('_', 1)[1]}", expanded=True):
                with st.form(key=f"form_{d_key}"):
                    new_rb = st.checkbox("✨ AI 智能去背", value=d_val["rb"])
                    new_sz = st.slider("縮放大小", 50, 400, d_val["sz"])
                    new_rot = st.slider("旋轉角度", -180, 180, d_val["rot"])
                    c1a, c2a = st.columns(2)
                    with c1a:
                        new_ox = st.number_input(
                            "左右微調 X", -100, 100, d_val["ox"]
                        )
                    with c2a:
                        new_oy = st.number_input(
                            "上下微調 Y", -100, 100, d_val["oy"]
                        )
                    if st.form_submit_button("✅ 確認套用"):
                        d_val.update(
                            {
                                "rb": new_rb,
                                "sz": new_sz,
                                "rot": new_rot,
                                "ox": new_ox,
                                "oy": new_oy,
                            }
                        )
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
  <h3>總計：NT$ {total_price:,}</h3>
  <p style="font-size:12px;color:#666;">（依件數與正反面印製自動計算，實際金額以專人確認為準）</p>
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

    if st.checkbox(
        "我接受此預估報價，並希望由專人協助確認與優化設計", value=False
    ):
        with st.container():
            c1b, c2b = st.columns(2)
            with c1b:
                c_name = st.text_input("您的稱呼 / 單位名稱")
                c_line = st.text_input("LINE ID（用於傳圖與聯絡）")
            with c2b:
                c_phone = st.text_input("手機號碼")
                c_note = st.text_input("需求備註（顏色、風格、希望感覺等）")

            if st.button(
                "🚀 生成正式詢價單（品牌專業版）",
                type="primary",
                use_container_width=True,
            ):
                if not c_name or not c_line:
                    st.error("請至少填寫「稱呼 / 單位名稱」與「LINE ID」。")
                elif not font_path:
                    st.error(
                        "目前缺少中文字型檔（NotoSansTC-Regular.ttf），"
                        "為避免詢價單中文字錯誤，請先補上字型再重新生成。"
                    )
                else:
                    sz_br = ", ".join(
                        [f"{k}*{v}" for k, v in size_inputs.items() if v > 0]
                    )
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

                    # 背面成品圖
                    base_b = (
                        Image.open(img_url_back).convert("RGBA")
                        if img_url_back
                        else Image.new("RGBA", (600, 800), (240, 240, 240))
                    )
                    final_b = base_b.copy()
                    for dk, dv in st.session_state["designs"].items():
                        ds, dpn = dk.split("_", 1)
                        tp = None
                        if ds == "back":
                            tp = item.get("pos_back", {}).get(dpn)
                        elif ds == "front" and dpn in SLEEVE_MAPPING:
                            tp = item.get("pos_back", {}).get(
                                SLEEVE_MAPPING[dpn]
                            )
                        if tp:
                            tx, ty = tp["coords"]
                            pimg = process_user_image(dv["bytes"], dv["rb"])
                            wr = dv["sz"] / pimg.width
                            pimg = pimg.resize(
                                (dv["sz"], int(pimg.height * wr))
                            )
                            if dv["rot"] != 0:
                                pimg = pimg.rotate(
                                    dv["rot"], expand=True
                                )
                            final_b.paste(
                                pimg,
                                (
                                    int(
                                        tx
                                        - pimg.width / 2
                                        + dv["ox"]
                                    ),
                                    int(
                                        ty
                                        - pimg.height / 2
                                        + dv["oy"]
                                    ),
                                ),
                                pimg,
                            )

                    # 整理印刷位置文字（比原本的 front_xxx 更友善）
                    design_list = []
                    for dk in st.session_state["designs"].keys():
                        ds, dpn = dk.split("_", 1)
                        side_label = "正面" if ds == "front" else "背面"
                        design_list.append(f"{side_label}｜{dpn}")

                    receipt = generate_inquiry_image(
                        final,
                        final_b,
                        dt,
                        design_list,
                        unit_price,
                    )
                    st.success("✅ 品牌級正式詢價單已生成！")
                    st.image(
                        receipt,
                        caption="📩 請長按儲存此圖片，並傳給阿默 LINE: @727jxovv",
                    )
                    st.link_button(
                        "👉 立即開啟 LINE 傳送圖檔給阿默",
                        "https://line.me/ti/p/~@727jxovv",
                    )
