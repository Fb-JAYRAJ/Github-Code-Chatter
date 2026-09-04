import streamlit as st
from pathlib import Path

# Import Aniket's backend functions
from backend.ingest import ingest_repository
from backend.rag_pipeline import RAGPipeline

st.set_page_config(page_title="GitHub Code Chatter", layout="wide")
st.title("GitHub Code Chatter 💬")

# 1. Initialize Session State for Chat and Indexing Status
if "messages" not in st.session_state:
    st.session_state.messages = []
if "is_indexed" not in st.session_state:
    st.session_state.is_indexed = False
if "repo_id" not in st.session_state:
    st.session_state.repo_id = None

# 2. Sidebar: GitHub URL Input & Pipeline Trigger
with st.sidebar:
    st.header("Repository Setup")
    repo_url = st.text_input("GitHub Repository URL:")
    
    if st.button("Index Repository"):
        if repo_url:
            with st.spinner("Cloning & chunking codebase... (This may take a moment due to API limits)"):
                try:
                    # Trigger the backend ingestion pipeline
                    result = ingest_repository(repo_url=repo_url, batch_size=50)
                    
                    # FIX: Match the empty string currently saved in ChromaDB
                    st.session_state.repo_id = "" 
                    
                    st.session_state.is_indexed = True
                    st.success("Repository successfully parsed and stored in ChromaDB!")
                    
                    # Display the metrics returned by ingest.py
                    st.divider()
                    st.subheader("Indexing Metrics")
                    st.write(f"**Python Files Parsed:** {result['python_files']}")
                    st.write(f"**Code Chunks Extracted:** {result['chunks']}")
                    st.write(f"**New Embeddings:** {result['embeddings']}")
                    st.write(f"**Total Chunks in DB:** {result['stored_chunks']}")
                    
                except Exception as e:
                    st.error(f"Ingestion failed: {e}")
        else:
            st.warning("Please enter a valid GitHub URL.")

# 3. Main Chat Interface
# FIX: Use `is not None` because an empty string `""` evaluates to False in Python
if st.session_state.is_indexed and st.session_state.repo_id is not None:
    
    # Render existing conversation
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Re-render sources if they exist for assistant messages
            if "sources" in message and message["sources"]:
                with st.expander("View Source Files"):
                    for source in message["sources"]:
                        st.markdown(f"- `{source['file_path']}` (Lines {source['start_line']}-{source['end_line']})")

    # Handle new user input
    if prompt := st.chat_input("Ask how a specific function works..."):
        
        # Display user prompt
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Retrieve context and generate Gemini response
        with st.chat_message("assistant"):
            with st.spinner("Searching vector database and generating answer..."):
                try:
                    # Initialize the pipeline with the current repo ID (which is now "")
                    pipeline = RAGPipeline(
                        repository_id=st.session_state.repo_id,
                        top_k=5,
                        model="gemini-3.6-flash"
                    )
                    
                    # Get the response dictionary from rag_pipeline.py
                    response = pipeline.ask(prompt)
                    
                    answer = response["answer"]
                    sources = response["sources"]
                    
                    st.markdown(answer)
                    
                    # Display the sources cited in a clean expander
                    if sources:
                        with st.expander("View Source Files"):
                            for source in sources:
                                st.markdown(f"- `{source['file_path']}` (Lines {source['start_line']}-{source['end_line']})")
                    
                    # Save response and sources to session state
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": answer,
                        "sources": sources
                    })
                    
                except Exception as e:
                    st.error(f"An error occurred while generating the answer: {e}")
else:
    st.info("👈 Enter a GitHub URL in the sidebar to clone the repository and initialize the RAG pipeline.")