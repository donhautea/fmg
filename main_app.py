# main_app.py

import streamlit as st

from collection import show_collection_page
from equities import show_equities_page
from equity_monitor import show_equity_monitor_page
from fixed_income import show_fixed_income_page
from portfolio_roi import show_portfolio_roi_page
from fi_analysis import show_fi_analysis
from duration_convexity import show_duration_convexity_page
from techanalysis import show_techanalysis_page

def main():
    # Configure page once, before any Streamlit commands
    st.set_page_config(
        page_title="Investment Analysis App",
        layout="wide"
    )
    st.title("Investment Portfolio Analysis")

    page = st.sidebar.selectbox(
        "Select Analysis Page:",
        [
            "Collection Report",
            "Equity Portfolio Analysis",
            "Equity Portfolio Monitoring",
            "Fixed Income",
            "Portfolio / ROI",
            "Fixed Income Statistical Data",
            "Duration, Convexity vs Rate Cuts",
            "Technical Analysis"
        ]
    )

    if page == "Collection Report":
        show_collection_page()

    elif page == "Equity Portfolio Analysis":
        show_equities_page()

    elif page == "Equity Portfolio Monitoring":
        show_equity_monitor_page()

    elif page == "Fixed Income":
        show_fixed_income_page()

    elif page == "Portfolio / ROI":
        show_portfolio_roi_page()

    elif page == "Fixed Income Statistical Data":
        show_fi_analysis()

    elif page == "Duration, Convexity vs Rate Cuts":
        show_duration_convexity_page()

    elif page == "Technical Analysis":
        show_techanalysis_page()

if __name__ == "__main__":
    main()