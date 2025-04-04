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
    "Business Start Date", "Phone 1", "Phone 2", "Email 1", "Email 2", "Business Address"
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
    return [col for col in df.columns if df[col].astype(str).str.contains(keyword).sum() > 2]

def build_full_name(df):
    if 'firstname' in df.columns and 'lastname' in df.columns:
        return df['firstname'].astype(str).str.strip() + ' ' + df['lastname'].astype(str).str.strip()
    name_col = next((c for c in df.columns if 'name' in c), None)
    return df[name_col] if name_col else pd.Series([