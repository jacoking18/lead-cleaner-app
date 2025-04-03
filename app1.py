import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime
from io import StringIO, BytesIO

# -------------------- PASSWORD PROTECTION --------------------
def check_password():
    def password_entered():
        if st.session_state["password"] == "capnow$":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Enter password:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Enter password:", type="password", on_change=password_entered, key="password")
        st.error("Incorrect password.")
        return False
    else:
        return True

if not check_password():
    st.stop()
# -------------------------------------------------------------

st.set_page_config(page_title="CAPNOW DATA CLEANER APP")
st.title("CAPNOW DATA CLEANER APP")
st.markdown("**Creator: Jaco Simkin – Director of Data Analysis**")

st.markdown("""
This app automatically cleans raw lead files (CSV or Excel) received from multiple providers.
It standardizes messy or inconsistent data into a unified format required by the CAPNOW HUB system.

**What it does:**
- Normalizes messy column headers and standardizes formats
- Recognizes and extracts key fields even if headers are nonstandard
- Shows a clean table with the main fields
- Highlights unrecognized columns in red

**Columns output:**
Lead Date, Business Name, Full Name, SSN, DOB, Industry, EIN, Business Start Date,
Phone 1, Phone 2, Email 1, Email 2, Business Address

**Second Table (Red):**
Shows all columns from your upload that were **not recognized or cleaned**, so you can review extra info.
""")

FINAL_COLUMNS = [
    "Lead Date", "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Email 1", "Email 2", "Business Address"
]

COLUMN_MAPPING = {
    # SSN
    "ssn": "SSN", "social": "SSN", "social security": "SSN", "socialsecurity": "SSN",

    # DOB
    "dob": "DOB", "birth date": "DOB", "date of birth": "DOB", "birthdate": "DOB",

    # EIN
    "ein": "EIN", "employer id": "EIN", "federal id": "EIN",

    # Business Start Date
    "business start date": "Business Start Date", "start date": "Business Start Date", "bsd": "Business Start Date", "yearsinbusiness": "Business Start Date",

    # Revenue
    "monthly revenue": "Monthly Revenue", "revenue": "Monthly Revenue", "turnover": "Monthly Revenue", "income": "Monthly Revenue", "sales": "Monthly Revenue",

    # Business Name
    "biz name": "Business Name", "businessname": "Business Name", "company": "Business Name", "business": "Business Name", "company name": "Business Name",

    # Full Name / First + Last
    "name": "Full Name", "full name": "Full Name", "contact name": "Full Name",
    "firstname": "First Name", "first name": "First Name", "given name": "First Name",
    "lastname": "Last Name", "last name": "Last Name", "surname": "Last Name",

    # Phones
    "phone": "Phone", "phone number": "Phone", "cellphone": "Phone", "mobile": "Phone", "cell": "Phone", "tlo phone 1": "Phone", "tlo phone 2": "Phone", "contact number": "Phone",

    # Emails
    "email": "Email", "email address": "Email", "tlo email 1": "Email", "tlo email 2": "Email", "google email": "Email", "e-mail": "Email",

    # Address
    "address": "Address", "city": "City", "state": "State", "zip": "Zip", "zipcode": "Zip",
    "street": "Street", "business address": "Address", "business address full": "Address",
    "business address street,city,state,zip": "Address", "business address street": "Street",

    # Industry
    "industry": "Industry", "sector": "Industry", "line of business": "Industry"
}

# Helpers
def normalize_column_name(col):
    return col.lower().strip()

def guess_phone_columns(df):
    phone_cols = [c for c in df.columns if any(keyword in c for keyword in ["phone", "cell"])]
    return phone_cols[:2] if len(phone_cols) >= 2 else phone_cols + [""]

def guess_email_columns(df):
    email_cols = [c for c in df.columns if "@" in str(df[c].iloc[0]) or "email" in c]
    return email_cols[:2] if len(email_cols) >= 2 else email_cols + [""]

def build_full_name(df):
    if "Full Name" in df.columns:
        return df["Full Name"]
    elif "First Name" in df.columns and "Last Name" in df.columns:
        return df["First Name"].astype(str).str.strip() + " " + df["Last Name"].astype(str).str.strip()
    return pd.Series(["" for _ in range(len(df))])

def clean_text(val):
    if pd.isna(val): return ""
    return re.sub(r"\s+", " ", str(val).replace(",", "")).strip()

def format_phone(phone):
    digits = re.sub(r"\D", "", str(phone))
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}" if len(digits) == 10 else str(phone)

def process_file(uploaded_file):
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    df = pd.read_csv(uploaded_file) if ext == ".csv" else pd.read_excel(uploaded_file)

    df.columns = [col.lower().strip().replace("  ", " ").replace("\n", " ") for col in df.columns]
    df.rename(columns=lambda c: COLUMN_MAPPING.get(c.strip().lower(), c.strip().title()), inplace=True)

    df["Full Name"] = build_full_name(df)

    phone_cols = guess_phone_columns(df)
    df["Phone 1"] = df[phone_cols[0]].apply(format_phone) if phone_cols[0] in df.columns else ""
    df["Phone 2"] = df[phone_cols[1]].apply(format_phone) if phone_cols[1] in df.columns else ""

    email_cols = guess_email_columns(df)
    df["Email 1"] = df[email_cols[0]] if email_cols[0] in df.columns else ""
    df["Email 2"] = df[email_cols[1]] if email_cols[1] in df.columns else ""

    df["Business Address"] = df.get("Street", "") + ", " + df.get("City", "") + ", " + df.get("State", "") + " " + df.get("Zip", "")
    df["Lead Date"] = datetime.today().strftime("%m/%d/%Y")

    cleaned = pd.DataFrame({col: df[col].apply(clean_text) if col in df.columns else "" for col in FINAL_COLUMNS})
    untouched_cols = [c for c in df.columns if c not in FINAL_COLUMNS]
    untouched = df[untouched_cols] if untouched_cols else pd.DataFrame()

    return cleaned, untouched

# -------------------- UI --------------------
uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"])

if uploaded_file:
    try:
        cleaned_df, untouched_df = process_file(uploaded_file)
        st.success("Data cleaned successfully.")

        st.markdown("### Cleaned CSV (Full Preview)")
        st.dataframe(cleaned_df, use_container_width=True)

        if not untouched_df.empty:
            st.markdown("### Unrecognized Columns (shown in red)")
            st.dataframe(untouched_df.style.set_properties(**{'background-color': 'salmon'}), use_container_width=True)

        filename = os.path.splitext(uploaded_file.name)[0] + "_cleaned.csv"
        st.download_button(
            label="Download Cleaned CSV",
            data=cleaned_df.to_csv(index=False).encode("utf-8"),
            file_name=filename,
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"Error during processing: {str(e)}")