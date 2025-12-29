# -*- coding: utf-8 -*-
# main.py — 興彰 x 默默｜品牌級線上設計 & 自助估價系統（含會員系統 + 來客統計）

import io
import os
import json
import uuid
import datetime
import hashlib
import hmac
from pathlib import Path

import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# 影像去背（可選）
try:
    from rembg import remove
    REMBG_OK = True
except Exception:
    REMBG_OK = False

# Google Sheet（可選）
try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_OK = True
except Exception:
    GSPREAD_OK = False

# 後台統計（可選）
try:
    import pandas as pd
    PANDAS_OK = True
except Exception:
    PANDAS_OK = False

# --- 匯入產品資料 ---
try:
    from products import PRODUCT_CATALOG
except Exception:
    PRODUCT_CATALOG = {}

# ==========================================
# 0) 基礎設定
# ==========================================
st.set_page_config(
    page_title="興彰 x 默默｜品牌級線上設計估價系統",
    page_icon="👕",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

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

SLEEVE_MAPPING = {
    "左臂 (Left Sleeve)": "左臂-後 (L.Sleeve Back)",
    "右臂 (Right Sleeve)": "右臂-後 (R.Sleeve Back)",
}

# ==========================================
# 1) Google Sheet 連線
# ==========================================
@st.cache_resource
def connect_to_gsheet():
    if not GSPREAD_OK:
        return None
    try:
        if "gcp_service_account" in st.secrets:
            info = st.secrets["gcp_service_account"]
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

def get_or_create_ws(title: str, headers: list[str], rows: int = 2000, cols: int = 30):
    if not sh:
        return None
    try:
        ws = sh.worksheet(title)
        return ws
    except Exception:
        try:
            ws = sh.add_worksheet(title=title, rows=rows, cols=cols)
            ws.append_row(headers)
            return ws
        except Exception:
            return None

# 建表（不影響主流程）
WS_EVENTS = get_or_create_ws(
    "events",
    ["timestamp","date","visitor_id","session_id","event","step","series","product","color","qty","meta_json"],
)
WS_USERS = get_or_create_ws(
    "users",
    ["email","name","role","pw_hash","salt","created_at","last_login_at"],
)
WS_ORDERS = get_or_create_ws(
    "orders",
    ["order_id","name","contact","phone","line","product","qty","price_note","promo_code","date"],
)
WS_LEADS = get_or_create_ws(
    "leads",
    ["lead_id","name","phone","line","series","product","color","qty","note","created_at"],
)

# ==========================================
# 2) Session / Visitor 識別（來客統計基礎）
# ==========================================
def ensure_ids():
    if "visitor_id" not in st.session_state:
        st.session_state["visitor_id"] = str(uuid.uuid4())
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())

ensure_ids()

def log_event(event: str, step: str = "", series: str = "", product: str = "", color: str = "", qty: int = 0, meta: dict | None = None):
    meta = meta or {}
    payload = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "date": datetime.date.today().isoformat(),
        "visitor_id": st.session_state.get("visitor_id", ""),
        "session_id": st.session_state.get("session_id", ""),
        "event": event,
        "step": step,
        "series": series,
        "product": product,
        "color": color,
        "qty": int(qty or 0),
        "meta": meta,
    }

    if WS_EVENTS:
        try:
            WS_EVENTS.append_row([
                payload["timestamp"],
                payload["date"],
                payload["visitor_id"],
                payload["session_id"],
                payload["event"],
                payload["step"],
                payload["series"],
                payload["product"],
                payload["color"],
                payload["qty"],
                json.dumps(payload["meta"], ensure_ascii=False),
            ])
        except Exception:
            pass

if "logged_page_view" not in st.session_state:
    st.session_state["logged_page_view"] = True
    log_event("page_view", step="entry")

# ==========================================
# 3) 會員系統（註冊/登入/角色）
# ==========================================
def pbkdf2_hash(password: str, salt: str, rounds: int = 120_000) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), rounds)
    return dk.hex()

