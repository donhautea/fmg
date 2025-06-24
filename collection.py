import streamlit as st
import pandas as pd
import os
import tempfile
import pdfplumber


def extract_pdf_with_pdfplumber(file_path, plan_type):
    """
    Extract tables from a PDF file using pdfplumber with structure validation.
    
    Args:
        file_path (str): Local path to the uploaded PDF
        plan_type (str): "MPF" or "NVPF" to determine column header structure

    Returns:
        pd.DataFrame or None
    """
    dfs = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                table = page.extract_table()
                if not table:
                    continue

                df = pd.DataFrame(table[1:], columns=table[0])
                if df.empty or df.shape[0] < 3:
                    continue

                # Drop header rows: 3 for MPF, 4 for NVPF to account for extra row
                header_rows = 3 if plan_type == "MPF" else 4
                df = df.iloc[header_rows:].reset_index(drop=True)

                col_count = df.shape[1]

                if plan_type == "MPF":
                    expected_cols = 18
                    if col_count >= expected_cols:
                        df = df.iloc[:, :expected_cols]
                        df.columns = [
                            "Payment_Date", "Posting_Date",
                            "ER_Num", "ER_Amount",
                            "SE_Num", "SE_Amount",
                            "SE_Expanded_Num", "SE_Expanded_Amount",
                            "VM_Num", "VM_Amount",
                            "HH_ER_Num", "HH_ER_Amount",
                            "OFW_Num", "OFW_Amount",
                            "NWS_Num", "NWS_Amount",
                            "Total_Num", "Total_Amount"
                        ]
                    else:
                        raise ValueError(
                            f"Page {page_num}: Expected at least {expected_cols} columns for MPF, but got {col_count}."
                        )

                elif plan_type == "NVPF":
                    expected_cols = 14
                    if col_count >= expected_cols:
                        df = df.iloc[:, :expected_cols]
                        df.columns = [
                            "Payment_Date", "Posting_Date",
                            "EE_Num", "EE_Amount",
                            "SE_Num", "SE_Amount",
                            "VM_Num", "VM_Amount",
                            "OFW_Num", "OFW_Amount",
                            "NWS_Num", "NWS_Amount",
                            "Total_Num", "Total_Amount"
                        ]
                    else:
                        raise ValueError(
                            f"Page {page_num}: Expected at least {expected_cols} columns for NVPF, but got {col_count}."
                        )
                else:
                    raise ValueError(f"Invalid plan_type: {plan_type}")

                # Remove TOTAL rows from Payment_Date
                df = df[df["Payment_Date"]
                        .astype(str)
                        .str.strip()
                        .str.upper() != "TOTAL"]

                dfs.append(df)

        return pd.concat(dfs, ignore_index=True) if dfs else None

    except Exception as e:
        raise RuntimeError(f"Error processing PDF with pdfplumber: {e}")


