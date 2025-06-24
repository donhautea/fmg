import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

def show_equity_monitor_page():
    st.title("📊 Equity Database Monitoring")
    st.markdown("""
        <style>
        .main .block-container {
            padding-left: 2rem;
            padding-right: 2rem;
            max-width: 100% !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # Sidebar: file upload and filters
    st.sidebar.header("Upload Excel File")
    uploaded_file = st.sidebar.file_uploader("Choose an Excel (.xlsx) file", type="xlsx")
    if not uploaded_file:
        st.info("📥 Please upload an Excel file with the required sheet structure to begin.")
        return

    fund_sheet_map = {
        "SSS": ["SSS_FVTPL", "SSS_FVTOCI"],
        "EC": ["EC_FVTPL", "EC_FVTOCI"],
        "MPF": ["MPF_FVTPL"],
        "NVPF": ["NVPF_FVTPL"]
    }
    all_funds = list(fund_sheet_map.keys())

    sheets = pd.read_excel(uploaded_file, sheet_name=None)
    selected_fund = st.sidebar.radio("Select Fund to Analyze:", all_funds + ["All Funds"])
    date_from = st.sidebar.date_input("Date From")
    date_to = st.sidebar.date_input("Date To")
    analysis_type = st.sidebar.radio(
        "Select Summary Type:", [
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
    chart_fund = st.sidebar.checkbox("Bar Chart by Fund: Total Value by Buy/Sell")
    chart_stock = st.sidebar.checkbox("Bar Chart by Fund: Buy/Sell by Stock")
    chart_broker = st.sidebar.checkbox("Bar Chart by Broker: Buy/Sell by Value")

    # Load and filter data
    dfs = []
    funds = all_funds if selected_fund == "All Funds" else [selected_fund]
    required = {"Date", "Classification", "Stock", "Buy_Sell", "Broker", "Volume", "Price"}
    for fund in funds:
        for sheet in fund_sheet_map[fund]:
            df = sheets.get(sheet)
            if df is None or not required.issubset(df.columns):
                continue
            df = df.copy()
            df["Date"] = pd.to_datetime(df["Date"]).dt.date
            df = df[df["Date"].between(date_from, date_to)]
            df["Value"] = df["Volume"] * df["Price"]
            df["Fund"] = fund
            dfs.append(df)

    if not dfs:
        st.warning("No valid data for the selected fund(s) and date range.")
        return

    full_df = pd.concat(dfs, ignore_index=True)

    # Formatting helpers
    def fmt_volume(x):
        return f"{x:,.0f}"
    def fmt_value(x):
        return f"₱{x:,.2f}"
    def fmt_m(val):
        return f"₱{val:.1f} M" if val != 0 else ""

    def format_df(df, vol_col="Volume", val_col="Value"):
        df = df.copy()
        if vol_col in df.columns:
            df[vol_col] = df[vol_col].apply(fmt_volume)
        if val_col in df.columns:
            df[val_col] = df[val_col].apply(fmt_value)
        return df

    # Display raw data
    st.subheader(f"📁 Data for: {selected_fund}")
    st.dataframe(format_df(full_df))

    # Generate summary
    if analysis_type == "Summary by Fund and Buy/Sell with Total":
        summary = full_df.groupby(["Fund", "Buy_Sell"]) ["Value"].sum().reset_index()
    elif analysis_type == "Summary by Classification":
        summary = full_df.groupby("Classification")["Value"].sum().reset_index()
    elif analysis_type == "Summary by Buy/Sell":
        summary = full_df.groupby("Buy_Sell")["Value"].sum().reset_index()
    elif analysis_type == "Summary by Stock":
        summary = full_df.groupby("Stock").agg(Total_Volume=("Volume", "sum"), Total_Value=("Value", "sum")).reset_index()
        summary["Avg_Price"] = summary["Total_Value"] / summary["Total_Volume"]
    elif analysis_type == "Summary by Broker":
        summary = full_df.groupby("Broker")["Value"].sum().reset_index()
    elif analysis_type == "Total Value by Buy/Sell":
        summary = full_df.groupby("Buy_Sell")["Value"].sum().rename("Total Value").reset_index()
    elif analysis_type == "Total Value by Stock":
        summary = full_df.groupby(["Buy_Sell", "Stock"]) ["Value"].sum().rename("Total Value").reset_index()
    elif analysis_type == "Summary by Date by Fund by Buy/Sell by Value":
        summary = full_df.groupby(["Date", "Fund", "Buy_Sell"]) ["Value"].sum().reset_index()
    else:
        grp = full_df.groupby(["Stock", "Buy_Sell"]).agg(Total_Value=("Value", "sum"), Total_Shares=("Volume", "sum")).reset_index()
        grp["Weighted_Avg_Price"] = grp["Total_Value"] / grp["Total_Shares"]
        summary = grp.pivot(index="Stock", columns="Buy_Sell", values="Weighted_Avg_Price").reset_index().rename(columns={"B": "Avg_Buy", "S": "Avg_Sell"})

    # Display summary
    st.subheader("📊 Summary")
    # Determine columns for formatting
    vol_col = "Total_Volume" if "Total_Volume" in summary.columns else None
    val_cols = [c for c in summary.columns if c in ["Value", "Total Value", "Total_Value", "Avg_Price", "Weighted_Avg_Price", "Avg_Buy", "Avg_Sell"]]
    val_col = val_cols[0] if val_cols else None
    st.dataframe(format_df(summary, vol_col or "", val_col or ""))

    # Charts
    if chart_fund:
        st.subheader("Bar Chart: Total Value by Fund & Buy/Sell")
        cd = full_df.groupby(["Fund", "Buy_Sell"]) ["Value"].sum().unstack().fillna(0) / 1e6
        ax = cd.plot(kind="bar", figsize=(10,5), title="Total Value by Fund & Buy/Sell (₱M)")
        ax.set_ylabel("₱ Millions")
        for cont in ax.containers:
            ax.bar_label(cont, labels=[fmt_m(v) for v in cont.datavalues], fontsize=8)
        st.pyplot(plt)

    if chart_stock:
        st.subheader("Bar Chart: Buy/Sell by Stock")
        stocks = sorted(full_df["Stock"].unique())
        sel = st.multiselect("Select Stocks:", stocks, default=stocks)
        if sel:
            fd = full_df[full_df["Stock"].isin(sel)]
            cd = fd.groupby(["Stock", "Buy_Sell"]) ["Value"].sum().unstack().fillna(0)/1e6
            ax = cd.plot(kind="bar", figsize=(12,6), title="Buy/Sell by Selected Stocks (₱M)")
            ax.set_ylabel("₱ Millions")
            for cont in ax.containers:
                ax.bar_label(cont, labels=[fmt_m(v) for v in cont.datavalues], fontsize=8)
            st.pyplot(plt)
        else:
            st.warning("Please select at least one stock.")

    if chart_broker:
        st.subheader("Bar Chart: Buy/Sell by Broker")
        cd = full_df.groupby(["Broker", "Buy_Sell"]) ["Value"].sum().unstack().fillna(0)/1e6
        ax = cd.plot(kind="bar", figsize=(12,6), title="Buy/Sell by Broker (₱M)")
        ax.set_ylabel("₱ Millions")
        for cont in ax.containers:
            ax.bar_label(cont, labels=[fmt_m(v) for v in cont.datavalues], fontsize=8)
        st.pyplot(plt)
