import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime

st.set_page_config(page_title="CAPNOW DATA CLEANER APP")
st.title("CAPNOW DATA CLEANER APP")
st.markdown("**Creator: Jaco Simkin – Director of Data Analysis**")

FINAL_COLUMNS = [
    "Lead Date", "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Phone 3", "Email 1", "Email 2",
    "Business Address", "Home Address", "Monthly Revenue"
]

def normalize_headers(columns):
    return [re.sub(r'[^a-z0-9]', '', col.lower().strip()) for col in columns]

def clean_text(val):
    if pd.isna(val): return ""
    return re.sub(r"\s+", " ", str(val).replace(",", "")).strip()

def guess_by_regex(df, regex):
    for col in df.columns:
        if df[col].astype(str).apply(lambda x: bool(re.match(regex, x))).sum() > 2:
            return col
    return None

def guess_by_contains(df, keyword):
    return [col for col in df.columns if df[col].astype(str).str.contains(keyword, na=False).sum() > 2]

def build_full_name(df):
    if 'firstname' in df.columns and 'lastname' in df.columns:
        return df['firstname'].astype(str).str.strip() + ' ' + df['lastname'].astype(str).str.strip()
    name_col = next((c for c in df.columns if 'fullname' in c or 'contactname' in c or 'name' in c), None)
    return df[name_col] if name_col else pd.Series(["" for _ in range(len(df))])

def extract_business_name(df):
    for col in df.columns:
        if df[col].astype(str).str.contains(r'\b(llc|inc|co|corp|ltd)\b', flags=re.IGNORECASE).sum() > 2:
            date_matches = df[col].astype(str).str.contains(r'\d{1,2}[-/]\d{1,2}[-/]\d{2,4}')
            if date_matches.sum() < len(df) * 0.3:
                return df[col]
    name = next((col for col in df.columns if any(k in col for k in ['business', 'company', 'dba', 'bizname'])), None)
    return df[name] if name else ""

def classify_date_columns(df):
    bsd_col, dob_col = None, None
    max_old_ratio = 0

    for col in df.columns:
        try:
            series = pd.to_datetime(df[col].astype(str), errors='coerce')
            valid_dates = series.dropna()

            if valid_dates.shape[0] < 3:
                continue

            old_dates_ratio = (valid_dates.dt.year < 2000).sum() / len(valid_dates)

            if old_dates_ratio > 0.6 and old_dates_ratio > max_old_ratio:
                dob_col = col
                max_old_ratio = old_dates_ratio

            elif valid_dates.dt.year.between(2005, datetime.now().year).sum() > len(valid_dates) * 0.6 and col != df.columns[0]:
                bsd_col = col

        except Exception as e:
            continue

    return bsd_col, dob_col

def combine_address(df):
    address_cols = [col for col in df.columns if any(k in col for k in ['address', 'street', 'city', 'zip', 'state'])]
    if address_cols:
        return df[address_cols].astype(str).agg(" ".join, axis=1)
    return ""

def format_phone(phone):
    digits = re.sub(r"\D", "", str(phone))
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}" if len(digits) == 10 else ""

def clean_dataframe(df):
    df.columns = normalize_headers(df.columns)
    ignore_keywords = ['folder', 'filelocation', 'pdflink', 'filepath', 'storage']
    df = df[[col for col in df.columns if not any(key in col for key in ignore_keywords)]]
    output = pd.DataFrame()

    try:
        parsed_first = pd.to_datetime(df.iloc[:, 0], errors='coerce')
        output["Lead Date"] = parsed_first.dt.strftime("%m/%d/%Y") if parsed_first.notna().sum() > 2 else ""
    except:
        output["Lead Date"] = ""

    output["Business Name"] = extract_business_name(df)
    output["Full Name"] = build_full_name(df)

    ssn_col = next((c for c in df.columns if any(k in c for k in ['ssn', 'social'])), None)
    output["SSN"] = df.get(ssn_col, df.get(guess_by_regex(df, r"^\d{3}-\d{2}-\d{4}$"), ""))

    ein_col = next((c for c in df.columns if any(k in c for k in ['ein', 'tax'])), None)
    output["EIN"] = df.get(ein_col, df.get(guess_by_regex(df, r"^\d{2}-\d{7}$"), ""))

    bsd_col, dob_col = classify_date_columns(df)
    output["Business Start Date"] = df[bsd_col] if bsd_col else ""
    if dob_col:
        parsed_dob = pd.to_datetime(df[dob_col], errors='coerce')
        output["DOB"] = parsed_dob.dt.strftime("%m/%d/%Y")
    else:
        dob_hint = next((c for c in df.columns if any(k in c for k in ['dob', 'birth'])), None)
        parsed_dob = pd.to_datetime(df[dob_hint], errors='coerce') if dob_hint else None
        output["DOB"] = parsed_dob.dt.strftime("%m/%d/%Y") if parsed_dob is not None else ""

    output["Industry"] = df.get(next((c for c in df.columns if 'industry' in c or 'sector' in c), ''), '')

    phone_cols = guess_by_contains(df, r'\d{3}.*\d{4}')[:3]
    output["Phone 1"] = df[phone_cols[0]].apply(format_phone) if len(phone_cols) > 0 else ""
    output["Phone 2"] = df[phone_cols[1]].apply(format_phone) if len(phone_cols) > 1 else ""
    output["Phone 3"] = df[phone_cols[2]].apply(format_phone) if len(phone_cols) > 2 else ""

    email_cols = guess_by_contains(df, "@")[:2]
    output["Email 1"] = df[email_cols[0]] if len(email_cols) > 0 else ""
    output["Email 2"] = df[email_cols[1]] if len(email_cols) > 1 else ""

    output["Business Address"] = combine_address(df)
    output["Home Address"] = ""
    rev_col = next((c for c in df.columns if 'revenue' in c or 'monthly' in c), None)
    output["Monthly Revenue"] = df.get(rev_col, "")

    output = output[FINAL_COLUMNS].applymap(clean_text)
    return output

uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"])
if uploaded_file:
    try:
        ext = os.path.splitext(uploaded_file.name)[1].lower()
        df = pd.read_csv(uploaded_file) if ext == ".csv" else pd.read_excel(uploaded_file)
        cleaned_df = clean_dataframe(df)
        st.success("Data cleaned successfully.")
        st.markdown("### Cleaned CSV (Full Preview)")
        st.dataframe(cleaned_df, use_container_width=True)

        st.markdown("### Original Uploaded CSV")
        st.dataframe(df, use_container_width=True)

        filename = os.path.splitext(uploaded_file.name)[0] + "_cleaned.csv"
        st.download_button(
            label="Download Cleaned CSV",
            data=cleaned_df.to_csv(index=False).encode("utf-8"),
            file_name=filename,
            mime="text/csv"
        )
    except Exception as e:
        st.error(f"Error during processing: {str(e)}")
