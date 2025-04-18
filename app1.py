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
- Logs mappings to improve smart predictions in the future.
- Suggests column mappings based on historical user behavior with confidence visualization.
- Download the cleaned result once mapping is done.
""")

FINAL_COLUMNS = [
    "Lead Date", "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Email 1", "Email 2",
    "Business Address", "Home Address", "Monthly Revenue"
]

if 'mappings' not in st.session_state:
    st.session_state.mappings = {}

if st.button("🔄 Clear Mappings"):
    st.session_state.mappings = {}
    st.rerun()

# 📦 Store training log
def log_user_mapping(filename, field, selected_cols):
    if not selected_cols:
        return
    sample_values = df[selected_cols].astype(str).head(5).values.tolist()
    with open("mappings_log.csv", "a") as log:
        for col in selected_cols:
            log.write(f"{filename},{col},\"{sample_values}\",{field}\n")

# 🧠 Suggest mappings from past logs with confidence
def get_suggested_columns_with_confidence(field):
    if not os.path.exists("mappings_log.csv"):
        return []
    try:
        log_df = pd.read_csv("mappings_log.csv", names=["filename", "column", "sample", "hub_field"])
        field_logs = log_df[log_df["hub_field"] == field]
        total = len(field_logs)
        counts = field_logs["column"].value_counts()
        suggestions = [(col, int((count / total) * 100)) for col, count in counts.items()]
        return suggestions
    except:
        return []

uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"], on_change=lambda: st.session_state.update({'mappings': {}}))

df = None
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            content = uploaded_file.read().decode(errors='ignore')
            lines = content.strip().split('\n')

            header_candidates = [line.split(',') for line in lines[:5] if len(line.split(',')) > 3]
            header_row_index = 0

            for i, row in enumerate(header_candidates):
                if any(cell.strip().lower() in ['phone1', 'firstname', 'lastname', 'email'] for cell in row):
                    header_row_index = i
                    break

            from io import StringIO
            df = pd.read_csv(StringIO(content), skiprows=header_row_index)

        elif uploaded_file.name.endswith('.xlsx'):
            try:
                import openpyxl
            except ImportError:
                st.error("Missing dependency 'openpyxl'. Please install it via pip: pip install openpyxl")
                st.stop()
            xl = pd.ExcelFile(uploaded_file)
            first_sheet = xl.sheet_names[0]
            df = xl.parse(first_sheet)
            if 'Unnamed' in str(df.columns[0]):
                df = xl.parse(first_sheet, skiprows=1)
        else:
            st.error("Unsupported file format.")
            st.stop()

        if df is None or df.empty or len(df.columns) <= 1:
            st.error("The file appears to be empty or not properly formatted. Please make sure it has column headers and data rows.")
            st.stop()

    except Exception as e:
        st.error(f"Error while reading the file: {e}")
        st.stop()

    st.success("File uploaded successfully!")
    st.subheader("Original Uploaded CSV")
    st.dataframe(df)

    st.markdown("### 👉 Map Your Columns to HUB Fields")
    all_headers = list(df.columns)

    used_columns = set()
    cols_left, cols_right = st.columns(2)
    for i, field in enumerate(FINAL_COLUMNS):
        col = cols_left if i % 2 == 0 else cols_right
        with col:
            st.markdown(f"<div style='font-weight:bold; font-size:16px; margin-bottom:4px'>{field}</div>", unsafe_allow_html=True)
            current_selection = st.session_state.mappings.get(field, [])
            available_options = [h for h in all_headers if h not in used_columns or h in current_selection]
            selected = st.multiselect("", options=available_options, default=current_selection, key=field)
            st.session_state.mappings[field] = selected
            used_columns.update(selected)

    st.markdown("---")

    if st.button("Generate Cleaned CSV"):
        cleaned_df = pd.DataFrame()
        for hub_col in FINAL_COLUMNS:
            selected_cols = st.session_state.mappings.get(hub_col, [])
            if selected_cols:
                combined = df[selected_cols].astype(str).apply(lambda row: ' '.join(row.dropna().astype(str)).strip(), axis=1)
                if "phone" in hub_col.lower():
                    combined = combined.str.replace(r'\.0$', '', regex=True)
                cleaned_df[hub_col] = combined.replace("nan", "", regex=False).replace("None", "", regex=False)
                log_user_mapping(uploaded_file.name, hub_col, selected_cols)
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
