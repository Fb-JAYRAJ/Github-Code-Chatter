import streamlit as st

from backend.ingest import ingest_repository
from backend.rag_pipeline import RAGPipeline

st.set_page_config(page_title="GitHub Code Chatter", page_icon="💬", layout="wide")

CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
    --gcc-bg: #0F1117;
    --gcc-panel: #171A21;
    --gcc-border: #262B36;
    --gcc-accent: #5B8DEF;
    --gcc-success: #3FB950;
    --gcc-amber: #F0B72F;
    --gcc-text: #E6E8EB;
    --gcc-muted: #8B93A1;
}

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
}

.gcc-header {
    display: flex;
    align-items: baseline;
    gap: 14px;
    margin-bottom: 4px;
}
.gcc-header h1 {
    font-size: 2.1rem;
    font-weight: 700;
    margin: 0;
    color: var(--gcc-text);
}
.gcc-tagline {
    color: var(--gcc-muted);
    font-size: 0.95rem;
    margin-bottom: 1.6rem;
}

[data-testid="stSidebar"] {
    background-color: var(--gcc-panel);
    border-right: 1px solid var(--gcc-border);
}
[data-testid="stTextInput"] input {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
}

.stButton > button {
    background-color: var(--gcc-accent);
    color: #0F1117;
    border: none;
    font-weight: 600;
    border-radius: 6px;
}
.stButton > button:hover {
    opacity: 0.85;
    color: #0F1117;
}

.gcc-chip-row .stButton > button {
    background-color: transparent;
    border: 1px solid var(--gcc-border);
    color: var(--gcc-muted);
    font-weight: 400;
    font-size: 0.85rem;
}
.gcc-chip-row .stButton > button:hover {
    border-color: var(--gcc-accent);
    color: var(--gcc-text);
}

.gcc-stat-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin-top: 12px;
}
.gcc-stat-card {
    background-color: var(--gcc-bg);
    border: 1px solid var(--gcc-border);
    border-radius: 8px;
    padding: 10px 12px;
}
.gcc-stat-card .gcc-stat-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.3rem;
    font-weight: 500;
    color: var(--gcc-success);
    display: block;
}
.gcc-stat-card .gcc-stat-label {
    font-size: 0.72rem;
    color: var(--gcc-muted);
}

[data-testid="stChatMessage"] {
    background-color: var(--gcc-panel);
    border: 1px solid var(--gcc-border);
    border-radius: 10px;
    padding: 4px 6px;
}

.gcc-source-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    background-color: var(--gcc-bg);
    border: 1px solid var(--gcc-border);
    border-left: 2px solid var(--gcc-amber);
    border-radius: 4px;
    padding: 4px 10px;
    margin: 3px 6px 3px 0;
    color: var(--gcc-muted);
}
.gcc-source-chip .gcc-line-range {
    color: var(--gcc-amber);
}
"""
st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)

QUICK_QUESTIONS = [
    "Give me an overview of how this project works, end to end",
    "How does the ingest_repository function work?",
    "How is rate limiting handled when generating embeddings?",
    "What happens if the same repository is indexed twice?",
    "Does it support indexing private repositories?",
]

if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_indexed" not in st.session_state:
    st.session_state.is_indexed = False
if "repo_id" not in st.session_state:
    st.session_state.repo_id = None
if "index_stats" not in st.session_state:
    st.session_state.index_stats = None


def render_sources(sources):
    if not sources:
        return
    chips = "".join(
        f'<span class="gcc-source-chip">{s["file_path"]}'
        f'<span class="gcc-line-range">:{s["start_line"]}-{s["end_line"]}</span></span>'
        for s in sources
    )
    st.markdown(chips, unsafe_allow_html=True)


def process_question(prompt: str):
    st.session_state.messages.append({"role": "user", "content": prompt})
    pipeline = RAGPipeline(repository_id=st.session_state.repo_id, top_k=5)
    response = pipeline.ask(prompt)
    st.session_state.messages.append({
        "role": "assistant",
        "content": response["answer"],
        "sources": response.get("sources", []),
    })


with st.sidebar:
    st.header("Repository Setup")
    repo_url = st.text_input("GitHub repository URL", placeholder="https://github.com/owner/repo")

    if st.button("Index Repository", use_container_width=True):
        if repo_url:
            with st.spinner("Cloning, parsing, and embedding the codebase..."):
                try:
                    result = ingest_repository(repo_url=repo_url, batch_size=50)
                    st.session_state.repo_id = ""
                    st.session_state.is_indexed = True
                    st.session_state.index_stats = result
                except Exception as e:
                    st.error(f"Indexing failed: {e}")
        else:
            st.warning("Enter a repository URL first.")

    if st.session_state.index_stats:
        r = st.session_state.index_stats
        st.markdown(
            f"""
            <div class="gcc-stat-grid">
                <div class="gcc-stat-card"><span class="gcc-stat-value">{r['python_files']}</span><span class="gcc-stat-label">Files parsed</span></div>
                <div class="gcc-stat-card"><span class="gcc-stat-value">{r['chunks']}</span><span class="gcc-stat-label">Chunks extracted</span></div>
                <div class="gcc-stat-card"><span class="gcc-stat-value">{r['embeddings']}</span><span class="gcc-stat-label">New embeddings</span></div>
                <div class="gcc-stat-card"><span class="gcc-stat-value">{r['stored_chunks']}</span><span class="gcc-stat-label">Total in DB</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown(
    """
    <div class="gcc-header"><h1>GitHub Code Chatter 💬</h1></div>
    <div class="gcc-tagline">Ask questions about any public repository — every answer is grounded in its actual source.</div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.is_indexed and st.session_state.repo_id is not None:

    if not st.session_state.messages:
        st.markdown('<div class="gcc-chip-row">', unsafe_allow_html=True)
        cols = st.columns(len(QUICK_QUESTIONS))
        for col, question in zip(cols, QUICK_QUESTIONS):
            with col:
                if st.button(question, key=f"chip_{question}"):
                    with st.spinner("Searching the codebase..."):
                        process_question(question)
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                render_sources(message["sources"])

    if prompt := st.chat_input("Ask how a specific function works..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Searching the codebase and generating an answer..."):
                try:
                    process_question(prompt)
                    last = st.session_state.messages[-1]
                    st.markdown(last["content"])
                    render_sources(last.get("sources"))
                except Exception as e:
                    st.error(f"Something went wrong: {e}")
else:
    st.info("👈 Enter a GitHub URL in the sidebar and index it to start chatting.")