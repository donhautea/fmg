# fi_analysis.py
import streamlit as st
import pandas as pd

# Calculate Weighted Average Interest Rate (WAIR)
def calculate_wair(df: pd.DataFrame, coupon_col: str, face_amount_cols: list) -> pd.DataFrame:
    wair_results = {}
    for col in face_amount_cols:
        total_face = df[col].sum()
        fund_name = col.replace("Face_Amount_", "")
        if total_face > 0:
            wair = (df[col] / total_face * df[coupon_col]).sum() * 100
            wair_results[fund_name] = round(wair, 3)
        else:
            wair_results[fund_name] = None
    return pd.DataFrame(
        list(wair_results.items()), columns=["Fund", "WAIR (%)"]
    )

# Calculate Weighted Average Tenor (WAT)
def calculate_wat(df: pd.DataFrame, term_col: str, face_amount_cols: list) -> pd.DataFrame:
    wat_results = {}
    for col in face_amount_cols:
        total_face = df[col].sum()
        fund_name = col.replace("Face_Amount_", "")
        if total_face > 0:
            wat = (df[col] / total_face * df[term_col]).sum()
            wat_results[fund_name] = round(wat, 3)
        else:
            wat_results[fund_name] = None
    return pd.DataFrame(
        list(wat_results.items()), columns=["Fund", "WAT (Years)"]
    )

# Calculate Weighted Average Yield to Maturity (WAYTM)
def calculate_waytm(df: pd.DataFrame, ytm_col: str, face_amount_cols: list) -> pd.DataFrame:
    waytm_results = {}
    for col in face_amount_cols:
        total_face = df[col].sum()
        fund_name = col.replace("Face_Amount_", "")
        if total_face > 0:
            waytm = (df[col] / total_face * df[ytm_col]).sum() * 100
            waytm_results[fund_name] = round(waytm, 3)
        else:
            waytm_results[fund_name] = None
    return pd.DataFrame(
        list(waytm_results.items()), columns=["Fund", "WAYTM (%)"]
    )

# Page function to show WAIR, WAT & WAYTM analysis
def show_fi_analysis():
    st.subheader("Fixed Income Statistical Data: WAIR, WAT & WAYTM Calculator")

    # File uploader and display option
    st.sidebar.header("Upload Data Files for Analysis")
    excel_file = st.sidebar.file_uploader(
        "Excel file (sheet 'GS_Consolidated_Php')", type=["xlsx", "xls"]
    )
    show_data = st.sidebar.checkbox("Show Data Preview")

    # Load data
    df = None
    if excel_file:
        try:
            df = pd.read_excel(excel_file, sheet_name="GS_Consolidated_Php")
        except Exception as e:
            st.sidebar.error(f"Error reading Excel: {e}")

    if df is not None:
        if show_data:
            st.write("### Data Preview")
            st.dataframe(df)

        coupon_col = "Coupon"
        term_col = "Remaining_Term_Yrs"
        ytm_col = "YTM"
        face_amount_cols = [
            "Face_Amount_Consolidated", "Face_Amount_SSS", "Face_Amount_EC", "Face_Amount_FLEXI",
            "Face_Amount_PESO", "Face_Amount_MIA", "Face_Amount_MPF", "Face_Amount_NVPF"
        ]

        # Compute metrics
        wair_df = calculate_wair(df, coupon_col, face_amount_cols)
        wat_df = calculate_wat(df, term_col, face_amount_cols)
        waytm_df = calculate_waytm(df, ytm_col, face_amount_cols)

        # Display in three columns
        col1, col2, col3 = st.columns(3)
        with col1:
            st.write("#### WAIR (%) by Fund")
            st.table(wair_df)
        with col2:
            st.write("#### WAT (Years) by Fund")
            st.table(wat_df)
        with col3:
            st.write("#### WAYTM (%) by Fund")
            st.table(waytm_df)
    else:
        st.info("Upload an Excel file to compute WAIR, WAT, and WAYTM.")