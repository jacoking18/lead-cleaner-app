import streamlit as st
import pandas as pd
import re

# ---------- CONFIG ---------- #
st.set_page_config(layout="wide")
st.title("CAPNOW DATA CLEANER APP")
st.caption("Creator: Jacoking | alber es marico")

# HUB Final Columns
FINAL_COLUMNS = [
    "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Email 1", "Email 2",
    "Business Address", "Home Address", "Monthly Revenue"
]

# Known Variations Mapping
COLUMN_MAPPING = {
    "ssn": "SSN", "social security": "SSN", "social": "SSN",
    "dob": "DOB", "birth date": "DOB", "dateofbirth": "DOB",
    "ein": "EIN", "employer id": "EIN",
    "business start date": "Business Start Date", "bsd": "Business Start Date", "startdate": "Business Start Date", "years in business": "Business Start Date",
    "revenue": "Monthly Revenue", "monthly revenue": "Monthly Revenue", "businessmonthlyrevenue": "Monthly Revenue",
    "biz name": "Business Name", "businessname": "Business Name", "company": "Business Name",
    "firstname": "First Name", "lastname": "Last Name", "ownerfullname": "Full Name", "name": "First Name",
    "phone1": "Phone", "cellphone": "Phone", "phone number": "Phone", "googlephone": "Phone", "number1": "Phone",
    "email": "Email", "email1": "Email", "email address": "Email", "google email": "Email",
    "address": "Address", "street": "Address", "city": "City", "state": "State", "zip": "Zip",
    "owner address": "Owner Address", "owner city": "Owner City", "owner state": "Owner State", "owner zip": "Owner Zip",
    "industry": "Industry"
}

# --------- Functions --------- #
def normalize_col(col):
    return re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z0-9 ]", "", col)).strip().lower()

def standardize_column(col):
    key = normalize_col(col)
    return COLUMN_MAPPING.get(key, col.strip())

def format_phone(phone):
    digits = re.sub(r"\D", "", str(phone))
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}" if len(digits) == 10 else ""

def clean_text(val):
    if pd.isna(val):
        return ""
    return re.sub(r"\s+", " ", str(val)).replace(",", "").strip()

def process_csv(uploaded_file):
    df = pd.read_csv(uploaded_file)
    original_cols = list(df.columns)

    # Standardize column names
    df.rename(columns=lambda c: standardize_column(c), inplace=True)

    # Handle Full Name
    if "Full Name" not in df.columns:
        df["Full Name"] = df.get("First Name", "").astype(str).fillna("") + " " + df.get("Last Name", "").astype(str).fillna("")

    # Business Address
    df["Business Address"] = (
        df.get("Address", "").astype(str).fillna("") + " " +
        df.get("City", "").astype(str).fillna("") + " " +
        df.get("State", "").astype(str).fillna("") + " " +
        df.get("Zip", "").astype(str).fillna("")
    ).str.replace(",", "").str.replace("  ", " ")

    # Home Address
    df["Home Address"] = (
        df.get("Owner Address", "").astype(str).fillna("") + " " +
        df.get("Owner City", "").astype(str).fillna("") + " " +
        df.get("Owner State", "").astype(str).fillna("") + " " +
        df.get("Owner Zip", "").astype(str).fillna("")
    ).str.replace(",", "").str.replace("  ", " ")

    # Phones
    phone_cols = [col for col in df.columns if "phone" in col.lower()]
    phones = df[phone_cols].applymap(format_phone).values.tolist()
    df["Phone 1"], df["Phone 2"] = zip(*[(p[0], p[1] if len(p) > 1 else "") for p in [list(dict.fromkeys(row)) for row in phones]])

    # Emails
    df["Email 1"] = df.get("Email", "").astype(str).fillna("")
    df["Email 2"] = ""

    # Final Clean DataFrame
    cleaned = pd.DataFrame()
    for col in FINAL_COLUMNS:
        cleaned[col] = df[col].apply(clean_text) if col in df.columns else ""

    # Add untouched columns (unrecognized ones)
    known_cols = set(FINAL_COLUMNS)
    recognized_cols = {standardize_column(c) for c in original_cols}
    untouched_cols = [col for col in df.columns if col not in known_cols and standardize_column(col) not in recognized_cols]

    untouched_df = df[untouched_cols].copy()
    untouched_df.columns = [f"❌ {col}" for col in untouched_cols]  # Mark in red (Streamlit doesn't support cell color natively)

    final_df = pd.concat([cleaned, untouched_df], axis=1)

    summary = {
        "✅ Cleaned Columns": FINAL_COLUMNS,
        "❌ Unrecognized Columns": untouched_cols,
        "📦 Total Columns": len(final_df.columns),
        "📈 Total Rows": len(final_df)
    }

    return final_df, summary

# ---------- Streamlit UI ---------- #

uploaded_file = st.file_uploader("Upload a CSV file", type="csv")

if uploaded_file:
    try:
        cleaned_df, summary = process_csv(uploaded_file)
        st.success("✅ Data cleaned successfully!")
        st.write("### Cleaned CSV (Full Preview)")
        st.dataframe(cleaned_df, use_container_width=True)

        st.download_button(
            label="📥 Download Cleaned CSV",
            data=cleaned_df.to_csv(index=False).encode("utf-8"),
            file_name="hub_cleaned.csv",
            mime="text/csv"
        )

        with st.expander("ℹ️ What was done?"):
            st.write(summary)

    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