def create_user(email: str, name: str, password: str, role: str = "user") -> tuple[bool, str]:
    if not WS_USERS:
        return False, "目前未連線 Google Sheet，無法啟用會員系統（請先設定憑證）。"
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        return False, "Email 格式不正確。"
    if not password or len(password) < 6:
        return False, "密碼至少 6 碼。"

    try:
        rows = WS_USERS.get_all_records()
        if any((r.get("email","").strip().lower() == email) for r in rows):
            return False, "此 Email 已註冊。"
    except Exception:
        pass

    salt = uuid.uuid4().hex
    pw_hash = pbkdf2_hash(password, salt)
    now = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        WS_USERS.append_row([email, name, role, pw_hash, salt, now, ""])
        log_event("signup", step="auth", meta={"email": email, "role": role})
        return True, "註冊成功。"
    except Exception:
        return False, "寫入 users 失敗（請確認 Sheet 權限）。"

def verify_user(email: str, password: str) -> tuple[bool, dict, str]:
    if not WS_USERS:
        return False, {}, "目前未連線 Google Sheet，無法登入（請先設定憑證）。"
    email = (email or "").strip().lower()
    try:
        rows = WS_USERS.get_all_records()
    except Exception:
        return False, {}, "讀取 users 失敗（請確認 Sheet 權限）。"

    user = None
    for r in rows:
        if (r.get("email","").strip().lower() == email):
            user = r
            break
    if not user:
        return False, {}, "帳號不存在。"

    salt = str(user.get("salt",""))
    pw_hash = str(user.get("pw_hash",""))
    calc = pbkdf2_hash(password, salt)
    if not hmac.compare_digest(calc, pw_hash):
        return False, {}, "密碼錯誤。"

    # 更新 last_login_at（不影響登入）
    try:
        all_values = WS_USERS.get_all_values()
        # 找到該 email 的 row index
        idx = None
        for i in range(1, len(all_values)):
            if all_values[i][0].strip().lower() == email:
                idx = i + 1
                break
        if idx:
            WS_USERS.update_cell(idx, 7, datetime.datetime.now().isoformat(timespec="seconds"))
    except Exception:
        pass

    safe_user = {
        "email": user.get("email",""),
        "name": user.get("name",""),
        "role": user.get("role","user") or "user",
    }
    log_event("login", step="auth", meta={"email": email, "role": safe_user["role"]})
    return True, safe_user, "登入成功。"

def logout():
    st.session_state.pop("auth_user", None)
    log_event("logout", step="auth")
    st.rerun()

def require_auth():
    return st.session_state.get("auth_user")

# ==========================================
# 4) 影像處理
# ==========================================
@st.cache_data(show_spinner=False)
def process_user_image(uploaded_file_bytes: bytes, apply_rb: bool):
    img = Image.open(io.BytesIO(uploaded_file_bytes)).convert("RGBA")
    max_width = 1200
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)))

    if apply_rb and REMBG_OK:
        img = remove(img)

    return img

# ==========================================
# 5) 價格計算
# ==========================================
def calculate_unit_price(qty: int, is_double_sided: bool) -> int:
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

def calculate_cp101_price(size_counts: dict) -> tuple[int, int]:
    """
    CP101 價格級距：
    - <=30：XS–2XL=255 / 3XL–5XL=265
    - <=100：XS–2XL=245 / 3XL–5XL=255
    - >100：XS–2XL=240 / 3XL–5XL=250
    系統最低訂量：20
    """
    total_qty = sum(size_counts.values())
    if total_qty < 20:
        return 0, 0

    small_sizes = ["XS", "S", "M", "L", "XL", "2XL"]
    big_sizes = ["3XL", "4XL", "5XL"]

    small_qty = sum(size_counts.get(s, 0) for s in small_sizes)
    big_qty = sum(size_counts.get(s, 0) for s in big_sizes)

    if total_qty <= 30:
        small_price, big_price = 255, 265
    elif total_qty <= 100:
        small_price, big_price = 245, 255
    else:
        small_price, big_price = 240, 250

    total_price = small_qty * small_price + big_qty * big_price
    avg_unit_price = round(total_price / total_qty) if total_qty else 0
    return avg_unit_price, total_price

