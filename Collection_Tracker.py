# collection_tracker.py


import streamlit as st
import pandas as pd
from datetime import datetime

def show_collection_tracker_page():
    st.set_page_config(page_title="CMD WISP & MPF Collection Viewer", layout="wide")
    st.title("📊 CMD WISP Tracker & MPF Collection Report")

    wisp_file = st.sidebar.file_uploader("Step 1: Upload CMD WISP Tracker (.xlsx)", type=["xlsx"])
    mpf_file = st.sidebar.file_uploader("Step 2: Upload MPF Collection Report (.csv)", type=["csv"])

    show_wisp_raw = st.sidebar.checkbox("Show Full Parsed Dataset (WISP Tracker)")
    show_mpf_raw = st.sidebar.checkbox("Show Full Parsed Dataset (MPF Collection Report)")
    show_merged = st.sidebar.checkbox("Show CMD vs MPF Comparison")

    combined_df = pd.DataFrame()
    latest_wisp_df = pd.DataFrame()
    mpf_df = pd.DataFrame()
    mpf_summary_df = pd.DataFrame()
    merged_df = pd.DataFrame()

    try:
        if wisp_file:
            xl = pd.ExcelFile(wisp_file)
            all_data = []

            for sheet_name in xl.sheet_names:
                try:
                    sheet_date = pd.to_datetime(sheet_name.strip(), format="%b %Y")
                    if sheet_date < pd.to_datetime("2020-12-01"):
                        continue
                    formatted_month = sheet_date.strftime("%Y-%m")
                except:
                    st.warning(f"⚠️ Skipping sheet: {sheet_name}")
                    continue

                if sheet_date < pd.to_datetime("2021-06-01"):
                    df = pd.read_excel(xl, sheet_name=sheet_name, header=None, skiprows=4, usecols="A:C")
                    df.columns = ["Run Date", "Amount", "Additional"]
                    df["Payment Date"] = None
                else:
                    df = pd.read_excel(xl, sheet_name=sheet_name, header=None, skiprows=4, usecols="A:D")
                    df.columns = ["Payment Date", "Run Date", "Amount", "Additional"]

                df["Payment Date"] = pd.to_datetime(df["Payment Date"], errors="coerce").dt.strftime('%Y-%m-%d')
                df["Run Date"] = pd.to_datetime(df["Run Date"], errors="coerce").dt.strftime('%Y-%m-%d')
                df["Payment Date"].fillna(method='ffill', inplace=True)
                df["Run Date"].fillna(method='ffill', inplace=True)
                df.dropna(how='all', inplace=True)
                df["Applicable Month"] = formatted_month
                df = df[["Payment Date", "Run Date", "Amount", "Applicable Month"]]
                all_data.append(df)

            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                combined_df["Amount"] = pd.to_numeric(combined_df["Amount"], errors="coerce")
                combined_df.dropna(subset=["Amount"], inplace=True)
                combined_df["Applicable Month"] = pd.to_datetime(combined_df["Applicable Month"], format="%Y-%m")
                combined_df.sort_values(by=["Applicable Month", "Payment Date"], inplace=True)

                latest_wisp_df = (
                    combined_df.groupby("Applicable Month")
                    .tail(1)
                    .sort_values(by="Applicable Month")
                    .reset_index(drop=True)
                )

                latest_wisp_df["Amount_CMD"] = latest_wisp_df["Amount"]
                latest_wisp_df["Applicable Month"] = latest_wisp_df["Applicable Month"].dt.strftime("%Y-%m")
                latest_wisp_df = latest_wisp_df[["Applicable Month", "Amount_CMD"]]

                st.subheader("📊 CMD WISP Summary")
                st.dataframe(latest_wisp_df)

                if show_wisp_raw:
                    df_display = combined_df.copy()
                    df_display["Amount"] = df_display["Amount"].map("{:,.2f}".format)
                    df_display["Applicable Month"] = df_display["Applicable Month"].dt.strftime("%Y-%m")
                    st.subheader("📋 Full Parsed Dataset (WISP Tracker)")
                    st.dataframe(df_display)
    except Exception as e:
        st.error(f"❌ Error reading CMD WISP Tracker File: {e}")

    try:
        if mpf_file:
            mpf_df = pd.read_csv(mpf_file, parse_dates=["Posting_Date"])

            if "Total_Amount" not in mpf_df.columns:
                st.error("❌ Column 'Total_Amount' is missing.")
            else:
                mpf_df["Total_Amount"] = (
                    mpf_df["Total_Amount"]
                    .astype(str)
                    .str.replace(",", "")
                    .str.replace("₱", "")
                    .str.extract(r"([0-9.]+)", expand=False)
                    .astype(float)
                )

                mpf_df["Posting_Month"] = mpf_df["Posting_Date"].dt.to_period("M").astype(str)

                mpf_summary_df = (
                    mpf_df.groupby("Posting_Month")["Total_Amount"]
                    .sum()
                    .reset_index()
                    .rename(columns={"Posting_Month": "Applicable Month", "Total_Amount": "Amount_Collection_Report"})
                )

                st.subheader("📊 MPF Collection Summary")
                st.dataframe(mpf_summary_df)

                if show_mpf_raw:
                    st.subheader("📋 Full Parsed Dataset (MPF Collection Report)")
                    st.dataframe(mpf_df)
    except Exception as e:
        st.error(f"❌ Error reading MPF Collection Report: {e}")

    try:
        if not latest_wisp_df.empty and not mpf_summary_df.empty and show_merged:
            merged_df = pd.merge(
                latest_wisp_df,
                mpf_summary_df,
                on="Applicable Month",
                how="outer"
            ).sort_values("Applicable Month")

            merged_df["Amount_CMD"] = pd.to_numeric(merged_df["Amount_CMD"], errors="coerce").fillna(0)
            merged_df["Amount_Collection_Report"] = pd.to_numeric(merged_df["Amount_Collection_Report"], errors="coerce").fillna(0)
            merged_df["Difference"] = merged_df["Amount_Collection_Report"] - merged_df["Amount_CMD"]
            with pd.option_context("mode.use_inf_as_na", True):
                merged_df["Percentage"] = (
                    merged_df["Amount_Collection_Report"] / merged_df["Amount_CMD"]
                ) - 1
            merged_df["Percentage"] = merged_df["Percentage"].fillna(0)

            total_cmd = merged_df["Amount_CMD"].sum()
            total_mpf = merged_df["Amount_Collection_Report"].sum()
            total_diff = total_mpf - total_cmd
            total_pct = (total_mpf / total_cmd - 1) if total_cmd != 0 else 0

            merged_df["Amount_CMD"] = merged_df["Amount_CMD"].map("{:,.2f}".format)
            merged_df["Amount_Collection_Report"] = merged_df["Amount_Collection_Report"].map("{:,.2f}".format)
            merged_df["Difference"] = merged_df["Difference"].map("{:,.2f}".format)
            merged_df["Percentage"] = merged_df["Percentage"].map("{:+.5%}".format)

            total_row = pd.DataFrame({
                "Applicable Month": ["Total"],
                "Amount_CMD": ["{:,.2f}".format(total_cmd)],
                "Amount_Collection_Report": ["{:,.2f}".format(total_mpf)],
                "Difference": ["{:,.2f}".format(total_diff)],
                "Percentage": ["{:+.5%}".format(total_pct)]
            })

            merged_df = pd.concat([merged_df, total_row], ignore_index=True)

            st.subheader("📊 CMD vs MPF Collection Comparison")
            st.dataframe(merged_df)
    except Exception as e:
        st.error(f"❌ Error merging datasets: {e}")
