import streamlit as st
import pandas as pd
import re
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

# -------------------- PAGE SETUP --------------------
st.set_page_config(page_title="CAPNOW DATA CLEANER APP")
st.title("CAPNOW DATA CLEANER APP")
st.markdown("**Creator: Jaco Simkin – Director of Data Analysis**")
st.markdown("This app cleans and classifies any messy CSV/XLSX lead file into a unified format ready for CAPNOW.")

# -------------------- FINAL STRUCTURE --------------------
FINAL_COLUMNS = [
    "Lead Date", "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Phone 3", "Email 1", "Email 2",
    "Business Address", "Home Address", "Monthly Revenue"
]

# -------------------- FILE UPLOAD --------------------
uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])

# -------------------- HELPERS --------------------
def normalize_header(header):
    return re.sub(r'[^a-z0-9]', '', header.lower().strip())

def looks_like_ssn(val):
    return bool(re.match(r'\d{3}-\d{2}-\d{4}', val))

def looks_like_ein(val):
    return bool(re.match(r'\d{2}-\d{7}', val))

def looks_like_email(val):
    return "@" in val and "." in val

def looks_like_phone(val):
    digits = re.sub(r"\D", "", val)
    return len(digits) == 10

def looks_like_date(val):
    try:
        d = pd.to_datetime(val, errors='coerce')
        return pd.notnull(d)
    except:
        return False

def extract_confidence_column(df, check_func):
    best_score = 0
    best_col = None
    for col in df.columns:
        score = df[col].astype(str).apply(check_func).mean()
        if score > best_score:
            best_score = score
            best_col = col
    return best_col if best_score > 0.5 else None

# -------------------- SMART CLASSIFIER --------------------
def smart_cleaner(df):
    df.columns = [normalize_header(col) for col in df.columns]

    cleaned = pd.DataFrame()
    
    # Lead Date from first column if mostly dates
    lead_col = df.columns[0]
    try:
        lead_dates = pd.to_datetime(df[lead_col], errors='coerce')
        if (lead_dates.notna().mean() > 0.5):
            cleaned["Lead Date"] = lead_dates.dt.date.astype(str)
        else:
            cleaned["Lead Date"] = ""
    except:
        cleaned["Lead Date"] = ""

    # Business Name
    biz_col = extract_confidence_column(df, lambda x: any(k in x.lower() for k in ["llc", "inc", "corp", "ltd"]))
    cleaned["Business Name"] = df[biz_col] if biz_col else ""

    # Full Name (either from full column or merge first+last)
    full = [c for c in df.columns if "fullname" in c or "contactname" in c or "name" == c]
    first = [c for c in df.columns if "first" in c]
    last = [c for c in df.columns if "last" in c]
    if full:
        cleaned["Full Name"] = df[full[0]]
    elif first and last:
        cleaned["Full Name"] = df[first[0]].astype(str) + " " + df[last[0]].astype(str)
    else:
        cleaned["Full Name"] = ""

    # SSN & EIN
    ssn_col = extract_confidence_column(df, looks_like_ssn)
    ein_col = extract_confidence_column(df, looks_like_ein)
    cleaned["SSN"] = df[ssn_col] if ssn_col else ""
    cleaned["EIN"] = df[ein_col] if ein_col else ""

    # DOB = old dates < 2000
    dob_col = None
    for col in df.columns:
        try:
            parsed = pd.to_datetime(df[col], errors='coerce')
            if (parsed.dt.year < 2000).mean() > 0.5:
                dob_col = col
                break
        except: continue
    cleaned["DOB"] = pd.to_datetime(df[dob_col], errors='coerce').dt.date.astype(str) if dob_col else ""

    # BSD = recent dates > 2005
    bsd_col = None
    for col in df.columns:
        try:
            parsed = pd.to_datetime(df[col], errors='coerce')
            if (parsed.dt.year >= 2005).mean() > 0.5:
                bsd_col = col
                break
        except: continue
    cleaned["Business Start Date"] = pd.to_datetime(df[bsd_col], errors='coerce').dt.date.astype(str) if bsd_col else ""

    # Industry
    industry_col = [c for c in df.columns if "industry" in c or "sector" in c]
    cleaned["Industry"] = df[industry_col[0]] if industry_col else ""

    # Phones
    phone_cols = [c for c in df.columns if df[c].astype(str).apply(looks_like_phone).mean() > 0.5]
    for i in range(3):
        cleaned[f"Phone {i+1}"] = df[phone_cols[i]] if i < len(phone_cols) else ""

    # Emails
    email_cols = [c for c in df.columns if df[c].astype(str).apply(looks_like_email).mean() > 0.5]
    cleaned["Email 1"] = df[email_cols[0]] if len(email_cols) > 0 else ""
    cleaned["Email 2"] = df[email_cols[1]] if len(email_cols) > 1 else ""

    # Revenue
    rev_cols = [c for c in df.columns if any(k in c for k in ["revenue", "income", "turnover"])]
    cleaned["Monthly Revenue"] = df[rev_cols[0]] if rev_cols else ""

    # Addresses
    addr_cols = [c for c in df.columns if "address" in c or "street" in c or "zip" in c or "city" in c or "state" in c]
    combined_addr = df[addr_cols].astype(str).agg(", ".join, axis=1) if addr_cols else ""
    cleaned["Business Address"] = combined_addr
    cleaned["Home Address"] = ""  # Optional: can add secondary logic

    return cleaned

# -------------------- PROCESSING --------------------
if uploaded_file:
    if uploaded_file.name.endswith("csv"):
        df = pd.read_csv(uploaded_file, dtype=str).fillna("")
    else:
        df = pd.read_excel(uploaded_file, dtype=str).fillna("")

    st.subheader("Original File Preview")
    st.dataframe(df, use_container_width=True)

    cleaned = smart_cleaner(df)
    st.subheader("Cleaned Output")
    st.dataframe(cleaned, use_container_width=True)

    name = uploaded_file.name.replace(".csv", "").replace(".xlsx", "")
    st.download_button("Download Cleaned CSV", cleaned.to_csv(index=False).encode("utf-8"), file_name=f"{name}_cleaned.csv")
