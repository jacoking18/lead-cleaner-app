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

It lets you visually assign uploaded columns into HUB fields — and allows combining multiple source columns per HUB column.

- Assign multiple source columns to each HUB field to merge them (e.g. address parts).
- Keeps all HUB columns even if left unmapped.
- Download the cleaned result once mapping is done.
""")

FINAL_COLUMNS = [
    "Lead Date", "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Phone 3", "Email 1", "Email 2",
    "Business Address", "Home Address", "Monthly Revenue"
]

if 'mappings' not in st.session_state:
    st.session_state.mappings = {}

uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"], on_change=lambda: st.session_state.update({'mappings': {}}))

if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            try:
                df = pd.read_csv(uploaded_file, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(uploaded_file, encoding='ISO-8859-1')
                except UnicodeDecodeError:
                    df = pd.read_csv(uploaded_file, encoding='cp1252')
        elif uploaded_file.name.endswith('.xlsx'):
            try:
                import openpyxl
            except ImportError:
                st.error("Missing dependency 'openpyxl'. Please install it via pip: pip install openpyxl")
                st.stop()
            df = pd.read_excel(uploaded_file, engine="openpyxl")
        else:
            st.error("Unsupported file format.")
            st.stop()
    except Exception as e:
        st.error(f"Error while reading the file: {e}")
        st.stop()

    st.success("File uploaded successfully!")
    st.subheader("Original Uploaded CSV")
    st.dataframe(df)

    st.markdown("### 👉 Map Your Columns to HUB Fields")
    all_headers = list(df.columns)

    cols_left, cols_right = st.columns(2)
    for i, field in enumerate(FINAL_COLUMNS):
        col = cols_left if i % 2 == 0 else cols_right
        with col:
            st.session_state.mappings[field] = st.multiselect(
                f"Select columns to combine for: {field}",
                all_headers,
                key=field
            )

    st.markdown("---")

    if st.button("Generate Cleaned CSV"):
        cleaned_df = pd.DataFrame()
        for hub_col in FINAL_COLUMNS:
            selected_cols = st.session_state.mappings.get(hub_col, [])
            if selected_cols:
                combined = df[selected_cols].astype(str).apply(lambda row: ' '.join(row.dropna().astype(str)).strip(), axis=1)
                cleaned_df[hub_col] = combined.replace("nan", "", regex=False).replace("None", "", regex=False)
            else:
                cleaned_df[hub_col] = ""

        for date_col in ["Lead Date", "DOB", "Business Start Date"]:
            if date_col in cleaned_df.columns:
                cleaned_df[date_col] = pd.to_datetime(cleaned_df[date_col], errors='coerce').dt.strftime('%Y-%m-%d')

        st.subheader("Cleaned CSV (Full Preview)")
        st.dataframe(cleaned_df)

        cleaned_filename = uploaded_file.name.rsplit('.', 1)[0] + '_cleaned.csv'
        cleaned_df.to_csv(cleaned_filename, index=False)
        with open(cleaned_filename, 'rb') as f:
            st.download_button("Download Cleaned CSV", f, file_name=cleaned_filename)
else:
    st.info("Awaiting file upload...")
