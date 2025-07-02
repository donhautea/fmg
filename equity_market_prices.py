# equity_market_prices.py

import streamlit as st
import sqlite3
import pandas as pd
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def show_equity_market_prices_page():
    st.header("Stock Data Viewer")

    # Connect to the local SQLite database
    db_path = os.path.join("data", "stock_prices.db")
    conn = sqlite3.connect(db_path)

    # Fetch available tables
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]

    # Sidebar: table selection
    table_name = st.sidebar.selectbox("Select table to load", tables)
    if not table_name:
        st.info("No tables found in the database.")
        conn.close()
        return

    # Load data
    df = pd.read_sql(f'SELECT * FROM "{table_name}"', conn, parse_dates=["Date"])
    df['Date'] = df['Date'].dt.normalize()
    df.drop(columns=['SourceFile'], errors='ignore', inplace=True)

    # Ensure numeric types
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Filter stocks
    stocks = df['Stock'].unique().tolist() if 'Stock' in df.columns else []
    selected_stocks = st.sidebar.multiselect("Select Stock(s)", stocks, default=stocks)
    if not selected_stocks:
        st.warning("Please select at least one stock.")
        conn.close()
        return
    data = df[df['Stock'].isin(selected_stocks)].copy()

    # Date range filter
    min_date, max_date = data['Date'].min(), data['Date'].max()
    start_date, end_date = st.sidebar.date_input(
        "Date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    data = data[(data['Date'] >= pd.to_datetime(start_date)) & (data['Date'] <= pd.to_datetime(end_date))]
    data.sort_values('Date', inplace=True)

    # View and indicator selection
    view = st.sidebar.selectbox("Chart Type", ["Table", "Line", "Candlestick"])
    indicators = st.sidebar.multiselect("Indicators", ["RSI", "MACD", "DMI", "Stochastics"])

    # Display raw data
    st.subheader("Data Table")
    st.dataframe(data)

    # Plot price + volume
    if view != "Table" and not data.empty:
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            row_heights=[0.7, 0.3],
            vertical_spacing=0.02
        )
        # Price trace
        if view == "Line":
            fig.add_trace(
                go.Scatter(x=data['Date'], y=data['Close'], name='Close'),
                row=1, col=1
            )
        else:
            fig.add_trace(
                go.Candlestick(
                    x=data['Date'],
                    open=data['Open'], high=data['High'],
                    low=data['Low'], close=data['Close'],
                    name='Price'
                ),
                row=1, col=1
            )
        # Volume bar trace
        fig.add_trace(
            go.Bar(x=data['Date'], y=data['Volume'], name='Volume'),
            row=2, col=1
        )
        fig.update_layout(margin=dict(l=20, r=20, t=30, b=20), showlegend=False)
        st.subheader(f"{view} Chart with Volume")
        st.plotly_chart(fig, use_container_width=True)

    # Initialize series dict for indicator series
    series = {}

    # Precompute indicator series if selected
    if indicators and not data.empty:
        if "RSI" in indicators and len(data) >= 15:
            delta = data['Close'].diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = -delta.clip(upper=0).rolling(14).mean()
            rs = gain / loss
            series['RSI'] = 100 - (100 / (1 + rs))
        if "MACD" in indicators and len(data) >= 26:
            ema12 = data['Close'].ewm(span=12, adjust=False).mean()
            ema26 = data['Close'].ewm(span=26, adjust=False).mean()
            macd = ema12 - ema26
            signal = macd.ewm(span=9, adjust=False).mean()
            series['MACD'] = macd
            series['Signal'] = signal
        if "DMI" in indicators and len(data) >= 15:
            h, l, c = data['High'], data['Low'], data['Close']
            pdm = (h.diff()).clip(lower=0)
            mdm = (-l.diff()).clip(lower=0)
            tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
            series['DI+'] = 100 * pdm.rolling(14).sum() / tr.rolling(14).sum()
            series['DI-'] = 100 * mdm.rolling(14).sum() / tr.rolling(14).sum()
            series['ADX'] = (abs(series['DI+'] - series['DI-']) / (series['DI+'] + series['DI-'])).rolling(14).mean() * 100
        if "Stochastics" in indicators and len(data) >= 14:
            low14 = data['Low'].rolling(14).min()
            high14 = data['High'].rolling(14).max()
            K = 100 * (data['Close'] - low14) / (high14 - low14)
            series['%K'] = K
            series['%D'] = K.rolling(3).mean()

    # Plot each indicator visually
    if indicators and series:
        for ind in indicators:
            if ind == 'RSI' and 'RSI' in series:
                fig_rsi = go.Figure(data=[go.Scatter(x=data['Date'], y=series['RSI'], name='RSI')])
                fig_rsi.update_layout(title='RSI (14)', margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig_rsi, use_container_width=True)
            if ind == 'MACD' and 'MACD' in series and 'Signal' in series:
                fig_macd = go.Figure()
                fig_macd.add_trace(go.Scatter(x=data['Date'], y=series['MACD'], name='MACD'))
                fig_macd.add_trace(go.Scatter(x=data['Date'], y=series['Signal'], name='Signal'))
                fig_macd.update_layout(title='MACD (12,26,9)', margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig_macd, use_container_width=True)
            if ind == 'DMI' and 'ADX' in series:
                fig_dmi = go.Figure()
                fig_dmi.add_trace(go.Scatter(x=data['Date'], y=series['DI+'], name='DI+'))
                fig_dmi.add_trace(go.Scatter(x=data['Date'], y=series['DI-'], name='DI-'))
                fig_dmi.add_trace(go.Scatter(x=data['Date'], y=series['ADX'], name='ADX'))
                fig_dmi.update_layout(title='DMI / ADX', margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig_dmi, use_container_width=True)
            if ind == 'Stochastics' and '%K' in series and '%D' in series:
                fig_stoch = go.Figure()
                fig_stoch.add_trace(go.Scatter(x=data['Date'], y=series['%K'], name='%K'))
                fig_stoch.add_trace(go.Scatter(x=data['Date'], y=series['%D'], name='%D'))
                fig_stoch.update_layout(title='Stochastics (14,3)', margin=dict(l=20, r=20, t=30, b=20))
                st.plotly_chart(fig_stoch, use_container_width=True)
    elif indicators:
        st.warning("Not enough data points to compute selected indicators.")
    else:
        st.info("No indicators selected. Add indicators from the sidebar to display them.")

    # Automated numeric analysis summary
    analysis = []
    if not data.empty:
        # Trend
        start_p, end_p = data['Close'].iloc[0], data['Close'].iloc[-1]
        trend = 'Upward' if end_p > start_p else 'Downward' if end_p < start_p else 'Sideways'
        analysis.append(f"Trend: {trend} (from {start_p:.2f} to {end_p:.2f})")
        # Candlestick pattern
        if len(data) >= 2:
            prev, curr = data.iloc[-2], data.iloc[-1]
            if (curr['Close'] > curr['Open'] > prev['Close'] > prev['Open']):
                analysis.append("Pattern: Bullish Engulfing")
            elif (curr['Open'] > curr['Close'] < prev['Open'] < prev['Close']):
                analysis.append("Pattern: Bearish Engulfing")
            else:
                analysis.append("Pattern: None detected")
        # Indicator values summary
        if 'RSI' in series:
            last = series['RSI'].iloc[-1]
            analysis.append(f"RSI: {last:.1f} ({'Overbought' if last>70 else 'Oversold' if last<30 else 'Neutral'})")
        if 'MACD' in series:
            last_macd = series['MACD'].iloc[-1]
            last_sig = series['Signal'].iloc[-1]
            cross = ('Bullish crossover' if last_macd>last_sig and series['MACD'].iloc[-2]<=series['Signal'].iloc[-2]
                     else 'Bearish crossover' if last_macd<last_sig and series['MACD'].iloc[-2]>=series['Signal'].iloc[-2]
                     else 'No crossover')
            momentum = 'Bullish momentum' if last_macd>0 else 'Bearish momentum'
            analysis.append(f"MACD: {last_macd:.2f}, Signal: {last_sig:.2f} ({cross}, {momentum})")
        if 'ADX' in series:
            dp = series['DI+'].iloc[-1]
            dm = series['DI-'].iloc[-1]
            adx_val = series['ADX'].iloc[-1]
            strength = 'Strong' if adx_val>25 else 'Weak'
            analysis.append(f"DMI/ADX: DI+ {dp:.1f}, DI- {dm:.1f}, ADX {adx_val:.1f} ({strength})")
        if '%K' in series:
            last_k = series['%K'].iloc[-1]
            last_d = series['%D'].iloc[-1]
            sig = 'Bullish' if last_k>last_d else 'Bearish'
            analysis.append(f"Stochastics: %K {last_k:.1f}, %D {last_d:.1f} ({sig})")

    if analysis:
        st.subheader("Automated Analysis")
        for item in analysis:
            st.markdown(f"• {item}")

    conn.close()
