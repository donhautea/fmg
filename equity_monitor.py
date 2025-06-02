import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def show_equity_monitor_page():
    st.set_page_config(page_title="Equity Database Monitoring", layout="wide")
    st.title("📊 Equity Database Monitoring")

    # Sidebar: Upload Excel file
    st.sidebar.header("Upload Excel File")
    uploaded_file = st.sidebar.file_uploader("Choose an Excel (.xlsx) file", type="xlsx")

    # Fund-to-sheet mapping
    fund_sheet_map = {
        "SSS": ["SSS_FVTPL", "SSS_FVTOCI"],
        "EC": ["EC_FVTPL", "EC_FVTOCI"],
        "MPF": ["MPF_FVTPL"],
        "NVPF": ["NVPF_FVTPL"]
    }
    all_funds = list(fund_sheet_map.keys())

    if uploaded_file:
        all_sheets = pd.read_excel(uploaded_file, sheet_name=None)

        st.sidebar.header("Fund Selection")
        selected_fund = st.sidebar.radio("Select Fund to Analyze:", all_funds + ["All Funds"])

        st.sidebar.header("Coverage")
        date_from = st.sidebar.date_input("Date From")
        date_to = st.sidebar.date_input("Date To")

        st.sidebar.header("Data Analysis Menu")
        analysis_type = st.sidebar.radio(
            "Select Summary Type:",
            [
                "Summary by Fund and Buy/Sell with Total",
                "Summary by Classification",
                "Summary by Buy/Sell",
                "Summary by Stock",
                "Summary by Broker",
                "Total Value by Buy/Sell",
                "Total Value by Stock",
                "Summary by Date by Fund by Buy/Sell by Value",
                "Summary by Stock: Weighted Average Buying and Selling"
            ]
        )

        st.sidebar.header("Chart Menu")
        chart_fund_buysell = st.sidebar.checkbox("Bar Chart by Fund: Total Value by Buy/Sell")
        chart_stock_buysell = st.sidebar.checkbox("Bar Chart by Fund: Buy/Sell by Stock")
        chart_broker_buysell = st.sidebar.checkbox("Bar Chart by Broker: Buy/Sell by Value")

        dfs = []
        funds_to_process = all_funds if selected_fund == "All Funds" else [selected_fund]

        for fund in funds_to_process:
            for sheet in fund_sheet_map[fund]:
                if sheet in all_sheets:
                    df = all_sheets[sheet]
                    required_cols = {"Date", "Classification", "Stock", "Buy_Sell", "Broker", "Volume", "Price"}
                    if required_cols.issubset(df.columns):
                        df["Date"] = pd.to_datetime(df["Date"]).dt.date
                        df = df[(df["Date"] >= date_from) & (df["Date"] <= date_to)]
                        df["Value"] = df["Volume"] * df["Price"]
                        df["Fund"] = fund
                        df["Sheet"] = sheet
                        dfs.append(df)
                    else:
                        st.warning(f"Sheet '{sheet}' is missing required columns.")

        if dfs:
            full_df = pd.concat(dfs, ignore_index=True)
            st.subheader(f"📁 Data for: {selected_fund}")
            st.dataframe(full_df)

            if analysis_type == "Summary by Fund and Buy/Sell with Total":
                summary = full_df.groupby(["Fund", "Buy_Sell"])["Value"].sum().reset_index()
                st.dataframe(summary)
            elif analysis_type == "Summary by Classification":
                summary = full_df.groupby("Classification")["Value"].sum().reset_index()
                st.dataframe(summary)
            elif analysis_type == "Summary by Buy/Sell":
                summary = full_df.groupby("Buy_Sell")["Value"].sum().reset_index()
                st.dataframe(summary)
            elif analysis_type == "Summary by Stock":
                grouped = full_df.groupby("Stock").agg(
                    Total_Volume=("Volume", "sum"),
                    Total_Value=("Value", "sum")
                ).reset_index()
                grouped["Avg_Price"] = grouped["Total_Value"] / grouped["Total_Volume"]
                summary = grouped[["Stock", "Total_Volume", "Avg_Price", "Total_Value"]]
                st.dataframe(summary.style.format({
                    "Total_Volume": "{:,.0f}",
                    "Avg_Price": "₱{:,.2f}",
                    "Total_Value": "₱{:,.2f}"
                }))
            elif analysis_type == "Summary by Broker":
                summary = full_df.groupby("Broker")["Value"].sum().reset_index()
                st.dataframe(summary)
            elif analysis_type == "Total Value by Buy/Sell":
                summary = full_df.groupby("Buy_Sell")["Value"].sum().reset_index().rename(columns={"Value": "Total Value"})
                st.dataframe(summary)
            elif analysis_type == "Total Value by Stock":
                summary = full_df.groupby(["Buy_Sell", "Stock"])["Value"].sum().reset_index().rename(columns={"Value": "Total Value"})
                st.dataframe(summary)
            elif analysis_type == "Summary by Date by Fund by Buy/Sell by Value":
                summary = full_df.groupby(["Date", "Fund", "Buy_Sell"])["Value"].sum().reset_index()
                st.dataframe(summary)
            elif analysis_type == "Summary by Stock: Weighted Average Buying and Selling":
                grouped = full_df.groupby(["Stock", "Buy_Sell"]).agg(
                    Total_Value=("Value", "sum"),
                    Total_Shares=("Volume", "sum")
                ).reset_index()
                grouped["Weighted_Avg_Price"] = grouped["Total_Value"] / grouped["Total_Shares"]
                summary = grouped.pivot(index="Stock", columns="Buy_Sell", values="Weighted_Avg_Price").reset_index()
                summary = summary.rename(columns={"B": "Avg_Buying_Price", "S": "Avg_Selling_Price"})
                st.dataframe(summary.style.format({
                    "Avg_Buying_Price": "₱{:,.2f}",
                    "Avg_Selling_Price": "₱{:,.2f}"
                }))

            def format_label(val):
                return f"₱{val:.1f} M" if val != 0 else ""

            if chart_fund_buysell:
                st.subheader("📊 Bar Chart: Total Value by Buy/Sell per Fund")
                chart_data = full_df.groupby(["Fund", "Buy_Sell"])["Value"].sum().unstack().fillna(0) / 1_000_000
                ax = chart_data.plot(kind="bar", figsize=(10, 5), title="Total Value by Buy/Sell per Fund (in Millions)")
                ax.set_ylabel("Value (₱ Millions)")
                for container in ax.containers:
                    labels = [format_label(v) for v in container.datavalues]
                    ax.bar_label(container, labels=labels, fontsize=8)
                st.pyplot(plt)

            if chart_stock_buysell:
                st.subheader("📊 Bar Chart: Buy/Sell by Stock")
                all_stocks = sorted(full_df["Stock"].dropna().unique().tolist())
                selected_stocks = st.multiselect("Select Stocks to Display:", options=all_stocks, default=all_stocks)

                if selected_stocks:
                    filtered_stock_df = full_df[full_df["Stock"].isin(selected_stocks)]
                    chart_data = filtered_stock_df.groupby(["Stock", "Buy_Sell"])["Value"].sum().unstack().fillna(0) / 1_000_000
                    ax = chart_data.plot(kind="bar", figsize=(12, 6), title="Buy/Sell by Selected Stocks (in Millions)")
                    ax.set_ylabel("Value (₱ Millions)")
                    for container in ax.containers:
                        labels = [format_label(v) for v in container.datavalues]
                        ax.bar_label(container, labels=labels, fontsize=8)
                    st.pyplot(plt)
                else:
                    st.warning("Please select at least one stock to display the chart.")

            if chart_broker_buysell:
                st.subheader("📊 Bar Chart: Buy/Sell by Broker")
                chart_data = full_df.groupby(["Broker", "Buy_Sell"])["Value"].sum().unstack().fillna(0) / 1_000_000
                ax = chart_data.plot(kind="bar", figsize=(12, 6), title="Buy/Sell by Broker (in Millions)")
                ax.set_ylabel("Value (₱ Millions)")
                for container in ax.containers:
                    labels = [format_label(v) for v in container.datavalues]
                    ax.bar_label(container, labels=labels, fontsize=8)
                st.pyplot(plt)
        else:
            st.warning("No valid data loaded for the selected fund(s) and date range.")
    else:
        st.info("📅 Please upload an Excel file with the required sheet structure to begin.")
