# equity_trans.py

import streamlit as st
import pandas as pd
import os
from datetime import datetime
import pytz

def extract_fund_name(file_name):
    base = os.path.basename(file_name)
    parts = base.replace(".xlsx", "").replace(".xls", "").split()
    fund = parts[-1]
    date_part = " ".join(parts[:-1])
    return date_part.strip(), fund.strip()

def process_file(file):
    try:
        xl = pd.ExcelFile(file)
        if "StockMonitoring" not in xl.sheet_names:
            st.warning(f"→ Skipping {file.name}: no ‘StockMonitoring’ sheet.")
            return pd.DataFrame()

        df = xl.parse("StockMonitoring", header=None)
        start = 4  # row 5 → index 4
        idx = df.loc[start:, 6].dropna().index
        if idx.empty:
            st.warning(f"→ Skipping {file.name}: no data in column G from row 5 onward.")
            return pd.DataFrame()
        end = idx[-1]

        dates = pd.to_datetime(df.loc[start:end, 6], errors="coerce").dt.date
        stocks = df.loc[start:end, 1]
        brokers = df.loc[start:end, 5]
        j = df.loc[start:end, 9].fillna(0)
        l = df.loc[start:end, 11].fillna(0)
        k = df.loc[start:end, 10].fillna(0)

        volume = j + l
        price = k
        buy_sell = j.apply(lambda x: "B" if x > 0 else "S")
        classification = "FVTPL"
        _, fund = extract_fund_name(file.name)

        out = pd.DataFrame({
            "Date": dates,
            "Classification": classification,
            "Stock": stocks,
            "Buy_Sell": buy_sell,
            "Broker": brokers,
            "Volume": volume,
            "Price": price,
            "Value": volume * price,
            "Fund": fund,
        }).dropna(subset=["Date", "Stock"])

        return out

    except Exception as e:
        st.error(f"Error reading {file.name}: {e}")
        return pd.DataFrame()

def show_equity_trans_page():
    st.header("📊 Equity Transaction Update")

    uploaded = st.file_uploader(
        "Upload one or more .xls / .xlsx files", 
        type=["xls", "xlsx"], 
        accept_multiple_files=True, 
        key="equity_trans"
    )

    if not uploaded:
        st.info("Please upload at least one Excel file to proceed.")
        return

    combined = pd.DataFrame()
    for f in uploaded:
        df = process_file(f)
        if not df.empty:
            combined = pd.concat([combined, df], ignore_index=True)

    if combined.empty:
        st.warning("No data could be extracted from the files you uploaded.")
        return

    combined = combined.sort_values(["Fund", "Broker"])
    st.dataframe(combined, height=600)

    # prepare download
    tz = pytz.timezone("Asia/Manila")
    today_str = datetime.now(tz).strftime("%Y-%m-%d")
    csv = combined.to_csv(index=False).encode("utf-8")

    st.download_button(
        "📥 Download combined data as CSV",
        data=csv,
        file_name=f"{today_str}_equity.csv",
        mime="text/csv"
    )
