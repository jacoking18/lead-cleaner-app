import streamlit as st
import pandas as pd
import re
from datetime import datetime
import os

# -------------------- PASSWORD PROTECTION --------------------
def check_password():
    def password_entered():
        if st.session_state["password"] == "capnow$":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Enter password to access the app:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Enter password to access the app:", type="password", on_change=password_entered, key="password")
        st.error("Incorrect password.")
        return False
    else:
        return True

if not check_password():
    st.stop()

st.set_page_config(page_title="CAPNOW DATA CLEANER APP")
st.image("logo.png", width=160)
st.title("CAPNOW DATA CLEANER APP")
st.markdown("**Creator: Jaco Simkin – Director of Data Analysis**")

st.markdown("""
This app automatically cleans raw lead files (CSV or Excel format) received from multiple providers.

It standardizes messy or inconsistent data into a unified format required by the CAPNOW HUB system.

What it does:
- Automatically detects phone and email columns by structure (e.g., @ for emails, 10-digit for phones)
- Normalizes messy columns like `biz name`, `googlephone`, `revenue`, `turnover`, etc.
- Outputs a clean DataFrame with the following columns:

Lead Date, Business Name, Full Name, SSN, DOB, Industry, EIN  
Business Start Date, Phone 1, Phone 2, Email 1, Email 2  
Business Address, Home Address, Monthly Revenue

Second Table (Red): The second DataFrame (highlighted in red) shows all columns from the uploaded file that were not recognized or cleaned.
""")

FINAL_COLUMNS = [
    "Lead Date", "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Email 1", "Email 2",
    "Business Address", "Home Address", "Monthly Revenue"
]

COLUMN_MAPPING = {
    "date": "Lead Date", "lead date": "Lead Date", "submission date": "Lead Date",
    "ssn": "SSN", "social": "SSN",
    "dob": "DOB", "birth date": "DOB",
    "ein": "EIN", "employer id": "EIN",
    "business start date": "Business Start Date", "start date": "Business Start Date",
    "monthly revenue": "Monthly Revenue", "rev": "Monthly Revenue", "revenue": "Monthly Revenue", "turnover": "Monthly Revenue",
    "biz name": "Business Name", "businessname": "Business Name", "company": "Business Name", "business name": "Business Name",
    "ownerfullname": "Full Name", "firstname": "First Name", "lastname": "Last Name",
    "address": "Address", "city": "City", "state": "State", "zip": "Zip",
    "owner address": "Owner Address", "owner city": "Owner City", "owner state": "Owner State", "owner zip": "Owner Zip"
}

def normalize_column_name(col):
    col = str(col).lower().replace(".", "").replace("_", " ").strip()
    col = re.sub(r"\s+", " ", col)
    return COLUMN_MAPPING.get(col, col)

def format_phone(val):
    digits = re.sub(r"\D", "", str(val))
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}" if len(digits) == 10 else ""

def is_phone_series(series):
    return series.apply(lambda x: len(re.sub(r"\D", "", str(x))) == 10).mean() > 0.5

def is_email_series(series):
    return series.apply(lambda x: "@" in str(x)).mean() > 0.5

def clean_text(val):
    val = str(val)
    return re.sub(r"\s+", " ", val.replace(",", "")).strip() if val.lower() != "nan" else ""

def process_file(uploaded_file):
    file_ext = uploaded_file.name.split(".")[-1].lower()
    base_filename = os.path.splitext(uploaded_file.name)[0]

    if file_ext == "csv":
        df = pd.read_csv(uploaded_file, dtype=str).fillna("")
    else:
        df = pd.read_excel(uploaded_file, dtype=str).fillna("")

    df.columns = [normalize_column_name(col) for col in df.columns]

    first = df.get("First Name", pd.Series([""] * len(df)))
    last = df.get("Last Name", pd.Series([""] * len(df)))
    full = df.get("Full Name", pd.Series([""] * len(df)))
    if "Full Name" not in df.columns or df["Full Name"].str.strip().eq("").all():
        df["Full Name"] = first.fillna("") + " " + last.fillna("")

    phone_candidates = [col for col in df.columns if is_phone_series(df[col])]
    df["Phone 1"] = df[phone_candidates[0]].apply(format_phone) if len(phone_candidates) > 0 else ""
    df["Phone 2"] = df[phone_candidates[1]].apply(format_phone) if len(phone_candidates) > 1 else ""

    email_candidates = [col for col in df.columns if is_email_series(df[col])]
    df["Email 1"] = df[email_candidates[0]] if len(email_candidates) > 0 else ""
    df["Email 2"] = df[email_candidates[1]] if len(email_candidates) > 1 else ""

    df["Business Address"] = df.get("Address", "") + ", " + df.get("City", "") + ", " + df.get("State", "") + " " + df.get("Zip", "")
    df["Home Address"] = df.get("Owner Address", "") + ", " + df.get("Owner City", "") + ", " + df.get("Owner State", "") + " " + df.get("Owner Zip", "")

    if "Lead Date" in df.columns:
        df["Lead Date"] = pd.to_datetime(df["Lead Date"], errors="coerce").dt.strftime("%m/%d/%Y")
        df["Lead Date"] = df["Lead Date"].fillna("")

    cleaned = pd.DataFrame()
    for col in FINAL_COLUMNS:
        if col in df.columns:
            cleaned[col] = df[col].apply(clean_text)
        else:
            cleaned[col] = [""] * len(df)

    untouched_cols = [col for col in df.columns if col not in FINAL_COLUMNS]
    untouched = df[untouched_cols] if untouched_cols else pd.DataFrame()

    summary = (
        f"Cleaned rows: {len(df)}\n"
        f"Standard columns: {len(FINAL_COLUMNS)}\n"
        f"Unrecognized columns: {len(untouched_cols)}"
    )

    return cleaned, untouched, summary, base_filename

uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"])

if uploaded_file:
    try:
        cleaned_df, untouched_df, summary, base_filename = process_file(uploaded_file)

        st.success("Data cleaned successfully.")
        st.markdown("### Cleaned CSV (Full Preview)")
        st.dataframe(cleaned_df, use_container_width=True)

        if not untouched_df.empty:
            st.markdown("### Unrecognized Columns (shown in red)")
            st.dataframe(untouched_df.style.set_properties(**{'background-color': 'salmon'}), use_container_width=True)

        st.download_button(
            label="Download Cleaned CSV",
            data=cleaned_df.to_csv(index=False).encode("utf-8"),
            file_name=f"{base_filename}_cleaned.csv",
            mime="text/csv"
        )

        st.markdown("### Summary")
        st.text(summary)

    except Exception as e:
        st.error(f"Error during processing: {str(e)}")

st.markdown("<hr style='margin-top:50px;'>", unsafe_allow_html=True)
st.caption("CAPNOW Data Cleaner v1.0 – April 2025")


