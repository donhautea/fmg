import streamlit as st
import pandas as pd
import altair as alt


def show_demographics_page():
    st.header("Excel Sheet Viewer")

    # File uploader
    event_file = st.sidebar.file_uploader(
        label="Upload an Excel file",
        type=["xlsx"]
    )

    if not event_file:
        st.info("Please upload an Excel (.xlsx) file to get started.")
        return

    try:
        excel_data = pd.ExcelFile(event_file)
        sheet_names = excel_data.sheet_names

        view_mode = st.sidebar.radio(
            "View options:",
            ("Summary Dashboard", "Sheet Viewer")
        )

        fill_sheets = [
            "unique_counts_by_age_sex",
            "unique_counts_by_sex_region",
            "unique_counts_by_sex_membership",
            "sum_by_sex_region",
            "sum_by_sex_membership",
            "sum_by_age_sex"
        ]

        if view_mode == "Summary Dashboard":
            # (Insert the existing dashboard code here exactly as in the original,
            # but without `st.set_page_config` and the top-level `st.title`.)
            # E.g., Contribution Pyramid and Count Pyramid sections...
            
            # Contribution Pyramid by Age and Sex
            age_sheet = "sum_by_AGE_SEX"
            if age_sheet in sheet_names:
                df_age = pd.read_excel(event_file, sheet_name=age_sheet)
                if 'SEX2' in df_age.columns:
                    df_age['SEX2'] = df_age['SEX2'].fillna(method='ffill')
                df_age['AGE24_INT'] = pd.to_numeric(df_age['AGE24_INT'], errors='coerce')
                df_age = df_age.dropna(subset=['AGE24_INT'])
                df_age['AGE24_INT'] = df_age['AGE24_INT'].astype(int)
                df_age = df_age[df_age['AGE24_INT'].between(14, 100)]
                df_age['TOTPREM'] = pd.to_numeric(df_age['TOTPREM'], errors='coerce').fillna(0)

                df_pivot = df_age.groupby(['AGE24_INT', 'SEX2'])['TOTPREM'].sum().reset_index()
                df_wide = df_pivot.pivot(index='AGE24_INT', columns='SEX2', values='TOTPREM').fillna(0)
                age_vals = sorted(df_wide.index, reverse=True)
                df_chart = df_wide.reset_index().melt(
                    id_vars='AGE24_INT', var_name='SEX2', value_name='Amount'
                )
                df_chart['Amount'] = df_chart.apply(
                    lambda r: -r['Amount']/1e6 if r['SEX2']=='M' else r['Amount']/1e6,
                    axis=1
                )
                contrib_chart = alt.Chart(df_chart).mark_bar().encode(
                    y=alt.Y('AGE24_INT:O', sort=age_vals, title='Age (years)'),
                    x=alt.X('Amount:Q', title='Total Contribution (Millions)', axis=alt.Axis(format=',.1f')),
                    color=alt.Color('SEX2:N', title='Sex', scale=alt.Scale(domain=['M','F'], range=['steelblue','salmon'])),
                    tooltip=[
                        alt.Tooltip('AGE24_INT:O', title='Age'),
                        alt.Tooltip('SEX2:N', title='Sex'),
                        alt.Tooltip('Amount:Q', title='Contribution (M)', format=',.2f')
                    ]
                ).properties(height=400)
                st.subheader("Contribution Pyramid by Age and Sex")
                st.altair_chart(contrib_chart, use_container_width=True)
                csv_data = df_chart.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Contribution Data as CSV",
                    data=csv_data, file_name="contribution_data.csv", mime="text/csv"
                )

                st.markdown(
                    """
**Investment Officer’s Ladderization Strategy Based on Age-Sex Demographics:**

- **Targeted Maturity Buckets:** Align ladder dates to concentration in ages 25–35 where contributions peak.
- **Duration Tilt by Cohort:** Assign longer-duration bonds to younger contributors (<25) and shorter-duration (<5 years) to older cohorts (45–60).
- **Gender-Aware Staging:** Schedule maturities reflecting slight gender-peaks to optimize cash flows for each group.
- **Liquidity Matching:** Use demographic bulges to time coupon receipts, ensuring liquidity for benefit payouts as members retire.
"""
                )
            else:
                st.warning(f"Sheet '{age_sheet}' not found.")

            # Contributor Count Pyramid by Age and Sex
            count_sheet = "Unique_Counts_by_AGE_SEX"
            if count_sheet in sheet_names:
                df_count = pd.read_excel(event_file, sheet_name=count_sheet)
                if 'SEX2' in df_count.columns:
                    df_count['SEX2'] = df_count['SEX2'].fillna(method='ffill')
                df_count['AGE24_INT'] = pd.to_numeric(df_count['AGE24_INT'], errors='coerce')
                df_count = df_count.dropna(subset=['AGE24_INT'])
                df_count['AGE24_INT'] = df_count['AGE24_INT'].astype(int)
                df_count = df_count[df_count['AGE24_INT'].between(14, 100)]
                df_count['SSNUM'] = pd.to_numeric(df_count['SSNUM'], errors='coerce').fillna(0)

                df_pivot2 = df_count.groupby(['AGE24_INT', 'SEX2'])['SSNUM'].sum().reset_index()
                df_wide2 = df_pivot2.pivot(index='AGE24_INT', columns='SEX2', values='SSNUM').fillna(0)
                age_vals2 = sorted(df_wide2.index, reverse=True)
                df_chart2 = df_wide2.reset_index().melt(
                    id_vars='AGE24_INT', var_name='SEX2', value_name='Count'
                )
                df_chart2['Count'] = df_chart2.apply(
                    lambda r: -r['Count']/1e3 if r['SEX2']=='M' else r['Count']/1e3,
                    axis=1
                )
                count_chart = alt.Chart(df_chart2).mark_bar().encode(
                    y=alt.Y('AGE24_INT:O', sort=age_vals2, title='Age (years)'),
                    x=alt.X('Count:Q', title='Number of Contributors (Thousands)', axis=alt.Axis(format=',.1f')),
                    color=alt.Color('SEX2:N', title='Sex', scale=alt.Scale(domain=['M','F'], range=['steelblue','salmon'])),
                    tooltip=[
                        alt.Tooltip('AGE24_INT:O', title='Age'),
                        alt.Tooltip('SEX2:N', title='Sex'),
                        alt.Tooltip('Count:Q', title='Contributors (K)', format=',.2f')
                    ]
                ).properties(height=400)
                st.subheader("Contributor Count Pyramid by Age and Sex (Thousands)")
                st.altair_chart(count_chart, use_container_width=True)
                csv_data2 = df_chart2.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Contributor Count Data as CSV",
                    data=csv_data2, file_name="contributor_count_data.csv", mime="text/csv"
                )

                st.markdown(
                    """
**Investment Officer’s Contributor Engagement Strategy:**

- **Early Retention Focus:** With counts peaking in ages 30–40, tailor communication and incentives to retain this core base into late career.
- **Re-Engagement Programs:** As counts taper post-45, introduce refresher campaigns or product features (e.g., top-up options) to sustain contribution levels.
- **Gender-Specific Outreach:** Leverage slight gender peaks by targeting cohort-specific messaging and benefits.
- **Risk Mitigation:** Anticipate lower participation near retirement by allocating liquid assets for benefit disbursements.
"""
                )
            else:
                st.warning(f"Sheet '{count_sheet}' not found.")

        else:
            # Sheet Viewer mode
            selected_sheet = st.sidebar.selectbox("Select a sheet to display:", sheet_names)
            df = pd.read_excel(event_file, sheet_name=selected_sheet)
            if selected_sheet.lower() in fill_sheets and 'SEX2' in df.columns:
                df['SEX2'] = df['SEX2'].fillna(method='ffill')
            st.subheader(f"Sheet: {selected_sheet}")
            numeric_cols = df.select_dtypes(include='number').columns.tolist()
            if numeric_cols:
                formatter = {col: '{:,.0f}' for col in numeric_cols}
                st.dataframe(df.style.format(formatter, na_rep=''))
            else:
                st.dataframe(df)
    except Exception as e:
        st.error(f"Error reading Excel file: {e}")