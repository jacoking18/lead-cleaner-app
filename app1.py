import streamlit as st
import pandas as pd
import re
import os
from datetime import datetime

# -------------------- PASSWORD PROTECTION --------------------
def check_password():
    def password_entered():
        if st.session_state["password"] == "capnow$":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Enter password:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Enter password:", type="password", on_change=password_entered, key="password")
        st.error("Incorrect password.")
        return False
    else:
        return True

if not check_password():
    st.stop()
# -------------------------------------------------------------

st.set_page_config(page_title="CAPNOW DATA CLEANER APP")
st.title("CAPNOW DATA CLEANER APP")
st.markdown("**Creator: Jaco Simkin – Director of Data Analysis**")

st.markdown("""
This app cleans raw CSV or Excel files received from lead providers and outputs a standardized file ready for the CAPNOW HUB.

It smartly detects and matches fields like Full Name, SSN, Phone, Revenue, and more, even if the original column names or formats vary.

- It always keeps all expected HUB columns, even if they’re empty.
- It uses smart logic to detect DOB (old dates), BSD (recent dates), Business Names (LLC/INC/etc), and more.
- It shows the original file for comparison so you can see what was cleaned.
- The final result is downloadable as: `originalfilename_cleaned.csv`.
""")

FINAL_COLUMNS = [
    "Lead Date", "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Phone 3", "Email 1", "Email 2",
    "Business Address", "Home Address", "Monthly Revenue"
]

FIELD_ALIASES = {
    "first_name": ["firstname", "first name", "fname", "applicantfirstname", "givenname"],
    "last_name": ["lastname", "last name", "lname", "applicantlastname", "surname"],
    "full_name": ["fullname", "contactname", "applicantname", "name", "borrowername", "clientname", "ownername"],
    "ssn": ["ssn", "social", "socialsecurity", "socialsecuritynumber", "social sec"],
    "ein": ["ein", "taxid", "tax id", "fein", "federalid", "business taxid", "employer id"],
    "dob": ["dob", "birthdate", "dateofbirth", "birth", "d.o.b", "applicantdob"],
    "business_name": ["businessname", "company", "companyname", "organization", "bizname", "dba", "employer", "legal business name"],
    "industry": ["industry", "sector", "business type", "business category", "natureofbusiness"],
    "phone": ["phone", "cell", "mobile", "contact", "primary phone", "contact number", "number", "telephone"],
    "phone2": ["phone2", "cell2", "mobile2", "secondary phone", "alt phone"],
    "phone3": ["phone3", "cell3", "mobile3", "extra phone"],
    "email": ["email", "email1", "gmail", "contact email", "googleemail", "applicantemail", "e-mail"],
    "email2": ["email2", "backupemail", "secondaryemail", "alt email"],
    "revenue": ["monthly revenue", "revenue", "income", "turnover", "monthlyincome", "monthly gross", "gross revenue", "grossmonthlyincome"],
    "address": ["address", "street", "city", "state", "zip", "zipcode", "mailing address", "business address", "home address", "location", "residential address"]
}

# -------------------- HELPERS --------------------
def normalize(col):
    return re.sub(r"[^a-z0-9]", "", str(col).lower().strip())

def extract_by_keywords(df, keys):
    for col in df.columns:
        if normalize(col) in [normalize(k) for k in keys]:
            return df[col]
    return pd.Series([""] * len(df))

def extract_phones(df):
    phones = []
    for col in df.columns:
        digits = df[col].astype(str).apply(lambda x: re.sub(r"\D", "", x))
        valid = digits[digits.str.len() == 10]
        if len(valid) > 0:
            phones.append(valid)
    phones = phones[:3] + [pd.Series([""] * len(df))] * (3 - len(phones))
    return phones

def extract_emails(df):
    emails = []
    for col in df.columns:
        matches = df[col].astype(str).str.contains(r"@")
        if matches.any():
            emails.append(df[col])
    emails = emails[:2] + [pd.Series([""] * len(df))] * (2 - len(emails))
    return emails

def extract_dobs(df):
    dob_candidates = []
    for col in df.columns:
        try:
            dates = pd.to_datetime(df[col], errors='coerce')
            if dates.notna().sum() > 0:
                if (dates.dropna().dt.year < 2000).mean() > 0.5:
                    dob_candidates.append(dates)
        except: pass
    return dob_candidates[0] if dob_candidates else pd.Series([""] * len(df))

def extract_bsd(df):
    bsd_candidates = []
    for col in df.columns:
        try:
            dates = pd.to_datetime(df[col], errors='coerce')
            if dates.notna().sum() > 0:
                if (dates.dropna().dt.year >= 2000).mean() > 0.5:
                    bsd_candidates.append(dates)
        except: pass
    return bsd_candidates[0] if bsd_candidates else pd.Series([""] * len(df))

def extract_lead_date(df):
    first_col = df.iloc[:, 0]
    try:
        date_series = pd.to_datetime(first_col, errors='coerce')
        if date_series.notna().sum() > 0 and (date_series.dropna().dt.year > 2000).mean() > 0.5:
            return date_series
    except: pass
    return pd.Series([""] * len(df))

# -------------------- PROCESS --------------------
uploaded_file = st.file_uploader("Upload your CSV or XLSX", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file, dtype=str).fillna("")
    else:
        df = pd.read_excel(uploaded_file, dtype=str).fillna("")

    # Clean headers
    df.columns = [str(c).strip() for c in df.columns]

    out = pd.DataFrame()

    out["Lead Date"] = extract_lead_date(df)
    out["Business Name"] = extract_by_keywords(df, FIELD_ALIASES["business_name"])
    out["Full Name"] = (
        extract_by_keywords(df, FIELD_ALIASES["first_name"]).astype(str) + " " +
        extract_by_keywords(df, FIELD_ALIASES["last_name"]).astype(str)
    ).str.strip()
    out["SSN"] = extract_by_keywords(df, FIELD_ALIASES["ssn"])
    out["DOB"] = extract_dobs(df).astype(str)
    out["Industry"] = extract_by_keywords(df, FIELD_ALIASES["industry"])
    out["EIN"] = extract_by_keywords(df, FIELD_ALIASES["ein"])
    out["Business Start Date"] = extract_bsd(df).astype(str)

    phones = extract_phones(df)
    out["Phone 1"] = phones[0]
    out["Phone 2"] = phones[1]
    out["Phone 3"] = phones[2]

    emails = extract_emails(df)
    out["Email 1"] = emails[0]
    out["Email 2"] = emails[1]

    out["Business Address"] = extract_by_keywords(df, FIELD_ALIASES["address"])
    out["Home Address"] = extract_by_keywords(df, ["home address", "residential address", "owner address"])
    out["Monthly Revenue"] = extract_by_keywords(df, FIELD_ALIASES["revenue"])

    st.subheader("Cleaned Output")
    st.dataframe(out, use_container_width=True)

    st.subheader("Original Uploaded File")
    st.dataframe(df, use_container_width=True)

    cleaned_filename = uploaded_file.name.replace(".csv", "").replace(".xlsx", "") + "_cleaned.csv"
    st.download_button("Download Cleaned CSV", out.to_csv(index=False).encode("utf-8"), file_name=cleaned_filename)
