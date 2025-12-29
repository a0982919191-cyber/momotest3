# -*- coding: utf-8 -*-
# main.py － 興彰 x 默默｜品牌級線上設計 & 自助估價系統（含會員95折 + 訪客分析）

import io
import os
import json
import uuid
import re
import time
import hmac
import hashlib
import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from PIL import Image, ImageDraw, ImageFont
from rembg import remove

# --- 從外部檔案匯入產品資料 ---
try:
    from products import PRODUCT_CATALOG
except ImportError:
    st.set_page_config(page_title="興彰 x 默默｜線上設計估價", page_icon="👕", layout="wide")
    st.error("❌ Critical Error: 找不到 products.py，請確認檔案是否存在於專案根目錄。")
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
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

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

# 正反袖口對應（AG21000 用）
SLEEVE_MAPPING = {
    "左臂 (Left Sleeve)": "左臂-後 (L.Sleeve Back)",
    "右臂 (Right Sleeve)": "右臂-後 (R.Sleeve Back)",
}

# 會員密碼加鹽加胡椒（建議放環境變數，避免寫死）
PEPPER_ENV_KEY = "MEMBER_PEPPER"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ==========================================
# 連線 Google Sheet（支援 st.secrets 或環境變數）
# ==========================================
@st.cache_resource
def connect_to_gsheet():
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

def ensure_worksheet(sheet, title: str, headers: list) -> Optional[gspread.Worksheet]:
    """
    確保工作表存在且表頭正確（不存在就建立；有但空就補表頭）。
    """
    if not sheet:
        return None
    try:
        try:
            ws = sheet.worksheet(title)
        except Exception:
            ws = sheet.add_worksheet(title=title, rows=1000, cols=max(10, len(headers) + 2))
            ws.append_row(headers)
            return ws

        # 若第一列是空（或資料列不足），補表頭
        values = ws.get_all_values()
        if not values:
            ws.append_row(headers)
        else:
            # 若第一列不像表頭（長度不足/不一致），也補一列表頭（避免破壞既有資料）
            if len(values[0]) < max(5, len(headers) // 2):
                ws.insert_row(headers, 1)
        return ws
    except Exception:
        return None

ORDERS_HEADERS = [
    "order_id", "client_name", "contact", "phone", "line",
    "product", "qty", "size_breakdown",
    "unit_price_before_discount", "total_before_discount",
    "discount_label", "discount_rate", "total_after_discount",
    "promo_code", "note",
    "member_email",
    "created_at",
    "session_id",
]

MEMBERS_HEADERS = [
    "email", "name", "salt", "pw_hash",
    "tier", "discount_rate",
    "created_at", "last_login_at",
]

VISITOR_HEADERS = [
    "log_id", "session_id", "ts",
    "event", "screen", "message",
    "series", "variant", "color",
    "qty", "is_double_sided",
    "member_email",
    "elapsed_seconds",
    "client_ip_hint",
    "user_agent_hint",
]

ws_orders = ensure_worksheet(sh, "orders", ORDERS_HEADERS)
ws_members = ensure_worksheet(sh, "members", MEMBERS_HEADERS)
ws_visitor = ensure_worksheet(sh, "visitor_logs", VISITOR_HEADERS)

# ==========================================
# Session state 初始化
# ==========================================
if "designs" not in st.session_state:
    st.session_state["designs"] = {}
if "uploader_keys" not in st.session_state:
    st.session_state["uploader_keys"] = {}

# 會員狀態
if "member" not in st.session_state:
    st.session_state["member"] = None

# 訪客追蹤（同一個瀏覽器分頁同一次會話）
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())
if "session_started_at" not in st.session_state:
    st.session_state["session_started_at"] = time.time()
if "last_seen_at" not in st.session_state:
    st.session_state["last_seen_at"] = time.time()
if "visitor_logged_start" not in st.session_state:
    st.session_state["visitor_logged_start"] = False

