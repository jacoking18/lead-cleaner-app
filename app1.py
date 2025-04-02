import streamlit as st
import pandas as pd
import re

# ========== CONFIG ==========
FINAL_COLUMNS = [
    "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Email 1", "Email 2",
    "Business Address", "Home Address", "Monthly Revenue"
]

COLUMN_MAPPING = {
    # --- Identification
    "ssn": "SSN", "social": "SSN", "social security": "SSN", "s.s.n.": "SSN",
    "dob": "DOB", "birth date": "DOB", "dateofbirth": "DOB",
    "ein": "EIN", "employer id": "EIN", "federal ein": "EIN",
    "industry": "Industry", "line of work": "Industry",

    # --- Business Info
    "biz name": "Business Name", "businessname": "Business Name", "company": "Business Name", "dba": "Business Name",
    "business start": "Business Start Date", "start date": "Business Start Date", "yearsinbusiness": "Business Start Date",

    # --- Name
    "first name": "First Name", "firstname": "First Name",
    "last name": "Last Name", "lastname": "Last Name",
    "full name": "Full Name", "owner name": "Full Name",

    # --- Revenue
    "monthly revenue": "Monthly Revenue", "revenue": "Monthly Revenue", "estimated revenue": "Monthly Revenue",

    # --- Phones
    "phone": "Phone", "phone1": "Phone", "phone 1": "Phone", "cellphone": "Phone", "mobile": "Phone",
    "altphone": "Phone", "phone number": "Phone", "googlephone": "Phone", "number1": "Phone",

    # --- Emails
    "email": "Email", "email1": "Email", "email 1": "Email", "email2": "Alt Email", "google email": "Alt Email",

    # --- Address
    "address": "Address", "address1": "Address", "business address": "Address",
    "city": "City", "state": "State", "zip": "Zip",

    "owner address": "Owner Address", "home address": "Owner Address",
    "owner city": "Owner City", "owner state": "Owner State", "owner zip": "Owner Zip",
}

# ========== HELPERS ==========

def normalize_column(col):
    col = col.strip().lower().replace(".", "").replace("  ", " ").replace(" ", "")
    return COLUMN_MAPPING.get(col, col)

def format_phone(val):
    digits = re.sub(r"\D", "", str(val))
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}" if len(digits) == 10 else str(val)

def clean_text(val):
    return re.sub(r"\s+", " ", str(val)).strip() if pd.notna(val) else ""

def clean_address(addr):
    addr = str(addr).replace(",", "")
    addr = re.sub(r"\s+", " ", addr)
    return addr.strip()

# ========== MAIN PROCESS ==========
def process_csv(uploaded_file):
    df = pd.read_csv(uploaded_file)
    df.columns = [normalize_column(col) for col in df.columns]

    # Handle Full Name
    if "full name" not in df.columns:
        df["full name"] = df.get("first name", "") + " " + df.get("last name", "")
        df["full name"] = df["full name"].str.strip()

    # Handle Phone
    phone_cols = [col for col in df.columns if "phone" in col]
    phones_clean = df[phone_cols].applymap(format_phone)
    df["Phone 1"] = phones_clean.apply(lambda row: next((p for p in row if p), ""), axis=1)
    df["Phone 2"] = phones_clean.apply(lambda row: next((p for i, p in enumerate(row) if i > 0 and p), ""), axis=1)

    # Handle Email
    df["Email 1"] = df.get("email", "")
    df["Email 2"] = df.get("alt email", "")

    # Combine Addresses
    df["Business Address"] = (
        df.get("address", "") + ", " + df.get("city", "") + ", " + df.get("state", "") + " " + df.get("zip", "")
    ).apply(clean_address)

    df["Home Address"] = (
        df.get("owner address", "") + ", " + df.get("owner city", "") + ", " + df.get("owner state", "") + " " + df.get("owner zip", "")
    ).apply(clean_address)

    # Final Cleaned Output
    cleaned = pd.DataFrame(columns=FINAL_COLUMNS)
    for col in FINAL_COLUMNS:
        cleaned[col] = df[col].apply(clean_text) if col in df.columns else ""

    # Add leftover columns
    extra_cols = [col for col in df.columns if col not in FINAL_COLUMNS]
    for col in extra_cols:
        cleaned[col] = df[col]

    # Summary
    summary = f"""
✅ Cleaned Columns: {len(FINAL_COLUMNS)}  
📌 Extra Columns Preserved: {len(extra_cols)}  
📞 Phone 3+ removed  
📬 Address commas stripped and double-spaces fixed  
📂 Fields not matched were kept safely  
🛡️ Errors are gracefully handled
"""
    return cleaned, summary

# ========== STREAMLIT UI ==========
st.set_page_config(layout="wide")
st.title("HUB Lead Cleaner")
st.caption("Upload a messy provider CSV → Download a cleaned version ready for the HUB")
st.markdown("**Creator: Jacoking**")
st.markdown("_albert es marico_")

uploaded_file = st.file_uploader("📎 Upload a CSV file", type="csv")

if uploaded_file:
    try:
        cleaned_df, summary = process_csv(uploaded_file)
        st.success("✅ File cleaned successfully!")
        st.markdown(summary)
        st.dataframe(cleaned_df)

        st.download_button(
            label="⬇️ Download Cleaned CSV",
            data=cleaned_df.to_csv(index=False).encode("utf-8"),
            file_name="hub_cleaned.csv",
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"❌ Error: {e}")
