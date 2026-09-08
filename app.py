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

/* Hide Streamlit chrome so it doesn't read as a template app */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { visibility: hidden; height: 0; }

.stApp {
    background-color: var(--gcc-bg);
}
.stApp::before {
    content: "";
    position: fixed;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--gcc-accent);
    z-index: 999;
}

.block-container {
    padding-top: 2.5rem !important;
    max-width: 1100px;
}

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: var(--gcc-bg); }
::-webkit-scrollbar-thumb { background: var(--gcc-border); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--gcc-accent); }

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
    margin-bottom: 1.8rem;
}

[data-testid="stSidebar"] {
    background-color: var(--gcc-panel);
    border-right: 1px solid var(--gcc-border);
}
[data-testid="stTextInput"] input {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
    border-radius: 6px !important;
}

/* Primary CTA (Index Repository) — solid accent */
.stButton > button[kind="primary"] {
    background-color: var(--gcc-accent);
    color: #0F1117;
    border: none;
    font-weight: 600;
    border-radius: 6px;
}
.stButton > button[kind="primary"]:hover {
    opacity: 0.85;
    color: #0F1117;
}

/* Secondary (quick-question chips) — quiet outline */
.stButton > button[kind="secondary"] {
    background-color: transparent;
    border: 1px solid var(--gcc-border);
    color: var(--gcc-muted);
    font-weight: 400;
    font-size: 0.85rem;
    border-radius: 20px;
}
.stButton > button[kind="secondary"]:hover {
    border-color: var(--gcc-accent);
    color: var(--gcc-text);
}

[data-testid="stAlert"] {
    border-radius: 8px;
    font-family: 'IBM Plex Sans', sans-serif;
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
    padding: 6px 8px;
    margin-bottom: 6px;
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

.gcc-empty-state {
    background-color: var(--gcc-panel);
    border: 1px solid var(--gcc-border);
    border-radius: 12px;
    padding: 36px 40px;
    margin-top: 24px;
    text-align: center;
}
.gcc-empty-state .gcc-empty-icon {
    font-size: 2rem;
    margin-bottom: 10px;
}
.gcc-empty-state h3 {
    color: var(--gcc-text);
    font-size: 1.15rem;
    margin: 0 0 8px 0;
}
.gcc-empty-state p {
    color: var(--gcc-muted);
    font-size: 0.9rem;
    max-width: 480px;
    margin: 0 auto 24px auto;
}
.gcc-feature-row {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 12px;
    text-align: left;
}
.gcc-feature {
    background-color: var(--gcc-bg);
    border: 1px solid var(--gcc-border);
    border-radius: 8px;
    padding: 12px 14px;
}
.gcc-feature strong {
    display: block;
    color: var(--gcc-text);
    font-size: 0.85rem;
    margin-bottom: 4px;
}
.gcc-feature span {
    color: var(--gcc-muted);
    font-size: 0.78rem;
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

    if st.button("Index Repository", type="primary", use_container_width=True):
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
        st.success("Repository indexed and stored in ChromaDB.")
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
        cols = st.columns(len(QUICK_QUESTIONS))
        for col, question in zip(cols, QUICK_QUESTIONS):
            with col:
                if st.button(question, key=f"chip_{question}", type="secondary"):
                    with st.spinner("Searching the codebase..."):
                        process_question(question)
                    st.rerun()

    for message in st.session_state.messages:
        avatar = "🧑‍💻" if message["role"] == "user" else "💬"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])
            if message.get("sources"):
                render_sources(message["sources"])

    if prompt := st.chat_input("Ask how a specific function works..."):
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(prompt)
        with st.chat_message("assistant", avatar="💬"):
            with st.spinner("Searching the codebase and generating an answer..."):
                try:
                    process_question(prompt)
                    last = st.session_state.messages[-1]
                    st.markdown(last["content"])
                    render_sources(last.get("sources"))
                except Exception as e:
                    st.error(f"Something went wrong: {e}")
else:
    st.markdown(
        """
        <div class="gcc-empty-state">
            <div class="gcc-empty-icon">📂</div>
            <h3>Point it at a repository to get started</h3>
            <p>Paste a public GitHub URL in the sidebar and index it — then ask anything about how the code works.</p>
            <div class="gcc-feature-row">
                <div class="gcc-feature"><strong>AST-based parsing</strong><span>Chunks at the function/class level, not fixed line counts</span></div>
                <div class="gcc-feature"><strong>Grounded answers</strong><span>Every claim cites a real file path and line range</span></div>
                <div class="gcc-feature"><strong>Resumable indexing</strong><span>Skips chunks that are already embedded</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
