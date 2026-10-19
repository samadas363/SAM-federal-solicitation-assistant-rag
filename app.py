import sys

import streamlit as st

sys.path.insert(0, "src")
from rag import _metas, ask

st.set_page_config(page_title="Federal Solicitation Assistant", layout="wide")
st.title("Federal Solicitation Assistant")
st.caption("Ask questions about SAM.gov solicitations. Answers cite file and page.")

titles = sorted({m["title"] for m in _metas})

with st.sidebar:
    st.header("Filters")
    notice = st.selectbox("Notice", ["All notices"] + titles)
    file_part = st.text_input("File name contains (optional)", placeholder="e.g. Amend0005")
    k = st.slider("Chunks to retrieve", 3, 12, 6)

question = st.text_input("Your question", placeholder="What past performance information is required?")

if st.button("Ask", type="primary") and question.strip():
    with st.spinner("Searching documents..."):
        try:
            answer, mets = ask(
                question,
                None if notice == "All notices" else notice,
                file_part.strip() or None,
                k,
            )
        except Exception as e:
            st.error(str(e))
            st.stop()

    st.subheader("Answer")
    st.markdown(answer)

    st.subheader("Sources")
    for i, m in enumerate(mets, start=1):
        section = m["section"] or "no section"
        st.write(f"**[{i}]** {m['file'].replace('+', ' ')} — page {m['page']} ({section})")