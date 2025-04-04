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
- Uses smart pattern recognition and logic to infer mislabeled or missing data
- Outputs a clean table with the following columns:

Lead Date, Business Name, Full Name, SSN, DOB, Industry, EIN, Business Start Date, 
Phone 1, Phone 2, Email 1, Email 2, Business Address

**Second Table (Red):**
Shows all columns from your upload that were **not recognized or cleaned**, so you can review extra info.
""")

FINAL_COLUMNS = [
    "Lead Date", "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Email 1", "Email 2", "Business Address"
]

# Normalize headers
def normalize_headers(columns):
    return [re.sub(r'[^a-z0-9]', '', col.lower().strip()) for col in columns]

def clean_text(val):
    if pd.isna(val): return ""
    return re.sub(r"\s+", " ", str(val).replace(",", "")).strip()

# Identify likely column by regex pattern
def guess_by_regex(df, regex):
    for col in df.columns:
        if df[col].astype(str).apply(lambda x: bool(re.match(regex, x))).sum() > 2:
            return col
    return None

# Guess best email or phone columns
def guess_by_contains(df, keyword):
    return [col for col in df.columns if df[col].astype(str).str.contains(keyword).sum() > 2]

def build_full_name(df):
    if 'firstname' in df.columns and 'lastname' in df.columns:
        return df['firstname'].astype(str).str.strip() + ' ' + df['lastname'].astype(str).str.strip()
    name_col = next((c for c in df.columns if 'name' in c), None)
    return df[name_col] if name_col else pd.Series(["" for _ in range(len(df))])

def extract_business_name(df):
    for col in df.columns:
        if df[col].astype(str).str.contains(r'\b(llc|inc|co|corp|ltd)\b', flags=re.IGNORECASE).sum() > 2:
            return df[col]
    name = next((col for col in df.columns if any(k in col for k in ['business', 'company', 'dba'])), None)
    return df[name] if name else ""

def classify_date_columns(df):
    candidates = []
    for col in df.columns:
        try:
            series = pd.to_datetime(df[col], errors='coerce')
            if series.notna().sum() > 2:
                recent = (datetime.today() - series).dt.days < (365 * 10)
                if recent.sum() > 2:
                    return col, None
                else:
                    return None, col
        except:
            continue
    return None, None

def combine_address(df):
    address_cols = [col for col in df.columns if any(k in col for k in ['address', 'street', 'city', 'zip', 'state'])]
    if address_cols:
        return df[address_cols].astype(str).agg(" ".join, axis=1)
    return ""

def format_phone(phone):
    digits = re.sub(r"\D", "", str(phone))
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}" if len(digits) == 10 else ""

def clean_dataframe(df):
    original_cols = df.columns.tolist()
    df.columns = normalize_headers(df.columns)
    output = pd.DataFrame()

    # Lead Date
    try:
        first_col = pd.to_datetime(df.iloc[:, 0], errors='coerce')
        if first_col.notna().sum() > 2:
            output["Lead Date"] = first_col.dt.strftime("%m/%d/%Y")
        else:
            output["Lead Date"] = datetime.today().strftime("%m/%d/%Y")
    except:
        output["Lead Date"] = datetime.today().strftime("%m/%d/%Y")

    output["Business Name"] = extract_business_name(df)
    output["Full Name"] = build_full_name(df)
    output["SSN"] = df.get(guess_by_regex(df, r"^\d{3}-\d{2}-\d{4}$"), "")
    output["EIN"] = df.get(guess_by_regex(df, r"^\d{2}-\d{7}$"), "")

    bsd_col, dob_col = classify_date_columns(df)
    output["Business Start Date"] = df.get(bsd_col, "")
    output["DOB"] = df.get(dob_col, "")

    output["Industry"] = df.get(next((c for c in df.columns if 'industry' in c or 'sector' in c), ''), '')

    # Phones
    phone_cols = guess_by_contains(df, r'\d{3}.*\d{4}')[:2]
    output["Phone 1"] = df[phone_cols[0]].apply(format_phone) if len(phone_cols) > 0 else ""
    output["Phone 2"] = df[phone_cols[1]].apply(format_phone) if len(phone_cols) > 1 else ""

    # Emails
    email_cols = guess_by_contains(df, "@")[:2]
    output["Email 1"] = df[email_cols[0]] if len(email_cols) > 0 else ""
    output["Email 2"] = df[email_cols[1]] if len(email_cols) > 1 else ""

    # Business Address
    output["Business Address"] = combine_address(df)

    # Clean text
    output = output[FINAL_COLUMNS].applymap(clean_text)

    # Unrecognized columns
    recognized = set(normalize_headers(FINAL_COLUMNS))
    leftovers = [c for c in df.columns if c not in recognized]
    unrecognized = df[leftovers] if leftovers else pd.DataFrame()

    return output, unrecognized

# UI
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