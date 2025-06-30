import streamlit as st

def show_pdf_viewer_page():
    st.subheader("📄 PDF Viewer")

    uploaded_file = st.sidebar.file_uploader("Upload a PDF file", type=["pdf"])

    if uploaded_file:
        st.success(f"File uploaded: {uploaded_file.name}")
        st.download_button(
            label="📥 Download and open PDF",
            data=uploaded_file.getvalue(),
            file_name=uploaded_file.name,
            mime="application/pdf"
        )
        st.info("Open the downloaded file using your PDF viewer.")
    else:
        st.info("👈 Upload a PDF to enable download.")
