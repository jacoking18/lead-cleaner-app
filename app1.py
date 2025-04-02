import streamlit as st
import pandas as pd
import re

# Branding
st.set_page_config(page_title="CAPNOW DATA CLEANER APP")
st.markdown("<h1 style='text-align: center;'>CAPNOW DATA CLEANER APP</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Creator: Jacoking | alber es marico</p>", unsafe_allow_html=True)

# Required HUB columns
FINAL_COLUMNS = [
    "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Email 1", "Email 2",
    "Business Address", "Home Address", "Monthly Revenue"
]

# Known dirty name mappings
COLUMN_MAPPING = {
    "ssn": "SSN", "social": "SSN", "social security": "SSN",
    "dob": "DOB", "date of birth": "DOB", "birth date": "DOB",
    "ein": "EIN", "employer id": "EIN",
    "business start date": "Business Start Date", "bsd": "Business Start Date",
    "start date": "Business Start Date", "yearsinbusiness": "Business Start Date",
    "revenue": "Monthly Revenue", "businessmonthlyrevenue": "Monthly Revenue", "monthlyrev": "Monthly Revenue",
    "biz name": "Business Name", "businessname": "Business Name", "company": "Business Name", "company name": "Business Name",
    "firstname": "First Name", "first name": "First Name", "name": "First Name",
    "lastname": "Last Name", "last name": "Last Name", "surname": "Last Name",
    "ownerfullname": "Full Name", "full name": "Full Name",
    "phone": "Phone A", "phone1": "Phone A", "cellphone": "Phone B", "businessphone": "Phone C", "altphone": "Phone D",
    "googlephone": "Phone E", "google phone": "Phone E",
    "email": "Email A", "email1": "Email A", "email 1": "Email A", "email2": "Email B", "email 2": "Email B", "google email": "Email B",
    "address": "Address", "address1": "Address", "street": "Address",
    "city": "City", "state": "State", "zip": "Zip", "zipcode": "Zip", "postal code": "Zip",
    "owner address": "Owner Address", "owner city": "Owner City", "owner state": "Owner State", "owner zip": "Owner Zip"
}

# Normalize column name: strip, lowercase, remove punctuation/spaces
def normalize_column(col):
    col = str(col).lower()
    col = re.sub(r"[^a-z0-9 ]+", "", col)
    col = re.sub(r"\s+", " ", col).strip()
    return COLUMN_MAPPING.get(col, col)

# Format phone like (123) 456-7890
def format_phone(phone):
    digits = re.sub(r"\D", "", str(phone))
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}" if len(digits) == 10 else phone

# Clean any text field (remove double spaces, commas, etc.)
def clean_text(val):
    if pd.isna(val):
        return ""
    val = str(val).replace(",", "").strip()
    val = re.sub(r"\s+", " ", val)
    return val

# Main logic
def process_csv(file):
    df = pd.read_csv(file, dtype=str, keep_default_na=False)

    # Normalize and rename columns
    original_cols = df.columns.tolist()
    col_map = {col: normalize_column(col) for col in df.columns}
    df.rename(columns=col_map, inplace=True)

    # Fix Full Name if missing
    if "Full Name" not in df.columns:
        first = df.get("First Name", "")
        last = df.get("Last Name", "")
        df["Full Name"] = first + " " + last

    # Combine addresses
    df["Business Address"] = (
        df.get("Address", "") + ", " + df.get("City", "") + ", " +
        df.get("State", "") + " " + df.get("Zip", "")
    )
    df["Home Address"] = (
        df.get("Owner Address", "") + ", " + df.get("Owner City", "") + ", " +
        df.get("Owner State", "") + " " + df.get("Owner Zip", "")
    )

    # Phones
    phone_cols = [c for c in df.columns if c.lower().startswith("phone")]
    phones_df = df[phone_cols].fillna("")
    df["Phone 1"] = phones_df.apply(lambda row: format_phone(next((p for p in row if p.strip()), "")), axis=1)
    df["Phone 2"] = phones_df.apply(lambda row: format_phone(next((p for p in row if p.strip() and p != row.get("Phone 1", "")), "")), axis=1)

    # Emails
    df["Email 1"] = df.get("Email A", "")
    df["Email 2"] = df.get("Email B", "")

    # Build cleaned DataFrame
    cleaned = pd.DataFrame()
    untouched_cols = []
    for col in FINAL_COLUMNS:
        if col in df.columns:
            cleaned[col] = df[col].apply(clean_text)
        else:
            cleaned[col] = ""

    # Preserve unrecognized columns after FINAL_COLUMNS
    recognized = set(cleaned.columns)
    all_cleaned_cols = [normalize_column(c) for c in original_cols]
    leftovers = [c for c in df.columns if c not in recognized]
    for col in leftovers:
        cleaned[col] = df[col]
        untouched_cols.append(col)

    # Generate summary message
    summary = []
    if untouched_cols:
        summary.append(f"⚠️ The following columns were untouched and placed at the end: `{', '.join(untouched_cols)}`.")
    else:
        summary.append("✅ All known columns were mapped successfully.")
    return cleaned, "\n".join(summary)

# Streamlit UI
uploaded_file = st.file_uploader("Upload a CSV file", type="csv")

if uploaded_file:
    try:
        cleaned_df, report = process_csv(uploaded_file)
        st.success("Data cleaned successfully!")
        st.markdown(report)
        st.dataframe(cleaned_df, use_container_width=True)

        st.download_button(
            label="Download Cleaned CSV",
            data=cleaned_df.to_csv(index=False).encode("utf-8"),
            file_name="hub_ready_cleaned.csv",
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"⚠️ Error: {str(e)}")
