import streamlit as st
import pandas as pd
import re

# Required HUB columns
FINAL_COLUMNS = [
    "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Phone 3", "Email 1", "Email 2",
    "Business Address", "Home Address", "Monthly Revenue"
]

# Mapping dirty column names to standard ones
COLUMN_MAPPING = {
    "ssn": "SSN", "social": "SSN", "social security": "SSN",
    "dob": "DOB", "date of birth": "DOB", "birth date": "DOB",
    "ein": "EIN", "employer id": "EIN",
    "business start date": "Business Start Date", "bsd": "Business Start Date", "start date": "Business Start Date", "yearsinbusiness": "Business Start Date",
    "revenue": "Monthly Revenue", "businessmonthlyrevenue": "Monthly Revenue",
    "biz name": "Business Name", "businessname": "Business Name", "company": "Business Name",
    "firstname": "First Name", "lastname": "Last Name", "ownerfullname": "Full Name",
    "phone1": "Phone A", "cellphone": "Phone B", "businessphone": "Phone C", "altphone": "Phone D",
    "googlephone": "Phone E", "google phone": "Phone E", "GOOGLEPHONE": "Phone E",
    "email": "Email A", "email1": "Email A", "email 1": "Email A", "email2": "Email B", "google email": "Email B",
    "address": "Address", "address1": "Address", "city": "City", "state": "State", "zip": "Zip",
    "owner address": "Owner Address", "owner city": "Owner City", "owner state": "Owner State", "owner zip": "Owner Zip"
}

# Standardize column names
def standardize_column(col):
    return COLUMN_MAPPING.get(col.strip().lower(), col.strip())

# Format phone number like (123) 456-7890
def format_phone(phone):
    digits = re.sub(r"\D", "", str(phone))
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return phone

# Clean general text
def clean_text(val):
    return re.sub(r"\s+", " ", str(val)).strip() if pd.notna(val) else ""

# Return Series safely, filled with empty string if not present
def safe_get(df, column_name):
    if column_name in df.columns:
        return df[column_name].astype(str).fillna("")
    else:
        return pd.Series([""] * len(df))

# Main cleaner function
def process_csv(uploaded_file):
    df = pd.read_csv(uploaded_file)
    df.rename(columns=lambda c: standardize_column(c), inplace=True)

    # Full Name
    if "Full Name" not in df.columns:
        df["Full Name"] = safe_get(df, "First Name") + " " + safe_get(df, "Last Name")

    # Business Address
    df["Business Address"] = safe_get(df, "Address") + ", " + safe_get(df, "City") + ", " + safe_get(df, "State") + " " + safe_get(df, "Zip")

    # Home Address
    df["Home Address"] = safe_get(df, "Owner Address") + ", " + safe_get(df, "Owner City") + ", " + safe_get(df, "Owner State") + " " + safe_get(df, "Owner Zip")

    # Phone cleaning
    phone_cols = [col for col in df.columns if col.lower().startswith("phone")]
    df["Phone 1"] = ""
    df["Phone 2"] = ""
    df["Phone 3"] = ""

    for i, row in df.iterrows():
        phones = list(dict.fromkeys([
            format_phone(str(row[col])) for col in phone_cols if pd.notna(row[col]) and str(row[col]).strip() != ""
        ]))
        for j in range(min(len(phones), 3)):
            df.at[i, f"Phone {j+1}"] = phones[j]

    # Emails (safe)
    df["Email 1"] = safe_get(df, "Email A")
    df["Email 2"] = safe_get(df, "Email B")

    # Final cleaned output
    cleaned = pd.DataFrame(columns=FINAL_COLUMNS)
    for col in FINAL_COLUMNS:
        cleaned[col] = df[col].apply(clean_text) if col in df.columns else ""

    return cleaned

# ------------- Streamlit App ----------------

st.title("HUB Lead Cleaner")
st.write("Upload a messy provider CSV → Download a cleaned version ready for the HUB")

uploaded_file = st.file_uploader("Upload a CSV file", type="csv")

if uploaded_file:
    try:
        cleaned_df = process_csv(uploaded_file)
        st.success("Data cleaned successfully!")
        st.dataframe(cleaned_df.head())

        st.download_button(
            label="Download Cleaned CSV",
            data=cleaned_df.to_csv(index=False).encode("utf-8"),
            file_name="hub_cleaned.csv",
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"Something went wrong while cleaning the file.\n\nError: {e}")
