import streamlit as st
import pandas as pd
import re

# -------------------- CONFIGURATION --------------------
st.set_page_config(page_title="CAPNOW DATA CLEANER APP", layout="wide")
st.title("CAPNOW DATA CLEANER APP")
st.markdown("### Creator: Jaco Simkin - Director of Data Analysis  \n*alber es marico*")
st.markdown("*For use with small business financial services CSVs.*")

# -------------------- STANDARDIZATION --------------------
FINAL_COLUMNS = [
    "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Email 1", "Email 2",
    "Business Address", "Home Address", "Monthly Revenue"
]

VARIANTS = {
    "ssn": "SSN", "social security": "SSN", "social": "SSN",
    "dob": "DOB", "date of birth": "DOB", "birthdate": "DOB",
    "ein": "EIN", "employer id": "EIN",
    "biz name": "Business Name", "businessname": "Business Name", "company": "Business Name",
    "industry": "Industry", "sector": "Industry",
    "start date": "Business Start Date", "years in business": "Business Start Date",
    "firstname": "First Name", "last name": "Last Name", "full name": "Full Name", "owner name": "Full Name",
    "phone1": "Phone A", "cellphone": "Phone B", "mobile": "Phone B", "alt phone": "Phone C", "googlephone": "Phone C",
    "email": "Email A", "email1": "Email A", "email2": "Email B", "work email": "Email B",
    "monthly revenue": "Monthly Revenue", "revenue": "Monthly Revenue",
    "address": "Address", "address1": "Address", "street": "Address",
    "city": "City", "state": "State", "zip": "Zip",
    "owner address": "Owner Address", "owner city": "Owner City", "owner state": "Owner State", "owner zip": "Owner Zip"
}

def normalize_column(col):
    col = re.sub(r"[^a-zA-Z0-9 ]", " ", str(col)).strip().lower()
    col = re.sub(r"\s+", " ", col)
    return VARIANTS.get(col, col.title())

def format_phone(p):
    digits = re.sub(r"\D", "", str(p))
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    return ""

def clean_text(val):
    return re.sub(r"\s+", " ", str(val)).strip().replace(",", "") if pd.notna(val) else ""

# -------------------- MAIN CLEANING FUNCTION --------------------
def process_csv(uploaded_file):
    df = pd.read_csv(uploaded_file, dtype=str)
    df.columns = [normalize_column(col) for col in df.columns]

    all_original_columns = set(df.columns)
    original_col_count = len(all_original_columns)

    # Full Name logic
    if "Full Name" not in df.columns:
        df["Full Name"] = df.get("First Name", "") + " " + df.get("Last Name", "")
    df["Full Name"] = df["Full Name"].apply(clean_text)

    # Business Address
    df["Business Address"] = (
        df.get("Address", "").fillna("") + ", " + df.get("City", "").fillna("") + ", " + df.get("State", "").fillna("") + " " + df.get("Zip", "").fillna("")
    )

    # Home Address
    df["Home Address"] = (
        df.get("Owner Address", "").fillna("") + ", " + df.get("Owner City", "").fillna("") + ", " + df.get("Owner State", "").fillna("") + " " + df.get("Owner Zip", "").fillna("")
    )

    # Phone logic — only keep first 2 valid phones
    phone_cols = [c for c in df.columns if "Phone" in c]
    phones_extracted = df[phone_cols].applymap(format_phone).values.tolist()
    df["Phone 1"] = [next((p for p in row if p), "") for row in phones_extracted]
    df["Phone 2"] = [next((p for p in row[1:] if p), "") for row in phones_extracted]

    # Email logic
    df["Email 1"] = df.get("Email A", "").fillna("").astype(str)
    df["Email 2"] = df.get("Email B", "").fillna("").astype(str)

    # Combine & clean final columns
    cleaned = pd.DataFrame()
    for col in FINAL_COLUMNS:
        if col in df.columns:
            cleaned[col] = df[col].apply(clean_text)
        else:
            cleaned[col] = ""

    # Remove components after use
    drop_cols = {"First Name", "Last Name", "Address", "City", "State", "Zip", "Owner Address", "Owner City", "Owner State", "Owner Zip"}
    df.drop(columns=[c for c in drop_cols if c in df.columns], inplace=True)

    # Unused columns
    used_cols = set(FINAL_COLUMNS) | drop_cols | {"Email A", "Email B", "Phone A", "Phone B", "Phone C"}
    extras = [col for col in df.columns if col not in used_cols]
    extra_df = df[extras] if extras else pd.DataFrame()

    return cleaned, extra_df, original_col_count, len(FINAL_COLUMNS) + len(extras)

# -------------------- STREAMLIT UI --------------------
uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
if uploaded_file:
    try:
        cleaned_df, extra_df, original, final = process_csv(uploaded_file)
        st.success(f"✔️ Cleaned successfully! Standardized {final} of {original} columns.")
        st.subheader("🧹 Cleaned CSV (Full Preview)")
        st.dataframe(cleaned_df, use_container_width=True)

        if not extra_df.empty:
            st.warning("⚠️ Some columns were not recognized and are shown below in red.")
            st.dataframe(extra_df.style.set_properties(**{'color': 'red'}), use_container_width=True)

        st.download_button(
            "📥 Download Cleaned CSV",
            cleaned_df.to_csv(index=False).encode("utf-8"),
            file_name="cleaned_output.csv",
            mime="text/csv"
        )

    except Exception as e:
        st.error(f"❌ Error: {e}")
