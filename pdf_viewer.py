import streamlit as st
import base64

def show_pdf_viewer_page():
    st.subheader("📄 PDF Viewer")

    uploaded_file = st.sidebar.file_uploader(
        label="Upload a PDF file",
        type=["pdf"]
    )

    if uploaded_file is not None:
        # Save file temporarily
        with open("temp_uploaded_file.pdf", "wb") as f:
            f.write(uploaded_file.read())

        # Display the PDF using an iframe
        def display_pdf(file_path):
            with open(file_path, "rb") as f:
                base64_pdf = base64.b64encode(f.read()).decode("utf-8")
                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="900px" type="application/pdf"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)

        st.success(f"📖 Now viewing: {uploaded_file.name}")
        display_pdf("temp_uploaded_file.pdf")
    else:
        st.info("👈 Upload a PDF from the sidebar to view it.")
