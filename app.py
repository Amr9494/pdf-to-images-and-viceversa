import io
import os
import zipfile
import fitz  # PyMuPDF
from PIL import Image
import streamlit as st

# Configure the Streamlit page
st.set_page_config(
    page_title="PDF & Image Converter",
    page_icon="🔄",
    layout="wide"
)

st.title("🔄 PDF & Image Converter")
st.caption("Convert PDFs to ultra-high-resolution images or compile images into a single PDF.")

# Sidebar / Mode Selector
task = st.radio(
    "Choose Mode:",
    ["📄 PDF to High-Quality Images", "🖼️ Images to PDF"],
    horizontal=True
)

st.divider()

# =====================================================================
# TASK 1: PDF to High-Quality Images
# =====================================================================
if task == "📄 PDF to High-Quality Images":
    st.subheader("Convert PDF to Images")

    col1, col2 = st.columns([2, 1])

    with col1:
        uploaded_pdf = st.file_uploader(
            "Choose a PDF file",
            type=["pdf"],
            help="Upload the PDF you want to convert into images."
        )

    with col2:
        # DPI setting controls the resolution and quality
        dpi = st.select_slider(
            "Image Quality (DPI)",
            options=[150, 200, 300, 400, 600],
            value=300,
            help="300 DPI is standard print quality. 600 DPI is ultra-high definition."
        )
        img_format = st.selectbox("Output Format", ["PNG", "JPEG"])

    if uploaded_pdf is not None:
        base_name = os.path.splitext(uploaded_pdf.name)[0]

        if st.button("🚀 Convert PDF to Images", type="primary"):
            with st.spinner("Processing pages at high resolution..."):
                # Open PDF directly from uploaded bytes
                pdf_bytes = uploaded_pdf.read()
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                total_pages = len(doc)

                converted_images = []
                zip_buffer = io.BytesIO()

                # Zoom factor: 72 DPI is base resolution in PyMuPDF
                zoom = dpi / 72.0
                mat = fitz.Matrix(zoom, zoom)

                # Prepare in-memory ZIP archive
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    progress_bar = st.progress(0)

                    for page_idx in range(total_pages):
                        page = doc.load_page(page_idx)
                        pix = page.get_pixmap(matrix=mat, alpha=False)

                        img_bytes = pix.tobytes(img_format.lower())
                        page_num = page_idx + 1
                        file_name = f"{base_name}_{page_num}.{img_format.lower()}"

                        # Save to ZIP
                        zip_file.writestr(file_name, img_bytes)

                        # Save for on-screen preview
                        converted_images.append((file_name, img_bytes))
                        progress_bar.progress((page_idx + 1) / total_pages)

                doc.close()

            st.success(f"Successfully converted {total_pages} page(s) at {dpi} DPI!")

            # Download all as ZIP
            st.download_button(
                label=f"📦 Download All Images (.zip)",
                data=zip_buffer.getvalue(),
                file_name=f"{base_name}_images.zip",
                mime="application/zip",
                type="primary"
            )

            # Preview Section
            st.write("### Preview & Individual Downloads")
            grid_cols = st.columns(3)
            for idx, (img_name, img_data) in enumerate(converted_images):
                with grid_cols[idx % 3]:
                    st.image(img_data, caption=img_name, use_container_width=True)
                    st.download_button(
                        label=f"⬇️ Download {img_name}",
                        data=img_data,
                        file_name=img_name,
                        mime=f"image/{img_format.lower()}",
                        key=f"dl_{idx}"
                    )

# =====================================================================
# TASK 2: Images to PDF
# =====================================================================
else:
    st.subheader("Convert Images to PDF")

    uploaded_images = st.file_uploader(
        "Choose image files (PNG, JPG, JPEG, WEBP)",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True
    )

    if uploaded_images:
        pdf_output_name = st.text_input(
            "Output PDF file name (without .pdf)",
            value="merged_images"
        ).strip()
        if not pdf_output_name:
            pdf_output_name = "merged_images"

        st.write(f"**Total images uploaded:** {len(uploaded_images)}")

        # Display thumbnail previews
        with st.expander("Preview uploaded images", expanded=False):
            prev_cols = st.columns(min(len(uploaded_images), 4))
            for idx, img_file in enumerate(uploaded_images):
                with prev_cols[idx % 4]:
                    st.image(img_file, caption=img_file.name, use_container_width=True)

        if st.button("🚀 Generate PDF", type="primary"):
            with st.spinner("Compiling images into PDF..."):
                processed_images = []

                for uploaded_img in uploaded_images:
                    img = Image.open(uploaded_img)
                    # Convert transparent RGBA / P images to RGB for PDF support
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    processed_images.append(img)

                # Save all images into a single PDF in memory
                pdf_buffer = io.BytesIO()
                first_img = processed_images[0]
                rest_imgs = processed_images[1:]

                first_img.save(
                    pdf_buffer,
                    format="PDF",
                    save_all=True,
                    append_images=rest_imgs,
                    resolution=100.0
                )

            st.success(f"PDF successfully created with {len(processed_images)} page(s)!")

            st.download_button(
                label=f"📄 Download {pdf_output_name}.pdf",
                data=pdf_buffer.getvalue(),
                file_name=f"{pdf_output_name}.pdf",
                mime="application/pdf",
                type="primary"
            )