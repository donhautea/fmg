import streamlit as st
import tempfile

def show_pdf_viewer_page():
    st.subheader("📄 PDF Viewer")

    uploaded_file = st.sidebar.file_uploader("Upload a PDF file", type=["pdf"])
    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
        st.markdown(f"[🔗 Open PDF in browser]({tmp_path})")
        st.info("PDF will open in a new tab if supported.")
