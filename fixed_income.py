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
        # Standardize date formats
        for date_col in ["Issue_Date", "Value_Date", "Maturity_Date"]:
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.strftime("%Y-%m-%d")

        st.subheader(f"Viewing: {selected_dataset}")
        st.dataframe(df.style.format(na_rep="-", formatter={col: "{:,.2f}" for col in df.select_dtypes(include='number').columns}))

        if selected_dataset in ["GS_Consolidated_Php", "GS_Consolidated_USD"]:
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

            funds = ["SSS", "EC", "FLEXI", "PESO", "MIA", "MPF", "NVPF"]
            total_dict = {}
            conversion_applied = False

            for fund in funds:
                col = f"Face_Amount_{fund}"
                if col in df_maturity.columns:
                    values = pd.to_numeric(df_maturity[col], errors="coerce")
                    if selected_dataset == "GS_Consolidated_USD" and exchange_rate:
                        values *= exchange_rate
                        conversion_applied = True
                    total_dict[fund] = values.sum()
                    df_maturity[col] = values
                else:
                    total_dict[fund] = 0

            df_maturity["Remarks"] = df_maturity["Issuer"].astype(str)
            display_cols = ["Maturity_Date"] + [f"Face_Amount_{f}" for f in funds if f"Face_Amount_{f}" in df.columns] + ["Remarks"]
            currency_display = "PhP" if conversion_applied or selected_dataset == "GS_Consolidated_Php" else "USD"

            st.subheader(f"\U0001F4C5 Maturities Report: {maturity_option} ({currency_display})")
            st.dataframe(df_maturity[display_cols].style.format({col: "{:,.2f}" for col in display_cols if "Face_Amount_" in col}))

            st.markdown(f"### \U0001F522 Total Face Amount by Fund ({currency_display})")
            st.dataframe(pd.DataFrame([total_dict]).style.format("{:,.2f}"))

        if selected_dataset in ["CBN_Php", "CBN_USD"]:
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

            funds = ["SSS", "EC", "FLEXI", "MIA", "MPF", "NVPF"]
            total_dict = {}
            conversion_applied = False

            for fund in funds:
                col = f"{fund}_Outstanding"
                if col in df_maturity.columns:
                    values = pd.to_numeric(df_maturity[col], errors="coerce")
                    if selected_dataset == "CBN_USD" and exchange_rate:
                        values *= exchange_rate
                        conversion_applied = True
                    total_dict[fund] = values.sum()
                    df_maturity[col] = values
                else:
                    total_dict[fund] = 0

            df_maturity["Remarks"] = df_maturity["Issuer"].astype(str)
            display_cols = ["Maturity_Date"] + [f"{f}_Outstanding" for f in funds if f"{f}_Outstanding" in df.columns] + ["Remarks"]
            currency_display = "PhP" if conversion_applied or selected_dataset == "CBN_Php" else "USD"

            st.subheader(f"\U0001F4C5 Maturities Report: {maturity_option} ({currency_display})")
            st.dataframe(df_maturity[display_cols].style.format({col: "{:,.2f}" for col in display_cols if "_Outstanding" in col}))

            st.markdown(f"### \U0001F522 Total Outstanding Amount by Fund ({currency_display})")
            st.dataframe(pd.DataFrame([total_dict]).style.format("{:,.2f}"))
    else:
        st.warning(f"{selected_dataset} not yet loaded. Please upload a file or check the default path.")