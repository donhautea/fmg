# nvpf_portfolio.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def show_nvpf_portfolio_page():
    # --- Sidebar File Upload ---
    st.sidebar.title("📂 NVPF Portfolio: Contribution vs. Income")
    uploaded_file = st.sidebar.file_uploader("Upload Excel file", type=["xlsx"])

    # --- Theme Option ---
    st.sidebar.markdown("---")
    theme_option = st.sidebar.selectbox("🎨 Select Chart Theme", ["Dark Theme", "Light Theme"])

    # --- Sidebar Toggle for Summary Table ---
    st.sidebar.markdown("---")
    show_summary_table = st.sidebar.checkbox("📊 Show Total Table (in Millions)", value=True)

    # --- Main App Display ---
    st.title("📊 Monthly Breakdown Viewer")
    st.markdown("**Figures are in millions**")

    if uploaded_file:
        try:
            # Read Excel from specified sheet, skip first 2 rows
            df = pd.read_excel(
                uploaded_file,
                sheet_name="Mo_breakdown",
                usecols="A:J",
                skiprows=1
            )

            df.dropna(how='all', inplace=True)

            # Rename columns
            df.columns = [
                "Applicable_Month",
                "Seed_Money_Contribution",
                "Members_Contribution",
                "Total_Contribution",
                "Seed_Money_Income",
                "Members_Income",
                "Total_Income",
                "Seed_Money_Mgt_Fee",
                "Members_Mgt_Fee",
                "Total_Mgt_Fee"
            ]

            # Format Applicable_Month to yyyy-mm-dd (no time)
            df["Applicable_Month"] = pd.to_datetime(df["Applicable_Month"]).dt.strftime("%Y-%m-%d")

            # Numeric copy for charts and summary
            numeric_df = df.copy()
            numeric_df[numeric_df.columns[1:]] = numeric_df[numeric_df.columns[1:]].apply(pd.to_numeric, errors='coerce')

            # Format for display
            formatted_df = df.copy()
            format_cols = formatted_df.columns[1:]
            formatted_df[format_cols] = formatted_df[format_cols].applymap(lambda x: f"{x:,.2f}" if pd.notnull(x) else "")

            # Display Main DataFrame
            st.subheader("📑 Loaded Data from 'Mo_breakdown'")
            st.dataframe(formatted_df, use_container_width=True)

            # --- Main Window Summary Table ---
            if show_summary_table:
                st.subheader("📊 Total Table (in Millions)")

                latest_month = numeric_df["Applicable_Month"].max()
                latest_row = numeric_df[numeric_df["Applicable_Month"] == latest_month]

                # Contributions (latest)
                latest_seed_contrib = latest_row["Seed_Money_Contribution"].values[0]
                latest_members_contrib = latest_row["Members_Contribution"].values[0]
                total_contrib = latest_seed_contrib + latest_members_contrib

                # Cumulative income
                cum_seed_income = numeric_df["Seed_Money_Income"].sum()
                cum_members_income = numeric_df["Members_Income"].sum()
                total_income = cum_seed_income + cum_members_income

                fmt = lambda x: f"{x:,.2f}"

                summary_table = pd.DataFrame({
                    "Contribution Sources": ["Seed Money", "Members", "Total"],
                    "Contributions": [
                        fmt(latest_seed_contrib),
                        fmt(latest_members_contrib),
                        fmt(total_contrib)
                    ],
                    "Income": [
                        fmt(cum_seed_income),
                        fmt(cum_members_income),
                        fmt(total_income)
                    ]
                })

                st.table(summary_table)

            # --- Visualization ---
            if st.sidebar.checkbox("📈 Show Contribution & Income Chart"):
                st.subheader("📊 Contribution vs Income Over Time")

                # Theme-based color palettes
                if theme_option == "Dark Theme":
                    colors = {
                        "Seed_Money_Contribution": "#00FFFF",
                        "Members_Contribution": "#FFD700",
                        "Seed_Money_Income": "#FF69B4",
                        "Members_Income": "#7CFC00",
                        "bgcolor": "#111111",
                        "gridcolor": "#444444",
                        "fontcolor": "white"
                    }
                else:
                    colors = {
                        "Seed_Money_Contribution": "#1f77b4",
                        "Members_Contribution": "#ff7f0e",
                        "Seed_Money_Income": "#2ca02c",
                        "Members_Income": "#d62728",
                        "bgcolor": "white",
                        "gridcolor": "#cccccc",
                        "fontcolor": "black"
                    }

                fig = go.Figure()

                # Line plots - Contribution
                fig.add_trace(go.Scatter(
                    x=numeric_df["Applicable_Month"],
                    y=numeric_df["Seed_Money_Contribution"],
                    mode="lines+markers",
                    name="Seed Money Contribution",
                    yaxis="y1",
                    line=dict(color=colors["Seed_Money_Contribution"])
                ))

                fig.add_trace(go.Scatter(
                    x=numeric_df["Applicable_Month"],
                    y=numeric_df["Members_Contribution"],
                    mode="lines+markers",
                    name="Members Contribution",
                    yaxis="y1",
                    line=dict(color=colors["Members_Contribution"])
                ))

                # Bar plots - Income
                fig.add_trace(go.Bar(
                    x=numeric_df["Applicable_Month"],
                    y=numeric_df["Seed_Money_Income"],
                    name="Seed Money Income",
                    yaxis="y2",
                    marker_color=colors["Seed_Money_Income"],
                    opacity=0.6
                ))

                fig.add_trace(go.Bar(
                    x=numeric_df["Applicable_Month"],
                    y=numeric_df["Members_Income"],
                    name="Members Income",
                    yaxis="y2",
                    marker_color=colors["Members_Income"],
                    opacity=0.6
                ))

                fig.update_layout(
                    xaxis=dict(title="Applicable Month", showgrid=True, gridcolor=colors["gridcolor"]),
                    yaxis=dict(title="Contribution (in millions)", side="left", showgrid=True, gridcolor=colors["gridcolor"]),
                    yaxis2=dict(title="Income (in millions)", overlaying="y", side="right", showgrid=False),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    barmode='group',
                    height=600,
                    plot_bgcolor=colors["bgcolor"],
                    paper_bgcolor=colors["bgcolor"],
                    font=dict(color=colors["fontcolor"])
                )

                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"❌ Error reading Excel file: {e}")
    else:
        st.info("📎 Please upload an Excel (.xlsx) file to begin.")
