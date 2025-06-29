# collection_compare.py
import streamlit as st
import pandas as pd
import re

def show_collection_compare_page():
    """
    Compare Total Amount and Number by Payment Date or Month
    """
    st.title("Compare Total Amount and Number by Payment Date or Month")

    # Sidebar file uploader
    uploaded_files = st.sidebar.file_uploader(
        "Upload exactly two CSV files",
        type=["csv"],
        accept_multiple_files=True,
        key="collection_compare_files"
    )

    enable_analysis = uploaded_files and len(uploaded_files) >= 2
    view_option = st.sidebar.radio(
        "View",
        options=["All", "Differences Only"],
        disabled=not enable_analysis,
        key="collection_compare_view"
    )

    tag_option = st.sidebar.radio(
        "Aggregate by",
        options=["Daily", "Monthly"],
        disabled=not enable_analysis,
        key="collection_compare_aggregate"
    )

    if uploaded_files:
        if len(uploaded_files) < 2:
            st.warning("Please upload exactly two CSV files to compare.")
            return

        group_dfs = []
        labels = []

        # Process up to two files
        for file in uploaded_files[:2]:
            name = file.name
            m = re.search(r"(\d{4}-\d{2}-\d{2})", name)
            lbl = m.group(1) if m else name
            labels.append(lbl)

            df = pd.read_csv(file)
            for col in ["Payment_Date", "Total_Amount", "Total_Num"]:
                if col not in df.columns:
                    st.error(f"Missing column '{col}' in {name}")
                    return

            # Parse and format date
            df['Payment_Date'] = pd.to_datetime(
                df['Payment_Date'], errors='coerce'
            ).dt.date.astype(str)

            # Ensure numeric
            df['Total_Amount'] = pd.to_numeric(
                df['Total_Amount'].astype(str).str.replace(',', ''),
                errors='coerce'
            ).fillna(0)
            df['Total_Num'] = pd.to_numeric(
                df['Total_Num'].astype(str).str.replace(',', ''),
                errors='coerce'
            ).fillna(0)

            # Group by date or month
            base = df.groupby('Payment_Date').agg({
                'Total_Amount': 'sum',
                'Total_Num': 'sum'
            }).reset_index()

            if tag_option == 'Monthly':
                base['Period'] = base['Payment_Date'].str[:7]
                base = base.groupby('Period').agg({
                    'Total_Amount': 'sum',
                    'Total_Num': 'sum'
                }).reset_index()
            else:
                base = base.rename(columns={'Payment_Date': 'Period'})

            # Rename for clarity
            base = base.rename(columns={
                'Total_Amount': f"Total_Amount_{labels[-1]}",
                'Total_Num': f"Total_Num_{labels[-1]}"
            })
            group_dfs.append(base)

        # Merge the two dataframes
        left = group_dfs[0]
        right = group_dfs[1]
        comp = pd.merge(left, right, on='Period', how='outer').fillna(0)

        a0 = f"Total_Amount_{labels[0]}"
        a1 = f"Total_Amount_{labels[1]}"
        n0 = f"Total_Num_{labels[0]}"
        n1 = f"Total_Num_{labels[1]}"

        # Calculate differences
        comp['Diff_Amount'] = comp[a1] - comp[a0]
        comp['Diff_Num'] = comp[n1] - comp[n0]
        comp['Pct_Amount'] = comp['Diff_Amount'] / comp[a0].replace({0: pd.NA}) * 100
        comp['Pct_Num'] = comp['Diff_Num'] / comp[n0].replace({0: pd.NA}) * 100

        comp = comp.sort_values('Period').set_index('Period')

        # Filter by view
        if view_option == 'Differences Only':
            df_disp = comp[(comp['Diff_Amount'] != 0) | (comp['Diff_Num'] != 0)]
        else:
            df_disp = comp

        # Styling
        fmt_dict = {col: '{:,.0f}' for col in [a0, a1, n0, n1, 'Diff_Amount', 'Diff_Num']}
        fmt_dict.update({'Pct_Amount': '{:.1f}%', 'Pct_Num': '{:.1f}%'})
        styled = df_disp.style.format(fmt_dict)

        # Display
        st.subheader('Comparison Table')
        st.dataframe(styled)
        st.subheader('Total Amount Comparison')
        st.line_chart(df_disp[[a0, a1]])
        st.subheader('Total Number Comparison')
        st.line_chart(df_disp[[n0, n1]])
        st.subheader('Difference in Amount')
        st.bar_chart(df_disp['Diff_Amount'])
        st.subheader('Difference in Number')
        st.bar_chart(df_disp['Diff_Num'])
        st.subheader('Percent Change in Amount')
        st.line_chart(df_disp['Pct_Amount'])
        st.subheader('Percent Change in Number')
        st.line_chart(df_disp['Pct_Num'])
