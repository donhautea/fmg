import streamlit as st
import pandas as pd
import re
import matplotlib.pyplot as plt
import io

def show_coupon_maturity_summary_page():
    st.title("📊 Monthly GS & CBN Coupon and Maturities Summary")

    uploaded_files = st.sidebar.file_uploader("Upload CSV files", type=["csv"], accept_multiple_files=True)
    display_mode = st.sidebar.radio("Display Figures In:", ["Actual", "Millions"])

    def scale(value):
        return value / 1_000_000 if display_mode == "Millions" else value

    def match_file(keyword):
        for file in uploaded_files:
            if re.search(keyword, file.name, re.IGNORECASE):
                return file
        return None

    def load_and_sum_by_month(uploaded_file, date_col, amount_cols):
        if uploaded_file is None:
            return pd.Series(dtype='float64')
        
        df = pd.read_csv(uploaded_file)

        # Only use columns that exist in the file
        available_cols = [col for col in amount_cols if col in df.columns]
        if not available_cols:
            return pd.Series(dtype='float64')

        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])
        df['Month'] = df[date_col].dt.to_period('M')
        df['Total'] = df[available_cols].sum(axis=1)
        return df.groupby('Month')['Total'].sum()

    # Match files
    coupon_gs_php = match_file("coupon.*gs.*php")
    coupon_gs_usd = match_file("coupon.*gs.*usd")
    coupon_cbn_php = match_file("coupon.*cbn.*php")
    coupon_cbn_usd = match_file("coupon.*cbn.*usd")
    maturity_gs_php = match_file("maturit.*gs.*php")
    maturity_gs_usd = match_file("maturit.*gs.*usd")
    maturity_cbn_php = match_file("maturit.*cbn.*php")
    maturity_cbn_usd = match_file("maturit.*cbn.*usd")

    # Load series
    gs_coupon_php_series = load_and_sum_by_month(coupon_gs_php, "Coupon_Payment_Date",
        ["Coupon_Payment_EC", "Coupon_Payment_FLEXI", "Coupon_Payment_MIA",
         "Coupon_Payment_MPF", "Coupon_Payment_NVPF", "Coupon_Payment_PESO", "Coupon_Payment_SSS"])

    gs_coupon_usd_series = load_and_sum_by_month(coupon_gs_usd, "Coupon_Payment_Date",
        ["Coupon_Payment_EC", "Coupon_Payment_MPF", "Coupon_Payment_SSS"])

    cbn_coupon_php_series = load_and_sum_by_month(coupon_cbn_php, "Coupon_Payment_Date",
        ["Coupon_Payment_EC", "Coupon_Payment_FLEXI", "Coupon_Payment_MIA",
         "Coupon_Payment_MPF", "Coupon_Payment_NVPF", "Coupon_Payment_SSS"])

    cbn_coupon_usd_series = load_and_sum_by_month(coupon_cbn_usd, "Coupon_Payment_Date",
        ["Coupon_Payment_EC", "Coupon_Payment_MPF", "Coupon_Payment_SSS"])

    gs_maturity_php_series = load_and_sum_by_month(maturity_gs_php, "Maturity_Date",
        ["Face_Amount_SSS", "Face_Amount_EC", "Face_Amount_FLEXI",
         "Face_Amount_PESO", "Face_Amount_MIA", "Face_Amount_MPF", "Face_Amount_NVPF"])

    gs_maturity_usd_series = load_and_sum_by_month(maturity_gs_usd, "Maturity_Date",
        ["Face_Amount_SSS", "Face_Amount_EC", "Face_Amount_FLEXI",
         "Face_Amount_PESO", "Face_Amount_MIA", "Face_Amount_MPF", "Face_Amount_NVPF"])

    cbn_maturity_php_series = load_and_sum_by_month(maturity_cbn_php, "Maturity_Date",
        ["SSS_Outstanding", "EC_Outstanding", "FLEXI_Outstanding",
         "MIA_Outstanding", "MPF_Outstanding", "NVPF_Outstanding"])

    cbn_maturity_usd_series = load_and_sum_by_month(maturity_cbn_usd, "Maturity_Date",
        ["SSS_Outstanding", "EC_Outstanding", "FLEXI_Outstanding",
         "MIA_Outstanding", "MPF_Outstanding", "NVPF_Outstanding"])

    # Combine series
    gs_coupon = gs_coupon_php_series.add(gs_coupon_usd_series, fill_value=0).rename("GS Coupon")
    cbn_coupon = cbn_coupon_php_series.add(cbn_coupon_usd_series, fill_value=0).rename("CBN Coupon")
    total_coupon = gs_coupon.add(cbn_coupon, fill_value=0).rename("Total Coupon")
    cumulative_coupon = total_coupon.cumsum().rename("Cumulative Coupon")

    gs_maturity = gs_maturity_php_series.add(gs_maturity_usd_series, fill_value=0).rename("GS Maturity")
    cbn_maturity = cbn_maturity_php_series.add(cbn_maturity_usd_series, fill_value=0).rename("CBN Maturity")
    total_maturity = gs_maturity.add(cbn_maturity, fill_value=0).rename("Total Maturity")
    cumulative_maturity = total_maturity.cumsum().rename("Cumulative Maturity")

    total_coupon_maturity = total_coupon.add(total_maturity, fill_value=0).rename("Total Coupon + Maturity")
    cumulative_coupon_maturity = total_coupon_maturity.cumsum().rename("Cumulative Total")

    # Create final DataFrame
    summary_df = pd.concat([
        gs_coupon, cbn_coupon, total_coupon, cumulative_coupon,
        gs_maturity, cbn_maturity, total_maturity, cumulative_maturity,
        total_coupon_maturity, cumulative_coupon_maturity
    ], axis=1).fillna(0)

    summary_df.index = summary_df.index.astype(str)
    scaled_df = summary_df.applymap(scale)

    # Display in app
    table_title = f"📋 Summary Table (Figures in {'Millions' if display_mode == 'Millions' else 'Actual'})"
    st.subheader(table_title)
    st.dataframe(scaled_df.style.format("{:,.2f}"), use_container_width=True)

    # 📥 CSV Export
    csv = scaled_df.reset_index().to_csv(index=False).encode("utf-8")
    st.download_button("📥 Download Table as CSV", csv, file_name="coupon_maturity_summary.csv", mime="text/csv")

    # 🖼️ PNG Export
    if st.button("🖼️ Download Table as PNG"):
        formatted_df = scaled_df.copy().applymap(lambda x: f"{x:,.2f}")
        formatted_df.insert(0, "Month", formatted_df.index)

        # Define column groups
        coupon_cols = ["GS Coupon", "CBN Coupon", "Total Coupon", "Cumulative Coupon"]
        maturity_cols = ["GS Maturity", "CBN Maturity", "Total Maturity", "Cumulative Maturity"]
        combined_cols = ["Total Coupon + Maturity", "Cumulative Total"]

        coupon_df = formatted_df[["Month"] + coupon_cols]
        maturity_df = formatted_df[["Month"] + maturity_cols]
        combined_df = formatted_df[["Month"] + combined_cols]

        row_height = 0.25
        fig_height = len(formatted_df) * row_height + 6
        fig, ax = plt.subplots(figsize=(16, fig_height))
        ax.axis("off")

        mode_label = "(Figures in Millions)" if display_mode == "Millions" else "(Figures in Actual)"

        def draw_table_and_title(ax, df, title, y_offset):
            ax.text(0, y_offset, f"{title} {mode_label}", fontsize=14, fontweight='bold', ha='left', va='bottom')
            table = ax.table(
                cellText=df.values,
                colLabels=df.columns,
                cellLoc='center',
                loc='upper center',
                bbox=[0, y_offset - 0.22, 1, 0.2]
            )
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1, 1.2)

        y_start = 0.95
        spacing = 0.33

        draw_table_and_title(ax, coupon_df, "📘 Coupon Summary", y_start)
        draw_table_and_title(ax, maturity_df, "📙 Maturity Summary", y_start - spacing)
        draw_table_and_title(ax, combined_df, "📗 Total Coupon + Maturity Summary", y_start - spacing * 2)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=300)
        st.image(buf, caption="Segmented Summary Table as PNG", use_column_width=True)
        st.download_button("Download PNG", data=buf.getvalue(), file_name="coupon_maturity_summary_segmented.png", mime="image/png")

    # 📈 Chart Visualization
    st.subheader("📈 Visualize Trends")

    chart_type = st.selectbox(
        "Select Chart Type:",
        ["Line", "Bar", "Scatter"]
    )

    chart_options = st.multiselect(
        "Select values to plot:",
        ["Total Coupon", "Total Maturity", "Total Coupon + Maturity"],
        default=["Total Coupon", "Total Maturity"]
    )

    if chart_options:
        chart_df = scaled_df[chart_options].copy()
        chart_df['Month'] = chart_df.index

        if chart_type == "Line":
            st.line_chart(chart_df.set_index("Month"))
        elif chart_type == "Bar":
            st.bar_chart(chart_df.set_index("Month"))
        elif chart_type == "Scatter":
            import altair as alt
            # Melt data for Altair plotting
            melted = chart_df.melt(id_vars='Month', var_name='Metric', value_name='Value')
            scatter = alt.Chart(melted).mark_circle(size=60).encode(
                x='Month:T',
                y='Value:Q',
                color='Metric:N',
                tooltip=['Month:T', 'Metric:N', 'Value:Q']
            ).interactive().properties(height=400)
            st.altair_chart(scatter, use_container_width=True)
