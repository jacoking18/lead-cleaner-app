import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime

st.set_page_config(page_title="CAPNOW DATA CLEANER APP")
st.title("CAPNOW DATA CLEANER APP")
st.markdown("**Creator: Jaco Simkin – Director of Data Analysis**")

st.markdown("""
This app automatically cleans raw lead files (CSV or Excel) received from multiple providers.
It standardizes messy or inconsistent data into a unified format required by the CAPNOW HUB system.

**What it does:**
- Normalizes messy column headers (lowercase, removes punctuation and spaces)
- Uses rules & pattern matching to identify common fields even if mislabeled
- Outputs a clean table with the following columns:

Lead Date, Business Name, Full Name, SSN, DOB, Industry, EIN, Business Start Date, 
Phone 1, Phone 2, Email 1, Email 2, Business Address

**Second Table (Red):**
Shows all columns from your upload that were **not recognized or cleaned**, so you can review extra info.
""")

# Define final clean columns
FINAL_COLUMNS = [
    "Lead Date", "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Email 1", "Email 2", "Business Address"
]

# Pattern-based recognition functions
def normalize_headers(columns):
    return [re.sub(r'[^a-z0-9]', '', col.lower().strip()) for col in columns]

def find_column_by_pattern(df, patterns):
    for pattern in patterns:
        for col in df.columns:
            if re.search(pattern, col.lower().strip()):
                return col
    return None

def extract_using_pattern(series, pattern):
    return series.astype(str).apply(lambda x: re.search(pattern, x).group() if re.search(pattern, x) else "")

def build_full_name(df):
    if 'firstname' in df.columns and 'lastname' in df.columns:
        return df['firstname'].astype(str).str.strip() + ' ' + df['lastname'].astype(str).str.strip()
    elif 'name' in df.columns:
        return df['name']
    return pd.Series(["" for _ in range(len(df))])

def combine_address(df):
    addr_parts = []
    for part in ['street', 'city', 'state', 'zip']:
        if part in df.columns:
            addr_parts.append(df[part].astype(str))
    return pd.Series([" ".join(x).strip() for x in zip(*addr_parts)]) if addr_parts else ""

def format_phone(phone):
    digits = re.sub(r"\D", "", str(phone))
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}" if len(digits) == 10 else ""

def clean_text(val):
    if pd.isna(val): return ""
    return re.sub(r"\s+", " ", str(val).replace(",", "")).strip()

def guess_by_regex(df, regex):
    for col in df.columns:
        if df[col].astype(str).apply(lambda x: bool(re.match(regex, x))).sum() > 0:
            return col
    return None

def clean_dataframe(df):
    df.columns = normalize_headers(df.columns)

    output = pd.DataFrame()
    output["Lead Date"] = datetime.today().strftime("%m/%d/%Y")

    output["Business Name"] = df.get(find_column_by_pattern(df, ["businessname", "company", "biz"]), "")
    output["Full Name"] = build_full_name(df)

    ssn_col = guess_by_regex(df, r"^\d{3}-\d{2}-\d{4}$")
    output["SSN"] = df.get(ssn_col, "")

    dob_col = guess_by_regex(df, r"\d{1,2}/\d{1,2}/\d{2,4}")
    output["DOB"] = df.get(dob_col, "")

    output["Industry"] = df.get(find_column_by_pattern(df, ["industry", "sector"]), "")
    output["EIN"] = df.get(find_column_by_pattern(df, ["ein", "federal"]), "")

    bsd_col = find_column_by_pattern(df, ["startdate", "yearsinbusiness"])
    output["Business Start Date"] = df.get(bsd_col, "")

    phone_cols = [col for col in df.columns if df[col].astype(str).str.contains(r"\d{3}.*\d{4}").sum() > 2][:2]
    output["Phone 1"] = df[phone_cols[0]].apply(format_phone) if len(phone_cols) > 0 else ""
    output["Phone 2"] = df[phone_cols[1]].apply(format_phone) if len(phone_cols) > 1 else ""

    email_cols = [col for col in df.columns if df[col].astype(str).str.contains("@").sum() > 2][:2]
    output["Email 1"] = df[email_cols[0]] if len(email_cols) > 0 else ""
    output["Email 2"] = df[email_cols[1]] if len(email_cols) > 1 else ""

    output["Business Address"] = combine_address(df)

    output = output[FINAL_COLUMNS].applymap(clean_text)
    unrecognized = df.drop(columns=[c for c in df.columns if c in output.columns or c in normalize_headers(FINAL_COLUMNS)], errors='ignore')
    return output, unrecognized

# Streamlit UI
uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"])
if uploaded_file:
    try:
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        df = pd.read_csv(uploaded_file) if ext == ".csv" else pd.read_excel(uploaded_file)
        cleaned_df, untouched_df = clean_dataframe(df)
        st.success("Data cleaned successfully.")

        st.markdown("### Cleaned CSV (Full Preview)")
        st.dataframe(cleaned_df, use_container_width=True)

        if not untouched_df.empty:
            st.markdown("### Unrecognized Columns (shown in red)")
            st.dataframe(untouched_df.style.set_properties(**{'background-color': 'salmon'}), use_container_width=True)

        filename = os.path.splitext(uploaded_file.name)[0] + "_cleaned.csv"
        st.download_button(
            label="Download Cleaned CSV",
            data=cleaned_df.to_csv(index=False).encode("utf-8"),
            file_name=filename,
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"Error during processing: {str(e)}")