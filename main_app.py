import streamlit as st

def main():
    st.set_page_config(page_title="Investment Analysis App", layout="wide")
    st.title("Investment Portfolio Analysis")

    page = st.sidebar.selectbox(
        "Select Analysis Page:",
        [
            "Collection Report",
            "Equity Portfolio Analysis",
            "Equity Portfolio Monitoring",
            "Fixed Income",
            "Portfolio / ROI",
            "Reference"
        ]
    )

    if page == "Collection Report":
        from collection import show_collection_page
        show_collection_page()

    elif page == "Equity Portfolio Analysis":
        from equities import show_equities_page
        show_equities_page()

    elif page == "Equity Portfolio Monitoring":
        from equity_monitor import show_equity_monitor_page
        show_equity_monitor_page()

    elif page == "Fixed Income":
        from fixed_income import show_fixed_income_page
        show_fixed_income_page()

    elif page == "Portfolio / ROI":
        from portfolio_roi import show_portfolio_roi_page
        show_portfolio_roi_page()

    elif page == "Reference":
        st.info("Reference data and tools coming soon.")

if __name__ == "__main__":
    main()
