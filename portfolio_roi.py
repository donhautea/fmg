import streamlit as st
import pandas as pd

def show_portfolio_roi_page():
    st.title("📊 Fund-Specific Summary Report")

    st.sidebar.header("Upload Excel File")
    uploaded_file = st.sidebar.file_uploader("Choose an Excel file (.xlsx)", type="xlsx")

    fund_ranges = {
        'MPF':   ('B', 'G'),
        'NVPF':  ('H', 'M'),
        'FLEXI': ('N', 'S'),
        'PESO':  ('T', 'Y'),
        'MIA':   ('Z', 'AE'),
    }

    asset_order = [
        "Money Market",
        "Capital Market",
        "Government Securities",
        "Corporate Notes and Bonds",
        "Equities",
    ]

    sheet_names = ["ROI", "INVESTMENT_LEVEL", "INVESTMENT_INCOME"]

    def col_letter_to_index(col):
        col = col.upper()
        index = 0
        for i, char in enumerate(reversed(col)):
            index += (ord(char) - ord('A') + 1) * (26 ** i)
        return index - 1

    def extract_fund_data(df_raw, start_col_letter, end_col_letter, sheet_name=None, format_roi=False):
        start_col = col_letter_to_index(start_col_letter)
        end_col = col_letter_to_index(end_col_letter) + 1
        headers = [str(h).strip() for h in df_raw.iloc[1, start_col:end_col].tolist()]
        data = df_raw.iloc[2:, start_col:end_col].copy()
        data.columns = headers
        data.insert(0, 'Date', pd.to_datetime(df_raw.iloc[2:, 0], errors='coerce').dt.strftime('%Y-%m-%d'))

        if sheet_name == "ROI" and format_roi:
            for col in data.columns[1:]:
                data[col] = pd.to_numeric(data[col], errors='coerce') * 100
                data[col] = data[col].map(lambda x: f"{x:.3f}%" if pd.notnull(x) else "")

        return data.dropna(subset=['Date'])

    if uploaded_file:
        st.success("✅ File uploaded successfully")

        raw_sheets = {}
        for sheet in sheet_names:
            raw_sheets[sheet] = pd.read_excel(uploaded_file, sheet_name=sheet, header=None)

        fund_choice = st.sidebar.selectbox("Select Fund", list(fund_ranges.keys()))
        show_datasets = st.sidebar.checkbox("Show dataset preview per sheet")

        fund_data = {}
        for sheet in sheet_names:
            df_raw = raw_sheets[sheet]
            start_col, end_col = fund_ranges[fund_choice]
            format_roi = True if sheet == "ROI" and show_datasets else False
            fund_data[sheet] = extract_fund_data(df_raw, start_col, end_col, sheet_name=sheet, format_roi=format_roi)

        common_dates = set(fund_data["ROI"]["Date"]) & set(fund_data["INVESTMENT_LEVEL"]["Date"]) & set(fund_data["INVESTMENT_INCOME"]["Date"])
        sorted_dates = sorted(list(common_dates), reverse=True)  # Sort descending
        date_choice = st.sidebar.selectbox("Select Date", sorted_dates, index=0)  # Default to latest

        def get_row(df):
            row = df[df["Date"] == date_choice]
            return row.iloc[0] if not row.empty else pd.Series()

        level_row = get_row(fund_data["INVESTMENT_LEVEL"])
        income_row = get_row(fund_data["INVESTMENT_INCOME"])

        # Extract unformatted ROI dataset for report values
        df_raw_roi = extract_fund_data(raw_sheets["ROI"], *fund_ranges[fund_choice], sheet_name="ROI", format_roi=False)
        roi_row = get_row(df_raw_roi)

        report = pd.DataFrame(columns=["Asset", "Investment Level", "% Distribution", "Investment Income", "ROI"])

        try:
            total_level = sum(pd.to_numeric(level_row.get(asset, 0), errors='coerce') for asset in asset_order if asset != "Capital Market")
            total_income = sum(pd.to_numeric(income_row.get(asset, 0), errors='coerce') for asset in asset_order if asset != "Capital Market")

            for asset in asset_order:
                inv_level = pd.to_numeric(level_row.get(asset, 0), errors='coerce')
                inv_income = pd.to_numeric(income_row.get(asset, 0), errors='coerce')
                roi_val = pd.to_numeric(roi_row.get(asset, None), errors='coerce')
                roi_value = f"{roi_val * 100:.2f}%" if pd.notnull(roi_val) else ""
                dist_pct = (inv_level / total_level * 100) if total_level else 0

                report = pd.concat([report, pd.DataFrame([{
                    "Asset": asset,
                    "Investment Level": f"{inv_level:,.2f}",
                    "% Distribution": f"{dist_pct:.2f}%",
                    "Investment Income": f"{inv_income:,.2f}",
                    "ROI": roi_value
                }])], ignore_index=True)

            overall_roi_val = None
            for col in roi_row.index:
                if str(col).strip().lower() == "overall roi":
                    overall_roi_val = pd.to_numeric(roi_row[col], errors='coerce')
                    break
            overall_roi = f"{overall_roi_val * 100:.2f}%" if pd.notnull(overall_roi_val) else ""

            report = pd.concat([report, pd.DataFrame([{
                "Asset": "Total",
                "Investment Level": f"{total_level:,.2f}",
                "% Distribution": "100.00%",
                "Investment Income": f"{total_income:,.2f}",
                "ROI": overall_roi
            }])], ignore_index=True)

            st.subheader(f"{fund_choice} Fund Report for {date_choice}")
            st.dataframe(report, use_container_width=True)

            if show_datasets:
                st.markdown("---")
                st.subheader("📂 Dataset Preview")
                for sheet in sheet_names:
                    st.markdown(f"**{sheet} - {fund_choice}**")
                    st.dataframe(fund_data[sheet], use_container_width=True)

        except Exception as e:
            st.error(f"Error generating report: {e}")
    else:
        st.warning("📥 Please upload an Excel file to begin.")
