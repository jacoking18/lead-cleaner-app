import streamlit as st
import pandas as pd
import re

# ---------------- CONFIG ----------------

FINAL_COLUMNS = [
    "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Email 1", "Email 2",
    "Business Address", "Home Address", "Monthly Revenue"
]

# Known messy header variations
HUB_COLUMN_MAP = {
    "businessname": "Business Name", "bizname": "Business Name", "companyname": "Business Name",
    "fullname": "Full Name", "contactname": "Full Name", "name": "Full Name", "ownername": "Full Name",
    "ssn": "SSN", "social": "SSN", "socialsecurity": "SSN", "socialsecuritynumber": "SSN",
    "dob": "DOB", "birthdate": "DOB", "dateofbirth": "DOB", "birth": "DOB",
    "industry": "Industry", "businesstype": "Industry", "sector": "Industry",
    "ein": "EIN", "employerid": "EIN", "taxid": "EIN",
    "businessstartdate": "Business Start Date", "startdate": "Business Start Date", "bsd": "Business Start Date",
    "phone": "Phone A", "phone1": "Phone A", "cell": "Phone B", "cellphone": "Phone B",
    "phone2": "Phone B", "altphone": "Phone B", "googlephone": "Phone B",
    "email": "Email A", "email1": "Email A", "emailaddress": "Email A",
    "email2": "Email B", "googleemail": "Email B",
    "address": "Address", "street": "Address", "businessaddress": "Address",
    "city": "City", "state": "State", "zip": "Zip",
    "owneraddress": "Owner Address", "homeaddress": "Owner Address",
    "ownercity": "Owner City", "ownerstate": "Owner State", "ownerzip": "Owner Zip",
    "monthlyrevenue": "Monthly Revenue", "revenue": "Monthly Revenue", "income": "Monthly Revenue"
}

def normalize_column(col):
    return re.sub(r"[^a-z0-9]", "", str(col).lower().strip())

def standardize_columns(df):
    new_cols = []
    for col in df.columns:
        normalized = normalize_column(col)
        mapped = HUB_COLUMN_MAP.get(normalized, col)
        new_cols.append(mapped)
    df.columns = new_cols
    return df

def format_phone(phone):
    digits = re.sub(r"\D", "", str(phone))
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return phone

def clean_text(val):
    return re.sub(r"\s+", " ", str(val)).strip() if pd.notna(val) else ""

def process_csv(uploaded_file):
    report = []

    df = pd.read_csv(uploaded_file)
    original_cols = df.columns.tolist()

    # Standardize columns
    df = standardize_columns(df)

    if "Full Name" not in df.columns:
        # Case: First Name contains full name
        if "First Name" in df.columns and "Last Name" not in df.columns:
            df["Full Name"] = df["First Name"]
            report.append("Full Name built from 'First Name'")
        elif "First Name" in df.columns and "Last Name" in df.columns:
            df["Full Name"] = df["First Name"].fillna("") + " " + df["Last Name"].fillna("")
            report.append("Full Name built from First + Last")
        else:
            df["Full Name"] = ""

    # Construct addresses
    df["Business Address"] = df.get("Address", "") + ", " + \
                             df.get("City", "") + ", " + \
                             df.get("State", "") + " " + df.get("Zip", "")

    df["Home Address"] = df.get("Owner Address", "") + ", " + \
                         df.get("Owner City", "") + ", " + \
                         df.get("Owner State", "") + " " + df.get("Owner Zip", "")

    # Phones
    phone_cols = [col for col in df.columns if "phone" in col.lower()]
    df["Phone 1"], df["Phone 2"] = "", ""
    for i, row in df.iterrows():
        phones = list(dict.fromkeys([
            format_phone(row[col]) for col in phone_cols
            if pd.notna(row[col]) and str(row[col]).strip() != ""
        ]))
        if phones:
            df.at[i, "Phone 1"] = phones[0]
        if len(phones) > 1:
            df.at[i, "Phone 2"] = phones[1]
    report.append(f"{len(phone_cols)} phone column(s) processed")

    # Emails
    df["Email 1"] = df.get("Email A", "")
    df["Email 2"] = df.get("Email B", "")

    # Build final cleaned DataFrame
    cleaned = pd.DataFrame()
    for col in FINAL_COLUMNS:
        cleaned[col] = df[col].apply(clean_text) if col in df.columns else ""

    # Append unmatched columns to the end (not lost)
    unmatched = [col for col in df.columns if col not in FINAL_COLUMNS]
    for col in unmatched:
        cleaned[col] = df[col]

    report.append(f"{len(FINAL_COLUMNS)} HUB columns cleaned")
    report.append(f"{len(unmatched)} extra columns kept (unmatched)")

    return cleaned, report

# ---------------- STREAMLIT UI ----------------

st.set_page_config(page_title="HUB Lead Cleaner", layout="centered")

st.title("HUB Lead Cleaner")
st.caption("Upload a messy provider CSV → Get a clean version for the HUB")
st.markdown("**Creator: Jacoking**")

uploaded_file = st.file_uploader("📤 Upload your CSV file", type="csv")

if uploaded_file:
    cleaned_df, summary = process_csv(uploaded_file)
    st.success("✅ File cleaned successfully!")

    # Display result
    st.dataframe(cleaned_df, use_container_width=True)

    # Download cleaned CSV
    st.download_button(
        label="📥 Download Cleaned CSV",
        data=cleaned_df.to_csv(index=False).encode("utf-8"),
        file_name="hub_cleaned.csv",
        mime="text/csv"
    )

    # Display summary report
    st.markdown("---")
    st.subheader("🧾 What was done:")
    for line in summary:
        st.write("• " + line)
