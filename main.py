import streamlit as st
import io
import os
import requests
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from rembg import remove
from products import PRODUCT_CATALOG
import datetime

# ==========================================
# 1. 全局設定 & 模擬資料庫
# ==========================================
st.set_page_config(page_title="Momo Design Pro", page_icon="💎", layout="wide")

# [模擬資料庫] 使用 cache_resource 讓資料在伺服器重啟前暫時保留
# 注意：在真實商業環境，這裡應該換成 Google Sheets API 或 SQL 資料庫
@st.cache_resource
def get_database():
    return {"members": []}

db = get_database()

# 初始化 Session
if "user_role" not in st.session_state: st.session_state["user_role"] = "guest"
if "user_info" not in st.session_state: st.session_state["user_info"] = {}
if "site_locked" not in st.session_state: st.session_state["site_locked"] = True

# ==========================================
# 2. 全站密碼鎖
# ==========================================
def check_lock():
    if st.session_state["site_locked"]:
        st.markdown("<h2 style='text-align:center;'>🔒 Momo 內部系統</h2>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1,1,1])
        with c2:
            pwd = st.text_input("請輸入密碼", type="password", label_visibility="collapsed")
            if st.button("進入系統", use_container_width=True):
                if pwd == "momo2025": # 全站密碼
                    st.session_state["site_locked"] = False
                    st.rerun()
                else:
                    st.error("密碼錯誤")
        st.stop()

check_lock()

# ==========================================
# 3. 字型終極處理 (自動下載 + 手動救援)
# ==========================================
FONT_FILE = "NotoSansTC-Regular.ttf"
DEFAULT_FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanstc/NotoSansTC-Regular.ttf"

@st.cache_resource
def load_system_font():
    # 嘗試自動下載
    if not os.path.exists(FONT_FILE):
        try:
            r = requests.get(DEFAULT_FONT_URL, timeout=10)
            if r.status_code == 200:
                with open(FONT_FILE, "wb") as f: f.write(r.content)
        except: pass
    return FONT_FILE

load_system_font()

# 字型物件取得器 (支援使用者手動上傳的字型)
def get_font_obj(size):
    # 優先檢查是否有手動上傳的字型 (存於 session)
    if "custom_font_bytes" in st.session_state:
        return ImageFont.truetype(io.BytesIO(st.session_state["custom_font_bytes"]), size)
    
    # 其次使用系統自動下載的
    if os.path.exists(FONT_FILE):
        return ImageFont.truetype(FONT_FILE, size)
        
    # 最後回退預設
    return ImageFont.load_default()

# ==========================================
# 4. CSS 美化 (手機優化版)
# ==========================================
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; font-family: "Microsoft JhengHei", sans-serif; }
    .block-container { padding-top: 1rem; padding-bottom: 3rem; }
    
    /* 頂部會員狀態條 (手機可見) */
    .member-bar {
        background: white; padding: 10px 15px; border-radius: 8px;
        margin-bottom: 15px; border-left: 5px solid #667eea;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        font-size: 14px; display: flex; justify-content: space-between; align-items: center;
    }
    
    /* 詢價單卡片 */
    .inquiry-card {
        background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
        padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* 按鈕優化 */
    .stButton>button { border-radius: 8px; font-weight: bold; }
    
    #MainMenu, footer, header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 5. 核心邏輯：詢價單生成
# ==========================================
def generate_inquiry(img, data):
    w, h = 800, 1300
    card = Image.new("RGB", (w, h), "white")
    draw = ImageDraw.Draw(card)
    
    # 顏色定義
    c_primary = "#2c3e50"
    c_highlight = "#e67e22"
    
    # 字體
    f_xl = get_font_obj(40)
    f_l = get_font_obj(30)
    f_m = get_font_obj(24)
    f_s = get_font_obj(20)
    
    # Header
    draw.rectangle([(0,0), (w, 140)], fill=c_primary)
    draw.text((40, 50), "Momo Design 需求詢價單", fill="white", font=f_xl)
    draw.text((w-250, 60), str(datetime.date.today()), fill="#ccc", font=f_s)
    
    # 圖片區
    t_w = 400
    ratio = t_w / img.width
    t_h = int(img.height * ratio)
    res = img.resize((t_w, t_h))
    draw.rectangle([((w-t_w)//2-5, 170-5), ((w-t_w)//2+t_w+5, 170+t_h+5)], fill="#eee")
    card.paste(res, ((w-t_w)//2, 170), res if res.mode=='RGBA' else None)
    
    y = 170 + t_h + 50
    draw.line([(50,y), (750,y)], fill="#ddd", width=2)
    y += 30
    
    # --- 核心商業邏輯：推廣碼顯示 ---
    # 如果有推廣碼，印在顯眼位置
    promo_code = data.get('promo_code')
    if promo_code and promo_code != "GUEST":
        draw.rectangle([(50, y), (750, y+60)], fill="#fff3cd") # 黃色底
        draw.text((70, y+15), f"★ 推薦人/分潤代碼：{promo_code}", fill="#856404", font=f_l)
        y += 90
    
    # 資料欄位
    fields = [
        ("詢價單位", data.get('name')),
        ("聯絡人", data.get('contact')),
        ("電話", data.get('phone')),
        ("LINE ID", data.get('line')),
        ("---", "---"), # 分隔線
        ("產品系列", data.get('series')),
        ("款式", data.get('variant')),
        ("數量", f"{data.get('qty')} 件"),
        ("備註", data.get('note'))
    ]
    
    for k, v in fields:
        if k == "---":
            y += 10
            draw.line([(50,y), (750,y)], fill="#eee", width=1)
            y += 20
            continue
            
        draw.text((60, y), f"【{k}】", fill=c_primary, font=f_m)
        
        # 內容換行處理
        val = str(v) if v else "-"
        max_char = 22
        for i in range(0, len(val), max_char):
            line = val[i:i+max_char]
            draw.text((250, y), line, fill="#333", font=f_m)
            y += 40
        y += 10

    # Footer
    draw.rectangle([(0, h-80), (w, h)], fill="#f8f9fa")
    draw.text((200, h-50), "此單據僅供詢價，正式報價以業務回傳為主", fill="#999", font=f_s)
    
    return card

# ==========================================
# 6. 介面佈局
# ==========================================

# --- 側邊欄：功能選單 ---
with st.sidebar:
    st.title("🔧 功能選單")
    
    # 1. 管理員登入
    with st.expander("🔐 管理員後台 (Admin)", expanded=False):
        admin_pwd = st.text_input("管理密碼", type="password")
        if admin_pwd == "admin888": # 後台密碼
            st.success("登入成功")
            st.markdown("### 👥 會員名單")
            if db["members"]:
                df = pd.DataFrame(db["members"])
                st.dataframe(df, use_container_width=True)
                st.caption("注意：此為模擬資料，重啟後會消失。")
            else:
                st.info("尚無會員資料")
    
    # 2. 字型救援
    with st.expander("🔤 字型救援 (Font Fix)", expanded=False):
        st.caption("如果詢價單文字變成方塊，請在此上傳電腦裡的 .ttf 字型檔 (如微軟正黑體)")
        custom_font = st.file_uploader("上傳字型檔", type=["ttf", "otf"])
        if custom_font:
            st.session_state["custom_font_bytes"] = custom_font.getvalue()
            st.success("字型已套用！")

# --- 主畫面：頂部會員狀態 (手機易讀) ---
if st.session_state["user_role"] == "member":
    u_info = st.session_state["user_info"]
    code_display = f"｜推廣碼：**{u_info['code']}**" if u_info['is_ambassador'] else ""
    st.markdown(f"""
        <div class="member-bar">
            <span>👤 會員：{u_info['name']} {code_display}</span>
        </div>
    """, unsafe_allow_html=True)
    if st.button("登出", key="top_logout"):
        st.session_state["user_role"] = "guest"
        st.session_state["user_info"] = {}
        st.rerun()
else:
    # 未登入：顯示註冊/登入區塊
    with st.expander("🚀 會員登入 / 註冊推廣大使 (點擊展開)", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            r_name = st.text_input("姓名/暱稱")
            r_phone = st.text_input("手機號碼")
        with c2:
            st.write("") 
            st.write("")
            is_amb = st.checkbox("我要開啟分潤功能 (成為大使)")
            
        if st.button("確認進入", type="primary", use_container_width=True):
            if r_name and r_phone:
                # 產生代碼
                code = f"{r_name.upper()}{r_phone[-3:]}" if is_amb else "MEMBER"
                
                # 寫入模擬資料庫 (給後台看)
                new_member = {
                    "Name": r_name,
                    "Phone": r_phone,
                    "Is_Ambassador": "Yes" if is_amb else "No",
                    "Code": code,
                    "Date": str(datetime.date.today())
                }
                db["members"].append(new_member)
                
                # 更新 Session
                st.session_state["user_role"] = "member"
                st.session_state["user_info"] = {"name": r_name, "code": code, "is_ambassador": is_amb}
                st.rerun()
            else:
                st.error("請輸入姓名與電話")

# --- 主畫面：服務模式 ---
st.markdown("#### 🛍️ 選擇模式")
mode = st.radio("Mode", ["一般訂製 / 推廣", "公司團體 (詢價)"], horizontal=True, label_visibility="collapsed")

# 決定 partner_id (用於浮水印和詢價單)
current_code = "GUEST"
if st.session_state["user_role"] == "member":
    current_code = st.session_state["user_info"]["code"]

# --- 核心操作區 ---
col_preview, col_tools = st.columns([1.5, 1], gap="medium")

with col_tools:
    st.markdown("### 1. 產品")
    c_s, c_v = st.columns(2)
    with c_s: series = st.selectbox("系列", list(PRODUCT_CATALOG.keys()))
    with c_v: variant = st.selectbox("款式", list(PRODUCT_CATALOG[series].keys()))
    
    item = PRODUCT_CATALOG[series][variant]
    pos_opts = item.get("positions", {"中":[150,150]})
    
    st.markdown("### 2. 設計")
    up_file = st.file_uploader("上傳圖案", type=["png","jpg","jpeg"])
    
    if up_file:
        with st.expander("調整參數", expanded=True):
            rm_bg = st.toggle("AI 去背")
            pos_k = st.selectbox("位置", list(pos_opts.keys()))
            sz = st.slider("大小", 50, 450, 180)
            ox = st.slider("左右", -60, 60, 0)
            oy = st.slider("上下", -60, 60, 0)
            rot = st.slider("旋轉", -180, 180, 0)
    else:
        pos_k, sz, ox, oy, rot, rm_bg = list(pos_opts.keys())[0], 150, 0, 0, 0, False

with col_preview:
    try:
        base = Image.open(item["image"]).convert("RGBA")
        final = base.copy()
        
        if up_file:
            d = Image.open(up_file).convert("RGBA")
            if rm_bg: d = remove(d)
            wr = sz / d.width
            d = d.resize((sz, int(d.height * wr)))
            if rot: d = d.rotate(rot, expand=True)
            tx, ty = pos_opts[pos_k]
            final.paste(d, (int(tx-d.width/2+ox), int(ty-d.height/2+oy)), d)
        
        # 顯示圖片 (浮水印僅在一般模式顯示)
        st.image(final, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error: {e}")

# --- 底部行動區 ---
with col_tools:
    st.markdown("---")
    
    if mode == "公司團體 (詢價)":
        st.markdown("### 3. 詢價資料")
        with st.container(border=True):
            in_name = st.text_input("單位名稱")
            c1, c2 = st.columns(2)
            with c1: in_contact = st.text_input("聯絡人")
            with c2: in_phone = st.text_input("電話")
            in_line = st.text_input("LINE ID")
            c3, c4 = st.columns([1,2])
            with c3: in_qty = st.number_input("數量", value=20)
            with c4: in_note = st.text_input("備註")
            
            if st.button("📄 生成詢價單", type="primary", use_container_width=True):
                data = {
                    "name": in_name, "contact": in_contact, "phone": in_phone, 
                    "line": in_line, "qty": in_qty, "note": in_note,
                    "series": series, "variant": variant,
                    "promo_code": current_code # 將推廣碼傳入詢價單
                }
                with st.spinner("生成中..."):
                    card = generate_inquiry(final, data)
                    buf = io.BytesIO()
                    card.save(buf, format="PNG")
                
                st.success("完成！")
                st.download_button("📥 下載圖片", data=buf.getvalue(), file_name=f"Inquiry_{in_name}.png", mime="image/png", use_container_width=True, type="primary")

    else:
        # 一般模式 / 推廣模式
        st.markdown(f"#### 建議售價：NT$ {item.get('price', 0)}")
        
        # 生成浮水印圖
        wm = Image.new("RGBA", final.size, (0,0,0,0))
        d_wm = ImageDraw.Draw(wm)
        fw, fh = final.size
        f_wm = get_font_obj(int(fh*0.04))
        
        # 如果是推廣大使，印出代碼
        wm_text = f"Promo: {current_code}" if st.session_state["user_info"].get("is_ambassador") else "Momo Design"
        d_wm.rectangle([(fw-300, fh-80), (fw, fh)], fill=(255,255,255,200))
        d_wm.text((fw-280, fh-60), wm_text, fill="red", font=f_wm)
        final_wm = Image.alpha_composite(final, wm)
        
        buf = io.BytesIO()
        final_wm.save(buf, format="PNG")
        
        if st.session_state["user_info"].get("is_ambassador"):
            st.download_button("✨ 下載分潤推廣圖", data=buf.getvalue(), file_name=f"Promo_{current_code}.png", mime="image/png", type="primary", use_container_width=True)
        else:
            st.download_button("📥 下載設計圖", data=buf.getvalue(), file_name="Design.png", mime="image/png", use_container_width=True)
