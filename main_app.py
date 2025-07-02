# main_app.py

import streamlit as st

from collection import show_collection_page
from compare import show_collection_compare_page
from equities import show_equities_page
from equity_monitor import show_equity_monitor_page
from fixed_income import show_fixed_income_page
from portfolio_roi import show_portfolio_roi_page
from fi_analysis import show_fi_analysis
from duration_convexity import show_duration_convexity_page
from techanalysis import show_techanalysis_page
from demographics_app import show_demographics_page
from pdf_viewer import show_pdf_viewer_page
from equity_trans import show_equity_trans_page  # ✅ NEW IMPORT

def main():
    st.set_page_config(
        page_title="Investment Analysis App",
        layout="wide"
    )
    st.title("Investment Portfolio Analysis")

    page = st.sidebar.selectbox(
        "Select Analysis Page:",
        [
            "Collection Report",
            "Collection Compare",
            "Equity Portfolio Analysis",
            "Equity Transaction Update",       # ✅ NEW MENU OPTION
            "Equity Portfolio Monitoring",
            "Fixed Income",
            "Portfolio / ROI",
            "Fixed Income Statistical Data",
            "Duration, Convexity vs Rate Cuts",
            "Technical Analysis",
            "Demographics Dashboard",
            "PDF Viewer"
        ]
    )

    if page == "Collection Report":
        show_collection_page()
    elif page == "Collection Compare":
        show_collection_compare_page()
    elif page == "Equity Portfolio Analysis":
        show_equities_page()
    elif page == "Equity Transaction Update":
        show_equity_trans_page()            # ✅ CALL NEW FUNCTION
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
    elif page == "Demographics Dashboard":
        show_demographics_page()
    elif page == "PDF Viewer":
        show_pdf_viewer_page()

if __name__ == "__main__":
    main()
