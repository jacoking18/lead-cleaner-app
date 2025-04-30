
import streamlit as st
import pandas as pd
import fitz
import re
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
from datetime import datetime
from collections import defaultdict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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

st.set_page_config(page_title="CAPNOW Bank Statements Verifier", layout="wide")
st.markdown("""
<h1 style='text-align: center;'>CAPNOW Bank Statements Verifier</h1>
<h4 style='text-align: center;'>Creator: Jacobo Simkin</h4>
<p style='text-align: center; font-style: italic;'>OCR-powered fallback now included for scanned or image-based PDFs. Supports all bank formats.</p>
""", unsafe_allow_html=True)

if not check_password():
    st.stop()

def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = "\n".join([page.get_text() for page in doc])
    if not text.strip():
        st.warning(f"🔍 No text found in {file.name}. Using OCR fallback...")
        file.seek(0)
        images = convert_from_bytes(file.read())
        text = "\n".join([pytesseract.image_to_string(img) for img in images])
    return text

def parse_transactions(text):
    pattern = r"(\b\w{3} \d{2})\s+([A-Z0-9/.,&*()\- ]{5,})\s+(\$?\-?[0-9,]+\.\d{2})"
    matches = re.findall(pattern, text)
    data = []
    for date_str, desc, amount in matches:
        try:
            parsed_date = datetime.strptime(date_str + " 2024", "%b %d %Y")
            amt = float(amount.replace('$','').replace(',','').replace('(','-').replace(')',''))
            cleaned_desc = re.sub(r"[^a-zA-Z0-9/ ]", "", desc).strip().lower()
            data.append({
                "Date": parsed_date,
                "Month": parsed_date.strftime("%B %Y"),
                "Raw Description": desc.strip(),
                "Normalized Description": cleaned_desc,
                "Amount": amt,
                "Type": "Credit" if amt > 0 else "Debit"
            })
        except:
            continue
    return pd.DataFrame(data)

def extract_daily_balances(text):
    pattern = r"(\b\w{3} \d{2})\s+([0-9,]+\.\d{2})"
    matches = re.findall(pattern, text)
    daily_balances = defaultdict(list)
    for date_str, balance in matches:
        try:
            dt = datetime.strptime(date_str + " 2024", "%b %d %Y")
            val = float(balance.replace(",", ""))
            daily_balances[dt.strftime("%B %Y")].append(val)
        except:
            continue
    return daily_balances

def detect_negative_days(text):
    pattern = r"(\b\w{3} \d{2})\s+\$\-?([0-9,]+\.\d{2})"
    matches = re.findall(pattern, text)
    return sum(1 for _, balance in matches if float(balance.replace(",", "")) < 0)

uploaded_files = st.file_uploader("Upload Bank Statements (PDF)", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_txns, all_texts, neg_counts, balance_map = pd.DataFrame(), [], [], []
    failed_pdfs = []

    for file in uploaded_files:
        file.seek(0)
        text = extract_text_from_pdf(file)
        all_texts.append(text)

        df = parse_transactions(text)
        if df.empty:
            failed_pdfs.append(file.name)
            continue

        df["Source File"] = file.name
        all_txns = pd.concat([all_txns, df], ignore_index=True)
        neg_counts.append((file.name, detect_negative_days(text)))
        for m, v in extract_daily_balances(text).items():
            balance_map.append({"Month": m, "Source": file.name, "Avg Daily Balance": f"${round(sum(v)/len(v), 2):,.2f}"})

    if failed_pdfs:
        st.warning("⚠️ These PDFs could not be parsed or had no recognizable transactions: " + ", ".join(failed_pdfs))

    if not all_txns.empty:
        selected_month = st.selectbox("📅 Filter by Month", sorted(all_txns["Month"].unique()))
        filtered_df = all_txns[all_txns["Month"] == selected_month]

        st.subheader(f"📄 Transactions for {selected_month}")
        txns_view = filtered_df[["Date", "Raw Description", "Amount", "Type"]].copy()
        txns_view["Amount"] = txns_view["Amount"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(txns_view, use_container_width=True)

        credits = all_txns[all_txns["Type"] == "Credit"].groupby("Month")["Amount"].sum().reset_index(name="Monthly Revenue")
        debits = all_txns[all_txns["Type"] == "Debit"]
        debits_grouped = debits.groupby(["Month", "Normalized Description", "Amount"])

        repeat_summaries = []
        monthly_totals = defaultdict(float)
        for (month, norm_desc, amt), grp in debits_grouped:
            if len(grp) > 1:
                repeat_summaries.append({
                    "Month": month,
                    "Vendor": grp["Raw Description"].iloc[0],
                    "Amount": f"${amt:,.2f}",
                    "Times Charged": len(grp),
                    "Total Charged": f"${grp['Amount'].sum():,.2f}",
                    "Dates": ", ".join(grp["Date"].dt.strftime("%b %d").tolist())
                })
                monthly_totals[month] += grp["Amount"].sum()

        if repeat_summaries:
            st.subheader("🔁 Repeated Vendor Charges")
            st.dataframe(pd.DataFrame(repeat_summaries), use_container_width=True)
        else:
            st.info("No significant repeated charges found.")

        st.subheader("📉 Negative Balance Days per Statement")
        st.dataframe(pd.DataFrame(neg_counts, columns=["Statement", "Negative Balance Days"]), use_container_width=True)

        if len(uploaded_files) > 1:
            st.subheader("📈 Monthly Revenue Trend")
            credits["Trend"] = credits["Monthly Revenue"].pct_change().fillna(0).apply(lambda x: f"{x*100:.2f}%")
            credits["Monthly Revenue"] = credits["Monthly Revenue"].apply(lambda x: f"${x:,.2f}")
            st.dataframe(credits, use_container_width=True)

        st.subheader("💸 % of Revenue Spent on Repeated Payments")
        percent_data = []
        revenue_map = dict(zip(credits["Month"], [float(x.replace("$", "").replace(",", "")) for x in credits["Monthly Revenue"]]))
        for m in monthly_totals:
            rev = revenue_map.get(m, 0)
            spent = monthly_totals[m]
            percent = f"{(spent/rev)*100:.2f}%" if rev else "N/A"
            percent_data.append({"Month": m, "Revenue": f"${rev:,.2f}", "To Repeated": f"${spent:,.2f}", "Percent": percent})
        st.dataframe(pd.DataFrame(percent_data), use_container_width=True)

        st.subheader("🏦 Average Daily Balances per Month")
        st.dataframe(pd.DataFrame(balance_map), use_container_width=True)

        if len(all_texts) > 1:
            st.subheader("🧠 Similarity Score Between PDFs")
            tfidf = TfidfVectorizer().fit_transform(all_texts)
            sim = cosine_similarity(tfidf)
            for i in range(1, len(all_texts)):
                st.markdown(f"Confidence between PDF 1 and PDF {i+1}: **{sim[0][i]*100:.2f}%**")
    else:
        st.warning("⚠️ No transactions extracted from any PDFs, even after OCR fallback.")
