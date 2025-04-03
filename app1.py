import streamlit as st
import pandas as pd
import re

# -------------------- PASSWORD PROTECTION --------------------
def check_password():
    def password_entered():
        if st.session_state["password"] == "capnow$":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Enter password to access the app:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Enter password to access the app:", type="password", on_change=password_entered, key="password")
        st.error("Incorrect password.")
        return False
    else:
        return True

if not check_password():
    st.stop()

# -------------------------------------------------------------

st.set_page_config(page_title="CAPNOW DATA CLEANER APP")

st.image("logo.png", width=160)
st.title("CAPNOW DATA CLEANER APP")
st.markdown("**Creator: Jaco Simkin – Director of Data Analysis**")

st.markdown("""
This app automatically cleans raw lead files (CSV format) received from multiple providers.

It standardizes messy or inconsistent data into a unified format required by the CAPNOW HUB system.

What it does:
- Normalizes messy columns like `biz name`, `googlephone`, `revenue`, etc.
- Outputs a clean DataFrame with the following columns:

Business Name, Full Name, SSN, DOB, Industry, EIN  
Business Start Date, Phone 1, Phone 2, Email 1, Email 2  
Business Address, Home Address, Monthly Revenue

Second Table (Red): The second DataFrame (highlighted in red) shows all columns from the uploaded file that were not recognized or cleaned.
You can use this to see what additional data was present but not part of the HUB format.
""")

# HUB columns
FINAL_COLUMNS = [
    "Business Name", "Full Name", "SSN", "DOB", "Industry", "EIN",
    "Business Start Date", "Phone 1", "Phone 2", "Email 1", "Email 2",
    "Business Address", "Home Address", "Monthly Revenue"
]

# Flexible mappings
COLUMN_MAPPING = {
    "ssn": "SSN", "social": "SSN", "social security": "SSN", "socialsecurity": "SSN",
    "dob": "DOB", "birth date": "DOB", "date of birth": "DOB",
    "ein": "EIN", "employer id": "EIN",
    "business start date": "Business Start Date", "start date": "Business Start Date", "bsd": "Business Start Date", "yearsinbusiness": "Business Start Date",
    "monthly revenue": "Monthly Revenue", "businessmonthlyrevenue": "Monthly Revenue", "rev": "Monthly Revenue",
    "revenue": "Monthly Revenue", "Revenue": "Monthly Revenue", "turnover": "Monthly Revenue", "Turnover": "Monthly Revenue",
    "biz name": "Business Name", "businessname": "Business Name", "company": "Business Name",
    "ownerfullname": "Full Name", "firstname": "First Name", "first name": "First Name",
    "lastname": "Last Name", "last name": "Last Name",
    "phone1": "Phone A", "cellphone": "Phone B", "businessphone": "Phone C", "altphone": "Phone D",
    "googlephone": "Phone E", "google phone": "Phone E", "GOOGLEPHONE": "Phone E", "number1": "Phone A",
    "email": "Email A", "email1": "Email A", "email 1": "Email A",
    "email2": "Email B", "google email": "Email B", "googleemail": "Email B",
    "GOOGLEEMAIL": "Email B", "Google Email": "Email B", "Google email": "Email B",
    "address": "Address", "address1": "Address", "city": "City", "state": "State", "zip": "Zip",
    "owner address": "Owner Address", "owner city": "Owner City", "owner state": "
