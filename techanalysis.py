import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# Indicator calculation functions
def compute_rsi(series, window=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def show_techanalysis_page():
    st.set_page_config(page_title="CSV Loader & Technical Charts", layout="wide")
    st.title("CSV File Loader and Technical Indicator Visualizer")

    # Sidebar: file upload
    st.sidebar.header("Upload CSV File")
    uploaded_file = st.sidebar.file_uploader("Choose a CSV file", type=["csv"])

    if uploaded_file is not None:
        # Load data
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            text = uploaded_file.read().decode('utf-8')
            rows = [r.split(',') for r in text.splitlines()]
            df = pd.DataFrame(rows)
            st.warning(f"Fallback parse used due to: {e}")

        # Parse dates
        if 'Date' in df.columns:
            try:
                df['Date'] = pd.to_datetime(df['Date'])
            except Exception:
                st.warning("Unable to convert 'Date' to datetime.")
        else:
            st.error("Data must include a 'Date' column.")
            return

        # Filter by date range
        if pd.api.types.is_datetime64_any_dtype(df['Date']):
            st.sidebar.header("Date Range")
            start, end = st.sidebar.date_input(
                "Select Date Range", [df['Date'].min().date(), df['Date'].max().date()]
            )
            if isinstance(start, (list, tuple)):
                start, end = start
            df = df[(df['Date'] >= pd.to_datetime(start)) & (df['Date'] <= pd.to_datetime(end))]

        # Display data preview
        st.subheader("Data Preview")
        st.dataframe(df)

        # Yearly performance analysis
        if {'Date', 'Close', 'High', 'Low'}.issubset(df.columns):
            df = df.sort_values('Date').reset_index(drop=True)
            df['Year'] = df['Date'].dt.year
            # Last close per year
            last_close = df.groupby('Year')['Close'].last()
            # Annual return = last_close_this_year / last_close_prev_year - 1
            annual_return = last_close / last_close.shift(1) - 1
            # High and low per year
            yearly_high = df.groupby('Year')['High'].max()
            yearly_low = df.groupby('Year')['Low'].min()
            # Combine into DataFrame
            yearly = pd.DataFrame({
                'Yearly Return (%)': annual_return * 100,
                'Highest High': yearly_high,
                'Lowest Low': yearly_low
            }).dropna()

            st.header("Yearly Analysis")
            st.dataframe(yearly)

            # Plot yearly return trend with bold zero axis in red
            st.subheader("Yearly Return Trend")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=yearly.index,
                y=yearly['Yearly Return (%)'],
                mode='lines+markers',
                name='Annual Return'
            ))
            fig.add_shape(
                type='line',
                x0=yearly.index.min(),
                x1=yearly.index.max(),
                y0=0,
                y1=0,
                line=dict(color='red', width=3)
            )
            fig.update_layout(
                xaxis_title='Year',
                yaxis_title='Yearly Return (%)',
                showlegend=False
            )
            st.plotly_chart(fig)

        # Chart and indicator options
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        st.sidebar.header("Chart Options")
        chart_option = st.sidebar.selectbox("Chart Type", ["Line Chart", "Candlestick"])
        indicators = st.sidebar.multiselect(
            "Select Technical Indicators", ['RSI', 'Stochastic', 'MACD', 'DMI']
        )

        # Render main price/chart view
        if chart_option == 'Line Chart':
            if 'Date' in df.columns and numeric_cols:
                cols = st.sidebar.multiselect(
                    "Columns to plot", numeric_cols, default=numeric_cols[:1]
                )
                if cols:
                    st.line_chart(df.set_index('Date')[cols])
                else:
                    st.warning("Select at least one numeric column.")
            else:
                st.error("Line Chart requires numeric data and 'Date'.")
        else:
            req = {'Open', 'High', 'Low', 'Close'}
            if req.issubset(df.columns):
                fig2 = go.Figure(data=[
                    go.Candlestick(
                        x=df['Date'], open=df['Open'], high=df['High'],
                        low=df['Low'], close=df['Close']
                    )
                ])
                fig2.update_layout(xaxis_rangeslider_visible=False)
                st.plotly_chart(fig2)
            else:
                st.error("Candlestick requires 'Open', 'High', 'Low', 'Close'.")

        # Compute and render indicators
        if indicators:
            st.header("Technical Indicators")
            df = df.sort_values('Date').reset_index(drop=True)

            if 'RSI' in indicators and 'Close' in df.columns:
                df['RSI'] = compute_rsi(df['Close'])
                st.subheader('RSI (14)')
                st.line_chart(df.set_index('Date')['RSI'])

            if 'Stochastic' in indicators and {'High', 'Low', 'Close'}.issubset(df.columns):
                low14 = df['Low'].rolling(14).min()
                high14 = df['High'].rolling(14).max()
                df['%K'] = (df['Close'] - low14) / (high14 - low14) * 100
                df['%D'] = df['%K'].rolling(3).mean()
                st.subheader('Stochastic (%K and %D)')
                st.line_chart(df.set_index('Date')[['%K', '%D']])

            if 'MACD' in indicators and 'Close' in df.columns:
                exp12 = df['Close'].ewm(span=12, adjust=False).mean()
                exp26 = df['Close'].ewm(span=26, adjust=False).mean()
                df['MACD'] = exp12 - exp26
                df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
                st.subheader('MACD and Signal')
                st.line_chart(df.set_index('Date')[['MACD', 'Signal']])
                df['Hist'] = df['MACD'] - df['Signal']
                st.subheader('MACD Histogram')
                st.bar_chart(df.set_index('Date')['Hist'])

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
                st.line_chart(df.set_index('Date')[['+DI', '-DI']])

        # Download filtered data
        csv_data = df.to_csv(index=False).encode('utf-8')
        st.download_button("Download CSV", data=csv_data, file_name='data.csv')

if __name__ == '__main__':
    show_techanalysis_page()