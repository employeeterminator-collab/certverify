import streamlit as st
import os
import gspread
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
# Google Sheets Connection Helper
# ==========================================
def get_sheets_connection():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    return client.open("ShisaKanko_Exam_Database")

# ==========================================
# UI Layout & Header
# ==========================================
st.markdown("<h1 style='text-align: center;'>Shisa Kanko-Shi Credential Verifier</h1>", unsafe_allow_html=True)
st.write("Verify official certification details by **uploading your digital badge** or entering your **Voucher Code**.")

# 建立兩個分頁供選擇：上傳徽章 vs 手動輸入驗證碼
tab1, tab2 = st.tabs(["🛡️ Verify by Badge Upload", "⌨️ Verify by Voucher Code"])

voucher_to_lookup = None
is_badge_upload = False

with tab1:
    st.subheader("Upload Digital Badge")
    uploaded_badge = st.file_uploader("Upload your CSCP-Badge-{Voucher}.png file", type=["png"])
    
    if uploaded_badge is not None:
        try:
            # 讀取上傳的 PNG 檔案並提取內嵌的 Metadata
            img = Image.open(uploaded_badge)
            extracted_voucher = img.info.get("VoucherCode")
            
            if extracted_voucher:
                voucher_to_lookup = extracted_voucher
                is_badge_upload = True
            else:
                st.error("❌ No valid metadata (VoucherCode) found in this image.")
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