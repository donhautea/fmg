# integrated_weighted_vs_vwap_app.py

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime

def show_weighted_vs_vwap_page():
    st.title("📊 Weighted Average Price vs Market VWAP Comparator (Integrated)")

    @st.cache_data
    def load_equity_monitor_data(uploaded_file, selected_fund, date_from, date_to):
        fund_sheet_map = {
            "SSS": ["SSS_FVTPL", "SSS_FVTOCI"],
            "EC": ["EC_FVTPL", "EC_FVTOCI"],
            "MPF": ["MPF_FVTPL"],
            "NVPF": ["NVPF_FVTPL"]
        }
        all_funds = list(fund_sheet_map.keys())

        sheets = pd.read_excel(uploaded_file, sheet_name=None)
        funds = all_funds if selected_fund == "All Funds" else [selected_fund]

        dfs = []
        for fund in funds:
            for sheet in fund_sheet_map[fund]:
                df = sheets.get(sheet)
                if df is None or not {"Date", "Classification", "Stock", "Buy_Sell", "Broker", "Volume", "Price"}.issubset(df.columns):
                    continue
                df = df.copy()
                df["Date"] = pd.to_datetime(df["Date"]).dt.date
                df = df[df["Date"].between(date_from, date_to)]
                df["Value"] = df["Volume"] * df["Price"]
                df["Fund"] = fund
                dfs.append(df)

        if not dfs:
            return pd.DataFrame()

        full_df = pd.concat(dfs, ignore_index=True)
        grouped = full_df.groupby(["Date", "Fund", "Buy_Sell", "Stock"]).agg(
            Total_Volume=("Volume", "sum"),
            Total_Value=("Value", "sum")
        ).reset_index()
        grouped["Weighted_Avg_Price"] = (grouped["Total_Value"] / grouped["Total_Volume"]).round(2)
        return grouped

    @st.cache_data
    def load_vwapex_data(start_date, end_date, selected_codes):
        with sqlite3.connect("vwap_data.db") as conn:
            df_all = pd.read_sql_query("SELECT * FROM vwap_data", conn)
        if df_all.empty:
            return pd.DataFrame()

        df_all["date"] = pd.to_datetime(df_all["date"]).dt.date
        df_all["code"] = df_all["code"].astype(str).str.strip()

        filtered = df_all[
            (df_all["date"] >= start_date) &
            (df_all["date"] <= end_date) &
            (df_all["code"].isin(selected_codes))
        ]
        return filtered

    # Sidebar
    st.sidebar.header("📥 Upload Equity Monitor File")
    uploaded_equity_file = st.sidebar.file_uploader("Choose Equity Excel (.xlsx) File", type="xlsx")

    st.sidebar.header("📅 Date Range")
    date_from = st.sidebar.date_input("Date From", datetime(2025, 1, 1))
    date_to = st.sidebar.date_input("Date To", datetime(2025, 12, 31))

    st.sidebar.header("🏦 Select Fund")
    fund_options = ["SSS", "EC", "MPF", "NVPF", "All Funds"]
    selected_fund = st.sidebar.selectbox("Select Fund", fund_options)

    st.sidebar.header("📈 VWAPEx Filter Options")
    with sqlite3.connect("vwap_data.db") as conn:
        vwap_df_all = pd.read_sql_query("SELECT DISTINCT code FROM vwap_data", conn)
        all_codes = sorted(vwap_df_all["code"].dropna().astype(str).unique().tolist()) if not vwap_df_all.empty else []

    select_all_codes = st.sidebar.checkbox("Select All Codes", value=True)
    selected_codes = all_codes if select_all_codes else st.sidebar.multiselect("Choose Stock Code", all_codes, default=[])

    if uploaded_equity_file and selected_codes:
        wap_df = load_equity_monitor_data(uploaded_equity_file, selected_fund, date_from, date_to)
        vwapex_df = load_vwapex_data(date_from, date_to, selected_codes)

        if not wap_df.empty and not vwapex_df.empty:
            wap_df.rename(columns={"Stock": "code"}, inplace=True)
            merged_df = pd.merge(
                wap_df,
                vwapex_df,
                how='left',
                left_on=['Date', 'code'],
                right_on=['date', 'code']
            ).drop(columns=['date'])

            merged_df['Disparity'] = merged_df['Weighted_Avg_Price'] - merged_df['vwap_ex']
            merged_df.rename(columns={"vwap_ex": "market_vwap_ex"}, inplace=True)

            st.subheader("📘 Merged Data with Disparity")
            st.dataframe(merged_df)

            # Sidebar filters
            st.sidebar.header("📊 Visualization Filters")
            selected_stock = st.sidebar.selectbox("Filter by Stock", ["All"] + sorted(merged_df["code"].unique().tolist()))
            exclude_codes = st.sidebar.multiselect("Exclude Stock Codes", sorted(merged_df["code"].unique().tolist()), default=[])
            chart_type = st.sidebar.radio("Chart Type", ["Line", "Bar"])

            filter_df = merged_df.copy()
            if selected_stock != "All":
                filter_df = filter_df[filter_df["code"] == selected_stock]
            if exclude_codes:
                filter_df = filter_df[~filter_df["code"].isin(exclude_codes)]

            if not filter_df.empty:
                for action in ['B', 'S']:
                    subset = filter_df[filter_df["Buy_Sell"] == action]
                    if not subset.empty:
                        fig = (
                            px.line(subset, x="Date", y=["Weighted_Avg_Price", "market_vwap_ex"], markers=True)
                            if chart_type == "Line" else
                            px.bar(subset, x="Date", y=["Weighted_Avg_Price", "market_vwap_ex"], barmode="group")
                        )
                        fig.update_layout(title=f"{'Buy' if action == 'B' else 'Sell'}: {selected_stock} – WAP vs Market VWAP")
                        st.plotly_chart(fig, use_container_width=True)

                # Daily Trade Summary
                st.markdown("## 📈 Daily Trade Performance Summary")

                def compute_stats(group):
                    total_volume = group['Total_Volume'].sum()
                    total_value = group['Total_Value'].sum()
                    internal_vwap = total_value / total_volume if total_volume != 0 else None
                    market_vwap_avg = group['market_vwap_ex'].mean()
                    disparity = internal_vwap - market_vwap_avg if internal_vwap and market_vwap_avg else None
                    price_std = group['Weighted_Avg_Price'].std()
                    result = {
                        'Trades': group.shape[0],
                        'Total Volume': total_volume,
                        'Total Value': total_value,
                        'Internal VWAP': internal_vwap,
                        'Avg Market VWAP': market_vwap_avg,
                        'VWAP Disparity': disparity,
                        'Min Price': group['Weighted_Avg_Price'].min(),
                        'Max Price': group['Weighted_Avg_Price'].max()
                    }
                    if price_std and price_std > 0:
                        result['Price StdDev'] = price_std
                    return pd.Series(result)

                group_cols = ['Date', 'Buy_Sell'] if selected_stock != "All" else ['Date', 'code', 'Buy_Sell']
                stats_df = filter_df.groupby(group_cols).apply(compute_stats).reset_index()
                st.dataframe(stats_df)

                # Execution Insights
                st.markdown("## 📌 Execution Summary & Insights by Transaction Type")
                for action in ['B', 'S']:
                    action_name = "Buy" if action == 'B' else "Sell"
                    subset = stats_df[stats_df['Buy_Sell'] == action]
                    if subset.empty:
                        continue
                    mean_disp = subset['VWAP Disparity'].mean()
                    min_disp = subset['VWAP Disparity'].min()
                    max_disp = subset['VWAP Disparity'].max()
                    st.markdown(f"""
                    ### 🔍 {action_name} Transactions
                    - Trade Days: {subset['Date'].nunique()}
                    - Average VWAP Disparity: {mean_disp:+.2f}
                    - Best Execution: {min_disp:+.2f}
                    - Worst Execution: {max_disp:+.2f}
                    """)
                    if action == 'B':
                        if mean_disp < 0:
                            st.success("✅ Buy execution was better than market VWAP.")
                        elif mean_disp > 0:
                            st.warning("⚠️ Buy execution was not better than market VWAP.")
                        else:
                            st.info("ℹ️ Buy execution matched market VWAP.")
                    else:
                        if mean_disp > 0:
                            st.success("✅ Sell execution was better than market VWAP.")
                        elif mean_disp < 0:
                            st.warning("⚠️ Sell execution was not better than market VWAP.")
                        else:
                            st.info("ℹ️ Sell execution matched market VWAP.")

                # Summary by Stock
                st.markdown("## 📊 Summary of All Stocks by Buy/Sell")

                def summarize_by_stock(group):
                    total_volume = group['Total_Volume'].sum()
                    total_value = group['Total_Value'].sum()
                    internal_vwap = total_value / total_volume if total_volume else None
                    market_vwap = group['market_vwap_ex'].mean()
                    avg_disp = internal_vwap - market_vwap if internal_vwap and market_vwap else None
                    min_disp = group['Disparity'].min()
                    max_disp = group['Disparity'].max()
                    trade_days = group['Date'].nunique()
                    action = group['Buy_Sell'].iloc[0]
                    if avg_disp is None:
                        interpretation = "N/A"
                    elif action == 'B':
                        interpretation = "✅ Better Buy" if avg_disp < 0 else "⚠️ Not Better Buy" if avg_disp > 0 else "ℹ️ Neutral Buy"
                    elif action == 'S':
                        interpretation = "✅ Better Sell" if avg_disp > 0 else "⚠️ Not Better Sell" if avg_disp < 0 else "ℹ️ Neutral Sell"
                    else:
                        interpretation = "Unknown"
                    return pd.Series({
                        'Total Volume': total_volume,
                        'Total Value': total_value,
                        'Internal VWAP': internal_vwap,
                        'Avg Market VWAP': market_vwap,
                        'Avg VWAP Disparity': avg_disp,
                        'Min Disparity': min_disp,
                        'Max Disparity': max_disp,
                        'Trade Days': trade_days,
                        'Interpretation': interpretation
                    })

                summary_all = filter_df.groupby(['code', 'Buy_Sell']).apply(summarize_by_stock).reset_index()
                st.dataframe(summary_all)

                # Downloads
                st.download_button("📥 Download Filtered CSV", data=filter_df.to_csv(index=False), file_name="filtered_data.csv")
                st.download_button("📥 Download Daily Summary", data=stats_df.to_csv(index=False), file_name="daily_summary.csv")
                st.download_button("📥 Download Stock Summary", data=summary_all.to_csv(index=False), file_name="stock_summary.csv")

            else:
                st.warning("No data after applying filters.")
        else:
            st.warning("No data from uploaded files or VWAPEx.")
    else:
        st.info("Upload file and select stock codes to begin.")
