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

# -------------------- FILE UPLOAD --------------------
uploaded_file = st.file_uploader("Upload a CSV or Excel file", type=["csv", "xlsx"])

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
            df = pd.read_excel(uploaded_file, engine="openpyxl")
        else:
            st.error("Unsupported file format.")
            st.stop()
    except Exception as e:
        st.error(f"Error while reading the file: {e}")
        st.stop()

    st.success("File uploaded successfully!")
    st.dataframe(df)
else:
    st.info("Awaiting file upload...")
