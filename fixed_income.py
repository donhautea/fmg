# fixed_income.py
# Note: Remove set_page_config from this module to avoid multiple invocation errors

import streamlit as st
import pandas as pd
import os
from datetime import datetime

def show_fixed_income_page():
    st.sidebar.title("\U0001F4C2 Fixed Income File Loader")
    uploaded_file = st.sidebar.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])

    dataset_names = ["GS_Consolidated_Php", "GS_Consolidated_USD", "CBN_Php", "CBN_USD"]
    selected_dataset = st.sidebar.radio("Select Dataset to View", options=dataset_names)

    exchange_rate = None
    currency_label = "PhP"

    if selected_dataset in ["GS_Consolidated_USD", "CBN_USD"]:
        exchange_rate_input = st.sidebar.text_input("Php to 1 USD Exchange Rate (leave blank to keep USD)", "")
        try:
            exchange_rate = float(exchange_rate_input) if exchange_rate_input else None
            currency_label = "PhP" if exchange_rate else "USD"
        except ValueError:
            st.sidebar.error("Invalid exchange rate. Please enter a valid number.")

    data_storage = {name: None for name in dataset_names}

    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
                for name in dataset_names:
                    if name.lower() in uploaded_file.name.lower():
                        data_storage[name] = df
                        break
            elif uploaded_file.name.endswith(".xlsx"):
                excel = pd.ExcelFile(uploaded_file)
                for name in dataset_names:
                    if name in excel.sheet_names:
                        data_storage[name] = excel.parse(sheet_name=name)
        except Exception as e:
            st.error(f"Error reading uploaded file: {e}")
    else:
        default_path = r"FIID_Data.xlsx"
        if os.path.exists(default_path):
            try:
                excel = pd.ExcelFile(default_path)
                for name in dataset_names:
                    if name in excel.sheet_names:
                        data_storage[name] = excel.parse(sheet_name=name)
            except Exception as e:
                st.error(f"Error reading default file: {e}")
        else:
            st.warning("No file uploaded and default file not found.")

    st.title("\U0001F4CA Fixed Income Dataset Viewer")

    df = data_storage[selected_dataset]
    if df is not None:
        for date_col in ["Issue_Date", "Value_Date", "Maturity_Date"]:
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.strftime("%Y-%m-%d")

        st.subheader(f"Viewing: {selected_dataset}")
        st.dataframe(df.style.format(na_rep="-", formatter={col: "{:,.2f}" for col in df.select_dtypes(include='number').columns}))

        # Reports on Maturities
        st.sidebar.subheader("Reports on Maturities")
        maturity_option = st.sidebar.radio("Maturity Range", ["All Maturities", "For the Month", "For the Year"])
        df["Maturity_Date"] = pd.to_datetime(df["Maturity_Date"], errors='coerce')
        today = pd.Timestamp.today().normalize()
        if maturity_option == "For the Month":
            df_maturity = df[df["Maturity_Date"].dt.to_period("M") == today.to_period("M")]
        elif maturity_option == "For the Year":
            df_maturity = df[df["Maturity_Date"].dt.year == today.year]
        else:
            df_maturity = df[df["Maturity_Date"] >= today]
        df_maturity["Maturity_Date"] = df_maturity["Maturity_Date"].dt.strftime("%Y-%m-%d")

        funds = ["SSS", "EC", "FLEXI", "PESO", "MIA", "MPF", "NVPF"] if selected_dataset.startswith("GS") else ["SSS", "EC", "FLEXI", "MIA", "MPF", "NVPF"]
        total_dict = {}
        conversion_applied = False

        for fund in funds:
            col = f"Face_Amount_{fund}" if selected_dataset.startswith("GS") else f"{fund}_Outstanding"
            if col in df_maturity.columns:
                values = pd.to_numeric(df_maturity[col], errors="coerce")
                if selected_dataset.endswith("_USD") and exchange_rate:
                    values *= exchange_rate
                    conversion_applied = True
                total_dict[fund] = values.sum()
                df_maturity[col] = values
            else:
                total_dict[fund] = 0

        remark_col = "Reference" if selected_dataset.startswith("GS") else "Issuer"
        df_maturity["Remarks"] = df_maturity[remark_col].astype(str) if remark_col in df_maturity.columns else ""
        display_cols = ["Maturity_Date"] + [col for col in df_maturity.columns if col.startswith("Face_Amount_") or col.endswith("_Outstanding")] + ["Remarks"]
        currency_display = "PhP" if conversion_applied or selected_dataset.endswith("_Php") else "USD"

        st.subheader(f"\U0001F4C5 Maturities Report: {maturity_option} ({currency_display})")
        st.dataframe(df_maturity[display_cols].style.format({col: "{:,.2f}" for col in display_cols if col != "Maturity_Date" and col != "Remarks"}))

        st.markdown(f"### \U0001F522 Total Amount by Fund ({currency_display})")
        st.dataframe(pd.DataFrame([total_dict]).style.format("{:,.2f}"))

        # Filtering Reports by Reference and Fund
        st.subheader("\U0001F50D Filtering Reports by Reference and Fund")

        reference_column = "Reference" if selected_dataset.startswith("GS") else "Issuer"
        if reference_column in df.columns:
            references = sorted(df[reference_column].dropna().unique())
            selected_reference = st.selectbox("Select Reference", ["All"] + references)
            if selected_reference != "All":
                df = df[df[reference_column] == selected_reference]

        fund_cols = [col for col in df.columns if "Face_Amount_" in col or "_Outstanding" in col]
        selected_fund_col = st.selectbox("Select Fund Column", fund_cols)

        if "Remaining_Term_Yrs" in df.columns:
            term_min, term_max = float(df["Remaining_Term_Yrs"].min()), float(df["Remaining_Term_Yrs"].max())
            selected_term = st.slider("Filter by Remaining Term (Years)", min_value=term_min, max_value=term_max, value=(term_min, term_max))
            df = df[df["Remaining_Term_Yrs"].between(*selected_term)]

        if selected_fund_col in df.columns:
            values = pd.to_numeric(df[selected_fund_col], errors="coerce")
            if selected_dataset.endswith("_USD") and exchange_rate:
                values *= exchange_rate
                currency_label = "PhP"
            else:
                currency_label = "USD" if selected_dataset.endswith("_USD") else "PhP"

            total = values.sum()
            st.markdown(f"### \U0001F4B0 Total for **{selected_fund_col}**: {total:,.2f} {currency_label}")

            display_cols = [selected_fund_col, reference_column, "Maturity_Date"]
            if "Remaining_Term_Yrs" in df.columns:
                display_cols.append("Remaining_Term_Yrs")
            formatters = {col: "{:,.2f}" for col in display_cols if df[col].dtype.kind in "fi"}
            st.dataframe(df[display_cols].style.format(formatters))
    else:
        st.warning(f"{selected_dataset} not yet loaded. Please upload a file or check the default path.")
