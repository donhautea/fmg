import streamlit as st
import pandas as pd
import datetime, calendar

# --- Excel-like Duration and Convexity calculation utilities ---

def add_months(dt, months):
    month = dt.month - 1 + months
    year  = dt.year + month // 12
    month = month % 12 + 1
    day   = min(dt.day, calendar.monthrange(year, month)[1])
    return datetime.date(year, month, day)


def previous_coupon_date(settlement, maturity, freq):
    months = 12 // freq
    current = maturity
    while current > settlement:
        current = add_months(current, -months)
    return current


def next_coupon_date(settlement, maturity, freq):
    prev = previous_coupon_date(settlement, maturity, freq)
    return add_months(prev, 12 // freq)


def duration(settlement, maturity, coupon, yld, freq, basis='ACT/360', face=1):
    prev_coup = previous_coupon_date(settlement, maturity, freq)
    next_coup = next_coupon_date(settlement, maturity, freq)
    period_days = (next_coup - prev_coup).days
    accrual_days = (settlement - prev_coup).days
    t1 = (period_days - accrual_days) / period_days / freq
    payment_dates = [next_coup]
    current = next_coup
    while True:
        current = add_months(current, 12 // freq)
        if current > maturity:
            break
        payment_dates.append(current)
    coupon_amt = coupon * face / freq
    pv_times, pv_vals = [], []
    for i, pay in enumerate(payment_dates):
        t = t1 + i * (1/freq)
        cf = coupon_amt + (face if pay == maturity else 0)
        dfactor = (1 + yld / freq) ** (-(t * freq))
        pv = cf * dfactor
        pv_vals.append(pv)
        pv_times.append(t * pv)
    price = sum(pv_vals)
    return sum(pv_times) / price if price else 0


def convexity(settlement, maturity, coupon, yld, freq, basis='ACT/360', face=1):
    prev_coup = previous_coupon_date(settlement, maturity, freq)
    next_coup = next_coupon_date(settlement, maturity, freq)
    period_days = (next_coup - prev_coup).days
    accrual_days = (settlement - prev_coup).days
    t1 = (period_days - accrual_days) / period_days / freq
    payment_dates = [next_coup]
    current = next_coup
    while True:
        current = add_months(current, 12 // freq)
        if current > maturity:
            break
        payment_dates.append(current)
    coupon_amt = coupon * face / freq
    pv_convs, pv_vals = [], []
    for i, pay in enumerate(payment_dates):
        t = t1 + i * (1/freq)
        cf = coupon_amt + (face if pay == maturity else 0)
        dfactor = (1 + yld / freq) ** (-(t * freq))
        pv = cf * dfactor
        pv_vals.append(pv)
        pv_convs.append(pv * t * (t + 1/freq))
    price = sum(pv_vals)
    return sum(pv_convs) / price if price else 0

# --- Streamlit App ---
st.set_page_config(page_title="Excel Sheets Reader", layout="wide")
st.title("Excel Sheets Reader")

# Sidebar controls
st.sidebar.header("Upload and Filters")
uploader = st.sidebar.file_uploader("Choose an Excel file", type=["xlsx"])
settlement_date = st.sidebar.date_input("Date of Settlement", value=datetime.date.today())
roi_input = st.sidebar.number_input("Portfolio ROI (%)", min_value=0.0, value=7.01, step=0.01) / 100.0

if uploader:
    try:
        excel_data = pd.read_excel(uploader, sheet_name=None)
        key = "GS_Consolidated_Php"
        if key in excel_data:
            df = excel_data[key]
            # Class selector
            classes = df['Class'].dropna().unique().tolist()
            selected_class = st.sidebar.selectbox("Select Class", classes)
            df = df[df['Class'] == selected_class]

            # Fund selector
            funds = df['Fund'].dropna().unique().tolist()
            fund = st.sidebar.selectbox("Select Fund", funds)

            # Extract columns
            cols = [
                "Class","Fund","Reference","ISIN","Issue_Date","Value_Date","Maturity_Date",
                "YTM","Coupon","Term","Remaining_Term_Yrs","Coupon_Freq",
                f"Settlement_Amount_{fund}", f"Face_Amount_{fund}"
            ]
            cols = [c for c in cols if c in df.columns]
            df_extracted = df[cols].copy()

            # Convert types
            df_extracted['Maturity_Date'] = pd.to_datetime(df_extracted['Maturity_Date']).dt.date
            df_extracted['Coupon'] = df_extracted['Coupon'].astype(float)
            df_extracted['YTM'] = df_extracted['YTM'].astype(float)
            df_extracted['Coupon_Freq'] = df_extracted['Coupon_Freq'].astype(int)

            # Calculate metrics
            df_extracted['Duration'] = df_extracted.apply(
                lambda r: duration(settlement_date, r['Maturity_Date'], r['Coupon'], r['YTM'], r['Coupon_Freq']), axis=1)
            df_extracted['ModDuration'] = df_extracted['Duration'] / (1 + df_extracted['YTM']/df_extracted['Coupon_Freq'])
            df_extracted['Convexity'] = df_extracted.apply(
                lambda r: convexity(settlement_date, r['Maturity_Date'], r['Coupon'], r['YTM'], r['Coupon_Freq']), axis=1)

            # Weighted-average metrics
            face_col = f"Face_Amount_{fund}"
            total_face = df_extracted[face_col].sum()
            wa_duration = (df_extracted['Duration'] * df_extracted[face_col] / total_face).sum()
            wa_mod = (df_extracted['ModDuration'] * df_extracted[face_col] / total_face).sum()
            wa_conv = (df_extracted['Convexity'] * df_extracted[face_col] / total_face).sum()

            # Scenario: -25bps on ROI input
            dy = -0.0025
            pct_change = -wa_mod * dy + 0.5 * wa_conv * dy**2
            new_roi = roi_input + pct_change

            # Display
            st.subheader(f"Data for {selected_class} / {fund}")
            st.dataframe(df_extracted)
            st.markdown(f"**Weighted-average Duration:** {wa_duration:.6f} years")
            st.markdown(f"**Weighted-average Modified Duration:** {wa_mod:.6f} years")
            st.markdown(f"**Weighted-average Convexity:** {wa_conv:.6f}")
            st.markdown(f"**ROI before:** {roi_input:.2%}")
            st.markdown(f"**ROI after -25bps:** {new_roi:.2%}")
            st.markdown(f"**Est. % Price Change:** {pct_change:.2%}")

        # Show all sheets
        for name, table in excel_data.items():
            st.subheader(f"Sheet: {name}")
            st.dataframe(table)
    except Exception as e:
        st.error(f"Error: {e}")
