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
        # Clean column names to avoid whitespace and BOM issues
        df_port.columns = df_port.columns.str.strip()
        # Rename common variants to match expected names
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

    # Prepare price dataset if available
    if not df_price.empty and 'Date' in df_price.columns:
        df = df_price.copy()
        date_col = df['Date']
        price_df = df.drop(columns=['Date'])
        price_df = price_df.replace(r'[₱,]', '', regex=True)
        price_df = price_df.apply(pd.to_numeric, errors='coerce').dropna(axis=1, how='all')
        # Compute returns and stats
        raw_returns = price_df.pct_change().fillna(0).reset_index(drop=True)
        returns_only = raw_returns.copy()
        mean_vals = returns_only.mean()
        excess_vals = returns_only.sub(mean_vals)
        N = len(returns_only)
        cov_df = excess_vals.T.dot(excess_vals) / N
        stats_var = excess_vals.pow(2).mean()
        stats_std = stats_var.pow(0.5)
    else:
        # Initialize empty structures
        raw_returns = returns_only = cov_df = stats_var = stats_std = pd.DataFrame()
        N = 0
        date_col = None

    # Dataset selection
    dataset_choice = st.sidebar.radio(
        "Select Dataset to Analyze:",
        ["Price Data", "Portfolio Returns and Weights", "Visualization"]
    )

    if dataset_choice == "Portfolio Returns and Weights":
        st.header("Portfolio Returns and Weights")
        st.dataframe(df_port)

        required_cols = {
            'Stock', 'Return', 'Weights',
            'Target Return', 'Target Weights', 'Acquisition_Return'
        }
        # Strip whitespace on column names again before checking
        df_port.columns = df_port.columns.str.strip()
        if required_cols.issubset(df_port.columns):
            try:
                curr_ret = df_port['Return'].str.rstrip('%').astype(float) / 100
                curr_wts = df_port['Weights'].str.rstrip('%').astype(float) / 100
                targ_ret = df_port['Target Return'].str.rstrip('%').astype(float) / 100
                targ_wts = df_port['Target Weights'].str.rstrip('%').astype(float) / 100
                acq_ret = df_port['Acquisition_Return'].str.rstrip('%').astype(float) / 100
            except Exception as e:
                st.error(f"Data conversion error: {e}")
                st.stop()

            stocks = df_port['Stock'].astype(str)
            curr_ret.index = stocks
            curr_wts.index = stocks
            targ_ret.index = stocks
            targ_wts.index = stocks
            acq_ret.index = stocks

            curr_port_return = curr_ret.dot(curr_wts)
            acq_port_return = acq_ret.dot(curr_wts)
            prop_port_return = targ_ret.dot(targ_wts)

            assets = returns_only.columns.tolist()
            curr_wts = curr_wts.reindex(assets)
            targ_wts = targ_wts.reindex(assets)

            if curr_wts.isnull().any() or targ_wts.isnull().any():
                st.error(
                    "Portfolio weights contain missing values after reindexing."
                    " Check stock names alignment with price CSV."
                )
            else:
                aligned_curr_wts = curr_wts.values
                aligned_targ_wts = targ_wts.values
                aligned_acq_wts = aligned_curr_wts

                curr_port_var = aligned_curr_wts.dot(cov_df.values).dot(aligned_curr_wts)
                prop_port_var = aligned_targ_wts.dot(cov_df.values).dot(aligned_targ_wts)
                acq_port_var = aligned_acq_wts.dot(cov_df.values).dot(aligned_acq_wts)

                curr_port_risk = np.sqrt(curr_port_var * N)
                prop_port_risk = np.sqrt(prop_port_var * N)
                acq_port_risk = np.sqrt(acq_port_var * N)

                summary_df = pd.DataFrame({
                    'Acquisition': [acq_port_return, acq_port_risk],
                    'Current':     [curr_port_return, curr_port_risk],
                    'Proposed':    [prop_port_return, prop_port_risk]
                }, index=['Portfolio Return', 'Portfolio Risk'])

                st.subheader("Portfolio Return and Risk Summary")
                styled_summary = summary_df.style.format({
                    'Acquisition': '{:.2%}',
                    'Current':     '{:.2%}',
                    'Proposed':    '{:.2%}'
                }).set_properties(**{'text-align': 'center'}).set_table_styles([
                    {'selector': 'th', 'props': [('text-align', 'center')]}
                ])
                st.dataframe(styled_summary)
        else:
            st.error("Required columns not found in portfolio dataset."
                     " Ensure your CSV has: " + ", ".join(required_cols))

    elif dataset_choice == "Price Data":
        st.header("Price Data Analysis")

        def attach_date(df_attach):
            if date_col is not None and 'Date' not in df_attach.columns:
                df_attach.insert(0, 'Date', date_col.values[:len(df_attach)])
            return df_attach

        daily_returns = attach_date(raw_returns.copy())

        st.subheader("Display Options for Price Data")
        view_option = st.radio(
            "View:",
            [
                "Prices", "Daily Returns", "Excess Returns",
                "Covariance Matrix", "Correlation Matrix", "Statistics"
            ]
        )

        if view_option == "Prices":
            st.dataframe(attach_date(price_df.copy()))
        elif view_option == "Daily Returns":
            st.dataframe(daily_returns.iloc[1:].reset_index(drop=True))
        elif view_option == "Excess Returns":
            st.dataframe(attach_date(excess_vals.reset_index(drop=True)))
        elif view_option == "Covariance Matrix":
            st.write(f"Covariance Matrix (E^T E / N), N={N}")
            st.dataframe(cov_df)
        elif view_option == "Correlation Matrix":
            outer_std = np.outer(stats_std, stats_std)
            corr_df = pd.DataFrame(
                cov_df.values / outer_std,
                index=returns_only.columns,
                columns=returns_only.columns
            )
            st.write(f"Correlation Matrix, N={N}")
            st.dataframe(corr_df)
        elif view_option == "Statistics":
            stats_df = pd.DataFrame({
                'Average Return': mean_vals,
                'Variance': stats_var,
                'StdDev': stats_std
            })
            st.dataframe(stats_df)

    else:
        st.header("Portfolio Visualization")
        if 'Stock' in df_port.columns:
            st.subheader("Value Metrics")
            value_metrics = [m for m in ['Est_Acquisition_Cost', 'Carrying_Cost', 'Market_Value'] if m in df_port.columns]
            if value_metrics:
                value_metric = st.radio("Select value metric to plot:", value_metrics)
                val_series = df_port.set_index('Stock')[value_metric].astype(float)
                st.bar_chart(val_series)
            st.subheader("Return Metrics")
            return_metrics = [m for m in ['Acquisition_Return', 'Return', 'Target Return'] if m in df_port.columns]
            if return_metrics:
                return_metric = st.radio("Select return metric to plot:", return_metrics)
                ret_series = df_port[return_metric]
                if return_metric in ['Acquisition_Return', 'Return', 'Target Return']:
                    ret_series = ret_series.astype(str).str.rstrip('%').astype(float) / 100
                ret_series.index = df_port['Stock']
                st.bar_chart(ret_series)
        else:
            st.error("'Stock' column is required in portfolio dataset for visualization.")
