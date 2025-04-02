import streamlit as st
import pandas as pd
import re

# Final HUB columns expected
FINAL_COLUMNS = [
    "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Email 1", "Email 2",
    "Business Address", "Home Address", "Monthly Revenue"
]

# Mapping possible column name variations
COLUMN_MAPPING = {
    # Name
    "biz name": "Business Name", "business name": "Business Name", "company": "Business Name",
    "fullname": "Full Name", "full.name": "Full Name", "name": "Full Name",
    "firstname": "First Name", "first name": "First Name",
    "lastname": "Last Name", "last name": "Last Name",

    # SSN & DOB
    "ssn": "SSN", "social": "SSN", "social security": "SSN",
    "dob": "DOB", "birth date": "DOB", "date of birth": "DOB",

    # EIN & Industry
    "ein": "EIN", "employer id": "EIN",
    "industry": "Industry", "sector": "Industry",

    # Start Date & Revenue
    "start date": "Business Start Date", "yearsinbusiness": "Business Start Date",
    "revenue": "Monthly Revenue", "monthly income": "Monthly Revenue",

    # Phones
    "phone": "Phone", "phone1": "Phone", "number1": "Phone", "cell": "Phone", "googlephone": "Phone",
    "phone number": "Phone", "mobile": "Phone", "telephone": "Phone",

    # Emails
    "email": "Email", "email1": "Email", "email address": "Email",
    "alt email": "Alt Email", "email2": "Alt Email",

    # Addresses
    "address": "Address", "address1": "Address", "addr": "Address", "full address": "Address",
    "city": "City", "state": "State", "zip": "Zip",
    "owner address": "Owner Address", "owner city": "Owner City", "owner state": "Owner State", "owner zip": "Owner Zip"
}

def normalize_column(col):
    """Clean column names: remove punctuation, lowercase, trim spaces"""
    col = re.sub(r'[^\w\s]', '', col)  # remove punctuation
    return COLUMN_MAPPING.get(col.strip().lower().replace(" ", ""), col.strip())

def format_phone(phone):
    digits = re.sub(r"\D", "", str(phone))
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}" if len(digits) == 10 else phone

def clean_text(val):
    if pd.isna(val):
        return ""
    val = str(val).replace(",", "").replace("  ", " ")
    return re.sub(r"\s+", " ", val).strip()

def process_csv(uploaded_file):
    df = pd.read_csv(uploaded_file)

    # Step 1: Standardize headers
    df.columns = [normalize_column(col) for col in df.columns]

    # Step 2: Handle names
    if "Full Name" not in df.columns:
        first = df.get("First Name", "")
        last = df.get("Last Name", "")
        df["Full Name"] = first.fillna("") + " " + last.fillna("")
    df["Full Name"] = df["Full Name"].apply(clean_text)

    # Step 3: Phone columns
    phone_cols = [col for col in df.columns if "phone" in col.lower()]
    df["Phone 1"], df["Phone 2"] = "", ""
    for i, row in df.iterrows():
        phones = [format_phone(row[col]) for col in phone_cols if pd.notna(row[col]) and str(row[col]).strip()]
        for j, val in enumerate(phones[:2]):
            df.at[i, f"Phone {j+1}"] = val

    # Step 4: Email
    df["Email 1"] = df.get("Email", "").fillna("")
    df["Email 2"] = df.get("Alt Email", "").fillna("")

    # Step 5: Address
    df["Business Address"] = (
        df.get("Address", "").fillna("") + ", " +
        df.get("City", "").fillna("") + ", " +
        df.get("State", "").fillna("") + " " +
        df.get("Zip", "").fillna("")
    )

    df["Home Address"] = (
        df.get("Owner Address", "").fillna("") + ", " +
        df.get("Owner City", "").fillna("") + ", " +
        df.get("Owner State", "").fillna("") + " " +
        df.get("Owner Zip", "").fillna("")
    )

    # Step 6: Build clean final dataframe
    cleaned = pd.DataFrame()
    for col in FINAL_COLUMNS:
        if col in df.columns:
            cleaned[col] = df[col].apply(clean_text)
        else:
            cleaned[col] = ""

    # Step 7: Add extra unknown columns to the end
    for col in df.columns:
        if col not in FINAL_COLUMNS and col not in cleaned.columns:
            cleaned[col] = df[col].apply(clean_text)

    # Step 8: Summary
    summary = {
        "rows_loaded": len(df),
        "final_columns": list(cleaned.columns),
        "unrecognized_columns": [col for col in df.columns if col not in FINAL_COLUMNS]
    }

    return cleaned, summary

# Streamlit UI
st.set_page_config(page_title="CAPNOW DATA CLEANER APP")
st.title("CAPNOW DATA CLEANER APP")
st.write("Upload a messy provider CSV → Download a cleaned version ready for the HUB")

uploaded_file = st.file_uploader("Upload a CSV file", type="csv")

if uploaded_file:
    try:
        cleaned_df, summary = process_csv(uploaded_file)
        st.success(f"✅ {summary['rows_loaded']} rows cleaned successfully!")

        if summary["unrecognized_columns"]:
            st.warning(f"⚠️ Extra columns added at the end: {', '.join(summary['unrecognized_columns'])}")

        st.dataframe(cleaned_df, use_container_width=True)

        st.download_button(
            label="⬇️ Download Cleaned CSV",
            data=cleaned_df.to_csv(index=False).encode('utf-8'),
            file_name="hub_cleaned.csv",
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"❌ Error: {e}")

# Footer
st.markdown("---")
st.markdown("**Creator: Jacoking**  \n_alber es marico_")
