# equity_market_prices.py

import streamlit as st
import sqlite3
import pandas as pd
import tempfile
import os
import plotly.graph_objects as go


def show_equity_market_prices_page():
    # Section header
    st.header("Stock Data Viewer")

    # Sidebar: upload .db file
    db_file = st.sidebar.file_uploader(
        label="Upload SQLite .db file",
        type=["db", "sqlite"]
    )

    if db_file:
        # Save uploaded file to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_file:
            tmp_file.write(db_file.read())
            tmp_path = tmp_file.name

        conn = sqlite3.connect(tmp_path)
        cursor = conn.cursor()

        # List tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        # Sidebar: select table
        table_name = st.sidebar.selectbox("Select table to load", tables)

        if table_name:
            # Load data
            df = pd.read_sql(f'SELECT * FROM "{table_name}"', conn, parse_dates=["Date"])
            df['Date'] = pd.to_datetime(df['Date']).dt.normalize()
            df = df.drop(columns=['SourceFile'], errors='ignore')

            # Ensure numeric types
            for col in ['Open','High','Low','Close','Volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # Sidebar filters
            stocks = df['Stock'].unique().tolist() if 'Stock' in df.columns else []
            selected_stocks = st.sidebar.multiselect("Select Stock(s)", stocks, default=stocks)
            if not selected_stocks:
                st.warning("Please select at least one stock.")
                return
            filtered = df[df['Stock'].isin(selected_stocks)]

            # Date range filter
            min_date, max_date = filtered['Date'].min(), filtered['Date'].max()
            start_date, end_date = st.sidebar.date_input(
                "Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
            )
            data = filtered[(filtered['Date'] >= pd.to_datetime(start_date)) &
                            (filtered['Date'] <= pd.to_datetime(end_date))].sort_values('Date')

            # Sidebar view settings
            chart_type = st.sidebar.selectbox("Chart Type", ["Table", "Line", "Candlestick"])
            indicators = st.sidebar.multiselect(
                "Add Indicators", ["RSI","MACD","DMI","Stochastics"]
            )

            # Always display data table
            st.subheader("Data Table")
            st.dataframe(data)

            # Display chart
            if chart_type != "Table":
                st.subheader(f"{chart_type} Chart")
                if chart_type == "Line":
                    st.line_chart(data.set_index('Date')['Close'])
                else:
                    fig = go.Figure(data=[
                        go.Candlestick(
                            x=data['Date'], open=data['Open'], high=data['High'],
                            low=data['Low'], close=data['Close']
                        )
                    ])
                    fig.update_layout(margin=dict(l=20,r=20,t=30,b=20))
                    st.plotly_chart(fig, use_container_width=True)

            # Automated analysis setup
            analysis = []
            if not data.empty:
                first_close = data['Close'].iloc[0]
                last_close = data['Close'].iloc[-1]
                trend = ("upward" if last_close > first_close else
                         "downward" if last_close < first_close else "sideways")
                analysis.append(
                    f"• Overall trend over selected period: **{trend}** "  
                    f"(from {first_close} to {last_close})."
                )

            # Compute and analyze indicators
            ind_results = {}
            if data.shape[0] > 1:
                idx = data.set_index('Date')
                close = idx['Close']; high = idx['High']; low = idx['Low']

                if "RSI" in indicators:
                    delta = close.diff(); gain = delta.clip(lower=0); loss = -delta.clip(upper=0)
                    avg_gain = gain.rolling(14).mean(); avg_loss = loss.rolling(14).mean()
                    rs = avg_gain / avg_loss; rsi = 100 - (100 / (1 + rs))
                    ind_results['RSI'] = rsi
                    last_rsi = rsi.iloc[-1]
                    if last_rsi > 70:
                        analysis.append(f"• RSI ({last_rsi:.1f}) indicates **overbought** conditions.")
                    elif last_rsi < 30:
                        analysis.append(f"• RSI ({last_rsi:.1f}) indicates **oversold** conditions.")
                    else:
                        analysis.append(f"• RSI ({last_rsi:.1f}) is in **neutral** range.")

                if "MACD" in indicators:
                    ema12 = close.ewm(span=12, adjust=False).mean()
                    ema26 = close.ewm(span=26, adjust=False).mean()
                    macd = ema12 - ema26; signal = macd.ewm(span=9, adjust=False).mean()
                    ind_results['MACD'] = pd.DataFrame({'MACD': macd, 'Signal': signal})
                    if macd.iloc[-1] > signal.iloc[-1] and macd.iloc[-2] <= signal.iloc[-2]:
                        analysis.append("• MACD bullish crossover detected.")
                    elif macd.iloc[-1] < signal.iloc[-1] and macd.iloc[-2] >= signal.iloc[-2]:
                        analysis.append("• MACD bearish crossover detected.")
                    last_macd = macd.iloc[-1]
                    if last_macd > 0:
                        analysis.append(f"• MACD ({last_macd:.2f}) is above zero line, indicating **bullish momentum**.")
                    elif last_macd < 0:
                        analysis.append(f"• MACD ({last_macd:.2f}) is below zero line, indicating **bearish momentum**.")

                if "DMI" in indicators:
                    prev_h = high.shift(1); prev_l = low.shift(1); prev_c = close.shift(1)
                    pdm = (high - prev_h).where((high - prev_h) > (prev_l - low), 0)
                    mdm = (prev_l - low).where((prev_l - low) > (high - prev_h), 0)
                    tr = pd.concat([
                        high - low,
                        (high - prev_c).abs(),
                        (low - prev_c).abs()
                    ], axis=1).max(axis=1)
                    tr14 = tr.rolling(14).sum(); pdm14 = pdm.rolling(14).sum(); mdm14 = mdm.rolling(14).sum()
                    di_plus = 100 * pdm14 / tr14; di_minus = 100 * mdm14 / tr14
                    adx = (abs(di_plus - di_minus) / (di_plus + di_minus)).rolling(14).mean() * 100
                    ind_results['DMI'] = pd.DataFrame({'DI+': di_plus, 'DI-': di_minus, 'ADX': adx})
                    last_adx = adx.iloc[-1]
                    if last_adx > 25:
                        analysis.append(f"• ADX ({last_adx:.1f}) indicates a **strong trend**.")
                    else:
                        analysis.append(f"• ADX ({last_adx:.1f}) indicates a **weak trend**.")
                    if di_plus.iloc[-1] > di_minus.iloc[-1]:
                        analysis.append("• DI+ is above DI-, signaling a **bullish** condition.")
                    elif di_plus.iloc[-1] < di_minus.iloc[-1]:
                        analysis.append("• DI+ is below DI-, signaling a **bearish** condition.")

                if "Stochastics" in indicators:
                    low14 = low.rolling(14).min(); high14 = high.rolling(14).max()
                    percent_k = 100 * (close - low14) / (high14 - low14)
                    percent_d = percent_k.rolling(3).mean()
                    ind_results['Stochastics'] = pd.DataFrame({'%K': percent_k, '%D': percent_d})
                    k, d = percent_k.iloc[-1], percent_d.iloc[-1]
                    if k > d:
                        analysis.append(f"• Stochastics %K ({k:.1f}) above %D ({d:.1f}), bullish signal.")
                    else:
                        analysis.append(f"• Stochastics %K ({k:.1f}) below %D ({d:.1f}), bearish signal.")

            # Render indicators and analysis
            if chart_type != "Table":
                for ind in indicators:
                    st.subheader(ind)
                    if ind in ind_results:
                        st.line_chart(ind_results[ind])

            if analysis:
                st.subheader("Automated Analysis")
                for line in analysis:
                    st.markdown(line)

        conn.close()
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    else:
        st.info("Please upload a SQLite .db file to get started.")