def get_elapsed_seconds() -> int:
    return int(time.time() - float(st.session_state.get("session_started_at", time.time())))

def safe_ip_useragent_hints() -> Tuple[str, str]:
    """
    Streamlit 原生不保證可拿到 IP/User-Agent，這裡用『提示欄位』避免誤導。
    若你部署在反向代理（Nginx/Cloudflare）可改為讀 header，但需自行接入。
    """
    return ("N/A", "N/A")

def local_log_append(filepath: Path, row: list):
    filepath.parent.mkdir(exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

def log_event(event: str, screen: str = "", message: str = "", context: Optional[dict] = None):
    """
    訪客行為紀錄：寫入 Google Sheet（visitor_logs），若無則寫本機 data/visitor_logs.jsonl
    """
    series = ""
    variant = ""
    color = ""
    qty = ""
    is_ds = ""
    member_email = st.session_state.get("member", {}).get("email") if st.session_state.get("member") else ""
    if context:
        series = context.get("series", "")
        variant = context.get("variant", "")
        color = context.get("color", "")
        qty = context.get("qty", "")
        is_ds = context.get("is_double_sided", "")

    ip_hint, ua_hint = safe_ip_useragent_hints()
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    row = [
        f"LOG-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}",
        st.session_state["session_id"],
        ts,
        event,
        screen,
        message,
        series,
        variant,
        color,
        qty,
        is_ds,
        member_email,
        get_elapsed_seconds(),
        ip_hint,
        ua_hint,
    ]

    if ws_visitor:
        try:
            ws_visitor.append_row(row)
            return
        except Exception:
            pass

    local_log_append(DATA_DIR / "visitor_logs.jsonl", row)

# 進站記錄（只記一次）
if not st.session_state["visitor_logged_start"]:
    log_event(event="session_start", screen="app", message="訪客進入系統")
    st.session_state["visitor_logged_start"] = True

# 每次 rerun 更新最後時間（用於計算停留時間）
st.session_state["last_seen_at"] = time.time()

# ==========================================
# 會員系統（Google Sheet / 本機 JSON 雙模式）
# ==========================================
def pepper() -> str:
    return os.getenv(PEPPER_ENV_KEY, "CHANGE_ME_PLEASE")

def hash_password(password: str, salt: str) -> str:
    raw = (salt + (password or "") + pepper()).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def validate_email(email: str) -> bool:
    return bool(EMAIL_RE.match((email or "").strip()))

def members_local_path() -> Path:
    return DATA_DIR / "members.json"

def load_members_local() -> Dict[str, Any]:
    p = members_local_path()
    if not p.exists():
        p.write_text(json.dumps({"members": []}, ensure_ascii=False, indent=2), encoding="utf-8")
    return json.loads(p.read_text(encoding="utf-8"))

def save_members_local(db: Dict[str, Any]):
    members_local_path().write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")

def find_member(email: str) -> Optional[Dict[str, Any]]:
    email = (email or "").strip().lower()
    if not email:
        return None

    # 優先從 Google Sheet 查
    if ws_members:
        try:
            rows = ws_members.get_all_records()
            for r in rows:
                if str(r.get("email", "")).strip().lower() == email:
                    return r
        except Exception:
            pass

    # fallback 本機
    db = load_members_local()
    for m in db.get("members", []):
        if m.get("email", "").lower() == email:
            return m
    return None

def register_member(name: str, email: str, password: str) -> Dict[str, Any]:
    name = (name or "").strip()
    email = (email or "").strip().lower()

    if not name:
        return {"ok": False, "msg": "請輸入姓名"}
    if not validate_email(email):
        return {"ok": False, "msg": "Email 格式不正確"}
    if not password or len(password) < 6:
        return {"ok": False, "msg": "密碼至少 6 碼"}

    if find_member(email):
        return {"ok": False, "msg": "此 Email 已註冊"}

    salt = hashlib.sha256(f"{email}-{datetime.datetime.utcnow().isoformat()}".encode("utf-8")).hexdigest()[:16]
    pw_hash = hash_password(password, salt)

    member_row = {
        "email": email,
        "name": name,
        "salt": salt,
        "pw_hash": pw_hash,
        "tier": "member",
        "discount_rate": 0.95,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "last_login_at": "",
    }

    # 寫入 Google Sheet
    if ws_members:
        try:
            ws_members.append_row([
                member_row["email"],
                member_row["name"],
                member_row["salt"],
                member_row["pw_hash"],
                member_row["tier"],
                member_row["discount_rate"],
                member_row["created_at"],
                member_row["last_login_at"],
            ])
            log_event("member_register", "sidebar/member", f"註冊成功：{email}")
            return {"ok": True, "msg": "註冊成功，請登入"}
        except Exception:
            pass

    # fallback 本機
    db = load_members_local()
    db["members"].append(member_row)
    save_members_local(db)
    log_event("member_register", "sidebar/member", f"註冊成功（local）：{email}")
    return {"ok": True, "msg": "註冊成功，請登入"}

def update_member_last_login(email: str):
    email = (email or "").strip().lower()
    if not email:
        return
    ts = datetime.datetime.utcnow().isoformat()

    if ws_members:
        try:
            # 找到該 email 的列
            values = ws_members.get_all_values()
            # 假設第一列為表頭，email 在第1欄
            for idx in range(2, len(values) + 1):
                if values[idx - 1][0].strip().lower() == email:
                    # last_login_at 在第8欄
                    ws_members.update_cell(idx, 8, ts)
                    return
        except Exception:
            pass

    # fallback 本機
    db = load_members_local()
    for m in db.get("members", []):
        if m.get("email", "").lower() == email:
            m["last_login_at"] = ts
            save_members_local(db)
            return

def login_member(email: str, password: str) -> Dict[str, Any]:
    email = (email or "").strip().lower()
    m = find_member(email)
    if not m:
        return {"ok": False, "msg": "帳號或密碼錯誤"}

    salt = str(m.get("salt", ""))
    expected = str(m.get("pw_hash", ""))
    calc = hash_password(password or "", salt)

    if not hmac.compare_digest(expected, calc):
        return {"ok": False, "msg": "帳號或密碼錯誤"}

    update_member_last_login(email)

    member_session = {
        "email": email,
        "name": str(m.get("name", "")),
        "tier": str(m.get("tier", "member")),
        "discount_rate": float(m.get("discount_rate", 0.95)),
    }
    log_event("member_login", "sidebar/member", f"登入成功：{email}")
    return {"ok": True, "msg": "登入成功", "member": member_session}

def member_panel():
    st.sidebar.subheader("會員中心")
    if st.session_state["member"]:
        m = st.session_state["member"]
        st.sidebar.success(f"已登入：{m.get('name','')}（{m.get('email','')}）")
        st.sidebar.info("會員優惠：全站 95 折")
        if st.sidebar.button("登出"):
            log_event("member_logout", "sidebar/member", f"登出：{m.get('email','')}")
            st.session_state["member"] = None
            st.rerun()
        return

    tab_login, tab_register = st.sidebar.tabs(["登入", "註冊"])

    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("密碼", type="password", key="login_pw")
        if st.button("登入", key="login_btn"):
            res = login_member(email, password)
            if res["ok"]:
                st.session_state["member"] = res["member"]
                st.success(res["msg"])
                st.rerun()
            else:
                st.error(res["msg"])
                log_event("member_login_fail", "sidebar/member", res["msg"])

    with tab_register:
        name = st.text_input("姓名", key="reg_name")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("密碼（至少 6 碼）", type="password", key="reg_pw")
        if st.button("建立會員", key="reg_btn"):
            res = register_member(name, email, password)
            if res["ok"]:
                st.success(res["msg"])
            else:
                st.error(res["msg"])
                log_event("member_register_fail", "sidebar/member", res["msg"])

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
    CP101 價格：
    - 10–30：XS–2XL=255 / 3XL–5XL=265
    - 30–100：XS–2XL=245 / 3XL–5XL=255
    - 100以上：XS–2XL=240 / 3XL–5XL=250
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
    avg_unit_price = round(total_price / total_qty) if total_qty > 0 else 0
    return avg_unit_price, total_price

def classify_plan(qty, is_double_sided):
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

def apply_member_discount(total_before: int) -> Dict[str, Any]:
    """
    統一折扣入口：確保『顯示、詢價單、寫入訂單』三者金額一致。
    """
    member = st.session_state.get("member")
    if not member:
        return {
            "label": "一般價",
            "rate": 1.0,
            "total_after": int(total_before),
        }
    rate = float(member.get("discount_rate", 0.95))
    total_after = int(round(total_before * rate, 0))
    return {
        "label": "會員 95 折",
        "rate": rate,
        "total_after": total_after,
    }

# ==========================================
# 3. 詢價單生成（圖片）
# ==========================================
def get_fonts():
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
    candidates = ["LOGO.png", "logo.png", "logo.jpg", "logo.jpeg"]
    for fn in candidates:
        p = ASSETS_DIR / fn
        if p.exists():
            try:
                return Image.open(p).convert("RGBA")
            except Exception:
                continue
    return None

def generate_inquiry_image(img_front, img_back, data, design_list_text, unit_price, total_before, discount_label, total_after):
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

    label_font = font_M
    front_text = "FRONT VIEW"
    fb = draw.textbbox((0, 0), front_text, font=label_font)
    front_label_x = front_x + fw // 2 - (fb[2] - fb[0]) // 2
    draw.text((front_label_x, img_top - 30), front_text, fill="#939FA8", font=label_font)

    back_text = "BACK VIEW"
    bb = draw.textbbox((0, 0), back_text, font=label_font)
    back_label_x = back_x + fw // 2 - (bb[2] - bb[0]) // 2
    draw.text((back_label_x, img_top - 30), back_text, fill="#939FA8", font=label_font)

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
    price_box = (rx - 10, py - 6, w - 95, py + 190)
    draw.rounded_rectangle(price_box, radius=18, fill="#FFF3EC")

    draw.text((rx, py), "ESTIMATED TOTAL（預估總計）", fill="#D4684C", font=font_L)
    draw.text((rx, py + 40), f"NT$ {total_after:,}", fill="#C0392B", font=font_Title)
    draw.text((rx, py + 102), f"折扣：{discount_label}", fill="#A27E6F", font=font_M)
    draw.text((rx, py + 132), f"折扣前：NT$ {total_before:,}", fill="#A27E6F", font=font_M)
    draw.text((rx, py + 160), f"＠ NT$ {unit_price} × {data['qty']} pcs", fill="#A27E6F", font=font_M)

    py += 220
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
# 4. 寫入訂單資料（含折扣/會員/Session）
# ==========================================
def add_order_to_db(order_row: list) -> bool:
    """
    order_row 必須符合 ORDERS_HEADERS 欄位順序。
    """
    if ws_orders:
        try:
            ws_orders.append_row(order_row)
            return True
        except Exception:
            pass

    # fallback：本機
    local_log_append(DATA_DIR / "orders.jsonl", order_row)
    return True

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

# -------------------------
# 找圖工具（大小寫容錯 + debug）
# -------------------------
def resolve_asset_paths(base_name: str, color_code: str):
    """
    回傳：(front_path, back_path, tried_list)
    - 會嘗試 base / code 的大小寫變形
    - 若找不到完整一組，至少回傳能找到的 front/back（避免整片灰）
    """
    tried = []

    base_candidates = [base_name, base_name.lower(), base_name.upper()] if base_name else []
    code_candidates = [color_code, color_code.lower(), color_code.upper()] if color_code else []

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

    # 找不到完整一組就找可用的
    best_front = ""
    best_back = ""
    for name in tried:
        p = ASSETS_DIR / name
        if p.exists() and "_front" in name and not best_front:
            best_front = str(p)
        if p.exists() and "_back" in name and not best_back:
            best_back = str(p)

    return best_front, best_back, tried

# =========================
# Sidebar
# =========================
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
        st.error("⚠ 找不到 NotoSansTC-Regular.ttf，詢價單中文字可能顯示異常。")

    # 會員區
    member_panel()

    with st.expander("🛠 系統診斷 (System Debug)", expanded=False):
        st.write(f"字型路徑: `{font_path}`")
        st.write(f"Session ID: `{st.session_state['session_id']}`")
        st.write(f"停留時間(秒): `{get_elapsed_seconds()}`")

        st.write("📌 資產檔案（assets/）規範：")
        st.code(
            "\n".join([
                "- owner.jpg（側邊欄頭像）",
                "- LOGO.png / logo.png / logo.jpg / logo.jpeg（詢價單浮水印 Logo）",
                "- 尺寸表：",
                "  - CP101：assets/cp101_size_chart.png",
                "  - 其他：assets/size_chart.png 或 assets/size_chart.jpg",
                "- 衣服底圖命名：{image_base}_{color_code}_front.png / ..._back.png",
                "  - 例：AG21000_White_front.png / AG21000_White_back.png",
                "  - 例：cp101_white_front.png / cp101_white_back.png",
            ])
        )

        if ASSETS_DIR.exists():
            st.write("📁 assets 檔案：")
            st.code("\n".join(sorted(os.listdir(str(ASSETS_DIR)))))
        else:
            st.error("找不到 assets 資料夾（請確認專案根目錄下有 assets/）")

        if st.button("手動重新整理網頁"):
            st.rerun()

# =========================
# 主標題
# =========================
st.markdown(
    """
# 👕 興彰企業 x 默默文創｜品牌級旗艦版
> 從班服、社團服，到企業制服、聯名企劃，都用同一套高標準，穩定輸出你的品牌感。
---
"""
)
st.caption("🚀 興彰企業 x 默默文創｜工廠直營．品牌級品質．透明估價")

c1, c2 = st.columns([1.5, 1])

# =========================
# 右側：產品、尺寸、上傳
# =========================
with c2:
    st.markdown("### 1️⃣ 選擇產品 & 數量")

    if not PRODUCT_CATALOG:
        st.error("⚠️ products.py 讀取失敗（PRODUCT_CATALOG 為空）。")
        log_event("error", "product_select", "PRODUCT_CATALOG 為空")
        st.stop()

    series_list = list(PRODUCT_CATALOG.keys())
    s = st.selectbox("系列", series_list, key="series_select")

    style_list = list(PRODUCT_CATALOG[s].keys())
    v = st.selectbox("款式", style_list, key="variant_select")

    item = PRODUCT_CATALOG.get(s, {}).get(v, {})
    st.caption(f"🚀 {s}｜{v}｜興彰企業 x 默默文創")

    color_options = item.get("colors", ["預設"])
    selected_color_name = st.selectbox("顏色", color_options, key="color_select")
    color_code = item.get("color_map", {}).get(selected_color_name, "")

    base_name = item.get("image_base", "")

    img_url_front, img_url_back, tried_files = resolve_asset_paths(base_name, color_code)

    # 變更追蹤（畫面/操作）
    log_event(
        event="view_product",
        screen="right_panel",
        message="選擇產品/顏色",
        context={"series": s, "variant": v, "color": selected_color_name}
    )

    # 找不到就顯示 debug（不讓你盲修）
    if not img_url_front or not img_url_back:
        with st.expander("🧯 找不到衣服底圖？點我看原因（Debug）", expanded=False):
            st.write("系統目前組合的參數：")
            st.code(
                {
                    "image_base": base_name,
                    "color_code": color_code,
                    "selected_color": selected_color_name,
                }
            )
            st.write("系統曾嘗試找這些檔名（只要其中一組存在就會成功）：")
            st.code(
                "\n".join(tried_files[:60]) + ("\n...(略)" if len(tried_files) > 60 else "")
            )
            st.warning(
                "✅ 你的 assets 檔名若全小寫（例如 cp101_white_front.png），"
                "建議 products.py 的 image_base / color_map 也全小寫。"
            )
        log_event(
            event="asset_missing",
            screen="right_panel",
            message=f"衣服底圖缺失: base={base_name}, code={color_code}",
            context={"series": s, "variant": v, "color": selected_color_name}
        )

    st.markdown("---")

    # ✅ CP101 尺寸表：固定 assets/cp101_size_chart.png
    with st.expander("📏 查看尺寸表 (Size Chart)"):
        if "CP101" in v:
            sz_path = ASSETS_DIR / "cp101_size_chart.png"
            if sz_path.exists():
                st.image(str(sz_path))
            else:
                st.warning("找不到 cp101_size_chart.png，請上傳到 assets 資料夾。")
                log_event("asset_missing", "size_chart", "缺少 cp101_size_chart.png",
                          context={"series": s, "variant": v, "color": selected_color_name})
        else:
            sz_path = ASSETS_DIR / "size_chart.png"
            if not sz_path.exists():
                sz_path = ASSETS_DIR / "size_chart.jpg"
            if sz_path.exists():
                st.image(str(sz_path))
            else:
                st.warning("請上傳 size_chart.png 或 size_chart.jpg 到 assets 資料夾。")
                log_event("asset_missing", "size_chart", "缺少 size_chart.png/jpg",
                          context={"series": s, "variant": v, "color": selected_color_name})

    # 尺寸輸入（補齊 XS）
    size_inputs = {}
    st.markdown("### 尺寸件數設定")
    st.caption("請依實際需求輸入各尺寸件數（**最低總數 20 件**）：")

    rows = [("XS", "S"), ("M", "L"), ("XL", "2XL"), ("3XL", "4XL"), ("5XL", "")]

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
                    key=f"qty_{s}_{v}_{selected_color_name}_{size}",  # 避免切換產品時數量互相污染
                    label_visibility="collapsed",
                )

    total_qty = sum(size_inputs.values())

    # 2 上傳設計
    st.markdown("### 2️⃣ 創意設計 & 上傳")
    tab_f, tab_b = st.tabs(["👕 正面設計", "🔄 背面設計"])

    def render_upload_ui(pos_dict, side_prefix: str):
        if not pos_dict:
            st.info("此款式尚未設定印刷位置（pos_front/pos_back）。")
            return

        pk = st.selectbox(
            f"{'正面' if side_prefix=='front' else '背面'}位置",
            list(pos_dict.keys()),
            key=f"sel_{side_prefix}_{s}_{v}",
        )
        design_key = f"{side_prefix}_{pk}"

        if design_key not in st.session_state["uploader_keys"]:
            st.session_state["uploader_keys"][design_key] = 0
        uk = st.session_state["uploader_keys"][design_key]

        uf = st.file_uploader(
            f"上傳圖片（{pk}）",
            type=["png", "jpg", "jpeg"],
            key=f"u_{design_key}_{uk}_{s}_{v}_{selected_color_name}",
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

            log_event(
                event="upload_image",
                screen=f"upload/{side_prefix}",
                message=f"上傳：{pk}",
                context={"series": s, "variant": v, "color": selected_color_name, "qty": total_qty}
            )

        if design_key in st.session_state["designs"]:
            if st.button(f"🗑️ 刪除圖片（{pk}）", key=f"btn_clear_{design_key}_{s}_{v}"):
                del st.session_state["designs"][design_key]
                st.session_state["uploader_keys"][design_key] += 1
                log_event(
                    event="delete_image",
                    screen=f"upload/{side_prefix}",
                    message=f"刪除：{pk}",
                    context={"series": s, "variant": v, "color": selected_color_name, "qty": total_qty}
                )
                st.rerun()

    with tab_f:
        render_upload_ui(item.get("pos_front", {}), "front")
    with tab_b:
        render_upload_ui(item.get("pos_back", {}), "back")

    has_f = any(k.startswith("front_") for k in st.session_state["designs"].keys())
    has_b = any(k.startswith("back_") for k in st.session_state["designs"].keys())
    is_ds = has_f and has_b

    # CP101 用專屬價，其餘用一般價
    if "CP101" in v:
        unit_price, total_price_before = calculate_cp101_price(size_inputs)
    else:
        unit_price = calculate_unit_price(total_qty, is_ds)
        total_price_before = unit_price * total_qty

    plan_name, plan_desc = classify_plan(total_qty, is_ds)

    # 套用會員折扣（所有顯示/輸出/寫入以此為準）
    discount_info = apply_member_discount(int(total_price_before))
    total_price_after = discount_info["total_after"]

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
                with st.form(key=f"form_{d_key}"):
                    new_rb = st.checkbox("✨ AI 智能去背", value=d_val["rb"])
                    new_sz = st.slider("縮放大小", 50, 400, d_val["sz"])
                    new_rot = st.slider("旋轉角度", -180, 180, d_val["rot"])
                    c1a, c2a = st.columns(2)
                    with c1a:
                        new_ox = st.number_input("左右微調 X", -100, 100, d_val["ox"])
                    with c2a:
                        new_oy = st.number_input("上下微調 Y", -100, 100, d_val["oy"])
                    if st.form_submit_button("✅ 確認套用"):
                        d_val.update({"rb": new_rb, "sz": new_sz, "rot": new_rot, "ox": new_ox, "oy": new_oy})
                        log_event(
                            event="adjust_design",
                            screen=f"preview/{curr_side}",
                            message=f"調整：{d_key}",
                            context={"series": s, "variant": v, "color": selected_color_name, "qty": total_qty, "is_double_sided": is_ds}
                        )
                        st.rerun()

# =========================
# 報價區
# =========================
st.divider()
st.markdown("### 3️⃣ 興彰嚴選報價 & 品牌分級")

if total_qty < 20:
    st.warning("⚠️ 最低訂製量為 20 件，請調整各尺寸件數。")
    log_event("constraint", "pricing", "未達最低訂量20",
              context={"series": s, "variant": v, "color": selected_color_name, "qty": total_qty, "is_double_sided": is_ds})
else:
    cp, cv = st.columns([1, 1.5])
    with cp:
        member_badge = ""
        if st.session_state.get("member"):
            member_badge = f"<p style='margin:0;color:#2d6a4f;font-weight:700;'>✅ 會員已套用：{discount_info['label']}</p>"
        st.markdown(
            f"""
<div style="background-color:#f8f9fa;padding:20px;border-radius:10px;text-align:center;">
  <p>本次估價所屬方案</p>
  <h4>{plan_name}</h4>
  <hr>
  <p>預估單價</p>
  <h2>NT$ {unit_price}</h2>
  <hr>
  {member_badge}
  <h3>折扣前：NT$ {int(total_price_before):,}</h3>
  <h2 style="margin-top:6px;">折扣後：NT$ {int(total_price_after):,}</h2>
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

    accept = st.checkbox("我接受此預估報價，並希望由專人協助確認與優化設計", value=False)
    if accept:
        log_event("accept_quote_toggle", "inquiry_form", "客戶勾選接受預估報價",
                  context={"series": s, "variant": v, "color": selected_color_name, "qty": total_qty, "is_double_sided": is_ds})

        c1b, c2b = st.columns(2)
        with c1b:
            c_name = st.text_input("您的稱呼 / 單位名稱")
            c_line = st.text_input("LINE ID（用於傳圖與聯絡）")
        with c2b:
            c_phone = st.text_input("手機號碼")
            c_note = st.text_input("需求備註（顏色、風格、希望感覺等）")

        if st.button("🚀 生成正式詢價單（品牌專業版）", type="primary", use_container_width=True):
            # 基本校驗
            if not c_name or not c_line:
                st.error("請至少填寫「稱呼 / 單位名稱」與「LINE ID」。")
                log_event("form_error", "inquiry_form", "缺少稱呼或LINE ID",
                          context={"series": s, "variant": v, "color": selected_color_name, "qty": total_qty, "is_double_sided": is_ds})
            elif not font_path:
                st.error("缺少中文字型檔 NotoSansTC-Regular.ttf，請先補上再生成。")
                log_event("form_error", "inquiry_form", "缺少字型檔",
                          context={"series": s, "variant": v, "color": selected_color_name, "qty": total_qty, "is_double_sided": is_ds})
            else:
                # 尺寸字串
                sz_br = ", ".join([f"{k}*{v_}" for k, v_ in size_inputs.items() if v_ > 0])

                # 統一折扣金額（避免前後不一致）
                total_before_int = int(total_price_before)
                discount_label = discount_info["label"]
                discount_rate = float(discount_info["rate"])
                total_after_int = int(total_price_after)

                # 設計清單
                design_list = []
                for dk in st.session_state["designs"].keys():
                    ds, dpn = dk.split("_", 1)
                    side_label = "正面" if ds == "front" else "背面"
                    design_list.append(f"{side_label}｜{dpn}")

                # 背面底圖合成（確保位置正確：背面pos_back＋袖口映射）
                if img_url_back and os.path.exists(img_url_back):
                    base_b = Image.open(img_url_back).convert("RGBA")
                else:
                    base_b = Image.new("RGBA", (600, 800), (240, 240, 240))

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

                # 詢價資料
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

                # 訂單寫入（含會員/折扣/Session）
                oid = f"ORD-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                member_email = st.session_state.get("member", {}).get("email") if st.session_state.get("member") else ""
                created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                product_str = f"{s}-{v} / {selected_color_name}"

                order_row = [
                    oid,
                    dt["name"],
                    dt["contact"],
                    dt["phone"],
                    dt["line"],
                    product_str,
                    dt["qty"],
                    dt["size_breakdown"],
                    int(unit_price),
                    int(total_before_int),
                    discount_label,
                    discount_rate,
                    int(total_after_int),
                    dt["promo_code"],
                    dt["note"],
                    member_email,
                    created_at,
                    st.session_state["session_id"],
                ]
                add_order_to_db(order_row)

                # 生成詢價單圖片（折扣後總計）
                receipt = generate_inquiry_image(
                    final, final_b, dt, design_list,
                    unit_price=unit_price,
                    total_before=total_before_int,
                    discount_label=discount_label,
                    total_after=total_after_int
                )

                log_event(
                    event="generate_inquiry",
                    screen="inquiry_output",
                    message=f"生成詢價單：{oid}",
                    context={"series": s, "variant": v, "color": selected_color_name, "qty": total_qty, "is_double_sided": is_ds}
                )

                st.success("✅ 品牌級正式詢價單已生成！")
                st.image(receipt, caption="📩 請長按儲存此圖片，並傳給阿默 LINE: @727jxovv")
                st.link_button("👉 立即開啟 LINE 傳送圖檔給阿默", "https://line.me/ti/p/~@727jxovv")

# =========================
# Footer：營運可視化（你自己看的）
# =========================
with st.expander("📊 營運監控（僅供內部）", expanded=False):
    st.write("這裡顯示的是『本次 Session』的關鍵狀態（不等於完整訪客行為；完整在 visitor_logs）。")
    st.json({
        "session_id": st.session_state["session_id"],
        "elapsed_seconds": get_elapsed_seconds(),
        "member": st.session_state["member"],
        "selected": {"series": s, "variant": v, "color": selected_color_name},
        "qty": total_qty,
        "double_sided": is_ds,
        "unit_price": unit_price,
        "total_before_discount": int(total_price_before),
        "discount": discount_info,
        "total_after_discount": int(total_price_after),
        "design_keys": list(st.session_state["designs"].keys()),
    })
