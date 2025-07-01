# fixed_income.py
# Note: Remove set_page_config from this module to avoid multiple invocation errors

import streamlit as st
import pandas as pd
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta


def show_fixed_income_page():
    st.sidebar.title("📂 Fixed Income File Loader")
    uploaded_file = st.sidebar.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])

    dataset_names = ["GS_Consolidated_Php", "GS_Consolidated_USD", "CBN_Php", "CBN_USD"]
    selected_dataset = st.sidebar.radio("Select Dataset to View", options=dataset_names)

    exchange_rate = None
    currency_label = "PhP"

    # USD datasets may need conversion
    if selected_dataset in ["GS_Consolidated_USD", "CBN_USD"]:
        exchange_rate_input = st.sidebar.text_input("Php to 1 USD Exchange Rate (leave blank to keep USD)", "")
        try:
            exchange_rate = float(exchange_rate_input) if exchange_rate_input else None
            currency_label = "PhP" if exchange_rate else "USD"
        except ValueError:
            st.sidebar.error("Invalid exchange rate. Please enter a valid number.")

    data_storage = {name: None for name in dataset_names}

    # Load data
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
        # Normalize date columns
        for date_col in ["Issue_Date", "Issue_Value_Date", "Value_Date", "Maturity_Date"]:
            if date_col in df.columns:
                df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

        st.subheader(f"Viewing: {selected_dataset}")
        st.dataframe(
            df.style.format(
                na_rep="-", 
                formatter={col: "{:,.2f}" for col in df.select_dtypes(include='number').columns}
            )
        )

        # Reports on Maturities (unchanged)
        st.sidebar.subheader("Reports on Maturities")
        maturity_option = st.sidebar.radio("Maturity Range", ["All Maturities", "For the Month", "For the Year"])
        today = pd.Timestamp.today().normalize()
        if maturity_option == "For the Month":
            df_maturity = df[df["Maturity_Date"].dt.to_period("M") == today.to_period("M")]
        elif maturity_option == "For the Year":
            df_maturity = df[df["Maturity_Date"].dt.year == today.year]
        else:
            df_maturity = df[df["Maturity_Date"] >= today]

        # Totals (unchanged)
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
        st.subheader(f"🗓️ Maturities Report: {maturity_option} ({currency_display})")
        st.dataframe(df_maturity[display_cols].style.format({c: "{:,.2f}" for c in display_cols if c not in ["Maturity_Date","Remarks"]}))
        st.markdown(f"### 🔢 Total Amount by Fund ({currency_display})")
        st.dataframe(pd.DataFrame([total_dict]).style.format("{:,.2f}"))

        # Reports on Coupon Payments
        if selected_dataset.startswith("GS_Consolidated") or selected_dataset == "CBN_Php":
            st.sidebar.subheader("Reports on Coupon Payments")
            coupon_option = st.sidebar.radio("Coupon Payment Range", ["All Payments", "For the Month", "For the Year"], key="coupon_range")
            schedule_list = []
            for _, row in df.iterrows():
                # Determine fields based on dataset
                if selected_dataset.startswith("GS_Consolidated"):
                    issue = row.get("Issue_Date")
                    freq = pd.to_numeric(row.get("Coupon_Freq"), errors="coerce")
                    amt_base = "Face_Amount"
                else:
                    issue = row.get("Issue_Value_Date")
                    freq = pd.to_numeric(row.get("Interest_Payment_Schedule"), errors="coerce")
                    amt_base = "_Outstanding"
                mat = row.get("Maturity_Date")
                coupon_rate = pd.to_numeric(row.get("Coupon"), errors="coerce")
                reference = row.get(remark_col, "")

                # Skip invalid rows
                if pd.isna(issue) or pd.isna(mat) or pd.isna(freq) or pd.isna(coupon_rate):
                    continue
                freq = int(freq)
                if freq not in (2,4):
                    continue

                # Build schedule
                step_months = 12 // freq
                pay_date = issue
                while pay_date <= mat:
                    for fund in funds:
                        if selected_dataset.startswith("GS_Consolidated"):
                            col_amt = f"{amt_base}_{fund}"
                        else:
                            col_amt = f"{fund}{amt_base}"
                        raw_amt = row.get(col_amt)
                        face_amt = pd.to_numeric(raw_amt, errors="coerce")
                        if pd.isna(face_amt):
                            continue
                        if selected_dataset.endswith("_USD") and exchange_rate:
                            face_amt *= exchange_rate
                        payment = face_amt * coupon_rate / freq
                        schedule_list.append({
                            "Coupon_Payment_Date": pay_date,
                            "Fund": fund,
                            "Payment": payment,
                            "Remarks": reference
                        })
                    pay_date += relativedelta(months=step_months)

            # Display coupon schedule
            if schedule_list:
                sched_df = pd.DataFrame(schedule_list)
                pivot = sched_df.pivot_table(
                    index=["Coupon_Payment_Date","Remarks"],
                    columns="Fund",
                    values="Payment",
                    aggfunc="sum",
                    fill_value=0
                ).reset_index()
                pivot.columns.name = None
                pivot = pivot.rename(columns={f: f"Coupon_Payment_{f}" for f in funds})
                pivot["Coupon_Payment_Date"] = pd.to_datetime(pivot["Coupon_Payment_Date"])
                if coupon_option == "For the Month":
                    pivot = pivot[pivot["Coupon_Payment_Date"].dt.to_period("M")==today.to_period("M")]
                elif coupon_option == "For the Year":
                    pivot = pivot[pivot["Coupon_Payment_Date"].dt.year==today.year]
                fmt = {c: "{:,.2f}" for c in pivot.columns if c.startswith("Coupon_Payment_")}
                fmt["Coupon_Payment_Date"] = "{:%Y-%m-%d}"
                st.subheader(f"💳 Coupon Payments Report: {coupon_option} ({currency_display})")
                st.dataframe(pivot.style.format(fmt))
            else:
                st.info("No coupon payment data available.")
        else:
            st.info("Coupon schedule and reports are available for GS and CBN_Php datasets only.")

        # Filtering Reports (unchanged)
        st.subheader("🔍 Filtering Reports by Reference and Fund")
        reference_column = remark_col
        if reference_column in df.columns:
            refs = sorted(df[reference_column].dropna().unique())
            sel_ref = st.selectbox("Select Reference", ["All"]+refs)
            if sel_ref != "All":
                df = df[df[reference_column]==sel_ref]
        fund_cols = [c for c in df.columns if "Face_Amount_" in c or c.endswith("_Outstanding")]
        sel_fund_col = st.selectbox("Select Fund Column", fund_cols)
        if "Remaining_Term_Yrs" in df.columns:
            tmin,tmax = float(df["Remaining_Term_Yrs"].min()), float(df["Remaining_Term_Yrs"].max())
            sel_term = st.slider("Filter by Remaining Term (Years)",min_value=tmin,max_value=tmax,value=(tmin,tmax))
            df = df[df["Remaining_Term_Yrs"].between(*sel_term)]
        if sel_fund_col in df.columns:
            vals = pd.to_numeric(df[sel_fund_col],errors="coerce")
            if selected_dataset.endswith("_USD") and exchange_rate:
                vals*=exchange_rate
                currency_label="PhP"
            else:
                currency_label="USD" if selected_dataset.endswith("_USD") else "PhP"
            total = vals.sum()
            st.markdown(f"### 💰 Total for **{sel_fund_col}**: {total:,.2f} {currency_label}")
            disp=[sel_fund_col,reference_column]
            if "Remaining_Term_Yrs" in df.columns:
                disp.append("Remaining_Term_Yrs")
            fmtrs={c:"{:,.2f}" for c in disp if df[c].dtype.kind in "fi"}
            st.dataframe(df[disp].style.format(fmtrs))
    else:
        st.warning(f"{selected_dataset} not yet loaded. Please upload a file or check the default path.")
