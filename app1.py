import streamlit as st
import pandas as pd
import re

# ------------------- Config -------------------
st.set_page_config(page_title="CAPNOW DATA CLEANER APP", layout="wide")

# Required HUB columns
FINAL_COLUMNS = [
    "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Email 1", "Email 2",
    "Business Address", "Home Address", "Monthly Revenue"
]

# Column name variations (case-insensitive)
COLUMN_MAPPING = {
    "ssn": "SSN", "social": "SSN", "social security": "SSN",
    "dob": "DOB", "date of birth": "DOB", "birthdate": "DOB",
    "ein": "EIN", "employer id": "EIN",
    "business start date": "Business Start Date", "bsd": "Business Start Date", "start date": "Business Start Date", "yearsinbusiness": "Business Start Date",
    "revenue": "Monthly Revenue", "monthly revenue": "Monthly Revenue", "businessmonthlyrevenue": "Monthly Revenue",
    "biz name": "Business Name", "businessname": "Business Name", "company": "Business Name",
    "firstname": "First Name", "lastname": "Last Name", "name": "Full Name", "full name": "Full Name", "owner": "Full Name",
    "phone": "Phone", "phone1": "Phone", "cell": "Phone", "cellphone": "Phone", "mobile": "Phone", "contact": "Phone", "number1": "Phone",
    "email": "Email", "email1": "Email", "email address": "Email",
    "address": "Address", "city": "City", "state": "State", "zip": "Zip",
    "owner address": "Owner Address", "owner city": "Owner City", "owner state": "Owner State", "owner zip": "Owner Zip",
    "industry": "Industry"
}

# Standardize column names
def clean_column_name(col):
    col = re.sub(r"[^\w\s]", "", col.lower()).strip().replace("  ", " ")
    return COLUMN_MAPPING.get(col, col)

# Format phone numbers to (123) 456-7890
def format_phone(phone):
    digits = re.sub(r"\D", "", str(phone))
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}" if len(digits) == 10 else ""

# Clean general text
def clean_text(val):
    if pd.isna(val):
        return ""
    val = str(val).strip()
    val = re.sub(r"\s+", " ", val)
    val = val.replace(",", "")
    return val

# Main cleaning function
def process_csv(uploaded_file):
    df = pd.read_csv(uploaded_file, dtype=str, encoding_errors="ignore")
    df.columns = [clean_column_name(col) for col in df.columns]

    # Full Name
    if "Full Name" not in df.columns:
        df["Full Name"] = df.get("first name", "").fillna("") + " " + df.get("last name", "").fillna("")
    df["Full Name"] = df["Full Name"].apply(clean_text)

    # Business Address
    address_fields = ["address", "city", "state", "zip"]
    for f in address_fields:
        if f not in df.columns:
            df[f] = ""
    df["Business Address"] = df["address"] + ", " + df["city"] + ", " + df["state"] + " " + df["zip"]
    df["Business Address"] = df["Business Address"].apply(clean_text)

    # Home Address
    home_fields = ["owner address", "owner city", "owner state", "owner zip"]
    for f in home_fields:
        if f not in df.columns:
            df[f] = ""
    df["Home Address"] = df["owner address"] + ", " + df["owner city"] + ", " + df["owner state"] + " " + df["owner zip"]
    df["Home Address"] = df["Home Address"].apply(clean_text)

    # Phones (limit to 2)
    phone_cols = [col for col in df.columns if "phone" in col]
    df["Phone 1"], df["Phone 2"] = "", ""
    for i, row in df.iterrows():
        phones = []
        for col in phone_cols:
            val = row.get(col)
            if pd.notna(val):
                p = format_phone(val)
                if p:
                    phones.append(p)
        if len(phones) > 0:
            df.at[i, "Phone 1"] = phones[0]
        if len(phones) > 1:
            df.at[i, "Phone 2"] = phones[1]

    # Emails
    email_cols = [col for col in df.columns if "email" in col]
    emails = df[email_cols].fillna("").astype(str).applymap(clean_text) if email_cols else pd.DataFrame()
    df["Email 1"] = emails[email_cols[0]] if len(email_cols) > 0 else ""
    df["Email 2"] = emails[email_cols[1]] if len(email_cols) > 1 else ""

    # Final cleaned structure
    cleaned = pd.DataFrame()
    for col in FINAL_COLUMNS:
        cleaned[col] = df[col].apply(clean_text) if col in df.columns else ""

    # Add extra columns at the end
    remaining_cols = [col for col in df.columns if col not in cleaned.columns and col not in ["first name", "last name", "address", "city", "state", "zip", "owner address", "owner city", "owner state", "owner zip"]]
    for col in remaining_cols:
        cleaned[col] = df[col]

    # Summary
    summary = f"✅ Cleaned {len(df)} rows. Extra columns preserved: {len(remaining_cols)}"
    return cleaned, summary

# ------------------- Streamlit UI -------------------
st.title("CAPNOW DATA CLEANER APP")
st.caption("Creator: Jacoking")
st.caption("albert es marico")

st.write("Upload a messy provider CSV → Download a cleaned version ready for the HUB")

uploaded_file = st.file_uploader("Upload a CSV file", type="csv")

if uploaded_file:
    try:
        cleaned_df, summary = process_csv(uploaded_file)
        st.success(summary)
        st.dataframe(cleaned_df)  # Show full grid
        st.download_button(
            label="Download Cleaned CSV",
            data=cleaned_df.to_csv(index=False).encode("utf-8"),
            file_name="hub_cleaned.csv",
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"Error: {e}")
