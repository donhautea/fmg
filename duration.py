# duration.py
import streamlit as st
import pandas as pd
import numpy as np
from dateutil import relativedelta


def bond_duration(settlement: pd.Timestamp, maturity: pd.Timestamp, coupon: float, yld: float, freq: int) -> float:
    """
    Calculate Macaulay duration for a single bond with face=1.
    """
    diff = relativedelta.relativedelta(maturity, settlement)
    years = diff.years + diff.months/12 + diff.days/365
    periods = int(np.round(years * freq))
    # Cash flows per period
    cf = np.full(periods, coupon / freq)
    cf[-1] += 1
    times = np.arange(1, periods + 1)
    discount = 1 / (1 + yld/freq) ** times
    weighted = times * cf * discount
    pv = cf * discount
    return weighted.sum() / pv.sum()


def show_duration_page():
    st.subheader("Fixed Income Duration Data")

    # Sidebar inputs
    st.sidebar.header("Upload and Filter Data")
    excel_file = st.sidebar.file_uploader(
        "Excel file (sheet 'GS_Consolidated_Php')", type=["xlsx", "xls"]
    )
    settlement_date = st.sidebar.date_input(
        "Settlement Date", value=pd.to_datetime("2025-05-31")
    )
    fund = st.sidebar.selectbox(
        "Select Fund", [
            "Consolidated", "SSS", "EC", "FLEXI", "PESO", "MIA", "MPF", "NVPF"
        ]
    )

    if excel_file:
        try:
            df = pd.read_excel(excel_file, sheet_name="GS_Consolidated_Php")
        except Exception as e:
            st.sidebar.error(f"Error reading Excel: {e}")
            return

        # Filter by fund: include only rows with positive face amount
        face_col = f"Face_Amount_{fund}"
        data = df[df[face_col] > 0].copy()

        # Calculate Duration per bond
        data["Duration"] = data.apply(
            lambda r: bond_duration(
                settlement_date,
                pd.to_datetime(r["Maturity_Date"]),
                r["Coupon"],
                r["YTM"],
                int(r["Coupon_Freq"])
            ), axis=1
        )

        # Weighted Average Duration per row
        total_face = data[face_col].sum()
        data["Weighted_Ave_Duration"] = data[face_col] / total_face * data["Duration"]

                # Display selected columns
        settlement_col = f"Settlement_Amount_{fund}"
        display_cols = ["ISIN", "Maturity_Date", "YTM", "Coupon", "Coupon_Freq", settlement_col, face_col, "Duration", "Weighted_Ave_Duration"]
        st.write(f"### Duration Details for {fund} Fund")
        st.dataframe(data[display_cols])

        # Overall weighted average duration
        avg_dur = data["Weighted_Ave_Duration"].sum()
        st.write(f"**Weighted Average Duration ({fund}):** {round(avg_dur, 3)} years")
    else:
        st.info("📄 Please upload an Excel file to compute durations.")
