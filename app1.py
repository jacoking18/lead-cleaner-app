import streamlit as st
import pandas as pd
import re

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
# -------------------------------------------------------------

st.set_page_config(page_title="CAPNOW DATA CLEANER APP")

st.image("logo.png", width=160)
st.title("CAPNOW DATA CLEANER APP")
st.markdown("**Creator: Jaco Simkin – Director of Data Analysis**")

st.markdown("""
This app automatically cleans raw lead files (CSV format) received from multiple providers.

It standardizes messy or inconsistent data into a unified format required by the CAPNOW HUB system.

What it does:
- Normalizes messy columns like `biz name`, `googlephone`, `revenue`, etc.
- Outputs a clean DataFrame with the following columns:

Business Name, Full Name, SSN, DOB, Industry, EIN  
Business Start Date, Phone 1, Phone 2, Email 1, Email 2  
Business Address, Home Address, Monthly Revenue

Second Table (Red):
The second DataFrame (highlighted in red) shows all columns from the uploaded file that were not recognized or cleaned.
You can use this to see what additional data was present but not part of the HUB format.
""")

# HUB columns
FINAL_COLUMNS = [
    "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Email 1", "Email 2",
    "Business Address", "Home Address", "Monthly Revenue"
]

# Flexible mappings
COLUMN_MAPPING = {
    "ssn": "SSN", "social": "SSN", "social security": "SSN", "socialsecurity": "SSN",
    "dob": "DOB", "birth date": "DOB", "date of birth": "DOB",
    "ein": "EIN", "employer id": "EIN",
    "business start date": "Business Start Date", "start date": "Business Start Date", "bsd": "Business Start Date", "yearsinbusiness": "Business Start Date",
    "monthly revenue": "Monthly Revenue", "businessmonthlyrevenue": "Monthly Revenue", "rev": "Monthly Revenue",
    "revenue": "Monthly Revenue", "Revenue": "Monthly Revenue",
    "biz name": "Business Name", "businessname": "Business Name", "company": "Business Name",
    "ownerfullname": "Full Name", "firstname": "First Name", "first name": "First Name",
    "lastname": "Last Name", "last name": "Last Name",
    "phone1": "Phone A", "cellphone": "Phone B", "businessphone": "Phone C", "altphone": "Phone D",
    "googlephone": "Phone E", "google phone": "Phone E", "GOOGLEPHONE": "Phone E", "number1": "Phone A",
    "email": "Email A", "email1": "Email A", "email 1": "Email A",
    "email2": "Email B", "google email": "Email B", "googleemail": "Email B",
    "GOOGLEEMAIL": "Email B", "Google Email": "Email B", "Google email": "Email B",
    "address": "Address", "address1": "Address", "city": "City", "state": "State", "zip": "Zip",
    "owner address": "Owner Address", "owner city": "Owner City", "owner state": "Owner State", "owner zip": "Owner Zip"
}

# Helpers
def normalize_column_name(col):
    col = str(col).lower().replace(".", "").replace("_", " ").strip()
    col = re.sub(r"\s+", " ", col)
    return COLUMN_MAPPING.get(col, col)

def format_phone(phone):
    digits = re.sub(r"\D", "", str(phone))
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}" if len(digits) == 10 else str(phone)

def clean_text(val):
    val = str(val)
    return re.sub(r"\s+", " ", val.replace(",", "")).strip() if val.lower() != "nan" else ""

# Main cleaner
def process_csv(uploaded_file):
    df = pd.read_csv(uploaded_file, dtype=str).fillna("")
    df.columns = [normalize_column_name(col) for col in df.columns]

    if "Full Name" not in df.columns:
        df["Full Name"] = (df.get("First Name", "") + " " + df.get("Last Name", "")).str.strip()

    phone_cols = [col for col in df.columns if col.lower().startswith("phone")]
    phones_df = df[phone_cols].applymap(format_phone)
    phone_flat = phones_df.apply(lambda row: list(dict.fromkeys([v for v in row if v])), axis=1)
    df["Phone 1"] = phone_flat.apply(lambda x: x[0] if len(x) > 0 else "")
    df["Phone 2"] = phone_flat.apply(lambda x: x[1] if len(x) > 1 else "")

    df["Email 1"] = df.get("Email A", "")
    df["Email 2"] = df.get("Email B", "")

    df["Business Address"] = df.get("Address", "") + ", " + df.get("City", "") + ", " + df.get("State", "") + " " + df.get("Zip", "")
    df["Home Address"] = df.get("Owner Address", "") + ", " + df.get("Owner City", "") + ", " + df.get("Owner State", "") + " " + df.get("Owner Zip", "")

    cleaned = pd.DataFrame()
    for col in FINAL_COLUMNS:
        cleaned[col] = df[col].apply(clean_text) if col in df.columns else ""

    untouched_cols = [col for col in df.columns if col not in FINAL_COLUMNS]
    untouched = df[untouched_cols] if untouched_cols else pd.DataFrame()

    summary = (
        f"Cleaned rows: {len(df)}\n"
        f"Standard columns: {len(FINAL_COLUMNS)}\n"
        f"Unrecognized columns: {len(untouched_cols)}"
    )
    return cleaned, untouched, summary

# -------------------- UI --------------------
uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
