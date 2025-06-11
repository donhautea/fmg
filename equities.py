# equities.py
import streamlit as st
import pandas as pd
import numpy as np


def show_equities_page():
    st.title("Equities: CSV Loader & Returns Analysis")

    # Load Price Dataset
    st.sidebar.header("Load Price Dataset")
    uploaded_price_file = st.sidebar.file_uploader(
        "Choose Price CSV", type=["csv"], key="price_uploader"
    )
    if uploaded_price_file is not None:
        df_price = pd.read_csv(uploaded_price_file)
    else:
        df_price = pd.DataFrame()

    # Load Portfolio Returns and Weights
    st.sidebar.header("Load Portfolio Returns and Weights")
    uploaded_port_file = st.sidebar.file_uploader(
        "Choose Portfolio CSV", type=["csv"], key="port_uploader"
    )
    if uploaded_port_file is not None:
        df_port = pd.read_csv(uploaded_port_file)
        df_port.columns = df_port.columns.str.strip()
        # Normalize common header variants
        rename_map = {}
        if 'Target_Return' in df_port.columns:
            rename_map['Target_Return'] = 'Target Return'
        if 'Target_Weights' in df_port.columns:
            rename_map['Target_Weights'] = 'Target Weights'
        if 'Acquisition Return' in df_port.columns:
            rename_map['Acquisition Return'] = 'Acquisition_Return'
        if rename_map:
            df_port.rename(columns=rename_map, inplace=True)
    else:
        df_port = pd.DataFrame()

    # Prepare price returns time-series
    if not df_price.empty and 'Date' in df_price.columns:
        price_df = (
            df_price.drop(columns=['Date'])
                    .replace(r'[₱,]', '', regex=True)
                    .apply(pd.to_numeric, errors='coerce')
                    .dropna(axis=1, how='all')
        )
        returns_ts = price_df.pct_change().fillna(0)
    else:
        returns_ts = pd.DataFrame()

    # Sidebar selection
    mode = st.sidebar.radio(
        "Select Dataset to Analyze:",
        ["Price Data", "Portfolio Returns and Weights", "Visualization"]
    )

    if mode == "Portfolio Returns and Weights":
        st.header("Portfolio Returns and Weights")
        st.dataframe(df_port)

        # Required columns
        required = {
            'Stock', 'Return', 'Weights', 'Target Return', 'Target Weights', 'Acquisition_Return'
        }
        if not required.issubset(df_port.columns):
            missing = required - set(df_port.columns)
            st.error("Missing columns: " + ", ".join(missing))
            return

        # Parse percent strings
        parse_pct = lambda col: (
            df_port[col].astype(str).str.rstrip('%').astype(float).div(100).fillna(0)
        )
        curr_ret = parse_pct('Return')
        curr_wts = parse_pct('Weights')
        targ_ret = parse_pct('Target Return')
        targ_wts = parse_pct('Target Weights')
        acq_ret  = parse_pct('Acquisition_Return')

        stocks = df_port['Stock'].astype(str)
        curr_ret.index = curr_wts.index = targ_ret.index = targ_wts.index = acq_ret.index = stocks

        # Align to returns time-series columns
        assets = list(returns_ts.columns)
        missing_assets = [s for s in stocks if s not in assets]
        if missing_assets:
            st.error("Stocks missing in price data: " + ", ".join(missing_assets))
            return

        # Reindex and fill missing with zero
        w_curr = curr_wts.reindex(assets, fill_value=0)
        w_prop = targ_wts.reindex(assets, fill_value=0)
        w_acq  = curr_wts.reindex(assets, fill_value=0)
        r_curr = curr_ret.reindex(assets, fill_value=0)
        r_prop = targ_ret.reindex(assets, fill_value=0)
        r_acq  = acq_ret.reindex(assets, fill_value=0)

        # Compute portfolio time-series returns
        ts_curr = returns_ts.dot(w_curr)
        ts_prop = returns_ts.dot(w_prop)
        ts_acq  = returns_ts.dot(w_acq)

        # Compute summary metrics
        curr_port_return = ts_curr.mean()
        curr_port_risk   = ts_curr.std()
        prop_port_return = ts_prop.mean()
        prop_port_risk   = ts_prop.std()
        acq_port_return  = ts_acq.mean()
        acq_port_risk    = ts_acq.std()

        summary = pd.DataFrame(
            {
                'Acquisition': [acq_port_return, acq_port_risk],
                'Current':     [curr_port_return, curr_port_risk],
                'Proposed':    [prop_port_return, prop_port_risk]
            },
            index=['Portfolio Return', 'Portfolio Risk']
        )

        st.subheader("Portfolio Return and Risk Summary")
        st.dataframe(
            summary.style.format('{:.2%}').set_properties(**{'text-align': 'center'})
        )

    elif mode == "Price Data":
        st.header("Price Data Analysis")

        def show_matrix(df_mat, title):
            st.write(title)
            st.dataframe(df_mat)

        view = st.radio(
            "View:",
            ["Prices", "Daily Returns", "Covariance", "Correlation"]
        )
        if view == "Prices":
            st.dataframe(df_price)
        elif view == "Daily Returns":
            st.dataframe(returns_ts)
        elif view == "Covariance":
            cov = returns_ts.cov()
            show_matrix(cov, "Covariance Matrix")
        else:
            corr = returns_ts.corr()
            show_matrix(corr, "Correlation Matrix")

    else:
        st.header("Portfolio Visualization")
        if 'Stock' not in df_port.columns:
            st.error("'Stock' column is required for visualization.")
            return
        # Value metrics
        val_cols = [c for c in df_port.columns if c in ['Est_Acquisition_Cost', 'Carrying_Cost', 'Market_Value']]
        if val_cols:
            choice = st.selectbox("Value metric:", val_cols)
            st.bar_chart(df_port.set_index('Stock')[choice].astype(float))
        # Return metrics
        ret_cols = [c for c in df_port.columns if c in ['Acquisition_Return', 'Return', 'Target Return']]
        if ret_cols:
            choice = st.selectbox("Return metric:", ret_cols)
            vals = (
                df_port[choice].astype(str).str.rstrip('%').astype(float).div(100)
            )
            vals.index = df_port['Stock']
            st.bar_chart(vals)