def classify_plan(qty: int, is_double_sided: bool) -> tuple[str | None, str | None]:
    if qty < 20:
        return None, None
    if qty >= 100 or is_double_sided:
        return "品牌款 Brand Edition", "適合有明確品牌定位、需要一體化形象與高識別度的企業 / 品牌專案。"
    if qty >= 50:
        return "企業款 Corporate Edition", "適合公司制服、活動識別服，重視團隊感與一致的品牌觀感。"
    return "團體款 Team Edition", "適合班服、社團、活動紀念服，以高 CP 值完成一次性專案。"

# ==========================================
# 6) 詢價單圖片生成
# ==========================================
def get_fonts():
    if not font_path:
        f = ImageFont.load_default()
        return f, f, f, f
    try:
        return (
            ImageFont.truetype(font_path, 48),
            ImageFont.truetype(font_path, 32),
            ImageFont.truetype(font_path, 24),
            ImageFont.truetype(font_path, 20),
        )
    except Exception:
        f = ImageFont.load_default()
        return f, f, f, f

def load_logo():
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
    w, h = 1400, 1200
    card = Image.new("RGB", (w, h), "#F7F4EE")
    draw = ImageDraw.Draw(card)
    font_Title, font_L, font_M, font_S = get_fonts()

    header_h = 140
    draw.rectangle([(0, 0), (w, header_h)], fill="#F0E6D8")
    draw.text((70, 35), "HSINN ZHANG × MOMO", fill="#4A4A4A", font=font_Title)

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    draw.text((w - 260, 45), f"DATE  {today_str}", fill="#8A7E6A", font=font_M)
    draw.text((72, 95), "ORIGINAL TEE ESTIMATE ｜ 客製服飾設計估價", fill="#8A7E6A", font=font_M)

    card_y = header_h + 10
    img_box = (80, card_y, w - 80, card_y + 380)
    draw.rounded_rectangle(img_box, radius=26, fill="#FFFFFF")
    draw.text((w // 2 - 70, card_y + 16), "DESIGN PREVIEW", fill="#A1A7AD", font=font_M)

    fw = 520
    ratio = fw / img_front.width
    fh = int(img_front.height * ratio)
    res_f = img_front.resize((fw, fh))
    res_b = img_back.resize((fw, fh))

    front_x = 140
    back_x = w - 140 - fw
    img_top = card_y + 50
    card.paste(res_f, (front_x, img_top), res_f)
    card.paste(res_b, (back_x, img_top), res_b)

    # labels
    front_text = "FRONT VIEW"
    fb = draw.textbbox((0, 0), front_text, font=font_M)
    draw.text((front_x + fw // 2 - (fb[2] - fb[0]) // 2, img_top - 30), front_text, fill="#939FA8", font=font_M)

    back_text = "BACK VIEW"
    bb = draw.textbbox((0, 0), back_text, font=font_M)
    draw.text((back_x + fw // 2 - (bb[2] - bb[0]) // 2, img_top - 30), back_text, fill="#939FA8", font=font_M)

    left_box = (80, 560, 740, h - 90)
    right_box = (760, 560, w - 80, h - 90)
    draw.rounded_rectangle(left_box, radius=24, fill="#FFFFFF")
    draw.rounded_rectangle(right_box, radius=24, fill="#FFFFFF")

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

    rx = 795
    py = 595
    price_box = (rx - 10, py - 6, w - 95, py + 160)
    draw.rounded_rectangle(price_box, radius=18, fill="#FFF3EC")
    draw.text((rx, py), "ESTIMATED TOTAL（預估總計）", fill="#D4684C", font=font_L)
    draw.text((rx, py + 40), f"NT$ {unit_price * data['qty']:,}", fill="#C0392B", font=font_Title)
    draw.text((rx, py + 100), f"＠ NT$ {data['price']} × {data['qty']} pcs", fill="#A27E6F", font=font_M)

    py += 190
    draw.text((rx, py), "SIZE BREAKDOWN（尺寸分佈）", fill="#9BA3AC", font=font_S)
    draw.text((rx, py + 26), str(data.get("size_breakdown")), fill="#3C434A", font=font_M)

    py += 80
    draw.text((rx, py), "PRINT LOCATIONS（印刷位置）", fill="#9BA3AC", font=font_S)
    for t in design_list_text:
        py += 30
        draw.text((rx, py), f"• {t}", fill="#3C434A", font=font_M)

    draw.rectangle([(0, h - 70), (w, h)], fill="#C8443B")
    footer_text = "CONFIRMATION｜請將此圖片傳送至 LINE：@727jxovv 完成最終確認與下單"
    draw.text((w // 2 - 380, h - 50), footer_text, fill="white", font=font_M)

    logo = load_logo()
    if logo is not None:
        max_logo_w = 260
        ratio = max_logo_w / logo.width
        logo_h = int(logo.height * ratio)
        logo = logo.resize((max_logo_w, logo_h)).convert("RGBA")
        alpha = logo.split()[3].point(lambda p: int(p * 0.18))
        logo.putalpha(alpha)
        card.paste(logo, (w - max_logo_w - 60, h - logo_h - 130), logo)

    return card

# ==========================================
# 7) 寫入 leads / orders
# ==========================================
def add_lead_to_db(dt: dict) -> bool:
    if not WS_LEADS:
        return False
    try:
        lead_id = f"LEAD-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        WS_LEADS.append_row([
            lead_id,
            dt.get("name",""),
            dt.get("phone",""),
            dt.get("line",""),
            dt.get("series",""),
            dt.get("product",""),
            dt.get("color",""),
            int(dt.get("qty",0)),
            dt.get("note",""),
            datetime.datetime.now().isoformat(timespec="seconds"),
        ])
        return True
    except Exception:
        return False

def add_order_to_db(dt: dict) -> bool:
    if not WS_ORDERS:
        return False
    try:
        oid = f"ORD-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
        WS_ORDERS.append_row([
            oid,
            dt.get("name",""),
            dt.get("contact",""),
            dt.get("phone",""),
            dt.get("line",""),
            dt.get("product",""),
            int(dt.get("qty",0)),
            dt.get("price_note",""),
            dt.get("promo_code",""),
            str(datetime.date.today()),
        ])
        return True
    except Exception:
        return False

# ==========================================
# 8) assets 找圖（大小寫/全小寫容錯）
# ==========================================
def resolve_asset_paths(base_name: str, color_code: str):
    """
    回傳：(front_path, back_path, tried_list)
    嘗試 base/code 的原樣 + lower + upper，並試副檔名 png/jpg/jpeg
    """
    tried = []
    if not base_name or not color_code:
        return "", "", tried

    base_candidates = [base_name, base_name.lower(), base_name.upper()]
    code_candidates = [color_code, color_code.lower(), color_code.upper()]

    seen = set()
    for b in base_candidates:
        for c in code_candidates:
            key = (b, c)
            if key in seen:
                continue
            seen.add(key)

            f_try = f"{b}_{c}_front"
            b_try = f"{b}_{c}_back"
            for ext in [".png", ".jpg", ".jpeg"]:
                fp = ASSETS_DIR / (f_try + ext)
                bp = ASSETS_DIR / (b_try + ext)
                tried.append(fp.name)
                tried.append(bp.name)
                if fp.exists() and bp.exists():
                    return str(fp), str(bp), tried


# ==========================================
# 9) UI：全局樣式
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

# ==========================================
# 10) Sidebar：登入/登出 + 導航
# ==========================================
with st.sidebar:
    owner_path = ASSETS_DIR / "owner.jpg"
    if owner_path.exists():
        st.image(str(owner_path), caption="阿默｜興彰企業")
    else:
        st.info("💡 可上傳 owner.jpg 到 assets 資料夾（選配）")

    st.markdown("### 👨‍🔧 關於我們")
    st.info("**興彰企業 x 默默文創**\n📍 彰化市中山路一段556巷23號之7")
    st.success("🆔 **LINE ID: @727jxovv**")

    if not font_path:
        st.warning("⚠ 建議放入 NotoSansTC-Regular.ttf（避免詢價單中文字體異常）")

    st.markdown("---")

    auth_user = require_auth()

    # 登入/註冊區
    if not auth_user:
        st.markdown("### 🔐 會員登入")
        with st.expander("登入", expanded=True):
            email = st.text_input("Email", key="login_email")
            pw = st.text_input("Password", type="password", key="login_pw")
            if st.button("登入", use_container_width=True):
                ok, user, msg = verify_user(email, pw)
                if ok:
                    st.session_state["auth_user"] = user
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

        with st.expander("註冊新帳號", expanded=False):
            r_email = st.text_input("Email（註冊）", key="reg_email")
            r_name = st.text_input("姓名/單位", key="reg_name")
            r_pw = st.text_input("Password（至少6碼）", type="password", key="reg_pw")
            # 第一個註冊的人自動變 admin（方便你接管後台）
            is_first_admin = False
            try:
                if WS_USERS:
                    is_first_admin = (len(WS_USERS.get_all_records()) == 0)
            except Exception:
                pass
            role = "admin" if is_first_admin else "user"
            st.caption(f"本次註冊角色：{role}")
            if st.button("註冊", use_container_width=True):
                ok, msg = create_user(r_email, r_name, r_pw, role=role)
                if ok:
                    st.success(msg + " 請回到登入。")
                else:
                    st.error(msg)

        nav = "前台系統"
    else:
        st.markdown("### ✅ 已登入")
        st.write(f"**{auth_user.get('name','')}**")
        st.caption(auth_user.get("email",""))
        st.caption(f"Role：{auth_user.get('role','user')}")
        if st.button("登出", use_container_width=True):
            logout()

        # 導航
        nav_options = ["前台系統"]
        if auth_user.get("role") == "admin":
            nav_options.append("管理後台")
        nav = st.radio("導覽", nav_options)

    with st.expander("🛠 系統診斷 (System Debug)", expanded=False):
        st.write(f"字型路徑: `{font_path}`")
        st.write(f"assets 路徑: `{ASSETS_DIR}`")
        if ASSETS_DIR.exists():
            files = sorted(os.listdir(str(ASSETS_DIR)))
            st.code("\n".join(files[:200]) + ("\n...(略)" if len(files) > 200 else ""))
        st.write(f"Google Sheet: {'✅ 已連線' if sh else '❌ 未連線'}")
        st.write(f"rembg: {'✅ 可用' if REMBG_OK else '❌ 不可用（仍可上傳，只是不能去背）'}")

# ==========================================
# 11) 管理後台（admin）
# ==========================================
def admin_dashboard():
    st.markdown("# 📊 管理後台｜來客統計 & 漏斗")
    if not sh or not WS_EVENTS:
        st.error("後台需要 Google Sheet 連線（momo_db / events）。請先設定憑證。")
        return
    if not PANDAS_OK:
        st.warning("目前環境缺少 pandas，將以簡化模式顯示。")
        return

    try:
        rows = WS_EVENTS.get_all_records()
        if not rows:
            st.info("目前尚無 events 資料。")
            return
        df = pd.DataFrame(rows)
    except Exception:
        st.error("讀取 events 失敗（請確認 Sheet 權限）。")
        return

    # 基礎清理
    for c in ["qty"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    # 篩選區
    st.markdown("## 篩選")
    col1, col2, col3 = st.columns(3)
    with col1:
        dates = sorted(df["date"].dropna().unique().tolist())
        date_from = st.selectbox("起始日期", dates, index=max(0, len(dates) - 7))
    with col2:
        date_to = st.selectbox("結束日期", dates, index=len(dates) - 1)
    with col3:
        evt = st.selectbox("事件", ["(全部)"] + sorted(df["event"].dropna().unique().tolist()))

    df2 = df[(df["date"] >= date_from) & (df["date"] <= date_to)]
    if evt != "(全部)":
        df2 = df2[df2["event"] == evt]

    st.markdown("## KPI 概覽")
    pv = df2[df2["event"] == "page_view"]["session_id"].nunique()
    visitors = df2["visitor_id"].nunique()
    leads = df2[df2["event"] == "lead_submit"]["session_id"].nunique()
    conv = (leads / pv * 100) if pv else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Sessions（進站）", pv)
    k2.metric("Visitors（訪客）", visitors)
    k3.metric("Leads（送出詢價）", leads)
    k4.metric("轉換率", f"{conv:.1f}%")

    st.markdown("## 漏斗（簡化）")
    step1 = df2[df2["event"] == "select_product"]["session_id"].nunique()
    step2 = df2[df2["event"] == "upload_design"]["session_id"].nunique()
    step3 = df2[df2["event"] == "view_quote"]["session_id"].nunique()
    step4 = df2[df2["event"] == "lead_submit"]["session_id"].nunique()
    st.write({
        "Step1 選品": step1,
        "Step2 上傳": step2,
        "Step3 看報價": step3,
        "Step4 送出": step4,
    })

    st.markdown("## 熱門產品排行（select_product）")
    df_sel = df2[df2["event"] == "select_product"].copy()
    if not df_sel.empty:
        rank = (df_sel.groupby(["series","product","color"]).size().reset_index(name="count")
                .sort_values("count", ascending=False).head(20))
        st.dataframe(rank, use_container_width=True)
    else:
        st.info("範圍內沒有 select_product 資料。")

    st.markdown("## 原始 events（抽樣）")
    st.dataframe(df2.sort_values("timestamp", ascending=False).head(200), use_container_width=True)

# ==========================================
# 12) 前台主系統（估價 + 設計）
# ==========================================
def app_front():
    if not PRODUCT_CATALOG:
        st.error("找不到或讀不到 products.py（PRODUCT_CATALOG 為空）。請確認檔案是否在專案根目錄。")
        return

    st.markdown(
        """
# 👕 興彰企業 x 默默文創｜品牌級旗艦版
  
> 從班服、社團服，到企業制服、聯名企劃，都用同一套高標準，穩定輸出你的品牌感。
---
"""
    )
    st.caption("🚀 工廠直營．品牌級品質．透明估價（含會員系統 & 來客統計）")

    # Session state 初始化
    if "designs" not in st.session_state:
        st.session_state["designs"] = {}
    if "uploader_keys" not in st.session_state:
        st.session_state["uploader_keys"] = {}

    c1, c2 = st.columns([1.5, 1])

    # ================
    # 右側：Step1/2
    # ================
    with c2:
        st.markdown("### 1️⃣ 選擇產品 & 數量")

        series_list = list(PRODUCT_CATALOG.keys())
        s = st.selectbox("系列", series_list)
        v = st.selectbox("款式", list(PRODUCT_CATALOG[s].keys()))
        item = PRODUCT_CATALOG.get(s, {}).get(v, {})

        color_options = item.get("colors", ["預設"])
        selected_color_name = st.selectbox("顏色", color_options)
        color_code = item.get("color_map", {}).get(selected_color_name, "")
        base_name = item.get("image_base", "")

        img_url_front, img_url_back, tried_files = resolve_asset_paths(base_name, color_code)

        # 事件：選品（避免 rerun 洗爆）
        curr_sel = f"{s}|{v}|{selected_color_name}"
        if st.session_state.get("last_sel") != curr_sel:
            st.session_state["last_sel"] = curr_sel
            log_event("select_product", step="step1", series=s, product=v, color=selected_color_name, qty=0,
                      meta={"color_code": color_code, "image_base": base_name})

        if not img_url_front or not img_url_back:
            with st.expander("🧯 找不到衣服底圖？點我看原因（Debug）", expanded=False):
                st.write("系統參數：")
                st.code({"image_base": base_name, "color_code": color_code, "selected_color": selected_color_name})
                st.write("系統嘗試檔名：")
                st.code("\n".join(tried_files[:60]) + ("\n...(略)" if len(tried_files) > 60 else ""))
                st.warning("你的 assets 檔名若全小寫：products.py 的 image_base / color_map 建議全小寫（CP101 已處理）。")

        st.markdown("---")
        with st.expander("📏 查看尺寸表 (Size Chart)"):
            # ✅ CP101 專屬尺寸表
            if "CP101" in v:
                sz_path = ASSETS_DIR / "cp101_size_chart.png"
                if sz_path.exists():
                    st.image(str(sz_path))
                else:
                    st.warning("找不到 cp101_size_chart.png，請上傳到 assets 資料夾。")
            else:
                sz_path = ASSETS_DIR / "size_chart.png"
                if not sz_path.exists():
                    sz_path = ASSETS_DIR / "size_chart.jpg"
                if sz_path.exists():
                    st.image(str(sz_path))
                else:
                    st.warning("請上傳 size_chart.png 或 size_chart.jpg 到 assets 資料夾。")

        # 尺寸輸入（CP101 需要 XS）
        size_inputs = {}
        st.markdown("### 尺寸件數設定")
        st.caption("請依實際需求輸入各尺寸件數（**最低總數 20 件**）：")

        if "CP101" in v:
            rows = [("XS", "S"), ("M", "L"), ("XL", "2XL"), ("3XL", "4XL"), ("5XL", "")]
        else:
            rows = [("S", "M"), ("L", "XL"), ("2XL", "3XL"), ("4XL", "5XL")]

        for left_size, right_size in rows:
            cols = st.columns(2)
            for col, size in zip(cols, (left_size, right_size)):
                with col:
                    if not size:
                        st.empty()
                        continue
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
                        key=f"qty_{v}_{size}",
                        label_visibility="collapsed",
                    )

        total_qty = sum(size_inputs.values())

        st.markdown("### 2️⃣ 創意設計 & 上傳")
        tab_f, tab_b = st.tabs(["👕 正面設計", "🔄 背面設計"])

        def render_upload_ui(pos_dict, side_prefix: str):
            if not pos_dict:
                st.info("此產品未設定印刷位置。")
                return

            pk = st.selectbox(
                f"{'正面' if side_prefix=='front' else '背面'}位置",
                list(pos_dict.keys()),
                key=f"sel_{v}_{side_prefix}",
            )
            design_key = f"{side_prefix}_{pk}"

            if design_key not in st.session_state["uploader_keys"]:
                st.session_state["uploader_keys"][design_key] = 0
            uk = st.session_state["uploader_keys"][design_key]

            uf = st.file_uploader(
                f"上傳圖片（{pk}）",
                type=["png", "jpg", "jpeg"],
                key=f"u_{v}_{design_key}_{uk}",
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

                # ✅ 事件：上傳
                log_event(
                    "upload_design",
                    step="step2",
                    series=s,
                    product=v,
                    color=selected_color_name,
                    qty=int(total_qty),
                    meta={"pos": pk, "filename": uf.name, "bytes": len(file_bytes)},
                )

            if design_key in st.session_state["designs"]:
                if st.button(f"🗑️ 刪除圖片（{pk}）", key=f"btn_clear_{v}_{design_key}"):
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

        if "CP101" in v:
            unit_price, total_price = calculate_cp101_price(size_inputs)
        else:
            unit_price = calculate_unit_price(total_qty, is_ds)
            total_price = unit_price * total_qty

        plan_name, plan_desc = classify_plan(total_qty, is_ds)

    # ================
    # 左側：即時預覽
    # ================
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
            base = Image.new("RGBA", (900, 900), (220, 220, 220))
            d = ImageDraw.Draw(base)
            d.text((50, 50), "Image Missing in Assets", fill="red")

        final = base.copy()

        for d_key, d_val in st.session_state["designs"].items():
            d_side, d_pos_name = d_key.split("_", 1)
            should_draw = False
            target_pos = None

            if d_side == curr_side:
                should_draw = True
                target_pos = item.get(f"pos_{curr_side}", {}).get(d_pos_name)

            # AG21000：袖子正反映射（CP101 不需要）
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
                    (int(tx - p_img.width / 2 + d_val["ox"]), int(ty - p_img.height / 2 + d_val["oy"])),
                    p_img,
                )

        st.image(final, use_container_width=True)
        st.markdown("---")

        for d_key in list(st.session_state["designs"].keys()):
            if d_key.startswith(curr_side + "_"):
                d_val = st.session_state["designs"][d_key]
                with st.expander(f"🔧 調整：{d_key.split('_', 1)[1]}", expanded=True):
                    with st.form(key=f"form_{v}_{d_key}"):
                        new_rb = st.checkbox("✨ AI 智能去背", value=d_val["rb"], disabled=(not REMBG_OK))
                        new_sz = st.slider("縮放大小", 50, 400, d_val["sz"])
                        new_rot = st.slider("旋轉角度", -180, 180, d_val["rot"])
                        a, b = st.columns(2)
                        with a:
                            new_ox = st.number_input("左右微調 X", -200, 200, d_val["ox"])
                        with b:
                            new_oy = st.number_input("上下微調 Y", -200, 200, d_val["oy"])

                        if st.form_submit_button("✅ 確認套用"):
                            d_val.update({"rb": new_rb, "sz": new_sz, "rot": new_rot, "ox": new_ox, "oy": new_oy})
                            log_event("adjust_design", step="step2", series=s, product=v, color=selected_color_name, qty=int(total_qty),
                                      meta={"key": d_key, "rb": new_rb, "sz": new_sz, "rot": new_rot, "ox": new_ox, "oy": new_oy})
                            st.rerun()

    # ================
    # Step3：報價
    # ================
    st.divider()
    st.markdown("### 3️⃣ 興彰嚴選報價 & 品牌分級")

    if total_qty < 20:
        st.warning("⚠️ 最低訂製量為 20 件，請調整各尺寸件數。")
    else:
        if "logged_view_quote" not in st.session_state:
            st.session_state["logged_view_quote"] = True
            log_event("view_quote", step="step3", series=s, product=v, color=selected_color_name, qty=int(total_qty),
                      meta={"unit_price": unit_price, "total_price": total_price, "plan": plan_name})

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

        # ================
        # Step4：詢價（同時寫 leads + orders + events）
        # ================
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
                    st.error("缺少中文字型檔 NotoSansTC-Regular.ttf，建議補上避免詢價單中文字體錯誤。")
                else:
                    sz_br = ", ".join([f"{k}*{v}" for k, v in size_inputs.items() if v > 0])

                    # events：送出詢價
                    log_event("lead_submit", step="step4", series=s, product=v, color=selected_color_name, qty=int(total_qty),
                              meta={"name": c_name, "line": c_line, "phone": c_phone, "note": c_note})

                    # leads：寫入（你要的「來客訊息」本體）
                    add_lead_to_db({
                        "name": c_name,
                        "phone": c_phone,
                        "line": c_line,
                        "series": s,
                        "product": v,
                        "color": selected_color_name,
                        "qty": int(total_qty),
                        "note": c_note,
                    })

                    # 背面底圖
                    if img_url_back and os.path.exists(img_url_back):
                        base_b = Image.open(img_url_back).convert("RGBA")
                    else:
                        base_b = Image.new("RGBA", final.size, (240, 240, 240, 255))

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
                                (int(tx - pimg.width / 2 + dv["ox"]), int(ty - pimg.height / 2 + dv["oy"])),
                                pimg,
                            )

                    design_list = []
                    for dk in st.session_state["designs"].keys():
                        ds, dpn = dk.split("_", 1)
                        side_label = "正面" if ds == "front" else "背面"
                        design_list.append(f"{side_label}｜{dpn}")

                    dt_order = {
                        "name": c_name,
                        "contact": c_name,
                        "phone": c_phone,
                        "line": c_line,
                        "product": f"{s}-{v} / {selected_color_name}",
                        "qty": int(total_qty),
                        "price_note": f"{sz_br} | NT$ {unit_price} | Total NT$ {total_price}",
                        "promo_code": "MomoPro",
                    }
                    order_ok = add_order_to_db(dt_order)
                    if order_ok:
                        log_event("order_saved", step="step4", series=s, product=v, color=selected_color_name, qty=int(total_qty))

                    receipt = generate_inquiry_image(
                        final,
                        final_b,
                        {
                            "name": c_name,
                            "phone": c_phone,
                            "line": c_line,
                            "qty": int(total_qty),
                            "size_breakdown": sz_br,
                            "series": s,
                            "variant": f"{v} / {selected_color_name}",
                            "price": unit_price,
                        },
                        design_list,
                        unit_price,
                    )

                    st.success("✅ 品牌級正式詢價單已生成！")
                    st.image(receipt, caption="📩 請儲存此圖片並傳給阿默 LINE: @727jxovv")
                    st.link_button("👉 立即開啟 LINE 傳送圖檔給阿默", "https://line.me/ti/p/~@727jxovv")

# ==========================================
# 13) 入口：依 nav 切換
# ==========================================
if nav == "管理後台":
    # 只有 admin 才看得到
    u = require_auth()
    if not u or u.get("role") != "admin":
        st.error("權限不足。")
    else:
        admin_dashboard()
else:
    app_front()


