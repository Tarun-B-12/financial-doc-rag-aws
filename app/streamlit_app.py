import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.vectorstore import query_vectorstore
from src.generator import generate_answer

st.set_page_config(
    page_title="FinDocRAG",
    page_icon="📊",
    layout="wide"
)

st.markdown("""
<style>
.main-header {
    font-size: 2rem;
    font-weight: 700;
    color: #1e3a5f;
    margin-bottom: 0.25rem;
}
.sub-header {
    font-size: 1rem;
    color: #64748b;
    margin-bottom: 2rem;
}
.source-card {
    background: #f8fafc;
    border-left: 4px solid #2563eb;
    padding: 12px 16px;
    border-radius: 4px;
    margin-bottom: 8px;
    font-size: 0.875rem;
}
.grounded-badge {
    background: #dcfce7;
    color: #166534;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: 600;
}
.not-grounded-badge {
    background: #fee2e2;
    color: #991b1b;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 0.em;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">FinDocRAG</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Natural language question answering over SEC 10-K filings. Answers are grounded in source documents with citations.</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### Documents Indexed")
    st.markdown("- JPMorgan Chase 10-K 2025")
    st.markdown("- Goldman Sachs 10-K 2025")
    st.markdown("- Apple 10-K 2025")
    
    st.markdown("---")
    
    st.markdown("### Filter by Company")
    company_filter = st.selectbox(
        "Search within",
        ["All Companies", "JPMorgan Chase", "Goldman Sachs", "Apple"]
    )
    
    st.markdown("---")
    
    st.markdown("### Sample Questions")
    sample_questions = [
        "What are JPMorgan's primary risk management principles?",
        "What is Apple's revenue recognition policy?",
        "What were Goldman Sachs net revenues in 2025?",
        "How does JPMorgan describe its fortress balance sheet strategy?",
        "What are the main business segments of Goldman Sachs?",
        "How does Apple handle product warranty obligations?",
    ]
    
    for q in sample_questions:
        if st.button(q, key=q, use_container_width=True):
            st.session_state.question = q

st.markdown("### Ask a Question")

question = st.text_input(
    "Enter your question about the financial documents",
    value=st.session_state.get("question", ""),
    placeholder="e.g. What are JPMorgan's primary risk factors?"
)

col1, col2 = st.columns([1, 5])
with col1:
    search_clicked = st.button("Search", type="primary", use_container_width=True)
with col2:
    n_chunks = st.slider("Chunks to retrieve", min_value=2, max_value=8, value=4)

if search_clicked and question:
    with st.spinner("Searching documents and generating answer..."):
        
        filter_company = None if company_filter == "All Companies" else company_filter
        chunks = query_vectorstore(question, n_results=n_chunks, company_filter=filter_company)
        result = generate_answer(question, chunks)
    
    st.markdown("---")
    
    col_answer, col_sources = st.columns([3, 2])
    
    with col_answer:
        st.markdown("### Answer")
        
        if result["grounded"]:
            st.markdown('<span class="grounded-badge">Grounded in source documents</span>', 
                       unsafe_allow_html=True)
        else:
            st.markdown('<span class="not-grounded-badge">Not found in documents</span>', 
                       unsafe_allow_html=True)
        
        st.markdown("")
        st.markdown(result["answer"])
    
    with col_sources:
        st.markdown("### Sources Retrieved")
        for source in result["sources"]:
            st.markdown(f"""
<div class="source-card">
<strong>Source {source['source_num']}: {source['company']}</strong><br>
File: {source['file']}<br>
Relevance: {source['similarity']:.1%}
</div>
""", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### Retrieved Context")
    with st.expander("View raw chunks used to generate this answer"):
        for i, chunk in enumerate(chunks):
            st.markdown(f"**Chunk {i+1} ({chunk['metadata']['company']})**")
            st.text(chunk['text'][:500] + "...")
            st.markdown("---")

elif search_clicked and not question:
    st.warning("Please enter a question.")

st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#94a3b8;font-size:0.8rem'>"
    "Built by Tarun B | Financial Document RAG Pipeline on AWS S3 | "
    "Powered by Claude API and ChromaDB"
    "</div>",
    unsafe_allow_html=True
)
