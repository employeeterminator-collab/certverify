import streamlit as st
import os
import json
import gspread
import base64
from google.oauth2.service_account import Credentials
from PIL import Image

# ==========================================
# Page Configuration
# ==========================================
st.set_page_config(
    page_title="Shisa Kanko-Shi Credential Verifier",
    page_icon="Icon1.png",
    layout="centered"
)

# ==========================================
# Idle session killer — cost guard (5 min)
# ==========================================
# Ends the browser session after 5 minutes with no mouse /
# keyboard / touch input. 60s before the kill, a full-screen warning with
# countdown appears; any input cancels it. The kill navigates the top page
# away, which drops the Streamlit websocket and frees the Cloud Run instance.
st.components.v1.html(
    """
    <script>
    (function() {
        var TIMEOUT_MS = 5 * 60 * 1000;
        var WARN_AT_MS = TIMEOUT_MS - 60 * 1000;
        var KEY = '__idleLastActivityAtcertverify';
        function now() { return Date.now(); }
        try {
            if (!parent.window[KEY]) parent.window[KEY] = now();
            if (parent.window.__idleWatchercertverify) return;
            parent.window.__idleWatchercertverify = true;
        } catch (e) { return; }
        function touch() { try { parent.window[KEY] = now(); } catch (e) {} }
        ['mousemove', 'mousedown', 'keydown', 'touchstart', 'click', 'scroll'].forEach(function(ev) {
            try { parent.document.addEventListener(ev, touch, {passive: true}); } catch (e) {}
        });
        var warned = false;
        var overlay = null;
        var countdownEl = null;
        function showWarning() {
            try {
                overlay = parent.document.createElement('div');
                overlay.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;'
                    + 'background:rgba(0,0,0,0.85);z-index:2147483647;display:flex;'
                    + 'align-items:center;justify-content:center;flex-direction:column;'
                    + 'color:#fff;font-family:sans-serif;text-align:center;padding:24px;box-sizing:border-box;';
                overlay.innerHTML = '<div style="font-size:22px;font-weight:bold;margin-bottom:12px;">Session expiring due to inactivity</div>'
                    + '<div style="font-size:15px;opacity:0.9;">No activity detected for 5 minutes.<br>'
                    + 'This session will end in <span id="__idleCountdown" style="font-weight:bold;">60</span> seconds.<br>'
                    + 'Move your mouse or press any key to continue.</div>';
                parent.document.body.appendChild(overlay);
                countdownEl = overlay.querySelector('#__idleCountdown');
            } catch (e) {}
        }
        function hideWarning() {
            try { if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay); } catch (e) {}
            overlay = null; warned = false;
        }
        function killSession() {
            try {
                if (overlay) overlay.innerHTML = '<div style="font-size:22px;font-weight:bold;">Session ended</div>'
                    + '<div style="font-size:15px;opacity:0.9;margin-top:12px;">Closed due to inactivity. You may close this tab.</div>';
            } catch (e) {}
            setTimeout(function() {
                try { parent.window.location.href = 'about:blank'; } catch (e) {}
            }, 3000);
        }
        setInterval(function() {
            var last;
            try { last = parent.window[KEY] || now(); } catch (e) { return; }
            var idle = now() - last;
            if (idle >= TIMEOUT_MS) { killSession(); return; }
            if (idle >= WARN_AT_MS && !warned) { warned = true; showWarning(); }
            if (idle < WARN_AT_MS && warned) { hideWarning(); }
            if (warned && countdownEl) {
                countdownEl.textContent = Math.max(0, Math.ceil((TIMEOUT_MS - idle) / 1000));
            }
        }, 1000);
    })();
    </script>
    """,
    height=0,
)

# ==========================================
# Google Sheets Connection Helper
# ==========================================
def get_sheets_connection():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # Load service account JSON from environment variables
    creds_json = os.getenv("GCP_SERVICE_ACCOUNT")
    if not creds_json:
        raise ValueError("GCP_SERVICE_ACCOUNT environment variable is not set.")
    
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    
    # Use SPREADSHEET_ID environment variable for robust connection
    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    if spreadsheet_id:
        return client.open_by_key(spreadsheet_id)
    return client.open("ShisaKanko_Exam_Database")

