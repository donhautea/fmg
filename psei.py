# psei.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def compute_rsi(series, window=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def show_psei_page():
    st.title("PSEI Technical Indicator Visualizer")
    st.sidebar.header("Upload CSV File")
    uploaded_file = st.sidebar.file_uploader("Choose a CSV file", type=["csv"])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            text = uploaded_file.read().decode('utf-8')
            rows = [r.split(',') for r in text.splitlines()]
            df = pd.DataFrame(rows)
            st.warning(f"Fallback parse used due to: {e}")

        if 'Date' in df.columns:
            try:
                df['Date'] = pd.to_datetime(df['Date']).dt.date  # convert to date only
            except Exception:
                st.warning("Unable to convert 'Date' to datetime.")
        else:
            st.error("Data must include a 'Date' column.")
            return

        df = df.sort_values('Date').reset_index(drop=True)

        if pd.api.types.is_datetime64_any_dtype(pd.to_datetime(df['Date'])):
            st.sidebar.header("Date Range")
            start, end = st.sidebar.date_input(
                "Select Date Range", [df['Date'].min(), df['Date'].max()]
            )
            if isinstance(start, (list, tuple)):
                start, end = start
            df = df[(df['Date'] >= start) & (df['Date'] <= end)]

        st.subheader("Data Preview")
        df_display = df.copy()
        df_display['Date'] = df_display['Date'].astype(str)  # ensure yyyy-mm-dd as string
        st.dataframe(df_display)

        if {'Date', 'Close', 'High', 'Low'}.issubset(df.columns):
            df['Year'] = pd.to_datetime(df['Date']).dt.year
            latest_year = df['Year'].max()

            year_ends = []
            for year, group in df.groupby('Year'):
                last_row = group.iloc[-1].copy()
                if year != latest_year:
                    last_row['Date'] = pd.to_datetime(f"{year}-12-31").date()
                year_ends.append(last_row)
            year_end_df = pd.DataFrame(year_ends)

            yearly = year_end_df[['Date', 'Year', 'Close']].copy()
            yearly['Prev Close'] = yearly['Close'].shift(1)
            yearly['Yearly Change (%)'] = (yearly['Close'] / yearly['Prev Close'] - 1) * 100

            yearly_high = df.groupby('Year')['High'].max()
            yearly_low = df.groupby('Year')['Low'].min()

            yearly_summary = pd.merge(yearly, yearly_high.rename('Highest High'), on='Year')
            yearly_summary = pd.merge(yearly_summary, yearly_low.rename('Lowest Low'), on='Year')
            yearly_summary['Date'] = yearly_summary['Date'].astype(str)

            st.header("📈 Yearly Summary with Last Close and Change")
            st.dataframe(yearly_summary[['Year', 'Date', 'Close', 'Prev Close', 'Yearly Change (%)', 'Highest High', 'Lowest Low']])

            st.subheader("Yearly Return Trend")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=yearly_summary['Year'],
                y=yearly_summary['Yearly Change (%)'],
                mode='lines+markers',
                name='Annual Return'
            ))
            fig.add_shape(type='line', x0=yearly_summary['Year'].min(), x1=yearly_summary['Year'].max(), y0=0, y1=0,
                          line=dict(color='red', width=3))
            fig.update_layout(xaxis_title='Year', yaxis_title='Yearly Change (%)', showlegend=False)
            st.plotly_chart(fig)

        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        st.sidebar.header("Chart Options")
        chart_option = st.sidebar.selectbox("Chart Type", ["Line Chart", "Candlestick"])
        indicators = st.sidebar.multiselect("Select Technical Indicators", ['RSI', 'Stochastic', 'MACD', 'DMI'])

        if chart_option == 'Line Chart':
            cols = st.sidebar.multiselect("Columns to plot", numeric_cols, default=numeric_cols[:1])
            if cols:
                st.line_chart(df.set_index(pd.to_datetime(df['Date']))[cols])
            else:
                st.warning("Select at least one numeric column.")
        else:
            req = {'Open', 'High', 'Low', 'Close'}
            if req.issubset(df.columns):
                fig2 = go.Figure(data=[go.Candlestick(x=pd.to_datetime(df['Date']), open=df['Open'],
                                                     high=df['High'], low=df['Low'], close=df['Close'])])
                fig2.update_layout(xaxis_rangeslider_visible=False)
                st.plotly_chart(fig2)
            else:
                st.error("Candlestick requires 'Open', 'High', 'Low', 'Close'.")

        if indicators:
            st.header("Technical Indicators")
            df = df.sort_values('Date').reset_index(drop=True)

            if 'RSI' in indicators and 'Close' in df.columns:
                df['RSI'] = compute_rsi(df['Close'])
                st.subheader('RSI (14)')
                st.line_chart(df.set_index(pd.to_datetime(df['Date']))['RSI'])

            if 'Stochastic' in indicators and {'High', 'Low', 'Close'}.issubset(df.columns):
                low14 = df['Low'].rolling(14).min()
                high14 = df['High'].rolling(14).max()
                df['%K'] = (df['Close'] - low14) / (high14 - low14) * 100
                df['%D'] = df['%K'].rolling(3).mean()
                st.subheader('Stochastic (%K and %D)')
                st.line_chart(df.set_index(pd.to_datetime(df['Date']))[['%K', '%D']])

            if 'MACD' in indicators and 'Close' in df.columns:
                exp12 = df['Close'].ewm(span=12, adjust=False).mean()
                exp26 = df['Close'].ewm(span=26, adjust=False).mean()
                df['MACD'] = exp12 - exp26
                df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
                st.subheader('MACD and Signal')
                st.line_chart(df.set_index(pd.to_datetime(df['Date']))[['MACD', 'Signal']])
                df['Hist'] = df['MACD'] - df['Signal']
                st.subheader('MACD Histogram')
                st.bar_chart(df.set_index(pd.to_datetime(df['Date']))['Hist'])

            if 'DMI' in indicators and {'High', 'Low', 'Close'}.issubset(df.columns):
                prev_close = df['Close'].shift(1)
                df['TR'] = df.apply(lambda row: max(
                    row['High'] - row['Low'], abs(row['High'] - prev_close.loc[row.name]), abs(row['Low'] - prev_close.loc[row.name])
                ), axis=1)
                df['+DM'] = df['High'].diff().clip(lower=0)
                df['-DM'] = df['Low'].diff().clip(upper=0).abs()
                tr14 = df['TR'].rolling(14).sum()
                plus_dm14 = df['+DM'].rolling(14).sum()
                minus_dm14 = df['-DM'].rolling(14).sum()
                df['+DI'] = 100 * plus_dm14 / tr14
                df['-DI'] = 100 * minus_dm14 / tr14
                st.subheader('DMI (+DI and -DI)')
                st.line_chart(df.set_index(pd.to_datetime(df['Date']))[['+DI', '-DI']])

        df_export = df.copy()
        df_export['Date'] = df_export['Date'].astype(str)
        csv_data = df_export.to_csv(index=False).encode('utf-8')
        st.download_button("Download Processed CSV", data=csv_data, file_name='processed_data.csv')
