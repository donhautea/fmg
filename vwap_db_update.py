# db_vwap_app.py

import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px
import os

def show_vwap_db_update_page():
    st.title(":bar_chart: Stock Volume & VWAP Dashboard")

    DB_FILE = "stock_vwap.db"
    LOG_FILE = "db_insert_log.txt"

    # --- DB Setup ---
    def init_db(db_path):
        if not os.path.exists(db_path):
            st.info("Database file not found. Creating new database...")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_data (
                Date TEXT,
                Security TEXT,
                Volume REAL,
                Value REAL,
                VWAP REAL,
                SourceSheet TEXT,
                PRIMARY KEY (Date, Security, SourceSheet)
            );
        """)
        conn.commit()
        return conn

    # --- Logging Utility ---
    def log_to_file(message):
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now()}] {message}\n")

    # --- Delete by Date ---
    def delete_data_by_date(conn, selected_date):
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM stock_data WHERE Date = ?", (selected_date,))
            deleted = cursor.rowcount
            conn.commit()
            log_to_file(f"Deleted {deleted} records for Date = {selected_date}")
            return deleted
        except Exception as e:
            log_to_file(f"ERROR deleting data: {e}")
            st.error(f"Error deleting data: {e}")
            return 0

    # --- Delete by Security with Confirmation ---
    def delete_data_by_security(conn, selected_security):
        try:
            df = pd.read_sql("SELECT * FROM stock_data WHERE Security = ?", conn, params=(selected_security,))
            if df.empty:
                st.sidebar.info(f"No records found for Security: {selected_security}")
                return
            st.sidebar.subheader(f"Records to Delete for {selected_security}")
            st.sidebar.dataframe(df)
            if st.sidebar.button(f"Confirm Delete for {selected_security}"):
                cursor = conn.cursor()
                cursor.execute("DELETE FROM stock_data WHERE Security = ?", (selected_security,))
                deleted = cursor.rowcount
                conn.commit()
                log_to_file(f"Deleted {deleted} records for Security = {selected_security}")
                st.sidebar.success(f"Deleted {deleted} records for {selected_security}")
            else:
                st.sidebar.info("Deletion cancelled.")
        except Exception as e:
            log_to_file(f"ERROR deleting by Security: {e}")
            st.sidebar.error(f"Error deleting by Security: {e}")

    # --- Save to DB with duplicate prevention and audit trail ---
    def save_to_db(df, conn):
        df = df.copy()
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        df['Security'] = df['Security'].astype(str).str.strip().str.upper()
        df['SourceSheet'] = df['SourceSheet'].astype(str).str.strip().str.upper()
        df['key'] = df['Date'] + '|' + df['Security'] + '|' + df['SourceSheet']

        try:
            existing = pd.read_sql("SELECT Date, Security, SourceSheet FROM stock_data", conn)
            existing['Date'] = pd.to_datetime(existing['Date']).dt.strftime('%Y-%m-%d')
            existing['Security'] = existing['Security'].astype(str).str.strip().str.upper()
            existing['SourceSheet'] = existing['SourceSheet'].astype(str).str.strip().str.upper()
            existing['key'] = existing['Date'] + '|' + existing['Security'] + '|' + existing['SourceSheet']
            duplicates = df[df['key'].isin(existing['key'])]
            skipped_keys = duplicates['key'].tolist()
            if skipped_keys:
                log_to_file(f"SKIPPED duplicate entries: {skipped_keys}")
            df = df[~df['key'].isin(existing['key'])].drop(columns='key')
        except Exception as e:
            st.warning(f"Failed to check existing records. Proceeding to insert all rows. Error: {e}")
            log_to_file(f"ERROR during duplicate check: {e}")
            df = df.drop(columns='key')

        if df.empty:
            return 0, None

        insert_query = """
            INSERT OR IGNORE INTO stock_data (Date, Security, Volume, Value, VWAP, SourceSheet)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        records = []
        for _, row in df.iterrows():
            try:
                records.append((row['Date'], row['Security'], row['Volume'], row['Value'], row['VWAP'], row['SourceSheet']))
            except Exception as e:
                log_to_file(f"ERROR formatting record: {row.to_dict()} - {e}")

        try:
            cursor = conn.cursor()
            cursor.executemany(insert_query, records)
            conn.commit()
            inserted = cursor.rowcount
            log_to_file(f"INSERTED {inserted} new records.")
            return inserted, df
        except sqlite3.IntegrityError as e:
            log_to_file(f"IntegrityError on insert: {e}")
            st.error("Database insert failed due to duplicate primary keys.")
            return 0, None
        except Exception as e:
            log_to_file(f"Unexpected DB error: {e}")
            st.error(f"Unexpected error during database insert: {e}")
            return 0, None

    # --- Parse Excel Blocks ---
    def extract_blocks(sheet_df, sheet_name):
        blocks = []
        for col_start in range(0, sheet_df.shape[1], 6):
            if col_start + 4 >= sheet_df.shape[1]: continue
            date_val = sheet_df.iloc[0, col_start]
            if pd.isna(date_val): continue
            try: date = pd.to_datetime(date_val)
            except: continue
            block = sheet_df.iloc[2:, col_start:col_start + 5].copy()
            if block.shape[1] != 5: continue
            block.columns = ['Security', 'Volume', 'Vol_Pct', 'Value', 'Val_Pct']
            block['Date'] = pd.to_datetime(date).strftime('%Y-%m-%d')
            block['SourceSheet'] = sheet_name
            block['Security'] = block['Security'].astype(str).str.strip()
            blocks.append(block)
        return pd.concat(blocks, ignore_index=True) if blocks else pd.DataFrame()

    # --- Load from DB ---
    def load_all_data(conn):
        df = pd.read_sql("SELECT * FROM stock_data", conn, parse_dates=["Date"])
        df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
        return df

    # --- Sidebar: DB File Selector and Load ---
    st.sidebar.header("Database File Options")
    db_input_file = st.sidebar.text_input("SQLite DB Path", DB_FILE)
    conn = init_db(db_input_file)

    if st.sidebar.checkbox("Show Current Dataset"):
        try:
            current_data = load_all_data(conn)
            st.subheader("📄 Current Database Content")
            st.dataframe(current_data)
        except Exception as e:
            st.error(f"Error loading data from database: {e}")

    # --- Sidebar: Upload Monthly Volume File ---
    st.sidebar.markdown("---")
    st.sidebar.header("Upload Monthly Volume Excel (DB Update)")
    uploaded_volume = st.sidebar.file_uploader("Upload Monthly Excel File", type="xlsx", key="monthly")

    # --- Sidebar: Delete Data by Date ---
    st.sidebar.markdown("---")
    st.sidebar.header("Delete Records from Database")
    delete_date = st.sidebar.date_input("Select Date to Delete")
    if st.sidebar.button("Delete Data for Selected Date"):
        deleted_rows = delete_data_by_date(conn, delete_date.strftime('%Y-%m-%d'))
        if deleted_rows > 0:
            st.sidebar.success(f"Deleted {deleted_rows} records for {delete_date.strftime('%Y-%m-%d')}")
        else:
            st.sidebar.info(f"No records found for {delete_date.strftime('%Y-%m-%d')}")

    # --- Sidebar: Delete by Security ---
    st.sidebar.markdown("---")
    st.sidebar.header("Delete by Security")
    all_securities = pd.read_sql("SELECT DISTINCT Security FROM stock_data ORDER BY Security", conn)['Security'].tolist()
    selected_sec = st.sidebar.selectbox("Select Security to Delete", all_securities)
    if selected_sec:
        delete_data_by_security(conn, selected_sec)

    # --- Excel Parsing and DB Insertion ---
    sheet_names = [datetime(2025, i, 1).strftime('%B %Y') for i in range(1, 13)]

    if uploaded_volume:
        xls = pd.ExcelFile(uploaded_volume)
        all_blocks = []
        sheet_counts = {}
        for sheet in sheet_names:
            if sheet in xls.sheet_names:
                sheet_df = pd.read_excel(xls, sheet_name=sheet, header=None)
                parsed = extract_blocks(sheet_df, sheet)
                if not parsed.empty:
                    sheet_counts[sheet] = len(parsed)
                    all_blocks.append(parsed)
        combined_df = pd.concat(all_blocks, ignore_index=True) if all_blocks else pd.DataFrame()
        if not combined_df.empty:
            combined_df.dropna(subset=['Security'], inplace=True)
            combined_df = combined_df[combined_df['Security'].str.upper() != 'TOTAL:']
            combined_df['Volume'] = pd.to_numeric(combined_df['Volume'], errors='coerce')
            combined_df['Value'] = pd.to_numeric(combined_df['Value'], errors='coerce')
            combined_df['VWAP'] = combined_df['Value'] / combined_df['Volume']
            combined_df = combined_df[['Date', 'Security', 'Volume', 'Value', 'VWAP', 'SourceSheet']]
            inserted, new_data = save_to_db(combined_df, conn)

            for sheet, count in sheet_counts.items():
                st.write(f"✅ Parsed {count} records from sheet: {sheet}")

            if inserted > 0:
                date_from = new_data['Date'].min()
                date_to = new_data['Date'].max()
                st.success(f"✅ {inserted} new records added from {date_from} to {date_to}.")
            else:
                st.info("No new records were added to the database.")
                try:
                    db_data = load_all_data(conn)
                    if not db_data.empty:
                        earliest = db_data['Date'].min()
                        latest = db_data['Date'].max()
                        st.info(f"Current DB data range: {earliest} to {latest}.")
                except Exception as e:
                    st.warning(f"Unable to summarize DB contents: {e}")