# ==========================================
# UI Layout & Header
# ==========================================
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    return ""

img_base64 = get_base64_image("CPCS-Badge.png")

if img_base64:
    st.markdown(f"""
        <div style='text-align: center;'>
            <img src='data:image/png;base64,{img_base64}' width='120' style='vertical-align: middle; margin-right: 10px;'>
            <h1 style='display: inline-block; vertical-align: middle; margin: 0;'>Shisa Kanko-Shi Credential Verifier</h1>
        </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("<h1 style='text-align: center;'>Shisa Kanko-Shi Credential Verifier</h1>", unsafe_allow_html=True)

st.write("Verify official certification details by **uploading your digital badge** or entering your **Voucher Code**.")
st.markdown("---")

# 建立兩個分頁供選擇：上傳徽章 vs 手動輸入驗證碼
tab1, tab2 = st.tabs(["🛡️ Verify by Badge Upload", "⌨️ Verify by Voucher Code"])

voucher_to_lookup = None
is_badge_upload = False

with tab1:
    st.subheader("Upload Digital Badge")
    uploaded_badge = st.file_uploader("Upload your CSCP badge file (only .png accepted", type=["png"])
    
    if uploaded_badge is not None:
        try:
            # 讀取上傳的 PNG 檔案並提取內嵌的 Metadata
            img = Image.open(uploaded_badge)
            extracted_voucher = img.info.get("VoucherCode")
            
            if extracted_voucher:
                voucher_to_lookup = extracted_voucher
                is_badge_upload = True
            else:
                st.error("❌ No valid data found in this image.")
        except Exception as e:
            st.error(f"❌ Error reading image metadata: {e}")

with tab2:
    st.subheader("Enter Voucher Code")
    manual_voucher = st.text_input("Voucher Code:", placeholder="e.g., SK00001TEST").strip()
    if manual_voucher:
        voucher_to_lookup = manual_voucher
        is_badge_upload = False

# ==========================================
# Database Lookup & Result Display
# ==========================================
if voucher_to_lookup:
    with st.spinner("Verifying credential against database..."):
        try:
            db = get_sheets_connection()
            sheet = db.worksheet("Vouchers")
            records = sheet.get_all_records()
            
            matched_record = None
            for row in records:
                v_code = str(row.get("VoucherCode", row.get("Voucher Code", ""))).strip()
                if v_code.upper() == voucher_to_lookup.upper():
                    matched_record = row
                    break
            
            if matched_record:
                exam_status = str(matched_record.get("ExamStatus", matched_record.get("exam_status", ""))).strip().lower()
                
                if exam_status == "pass":
                    st.success("✅ Official Credential Verified Successfully")
                    
                    # 擷取指定欄位資料
                    first_name = str(matched_record.get("EnglishFirstName", matched_record.get("First Name", ""))).strip()
                    last_name = str(matched_record.get("EnglishLastName", matched_record.get("Last Name", ""))).strip()
                    japanese_name = str(matched_record.get("JapaneseName", matched_record.get("Japanese Name", ""))).strip()
                    exam_time = str(matched_record.get("ExamEndTime", "")).strip()
                    
                    st.markdown("---")
                    st.markdown("### 📋 Holder Details")
                    
                    # 嚴格依照要求列出 4 項資訊
                    st.markdown(f"**1. English First Name:** {first_name}")
                    st.markdown(f"**2. English Last Name:** {last_name}")
                    st.markdown(f"**3. Japanese Name:** {japanese_name}")
                    st.markdown(f"**4. Certification Date & Time:** {exam_time}")
                    
                    # 條件限制：如果是透過上傳徽章查詢，絕對不顯示 Voucher Code
                    if not is_badge_upload:
                        st.info(f"🔍 Verified via Voucher Code: {voucher_to_lookup}")
                        
                    st.markdown("---")
                else:
                    st.error("❌ Invalid credential or exam status not passed.")
            else:
                st.error("❌ Credential not found in the database.")
                
        except Exception as e:
            st.error(f"An error occurred while connecting to the database: {e}")
