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
    show_custom_summary = st.sidebar.checkbox("Show Net Value Summary", value=True)

    chart_fund = st.sidebar.checkbox("Bar Chart by Fund: Total Value by Buy/Sell")
    chart_stock = st.sidebar.checkbox("Bar Chart by Fund: Buy/Sell by Stock")
    chart_broker = st.sidebar.checkbox("Bar Chart by Broker: Buy/Sell by Value")

    # Date period string for display
    date_period = f"{date_from.strftime('%Y-%m-%d')}" if date_from == date_to else f"{date_from.strftime('%Y-%m-%d')} to {date_to.strftime('%Y-%m-%d')}"

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

    def fmt_value(x):
        return f"₱{x:,.2f}"

    def fmt_value_millions(x):
        return f"₱{x:,.1f}M" if x != 0 else ""

    def format_net(val):
        color = "green" if val >= 0 else "red"
        return f"<span style='color:{color}'>₱{val:,.2f}</span>"

    def format_pct(val):
        return f"{val:,.2f}%" if val > 0 else "0.00%"

    st.subheader(f"📁 Data for: {selected_fund}")
    full_df_display = full_df.copy()
    full_df_display["Value"] = full_df_display["Value"].apply(fmt_value)
    st.dataframe(full_df_display)

    if show_custom_summary:
        st.subheader("📊 Summary by Fund: Net Value")
        st.markdown(f"**🗓️ Period: {date_period}**")

        grouped = full_df.groupby(["Fund", "Buy_Sell"])["Value"].sum().unstack().fillna(0)
        grouped = grouped.rename(columns={"B": "Buy Value", "S": "Sell Value"})

        grouped["Buy Value"] = grouped.get("Buy Value", 0.0)
        grouped["Sell Value"] = grouped.get("Sell Value", 0.0)
        grouped["Net Value"] = grouped["Buy Value"] - grouped["Sell Value"]
        grouped["% Distribution"] = ((grouped["Buy Value"] + grouped["Sell Value"]) /
                                     (grouped["Buy Value"] + grouped["Sell Value"]).sum()) * 100
        grouped = grouped.reset_index()

        total_row = {
            "Fund": "Total",
            "Buy Value": grouped["Buy Value"].sum(),
            "Sell Value": grouped["Sell Value"].sum(),
            "Net Value": grouped["Net Value"].sum(),
            "% Distribution": 100.00
        }
        summary_df = pd.concat([grouped, pd.DataFrame([total_row])], ignore_index=True)

        def fmt_currency(val):
            return f"₱{val:,.2f}"

        def fmt_net(val):
            color = "green" if val >= 0 else "red"
            return f"<span style='color:{color}'>₱{val:,.2f}</span>"

        def fmt_pct(val):
            return f"{val:,.2f}%"

        summary_df["Buy Value"] = summary_df["Buy Value"].apply(fmt_currency)
        summary_df["Sell Value"] = summary_df["Sell Value"].apply(fmt_currency)
        summary_df["Net Value"] = summary_df["Net Value"].apply(fmt_net)
        summary_df["% Distribution"] = summary_df["% Distribution"].apply(fmt_pct)

        summary_df = summary_df[["Fund", "Buy Value", "Sell Value", "Net Value", "% Distribution"]]

        st.markdown("<style>table, th, td { border: 1px solid #ccc; border-collapse: collapse; padding: 8px; }</style>", unsafe_allow_html=True)
        st.markdown(summary_df.to_html(escape=False, index=False), unsafe_allow_html=True)

    if chart_fund:
        st.subheader("Bar Chart: Total Value by Fund & Buy/Sell")
        cd = full_df.groupby(["Fund", "Buy_Sell"])["Value"].sum().unstack().fillna(0) / 1e6
        title = f"Total Value by Fund & Buy/Sell (₱M) — {date_period}"
        ax = cd.plot(kind="bar", figsize=(10, 5), title=title)
        ax.set_ylabel("₱ Millions")
        for cont in ax.containers:
            ax.bar_label(cont, labels=[fmt_value_millions(v) for v in cont.datavalues], fontsize=8)
        st.pyplot(plt)

    if chart_stock:
        st.subheader("Bar Chart: Buy/Sell by Stock")
        stocks = sorted(full_df["Stock"].unique())
        sel = st.multiselect("Select Stocks:", stocks, default=stocks)
        if sel:
            fd = full_df[full_df["Stock"].isin(sel)]
            cd = fd.groupby(["Stock", "Buy_Sell"])["Value"].sum().unstack().fillna(0) / 1e6
            title = f"Buy/Sell by Selected Stocks (₱M) — {date_period}"
            ax = cd.plot(kind="bar", figsize=(12, 6), title=title)
            ax.set_ylabel("₱ Millions")
            for cont in ax.containers:
                ax.bar_label(cont, labels=[fmt_value_millions(v) for v in cont.datavalues], fontsize=8)
            st.pyplot(plt)
        else:
            st.warning("Please select at least one stock.")

    if chart_broker:
        st.subheader("Bar Chart: Buy/Sell by Broker")
        cd = full_df.groupby(["Broker", "Buy_Sell"])["Value"].sum().unstack().fillna(0) / 1e6
        title = f"Buy/Sell by Broker (₱M) — {date_period}"
        ax = cd.plot(kind="bar", figsize=(12, 6), title=title)
        ax.set_ylabel("₱ Millions")
        for cont in ax.containers:
            ax.bar_label(cont, labels=[fmt_value_millions(v) for v in cont.datavalues], fontsize=8)
        st.pyplot(plt)

    # New Report: Weighted Average Price with Volume and Value
    st.subheader("📘 Weighted Average Price with Volume and Value by Date, Fund, Buy/Sell, Stock")

    weighted_df = full_df.copy()

    # Compute Value if not already present
    if 'Value' not in weighted_df.columns:
        weighted_df["Value"] = weighted_df["Volume"] * weighted_df["Price"]

    weighted_summary = weighted_df.groupby(["Date", "Fund", "Buy_Sell", "Stock"]).agg(
        Total_Volume=("Volume", "sum"),
        Total_Value=("Value", "sum")
    ).reset_index()

    weighted_summary["Weighted_Avg_Price"] = (
        weighted_summary["Total_Value"] / weighted_summary["Total_Volume"]
    ).round(2)

    weighted_summary["Total_Value"] = weighted_summary["Total_Value"].round(2)

    # Format columns
    weighted_summary["Total_Volume"] = weighted_summary["Total_Volume"].apply(lambda x: f"{x:,.0f}")
    weighted_summary["Total_Value"] = weighted_summary["Total_Value"].apply(lambda x: f"₱{x:,.2f}")
    weighted_summary["Weighted_Avg_Price"] = weighted_summary["Weighted_Avg_Price"].apply(lambda x: f"₱{x:,.2f}")

    # Display table
    st.dataframe(weighted_summary, use_container_width=True)
