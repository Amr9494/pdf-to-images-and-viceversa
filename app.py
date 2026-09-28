import io
import os
import zipfile
import fitz  # PyMuPDF
from PIL import Image
import streamlit as st

st.set_page_config(
    page_title="PDF & Image Converter",
    page_icon="🔄",
    layout="wide"
)

st.title("🔄 PDF & Image Converter")
st.caption("Convert PDFs to ultra-high-resolution images or compile images into a single PDF.")

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
                pdf_bytes = uploaded_pdf.read()
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                total_pages = len(doc)

                converted_images = []
                zip_buffer = io.BytesIO()

                zoom = dpi / 72.0
                mat = fitz.Matrix(zoom, zoom)

                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    progress_bar = st.progress(0)

                    for page_idx in range(total_pages):
                        page = doc.load_page(page_idx)
                        pix = page.get_pixmap(matrix=mat, alpha=False)

                        img_bytes = pix.tobytes(img_format.lower())
                        page_num = page_idx + 1
                        file_name = f"{base_name}_{page_num}.{img_format.lower()}"

                        zip_file.writestr(file_name, img_bytes)
                        converted_images.append((file_name, img_bytes))
                        progress_bar.progress((page_idx + 1) / total_pages)

                doc.close()

            st.success(f"Successfully converted {total_pages} page(s) at {dpi} DPI!")

            st.download_button(
                label="📦 Download All Images (.zip)",
                data=zip_buffer.getvalue(),
                file_name=f"{base_name}_images.zip",
                mime="application/zip",
                type="primary"
            )

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
# TASK 2: Images to PDF (with Page Ordering & Reordering)
# =====================================================================
else:
    st.subheader("Convert Images to PDF")

    uploaded_images = st.file_uploader(
        "Choose image files (PNG, JPG, JPEG, WEBP)",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True
    )

    if uploaded_images:
        # Cache image data in session state so re-ordering doesn't re-upload
        current_names = [f.name for f in uploaded_images]
        
        # Check if files changed
        if "loaded_files" not in st.session_state or [img["name"] for img in st.session_state.get("image_list", [])] != current_names:
            st.session_state.image_list = [
                {"name": f.name, "bytes": f.read()} for f in uploaded_images
            ]
            st.session_state.loaded_files = current_names

        st.write("---")
        st.write("### 🔀 Arrange & Order Pages")

        # Quick-sort controls
        sort_col1, sort_col2 = st.columns([2, 2])
        with sort_col1:
            sort_order = st.selectbox(
                "Quick Sort Pages:",
                ["Keep Current Order", "File Name (A → Z)", "File Name (Z → A)"]
            )
            if st.button("Apply Quick Sort"):
                if sort_order == "File Name (A → Z)":
                    st.session_state.image_list.sort(key=lambda x: x["name"])
                    st.rerun()
                elif sort_order == "File Name (Z → A)":
                    st.session_state.image_list.sort(key=lambda x: x["name"], reverse=True)
                    st.rerun()

        st.caption("Use the ⬆️ and ⬇️ buttons below to fine-tune the exact sequence:")

        # Interactive manual reordering list
        num_items = len(st.session_state.image_list)
        for i in range(num_items):
            item = st.session_state.image_list[i]
            card_col1, card_col2, card_col3 = st.columns([1, 4, 2])

            with card_col1:
                st.image(item["bytes"], width=90)

            with card_col2:
                st.markdown(f"**Page {i + 1}:** `{item['name']}`")

            with card_col3:
                btn_up, btn_down = st.columns(2)
                with btn_up:
                    if st.button("⬆️ Up", key=f"up_{i}", disabled=(i == 0)):
                        st.session_state.image_list[i], st.session_state.image_list[i - 1] = (
                            st.session_state.image_list[i - 1],
                            st.session_state.image_list[i],
                        )
                        st.rerun()
                with btn_down:
                    if st.button("⬇️ Down", key=f"down_{i}", disabled=(i == num_items - 1)):
                        st.session_state.image_list[i], st.session_state.image_list[i + 1] = (
                            st.session_state.image_list[i + 1],
                            st.session_state.image_list[i],
                        )
                        st.rerun()

        st.write("---")

        # PDF Compilation settings
        col_out1, col_out2 = st.columns([2, 1])
        with col_out1:
            pdf_output_name = st.text_input(
                "Output PDF file name (without .pdf)",
                value="merged_images"
            ).strip()
            if not pdf_output_name:
                pdf_output_name = "merged_images"

        if st.button("🚀 Generate PDF", type="primary"):
            with st.spinner("Compiling images into PDF in current order..."):
                processed_images = []

                for item in st.session_state.image_list:
                    img = Image.open(io.BytesIO(item["bytes"]))
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    processed_images.append(img)

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