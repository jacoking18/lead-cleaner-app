import streamlit as st
import pandas as pd
import re

# ------------------ Column Setup ------------------

FINAL_COLUMNS = [
    "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Phone 3",
    "Email 1", "Email 2", "Business Address", "Home Address", "Monthly Revenue"
]

COLUMN_MAPPING = {
    "ssn": "SSN", "social": "SSN", "social security": "SSN",
    "dob": "DOB", "date of birth": "DOB", "birth date": "DOB",
    "ein": "EIN", "employer id": "EIN",
    "business start date": "Business Start Date", "bsd": "Business Start Date", "start date": "Business Start Date",
    "yearsinbusiness": "Business Start Date", "revenue": "Monthly Revenue", "businessmonthlyrevenue": "Monthly Revenue",
    "biz name": "Business Name", "businessname": "Business Name", "company": "Business Name",
    "firstname": "First Name", "lastname": "Last Name", "ownerfullname": "Full Name",
    "phone1": "Phone A", "cellphone": "Phone B", "businessphone": "Phone C", "altphone": "Phone D",
    "googlephone": "Phone E", "google phone": "Phone E", "GOOGLEPHONE": "Phone E",
    "email": "Email A", "email1": "Email A", "email 1": "Email A",
    "email2": "Email B", "google email": "Email B",
    "address": "Address", "address1": "Address", "city": "City", "state": "State", "zip": "Zip",
    "owner address": "Owner Address", "owner city": "Owner City", "owner state": "Owner State", "owner zip": "Owner Zip"
}

def standardize_column(col):
    return COLUMN_MAPPING.get(col.strip().lower(), col.strip())

def format_phone(phone):
    digits = re.sub(r"\D", "", str(phone))
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}" if len(digits) == 10 else phone

def clean_text(val):
    return re.sub(r"\s+", " ", str(val)).strip() if pd.notna(val) else ""

# ------------------ Main Processor ------------------

def process_csv(uploaded_file):
    df = pd.read_csv(uploaded_file)
    df.rename(columns=lambda c: standardize_column(c), inplace=True)

    # Full Name
    if "Full Name" not in df.columns:
        df["Full Name"] = (
            df["First Name"] if "First Name" in df.columns else pd.Series([""] * len(df))
        ) + " " + (
            df["Last Name"] if "Last Name" in df.columns else pd.Series([""] * len(df))
        )

    # Business Address
    df["Business Address"] = (
        (df["Address"] if "Address" in df.columns else pd.Series([""] * len(df))) + ", " +
        (df["City"] if "City" in df.columns else pd.Series([""] * len(df))) + ", " +
        (df["State"] if "State" in df.columns else pd.Series([""] * len(df))) + " " +
        (df["Zip"] if "Zip" in df.columns else pd.Series([""] * len(df)))
    )

    # Home Address
    df["Home Address"] = (
        (df["Owner Address"] if "Owner Address" in df.columns else pd.Series([""] * len(df))) + ", " +
        (df["Owner City"] if "Owner City" in df.columns else pd.Series([""] * len(df))) + ", " +
        (df["Owner State"] if "Owner State" in df.columns else pd.Series([""] * len(df))) + " " +
        (df["Owner Zip"] if "Owner Zip" in df.columns else pd.Series([""] * len(df)))
    )

    # Phones
    phone_cols = [col for col in df.columns if col.lower().startswith("phone")]
    df["Phone 1"], df["Phone 2"], df["Phone 3"] = "", "", ""
    for i, row in df.iterrows():
        phones = list(dict.fromkeys([
            format_phone(row[col]) for col in phone_cols
            if pd.notna(row[col]) and str(row[col]).strip() != ""
        ]))
        for j in range(min(len(phones), 3)):
            df.at[i, f"Phone {j+1}"] = phones[j]

    # Emails (safe fallback)
    df["Email 1"] = df["Email A"] if "Email A" in df.columns else pd.Series([""] * len(df))
    df["Email 2"] = df["Email B"] if "Email B"
