
import os
import sys
import hashlib

import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, "src")
load_dotenv()

st.set_page_config(
    page_title="Federal Solicitation Assistant",
    layout="wide",
)
st.title("Federal Solicitation Assistant")
st.subheader("Developed by Abdul Samad")
st.caption("SAM.gov Contract Analyst | AI Automation & RAG Developer")
st.write("AI-powered analysis of government solicitation documents.")
st.caption("Independent portfolio project; not affiliated with SAM.gov or the U.S. Government.")


mode = st.radio(
    "Choose a mode",
    ["Upload a Solicitation", "Existing SAM.gov Dataset"],
    horizontal=True,
)

# --------------------------------------------------
# MODE 1: UPLOAD AND ANALYZE A SOLICITATION
# --------------------------------------------------
if mode == "Upload a Solicitation":
    from upload_rag import build_index, answer_question

    st.subheader("Upload a Solicitation")
    st.info(
        "Upload a document you are authorized to share. "
        "Supported formats: PDF, DOCX, XLSX. Maximum size: 20 MB."
    )

    uploaded = st.file_uploader(
        "Choose a solicitation document",
        type=["pdf", "docx", "xlsx"],
    )

    if uploaded is not None:
        try:
            api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            api_key = ""

        api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")

        data = uploaded.getvalue()
        fingerprint = hashlib.sha256(data).hexdigest()

        current_index = st.session_state.get("upload_index")

        if (
            current_index is None
            or current_index.get("fingerprint") != fingerprint
        ):
            with st.spinner("Reading and indexing your document..."):
                try:
                    st.session_state.upload_index = build_index(
                        uploaded.name,
                        data,
                    )
                except Exception as exc:
                    st.error(f"Could not process this document: {exc}")
                    st.stop()

        index = st.session_state.upload_index

        st.success(
            f"Indexed {index['chunks']} text chunks from "
            f"{index['filename']}."
        )

        question = st.text_input(
            "Your question",
            placeholder="What are the proposal submission requirements?",
            key="upload_question",
        )

        if st.button("Ask about this document", type="primary"):
            if not question.strip():
                st.warning("Please enter a question first.")
                st.stop()

            if not api_key:
                st.error(
                    "Anthropic API key is not configured. "
                    "The app owner must configure ANTHROPIC_API_KEY."
                )
                st.stop()

            with st.spinner("Searching the document and preparing an answer..."):
                try:
                    answer, sources = answer_question(
                        index,
                        question.strip(),
                        api_key,
                    )
                except Exception as exc:
                    st.error(f"Unable to answer this question: {exc}")
                    st.stop()

            st.subheader("Answer")
            st.markdown(answer)

            st.subheader("Sources")
            for source in sources:
                st.write(
                    f"[{source['number']}] "
                    f"{source['filename']} — page {source['page']}"
                )

# --------------------------------------------------
# MODE 2: EXISTING LOCAL SAM.GOV DATASET
# --------------------------------------------------
else:
    try:
        from rag import _metas, ask
    except Exception as exc:
        st.error(
            "The existing SAM.gov dataset is unavailable in this environment."
        )
        st.caption(f"Details: {exc}")
        st.info(
            "Choose 'Upload a Solicitation' to analyze an uploaded document."
        )
        st.stop()

    st.subheader("Existing SAM.gov Dataset")

    titles = sorted({meta["title"] for meta in _metas})

    with st.sidebar:
        st.header("Filters")

        notice = st.selectbox(
            "Notice",
            ["All notices"] + titles,
        )

        file_part = st.text_input(
            "File name contains (optional)",
            placeholder="e.g. Amend0005",
        )

        k = st.slider(
            "Chunks to retrieve",
            min_value=3,
            max_value=12,
            value=6,
        )

    question = st.text_input(
        "Your question",
        placeholder="What past performance information is required?",
        key="dataset_question",
    )

    if st.button("Ask", type="primary"):
        if not question.strip():
            st.warning("Please enter a question first.")
            st.stop()

        with st.spinner("Searching documents..."):
            try:
                answer, metas = ask(
                    question.strip(),
                    None if notice == "All notices" else notice,
                    file_part.strip() or None,
                    k,
                )
            except Exception as exc:
                st.error(f"Unable to answer this question: {exc}")
                st.stop()

        st.subheader("Answer")
        st.markdown(answer)

        st.subheader("Sources")

        if not metas:
            st.info("No matching document sources were returned.")
        else:
            for i, meta in enumerate(metas, start=1):
                filename = meta.get(
                    "file", "unknown file"
                ).replace("+", " ")
                page = meta.get("page", "-")
                section = meta.get("section") or "no section"

                st.write(
                    f"**[{i}]** {filename} — page {page} ({section})"
                )
