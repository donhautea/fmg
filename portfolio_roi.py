import streamlit as st
import pandas as pd
from datetime import datetime
import calendar

def show_portfolio_roi_page():
    st.sidebar.header("Upload Excel File")
    uploaded_file = st.sidebar.file_uploader("Upload Excel (.xlsx) file", type=["xlsx"])

    def convert_to_end_of_month(label):
        try:
            if "as of" in label:
                parts = label.strip().split()
                month = datetime.strptime(parts[2], "%B").month
                year = int(parts[3])
                last_day = calendar.monthrange(year, month)[1]
                return datetime(year, month, last_day).strftime('%Y-%m-%d')
        except:
            return None

    def extract_section(sheet_df, date_row, rows_map, capital_market_row=None, percent=False):
        data_start_col = 12  # Column M
        date_row_values = sheet_df.iloc[date_row, data_start_col:]
        last_col = date_row_values.last_valid_index()
        if last_col is None:
            return pd.DataFrame()
        end_col = last_col + 1
        date_labels = sheet_df.iloc[date_row, data_start_col:end_col]
        dates = date_labels.apply(lambda x: convert_to_end_of_month(str(x)))

        data = {}
        if capital_market_row is not None:
            values = pd.to_numeric(sheet_df.iloc[capital_market_row, data_start_col:end_col].values, errors='coerce')
            if percent:
                values *= 100
            label = "Capital Market" if percent else "Capital Markets"
            data[label] = values

        for label, row in rows_map.items():
            row_values = sheet_df.iloc[row, data_start_col:end_col]
            valid_values = pd.to_numeric(row_values.values, errors='coerce')
            if percent:
                valid_values *= 100
            data[label] = valid_values

        df = pd.DataFrame(data, index=dates[:len(next(iter(data.values())))]).dropna()
        df.index.name = "Date"
        df = df.sort_index(ascending=False)

        desired_order = [col for col in ["Money Market", "Capital Market", "Capital Markets"] if col in df.columns]
        remaining_cols = [col for col in df.columns if col not in desired_order]
        df = df[desired_order + remaining_cols]

        return df

    if uploaded_file:
        excel = pd.ExcelFile(uploaded_file)
        sheet_names = [s for s in excel.sheet_names if s.startswith("FS")]
        st.title("Extracted Fund Data")

        all_data = {}
        all_dates = set()

        for sheet_name in sheet_names:
            df_sheet = excel.parse(sheet_name, header=None)

            # Return on Investment
            roi_rows = {
                "Money Market": 57,
                "Government Securities": 59,
                "Corporate Notes and Bonds": 60,
                "Equities": 61,
                "Overall ROI": 62,
            }
            capital_market_row_roi = 58

            # Investment Level
            investment_rows = {
                "Money Market": 9,
                "Government Securities": 7,
                "Corporate Notes and Bonds": 8,
                "Equities": 12,
                "Total Investments": 13,
            }
            capital_market_row_inv = 5

            # Investment Income
            income_rows = {
                "Money Market": 29,
                "Government Securities": 27,
                "Corporate Notes and Bonds": 28,
                "Equities": 32,
                "Total Investment Income": 33,
            }
            capital_market_row_inc = 25

            df_roi = extract_section(df_sheet, 55, roi_rows, capital_market_row=capital_market_row_roi, percent=True)
            df_inv = extract_section(df_sheet, 4, investment_rows, capital_market_row=capital_market_row_inv, percent=False)
            df_inc = extract_section(df_sheet, 24, income_rows, capital_market_row=capital_market_row_inc, percent=False)

            all_data[sheet_name] = {
                "Return on Investment": df_roi,
                "Investment Level": df_inv,
                "Investment Income": df_inc,
            }

            all_dates.update(df_roi.index.tolist())
            all_dates.update(df_inv.index.tolist())
            all_dates.update(df_inc.index.tolist())

        sorted_dates = sorted(all_dates, reverse=True)
        default_date = "2024-12-31" if "2024-12-31" in sorted_dates else sorted_dates[0]
        selected_date = st.sidebar.selectbox(
            "Select Date (applies to all sheets and sections)",
            options=sorted_dates,
            index=sorted_dates.index(default_date)
        )

        for sheet_name, sections in all_data.items():
            st.subheader(f"{sheet_name} – Data for {selected_date}")
            for section_title, df in sections.items():
                st.markdown(f"**{section_title}**")
                if selected_date in df.index:
                    filtered = df.loc[[selected_date]]
                    if section_title == "Return on Investment":
                        st.dataframe(filtered.style.format("{:.3f}%"))
                    else:
                        st.dataframe(filtered.style.format("{:,.2f}"))
                else:
                    st.info(f"No data available for {selected_date} in {section_title}")
