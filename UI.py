import streamlit as st
import pandas as pd
import socket
import time
import json
import http.client
import re
import smtplib
import os  # ✅ Import for file cleanup
from email.message import EmailMessage
from urllib.parse import urlparse
import concurrent.futures
from streamlit_lottie import st_lottie

# ---- LOAD LOTTIE ----
def load_lottie(filepath: str):
    with open(filepath, "r") as f:
        return json.load(f)

# ---- PAGE CONFIG ----
st.set_page_config(page_title="Website Status Checker", layout="wide")

# ---- HEADER ----
lottie_json = load_lottie("Animation - 1743016196710.json")
with st.container():
    col1, col2 = st.columns(2)
    with col1:
        st.title("⚡ Website Status Checker")
        st.markdown("""
            <div style='font-size:18px; color:#CCCCCC;'>
            Upload a CSV file and this tool checks all website statuses.<br><br>
            Skips LinkedIn/WhatsApp/etc. Only real websites are checked 🧠
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st_lottie(lottie_json, height=300)

st.markdown("---")

# ---- FILE UPLOADER ----
uploaded_file = st.file_uploader("📄 Upload your CSV file", type=["csv"])

# ---- SOCIAL DOMAINS ----
social_domains = [
    "linkedin.com", "facebook.com", "twitter.com", "instagram.com", "wa.me",
    "whatsapp.com", "t.me", "youtube.com", "pinterest.com", "tiktok.com"
]

valid_website_column_keywords = [
    "website", "company_website", "company domain", "company_domain",
    "site", "web", "webpage", "business_website", "official_site", "domain"
]

def is_social_url(url: str):
    if not isinstance(url, str):
        return True
    url = url.lower()
    return any(domain in url for domain in social_domains)

def is_social_column(series):
    return series.dropna().astype(str).apply(is_social_url).mean() > 0.7

# ---- WEBSITE CHECK FUNCTIONS ----
def check_website_status_fast(url: str, timeout=2):
    if pd.isna(url) or is_social_url(url):
        return "⚪ Skipped (Social/Empty)"
    try:
        host = url.replace("http://", "").replace("https://", "").split('/')[0]
        socket.setdefaulttimeout(timeout)
        socket.gethostbyname(host)
        return "🟢 Active"
    except Exception:
        return "🔴 Inactive"

def recheck_inactive_site(url: str, timeout=6):
    try:
        parsed_url = urlparse(url)
        conn = http.client.HTTPSConnection(parsed_url.netloc, timeout=timeout)
        conn.request("HEAD", parsed_url.path or "/")
        res = conn.getresponse()
        if 200 <= res.status < 400:
            return "🟢 Active"
        return "🔴 Inactive"
    except Exception:
        return "🔴 Inactive"

# ---- EMAIL FUNCTION ----
def is_valid_email(email):
    return re.match(r"[^@]+@[^@]+\.[^@]+", email)

def send_email_with_csv(receiver_email, file_path):
    sender_email = "b2bgrowthexpo@gmail.com"
    sender_password = "esoalaeiitmdpntw"  # App Password

    msg = EmailMessage()
    msg['Subject'] = '✅ Your Website Status CSV is Ready'
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg.set_content(f"""
Hi there 👋,

Thanks for using the Website Status Checker tool!

Your processed CSV file is attached to this email. It contains:
- ✅ Active websites
- 🔴 Inactive websites
- ⚪ Skipped (Social or Empty URLs)

We hope this helps you streamline your data.

Feel free to revisit the tool whenever you need to check website status in bulk.

Best regards,  
Website Status Checker 🔎  
B2B Growth Expo
""")

    with open(file_path, 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='octet-stream', filename="updated_status.csv")

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(sender_email, sender_password)
        smtp.send_message(msg)

# ---- MAIN WORKFLOW ----
if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)

        # Identify website column
        possible_cols = [col for col in df.columns if any(keyword in col.lower() for keyword in valid_website_column_keywords)]
        actual_website_col = None
        for col in possible_cols:
            if not is_social_column(df[col]):
                actual_website_col = col
                break

        if actual_website_col is None:
            st.error("❌ Could not find a valid website column.")
        else:
            st.success(f"✅ Found website column: `{actual_website_col}`")
            urls = df[actual_website_col].astype(str)

            start_time = time.time()
            st.info("🚀 Checking website statuses...")

            with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                status_list = list(executor.map(check_website_status_fast, urls))

            # Progress bar
            progress_bar = st.progress(0)
            for i in range(len(status_list)):
                time.sleep(0.001)
                progress_bar.progress((i + 1) / len(status_list))

            # Recheck Inactive
            st.info("🔄 Re-checking inactive sites...")
            updated_status = status_list.copy()
            inactive_indices = [i for i, status in enumerate(status_list) if status == "🔴 Inactive"]
            re_urls = urls.iloc[inactive_indices].tolist()

            with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
                rechecked = list(executor.map(recheck_inactive_site, re_urls))

            for idx, new_status in zip(inactive_indices, rechecked):
                updated_status[idx] = new_status

            # Insert results
            insert_at = df.columns.get_loc(actual_website_col) + 1
            df.insert(insert_at, "Website Status", updated_status)

            end_time = time.time()
            total_time = round(end_time - start_time, 2)

            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download Updated CSV", data=csv, file_name="updated_status.csv", mime="text/csv")

            # Save CSV for email
            saved_path = "updated_status.csv"
            df.to_csv(saved_path, index=False)

            active_count = updated_status.count("🟢 Active")
            inactive_count = updated_status.count("🔴 Inactive")
            skipped_count = updated_status.count("⚪ Skipped (Social/Empty)")

            st.info(f"⏱️ Time taken: **{total_time} seconds**")
            st.success(f"✅ Active: {active_count} | 🔴 Inactive: {inactive_count} | ⚪ Skipped: {skipped_count}")

            # ---- EMAIL SECTION ----
            email = st.text_input("📧 Enter your email to receive the updated CSV")

            if st.button("✉️ Send Email"):
                if is_valid_email(email):
                    send_email_with_csv(email, saved_path)
                    os.remove(saved_path)  # ✅ Delete temp file after sending
                    st.success("📤 Email sent successfully, Please check Spam folder!")
                else:
                    st.error("❌ Please enter a valid email address.")
    except Exception as e:
        st.error(f"⚠️ Error processing file: {e}")
        # ---- FOOTER ----
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>Made with 💙 by Ritvick</p>", unsafe_allow_html=True)
