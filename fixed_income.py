# fixed_income.py
import streamlit as st
import pandas as pd
import os

def show_fixed_income_page():
    st.sidebar.title("📂 Fixed Income File Loader")
    uploaded_file = st.sidebar.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])

    dataset_names = ["GS_Consolidated_Php", "GS_Consolidated_USD", "CBN_Php", "CBN_USD"]
    selected_dataset = st.sidebar.radio("Select Dataset to View", options=dataset_names)

    exchange_rate = None
    currency_label = "PhP"

    if selected_dataset in ["GS_Consolidated_USD", "CBN_USD"]:
        exchange_rate_input = st.sidebar.text_input("Php to 1 USD Exchange Rate (leave blank to keep USD)", "")
        try:
            exchange_rate = float(exchange_rate_input) if exchange_rate_input else None
            currency_label = "PhP" if exchange_rate else "USD"
        except ValueError:
            st.sidebar.error("Invalid exchange rate. Please enter a valid number.")
    else:
        currency_label = "PhP"

    # Initialize container for all datasets
    data_storage = {name: None for name in dataset_names}

    # Attempt to load uploaded file or default file
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith(".csv"):
                df = pd.read_csv(uploaded_file)
                for name in dataset_names:
                    if name.lower() in uploaded_file.name.lower():
                        data_storage[name] = df
                        break
            elif uploaded_file.name.endswith(".xlsx"):
                excel = pd.ExcelFile(uploaded_file)
                for name in dataset_names:
                    if name in excel.sheet_names:
                        data_storage[name] = excel.parse(sheet_name=name)
        except Exception as e:
            st.error(f"Error reading uploaded file: {e}")
    else:
        # Load default Excel file if no upload
        default_path = r"FIID_Data.xlsx"
        if os.path.exists(default_path):
            try:
                excel = pd.ExcelFile(default_path)
                for name in dataset_names:
                    if name in excel.sheet_names:
                        data_storage[name] = excel.parse(sheet_name=name)
            except Exception as e:
                st.error(f"Error reading default file: {e}")
        else:
            st.warning("No file uploaded and default file not found.")

    st.title("📊 Fixed Income Dataset Viewer")

    df = data_storage[selected_dataset]
    if df is not None:
        st.subheader(f"Viewing: {selected_dataset}")
        st.dataframe(df)

        st.subheader("📑 Summary by Fund and Classification")

        if selected_dataset in ["CBN_Php", "CBN_USD"]:
            group_by_option = st.selectbox("Group by:", options=["Group", "Issuer", "Type"])
            fund_options = ["SSS", "EC", "FLEXI", "MIA", "MPF", "NVPF", "Consolidated"]
            selected_fund = st.selectbox("Select Fund:", options=fund_options)

            fund_column = "Outstanding_Balance" if selected_fund == "Consolidated" else f"{selected_fund}_Outstanding"

            if fund_column not in df.columns:
                st.warning(f"{fund_column} column not found in the dataset.")
                return

            df[fund_column] = pd.to_numeric(df[fund_column], errors='coerce')
            if selected_dataset == "CBN_USD" and exchange_rate:
                df[fund_column] *= exchange_rate

            grouped_df = (
                df.groupby(group_by_option)[fund_column]
                .sum()
                .reset_index()
                .rename(columns={fund_column: f"{selected_fund} Outstanding"})
                .sort_values(by=f"{selected_fund} Outstanding", ascending=False)
            )

            st.markdown(f"### 💰 Outstanding Amount by {group_by_option} ({selected_fund}) in {currency_label}")
            st.dataframe(grouped_df.style.format({f"{selected_fund} Outstanding": "{:,.2f}"}))

        else:
            fund_map = {
                "SSS": ("Settlement_Amount_SSS", "Face_Amount_SSS"),
                "EC": ("Settlement_Amount_EC", "Face_Amount_EC"),
                "FLEXI": ("Settlement_Amount_FLEXI", "Face_Amount_FLEXI"),
                "PESO": ("Settlement_Amount_PESO", "Face_Amount_PESO"),
                "MIA": ("Settlement_Amount_MIA", "Face_Amount_MIA"),
                "MPF": ("Settlement_Amount_MPF", "Face_Amount_MPF"),
                "NVPF": ("Settlement_Amount_NVPF", "Face_Amount_NVPF")
            }

            classes = ["AC", "FVTPL", "FVOCI"]
            settlement_rows = []
            for class_val in classes:
                class_data = df[df["Class"] == class_val]
                row = {"Class": class_val}
                for fund, (settle_col, _) in fund_map.items():
                    val = pd.to_numeric(class_data.get(settle_col, pd.Series()), errors='coerce').sum()
                    if selected_dataset == "GS_Consolidated_USD" and exchange_rate:
                        val *= exchange_rate
                    row[fund] = val
                settlement_rows.append(row)

            total_row = {"Class": "Total"}
            for fund, (settle_col, _) in fund_map.items():
                val = pd.to_numeric(df.get(settle_col, pd.Series()), errors='coerce').sum()
                if selected_dataset == "GS_Consolidated_USD" and exchange_rate:
                    val *= exchange_rate
                total_row[fund] = val
            settlement_rows.append(total_row)

            settlement_df = pd.DataFrame(settlement_rows).set_index("Class")
            st.markdown(f"### 💰 Settlement Amount Summary ({currency_label})")
            st.dataframe(settlement_df.style.format("{:,.2f}"))

            face_rows = []
            for class_val in classes:
                class_data = df[df["Class"] == class_val]
                row = {"Class": class_val}
                for fund, (_, face_col) in fund_map.items():
                    val = pd.to_numeric(class_data.get(face_col, pd.Series()), errors='coerce').sum()
                    if selected_dataset == "GS_Consolidated_USD" and exchange_rate:
                        val *= exchange_rate
                    row[fund] = val
                face_rows.append(row)

            total_row = {"Class": "Total"}
            for fund, (_, face_col) in fund_map.items():
                val = pd.to_numeric(df.get(face_col, pd.Series()), errors='coerce').sum()
                if selected_dataset == "GS_Consolidated_USD" and exchange_rate:
                    val *= exchange_rate
                total_row[fund] = val
            face_rows.append(total_row)

            face_df = pd.DataFrame(face_rows).set_index("Class")
            st.markdown(f"### 🧾 Face Amount Summary ({currency_label})")
            st.dataframe(face_df.style.format("{:,.2f}"))
    else:
        st.warning(f"{selected_dataset} not yet loaded. Please upload a file or check the default path.")