def show_collection_page():
    st.sidebar.header("Data Source Selection")
    data_source = st.sidebar.radio("Select Data Source:", ("Raw PDF Files", "Processed Dataset"))

    dfs = []
    result_df = None

    if data_source == "Raw PDF Files":
        st.sidebar.subheader("Upload Raw PDF Data")
        plan_type = st.sidebar.radio("Select Plan:", ("MPF", "NVPF"))
        uploaded_files = st.sidebar.file_uploader("Browse PDF files", type=["pdf"], accept_multiple_files=True)

        if uploaded_files:
            temp_dir = tempfile.mkdtemp()
            for uploaded_file in uploaded_files:
                file_path = os.path.join(temp_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                try:
                    extracted_df = extract_pdf_with_pdfplumber(file_path, plan_type)
                    if extracted_df is not None:
                        dfs.append(extracted_df)
                except Exception as e:
                    st.sidebar.error(f"Error reading {uploaded_file.name}: {e}")

            if dfs:
                result_df = pd.concat(dfs, ignore_index=True)

    elif data_source == "Processed Dataset":
        st.sidebar.subheader("Clean Processed Dataset Selection")
        plan_type = st.sidebar.radio("Select Plan for Processed Data:", ("MPF", "NVPF"))
        uploaded_processed = st.sidebar.file_uploader("Browse processed CSV or Excel", type=["csv", "xlsx"], accept_multiple_files=False)

        if uploaded_processed:
            try:
                if uploaded_processed.name.lower().endswith(".csv"):
                    result_df = pd.read_csv(uploaded_processed)
                else:
                    result_df = pd.read_excel(uploaded_processed)
            except Exception as e:
                st.sidebar.error(f"Error reading processed dataset: {e}")
        else:
            default_path = "MPF_Collection.csv" if plan_type == "MPF" else "NVPF_Collection.csv"
            if os.path.exists(default_path):
                try:
                    result_df = pd.read_csv(default_path)
                    st.sidebar.info(f"Loaded default dataset: {os.path.basename(default_path)}")
                except Exception as e:
                    st.sidebar.error(f"Error reading default dataset: {e}")
            else:
                st.sidebar.error("Default dataset not found.")

    if result_df is not None:
        if "Payment_Date" in result_df.columns:
            result_df["Payment_Date"] = pd.to_datetime(result_df["Payment_Date"], errors="coerce")
        if "Posting_Date" in result_df.columns:
            result_df["Posting_Date"] = pd.to_datetime(result_df["Posting_Date"], errors="coerce")
        result_df = result_df[result_df["Payment_Date"].notna()]

        show_data = st.sidebar.radio("Display Data?", ("No", "Yes"))
        if show_data == "Yes":
            st.title("Loaded Dataset")
            display_df = result_df.copy()
            numeric_cols = display_df.select_dtypes(include=["number"]).columns
            for col in numeric_cols:
                display_df[col] = display_df[col].apply(lambda x: f"{x:,.0f}" if pd.notnull(x) else "")
            st.dataframe(display_df)

        non_numeric = ["Payment_Date", "Posting_Date"]
        numeric_cols = [col for col in result_df.columns if col not in non_numeric + ["Month"]]
        if numeric_cols:
            result_df[numeric_cols] = result_df[numeric_cols].replace({",": ""}, regex=True)
            result_df[numeric_cols] = result_df[numeric_cols].apply(pd.to_numeric, errors="coerce")
            if "Total_Num" in result_df.columns:
                result_df["Total_Num"] = result_df["Total_Num"].abs()
            if "Total_Amount" in result_df.columns:
                result_df["Total_Amount"] = result_df["Total_Amount"].abs()

        if "Month" not in result_df.columns and "Payment_Date" in result_df.columns:
            result_df["Month"] = result_df["Payment_Date"].dt.to_period("M").dt.to_timestamp()

        if "Total_Num" in result_df.columns and "Total_Amount" in result_df.columns:
            monthly_totals = result_df.groupby("Month")[["Total_Num", "Total_Amount"]].sum().reset_index()
            monthly_totals = monthly_totals.sort_values("Month").reset_index(drop=True)
            monthly_totals["Month_str"] = monthly_totals["Month"].dt.strftime("%Y-%m")
            for col in ["Total_Num", "Total_Amount"]:
                monthly_totals[col] = monthly_totals[col].round(0).astype("Int64")
            display_monthly = monthly_totals.copy()
            display_monthly["Total_Num"] = display_monthly["Total_Num"].apply(lambda x: f"{x:,}" if pd.notnull(x) else "")
            display_monthly["Total_Amount"] = display_monthly["Total_Amount"].apply(lambda x: f"{x:,}" if pd.notnull(x) else "")
        else:
            monthly_totals = None
            display_monthly = None

        show_monthly = st.sidebar.radio("Display Monthly Totals?", ("No", "Yes"))
        if show_monthly == "Yes" and display_monthly is not None:
            st.title("Monthly Totals")
            st.table(display_monthly[["Month_str", "Total_Num", "Total_Amount"]].rename(columns={"Month_str": "Month"}))

        overall_nums = int(result_df["Total_Num"].sum().round(0)) if "Total_Num" in result_df.columns else None
        overall_amount = int(result_df["Total_Amount"].sum().round(0)) if "Total_Amount" in result_df.columns else None

        amount_cols = [col for col in ["ER_Amount", "EE_Amount", "SE_Amount", "VM_Amount", "OFW_Amount", "NWS_Amount", "Total_Amount"] if col in result_df.columns]
        number_cols = [col for col in ["ER_Num", "EE_Num", "SE_Num", "VM_Num", "OFW_Num", "NWS_Num", "Total_Num"] if col in result_df.columns]
        if (amount_cols + number_cols) and ("Month" in result_df.columns):
            monthly_series = result_df.groupby("Month")[amount_cols + number_cols].sum().reset_index()
            monthly_series["Month_str"] = monthly_series["Month"].dt.strftime("%Y-%m")
        else:
            monthly_series = None

        report_type = st.sidebar.radio("Select Report:", ("Totals", "Comparative Line Chart", "Statistics"))

        if report_type == "Totals":
            st.title("Aggregate Totals")
            if (overall_nums is not None) and (overall_amount is not None):
                totals_df = pd.DataFrame({"Metric": ["Number", "Amount"], "Value": [f"{overall_nums:,}", f"{overall_amount:,}"]})
                st.table(totals_df)
            else:
                st.write("No Total_Num or Total_Amount columns found.")

        elif report_type == "Comparative Line Chart" and (monthly_series is not None):
            st.title("Comparative Line Chart")
            chart_group = st.sidebar.selectbox("Choose Value Type:", ("Amount", "Number"))
            if chart_group == "Amount":
                selected_cols = st.sidebar.multiselect("Select Amount Columns:", amount_cols, default=amount_cols)
                chart_df = monthly_series.set_index("Month_str")[selected_cols]
                st.line_chart(chart_df)
            else:
                selected_cols = st.sidebar.multiselect("Select Number Columns:", number_cols, default=number_cols)
                chart_df = monthly_series.set_index("Month_str")[selected_cols]
                st.line_chart(chart_df)

        elif report_type == "Statistics" and (monthly_totals is not None):
            st.title("Yearly and Monthly Statistics")
            monthly_totals["Year"] = pd.to_datetime(monthly_totals["Month_str"]).dt.year
            yearly_avg = monthly_totals.groupby("Year")[["Total_Num", "Total_Amount"]].mean().reset_index()
            yearly_avg["Avg_Num"] = yearly_avg["Total_Num"].apply(lambda x: f"{x:,.2f}")
            yearly_avg["Avg_Amount"] = yearly_avg["Total_Amount"].apply(lambda x: f"{x:,.2f}")
            yearly_avg_df = yearly_avg[["Year", "Avg_Num", "Avg_Amount"]]

            min_num = monthly_totals["Total_Num"].min()
            max_num = monthly_totals["Total_Num"].max()
            min_amt = monthly_totals["Total_Amount"].min()
            max_amt = monthly_totals["Total_Amount"].max()
            min_max_df = pd.DataFrame({
                "Metric": ["Min_Num", "Max_Num", "Min_Amount", "Max_Amount"],
                "Value": [
                    f"{int(min_num):,}", f"{int(max_num):,}",
                    f"{int(min_amt):,}", f"{int(max_amt):,}"
                ]
            })

            st.subheader("Yearly Averages")
            st.table(yearly_avg_df)
            st.subheader("Monthly Min/Max")
            st.table(min_max_df)

        else:
            st.write("Selected report or data not available.")
    else:
        st.write("Please select a data source and upload a dataset to begin.")
