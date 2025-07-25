# main_app.py

import streamlit as st

from collection import show_collection_page
from compare import show_collection_compare_page
from equities import show_equities_page
from equity_trans import show_equity_trans_page
from equity_monitor import show_equity_monitor_page
from fixed_income import show_fixed_income_page
from portfolio_roi import show_portfolio_roi_page
from fi_analysis import show_fi_analysis
from duration_convexity import show_duration_convexity_page
from techanalysis import show_techanalysis_page
from demographics_app import show_demographics_page
from pdf_viewer import show_pdf_viewer_page
from equity_market_prices import show_equity_market_prices_page
from coupon_maturity_summary import show_coupon_maturity_summary_page
from psei import show_psei_page
from integrated_weighted_vs_vwap_app import show_weighted_vs_vwap_page
from collection_tracker import show_collection_tracker_page  # ✅ New import
from vwap_db_update import show_vwap_db_update_page
from stock_db_bbupdate import show_stock_ohlc_update_page
from nvpf_portfolio import show_nvpf_portfolio_page

def main():
    st.set_page_config(
        page_title="Investment Analysis App",
        layout="wide"
    )
    st.title("Investment Portfolio Analysis")

    page_structure = {
        "Collection": [
            "Collection Report",
            "Collection Compare",
            "Demographics Dashboard",
            "CMG Tracker vs Collection Report"  # ✅ New page
        ],
        "Equity Asset": [
            "Equity Portfolio Analysis",
            "Equity Transaction Update",
            "Stock Data Viewer",
            "Equity Portfolio Monitoring",
            "Technical Analysis",
            "PSEI Analysis",
            "WAP vs Market VWAP Comparator"
        ],
        "Fixed Income Asset": [
            "Fixed Income",
            "Fixed Income Statistical Data",
            "Duration, Convexity vs Rate Cuts",
            "Coupon and Maturities Consolidated Report"
        ],
        "Other Analysis": [
            "Portfolio / ROI",
            "NVPF Portfolio: Contri vs Income",
            "PDF Viewer"
        ],
        "Database Update": [
            "VWAP Database Update",
            "Stock OHLC Database Update (bloomberg data)"
        ],
    }

    parent_selection = st.sidebar.selectbox("Select Analysis Category:", list(page_structure.keys()))
    sub_selection = st.sidebar.selectbox("Select Specific Page:", page_structure[parent_selection])

    if sub_selection == "Collection Report":
        show_collection_page()
    elif sub_selection == "Collection Compare":
        show_collection_compare_page()
    elif sub_selection == "Demographics Dashboard":
        show_demographics_page()
    elif sub_selection == "CMG Tracker vs Collection Report":
        show_collection_tracker_page()  # ✅ Routing
    elif sub_selection == "Equity Portfolio Analysis":
        show_equities_page()
    elif sub_selection == "Equity Transaction Update":
        show_equity_trans_page()
    elif sub_selection == "Stock Data Viewer":
        show_equity_market_prices_page()
    elif sub_selection == "Equity Portfolio Monitoring":
        show_equity_monitor_page()
    elif sub_selection == "Technical Analysis":
        show_techanalysis_page()
    elif sub_selection == "PSEI Analysis":
        show_psei_page()
    elif sub_selection == "WAP vs Market VWAP Comparator":
        show_weighted_vs_vwap_page()
    elif sub_selection == "Fixed Income":
        show_fixed_income_page()
    elif sub_selection == "Fixed Income Statistical Data":
        show_fi_analysis()
    elif sub_selection == "Duration, Convexity vs Rate Cuts":
        show_duration_convexity_page()
    elif sub_selection == "Coupon and Maturities Consolidated Report":
        show_coupon_maturity_summary_page()
    elif sub_selection == "Portfolio / ROI":
        show_portfolio_roi_page()
    elif sub_selection == "NVPF Portfolio: Contri vs Income":
        show_nvpf_portfolio_page()
    elif sub_selection == "PDF Viewer":
        show_pdf_viewer_page()
    elif sub_selection == "VWAP Database Update":
        show_vwap_db_update_page()
    elif sub_selection == "Stock OHLC Database Update (bloomberg data)":
        show_stock_ohlc_update_page()

if __name__ == "__main__":
    main()
