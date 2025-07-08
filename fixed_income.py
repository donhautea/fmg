# fixed_income.py
# Note: Remove set_page_config from this module to avoid multiple invocation errors

import streamlit as st
import pandas as pd
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

def show_fixed_income_page():
    st.sidebar.title("📂 Fixed Income File Loader")
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

    st.title("📊 Fixed Income Dataset Viewer")
    df = data_storage[selected_dataset]

    if df is not None:
        for date_col in ["Issue_Date", "Issue_Value_Date", "Value_Date", "Maturity_Date"]:
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce").dt.strftime("%Y-%m-%d")
                df[date_col] = pd.to_datetime(df[date_col])

        st.subheader(f"Viewing: {selected_dataset}")
        st.dataframe(
            df.style.format(
                na_rep="-",
                formatter={col: "{:,.2f}" for col in df.select_dtypes(include='number').columns}
            )
        )

        today = pd.Timestamp.today().normalize()
        default_start_date = today
        default_end_date = pd.Timestamp(datetime(today.year, 12, 31))

        st.sidebar.subheader("🔎 Date Range Selection")
        start_date = st.sidebar.date_input("Start Date", value=default_start_date, min_value=date(2000, 1, 1))
        end_date = st.sidebar.date_input("End Date", value=default_end_date, min_value=start_date)
        start_date = pd.to_datetime(start_date.strftime("%Y-%m-%d"))
        end_date = pd.to_datetime(end_date.strftime("%Y-%m-%d"))

        ### Maturities Report
        df_maturity = df[df["Maturity_Date"].between(start_date, end_date)]

        funds = ["SSS", "EC", "FLEXI", "PESO", "MIA", "MPF", "NVPF"]
        total_dict = {}
        conversion_applied = False
        for fund in funds:
            col = f"Face_Amount_{fund}" if selected_dataset.startswith("GS") else f"{fund}_Outstanding"
            if col in df_maturity.columns:
                vals = pd.to_numeric(df_maturity[col], errors="coerce")
                if selected_dataset.endswith("_USD") and exchange_rate:
                    vals *= exchange_rate
                    conversion_applied = True
                total_dict[fund] = vals.sum()
                df_maturity[col] = vals
            else:
                total_dict[fund] = 0

        remark_col = "Reference" if selected_dataset.startswith("GS") else "Issuer"
        df_maturity["Remarks"] = df_maturity[remark_col].astype(str) if remark_col in df_maturity.columns else ""
        df_maturity["Maturity_Date"] = df_maturity["Maturity_Date"].dt.strftime("%Y-%m-%d")
        currency_display = "PhP" if conversion_applied or selected_dataset.endswith("_Php") else "USD"
        display_cols = ["Maturity_Date"] + [c for c in df_maturity.columns if c.startswith("Face_Amount_") or c.endswith("_Outstanding")] + ["Remarks"]

        st.subheader(f"🗓️ Maturities Report: {start_date.date()} to {end_date.date()} ({currency_display})")
        st.dataframe(df_maturity[display_cols].style.format({c: "{:,.2f}" for c in display_cols if c not in ["Maturity_Date","Remarks"]}))
        st.markdown(f"### 🔢 Total Amount by Fund ({currency_display})")
        st.dataframe(pd.DataFrame([total_dict]).style.format("{:,.2f}"))

        ### Coupon Payment Report
        if selected_dataset.startswith("GS_Consolidated") or selected_dataset in ["CBN_Php", "CBN_USD"]:
            schedule_list = []
            for _, row in df.iterrows():
                issue = row.get("Issue_Date") if selected_dataset.startswith("GS_Consolidated") else row.get("Issue_Value_Date")
                freq = pd.to_numeric(row.get("Coupon_Freq") if selected_dataset.startswith("GS_Consolidated") else row.get("Interest_Payment_Schedule"), errors="coerce")
                mat = row.get("Maturity_Date")
                coupon_rate = pd.to_numeric(row.get("Coupon"), errors="coerce")
                reference = row.get(remark_col, "")
                if pd.isna(issue) or pd.isna(mat) or pd.isna(freq) or pd.isna(coupon_rate):
                    continue
                freq = int(freq)
                if freq not in (2, 4):
                    continue
                step_months = 12 // freq
                pay_date = issue
                while pay_date <= mat:
                    if pay_date >= start_date and pay_date <= end_date:
                        for fund in funds:
                            col_amt = f"Face_Amount_{fund}" if selected_dataset.startswith("GS_Consolidated") else f"{fund}_Outstanding"
                            raw_amt = row.get(col_amt)
                            face_amt = pd.to_numeric(raw_amt, errors="coerce")
                            if pd.isna(face_amt):
                                continue
                            if selected_dataset.endswith("_USD") and exchange_rate:
                                face_amt *= exchange_rate
                            payment = face_amt * coupon_rate / freq
                            schedule_list.append({
                                "Coupon_Payment_Date": pay_date.strftime("%Y-%m-%d"),
                                "Fund": fund,
                                "Payment": payment,
                                "Remarks": reference
                            })
                    pay_date += relativedelta(months=step_months)

            if schedule_list:
                sched_df = pd.DataFrame(schedule_list)
                pivot = sched_df.pivot_table(
                    index=["Coupon_Payment_Date", "Remarks"],
                    columns="Fund",
                    values="Payment",
                    aggfunc="sum",
                    fill_value=0
                ).reset_index()
                pivot.columns.name = None
                pivot = pivot.rename(columns={f: f"Coupon_Payment_{f}" for f in funds})
                pivot["Coupon_Payment_Date"] = pd.to_datetime(pivot["Coupon_Payment_Date"])
                fmt = {c: "{:,.2f}" for c in pivot.columns if c.startswith("Coupon_Payment_")}
                fmt["Coupon_Payment_Date"] = "{:%Y-%m-%d}"
                st.subheader(f"💳 Coupon Payments Report: {start_date.date()} to {end_date.date()} ({currency_display})")
                st.dataframe(pivot.style.format(fmt))
            else:
                st.info("No coupon payment data available.")
        else:
            st.info("Coupon schedule and reports are available for GS, CBN_Php, and CBN_USD datasets only.")

        # Filtering by Reference and Fund Columns (Retained)
        references = sorted(df[remark_col].dropna().unique()) if remark_col in df.columns else []
        selected_refs = st.multiselect("Select Reference(s)", options=references, default=references if references else [])

        fund_cols = [c for c in df.columns if "Face_Amount_" in c or c.endswith("_Outstanding")]
        selected_funds = st.multiselect("Select Fund Column(s)", options=fund_cols, default=fund_cols if fund_cols else [])

        if "Remaining_Term_Yrs" in df.columns and not df["Remaining_Term_Yrs"].isna().all():
            tmin, tmax = float(df["Remaining_Term_Yrs"].min()), float(df["Remaining_Term_Yrs"].max())
            sel_term = st.slider("Filter by Remaining Term (Years)", min_value=tmin, max_value=tmax, value=(tmin, tmax))
            df = df[df["Remaining_Term_Yrs"].between(*sel_term)]

        if selected_refs and selected_funds:
            df_filtered = df[df[remark_col].isin(selected_refs)].copy()
            for fund_col in selected_funds:
                df_filtered[fund_col] = pd.to_numeric(df_filtered[fund_col], errors="coerce")
                if selected_dataset.endswith("_USD") and exchange_rate:
                    df_filtered[fund_col] *= exchange_rate

            disp_cols = selected_funds + [remark_col]
            if "Remaining_Term_Yrs" in df_filtered.columns:
                disp_cols.append("Remaining_Term_Yrs")

            totals = df_filtered[selected_funds].sum().to_frame("Total_By_Fund").T
            if selected_dataset.startswith("GS_Consolidated"):
                filtered_funds = [col for col in selected_funds if col != "Face_Amount_Consolidated"]
            else:
                filtered_funds = selected_funds
            grand_total = totals[filtered_funds].sum(axis=1).values[0]
            totals["Total_All_Funds"] = grand_total

            currency_label = "PhP" if exchange_rate or selected_dataset.endswith("_Php") else "USD"

            st.markdown(f"### 💰 Total for Selected References and Funds ({currency_label})")
            st.dataframe(totals.style.format("{:,.2f}"))

            formatters = {col: "{:,.2f}" for col in selected_funds if df_filtered[col].dtype.kind in "fi"}
            st.dataframe(df_filtered[disp_cols].style.format(formatters))

        elif not selected_refs:
            st.info("Please select at least one reference.")
        elif not selected_funds:
            st.info("Please select at least one fund column.")

    else:
        st.warning(f"{selected_dataset} not yet loaded. Please upload a file or check the default path.")
