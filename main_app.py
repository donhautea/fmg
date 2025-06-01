import streamlit as st

def main():
    st.set_page_config(page_title="Investment Analysis App", layout="wide")
    st.title("Investment Portfolio Analysis")

    page = st.sidebar.selectbox(
        "Select Analysis Page:",
        ["Collection Report", "Equities", "Fixed Income", "Money Market", "Reference"]
    )

    if page == "Collection Report":
        # Import and call the function in collection.py
        from collection import show_collection_page
        show_collection_page()

    elif page == "Fixed Income":
        from fixed_income import show_fixed_income_page
        show_fixed_income_page()

    elif page == "Equities":
        from equities import show_equities_page
        show_equities_page()

    elif page == "Money Market":
        st.info("Money Market analysis coming soon.")

    elif page == "Reference":
        st.info("Reference data and tools coming soon.")


if __name__ == "__main__":
    main()
