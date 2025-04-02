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

def standardize_column(col):
    return COLUMN_MAPPING.get(col.strip().lower(), col.strip())

def format_phone(phone):
    digits = re.sub(r"\D", "", str(phone))
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return phone

def clean_text(val):
    return re.sub(r"\s+", " ", str(val)).strip() if pd.notna(val) else ""

def process_csv(uploaded_file):
    df = pd.read_csv(uploaded_file)
    df.rename(columns=lambda c: standardize_column(c), inplace=True)

    # Full name
    if "Full Name" not in df.columns:
        df["Full Name"] = df.get("First Name", pd.Series([""]*len(df))) + " " + df.get("Last Name", pd.Series([""]*len(df)))

    # Business Address
    df["Business Address"] = (
        df.get("Address", pd.Series([""])) + ", " +
        df.get("City", pd.Series([""])) + ", " +
        df.get("State", pd.Series([""])) + " " +
        df.get("Zip", pd.Series([""]))
    )

    # Home Address
    df["Home Address"] = (
        df.get("Owner Address", pd.Series([""])) + ", " +
        df.get("Owner City", pd.Series([""])) + ", " +
        df.get("Owner State", pd.Series([""])) + " " +
        df.get("Owner Zip", pd.Series([""]))
    )

    # If Home Address is empty and Business Address is filled, use that
    df["Home Address"] = df["Home Address"].replace(", ,  ", "", regex=False)
    df["Home Address"] = df["Home Address"].where(df["Home Address"].str.strip() != "", df["Business Address"])

    # Phone numbers
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

    # Email
    df["Email 1"] = df.get("Email A", pd.Series([""]))
    df["Email 2"] = df.get("Email B", pd.Series([""]))

    # Final structure
    cleaned = pd.DataFrame(columns=FINAL_COLUMNS)
    for col in FINAL_COLUMNS:
        cleaned[col] = df[col].apply(clean_text) if col in df.columns else ""

    return cleaned

# Streamlit app
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
            data=cleaned_df.to_csv(index=False).encode('utf-8'),
            file_name="hub_cleaned.csv",
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"⚠️ Something went wrong:\n\n{e}")
