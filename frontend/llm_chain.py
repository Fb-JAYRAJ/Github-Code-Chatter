# frontend/llm_chain.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from frontend.prompt_templates import SYSTEM_PROMPT

def format_docs(docs):
    """Formats retrieved code chunks and extracts file path metadata for citations."""
    formatted_chunks = []
    for doc in docs:
        source_file = doc.metadata.get("source", "Unknown File")
        lang = doc.metadata.get("language", "")
        formatted_chunks.append(
            f"--- FILE: {source_file} ---\n```{lang}\n{doc.page_content}\n```"
        )
    return "\n\n".join(formatted_chunks)

def generate_rag_response(retriever, query: str, api_key: str) -> str:
    """Retrieves relevant code chunks and runs the Gemini generation chain."""
    # 1. Fetch relevant code chunks using Aniket's retriever interface
    if hasattr(retriever, "invoke"):
        docs = retriever.invoke(query)
    else:
        docs = retriever.get_relevant_documents(query)

    # 2. Format the context with file citations
    context_text = format_docs(docs)

    # 3. Setup prompt
    prompt = ChatPromptTemplate.from_template(SYSTEM_PROMPT)
    
    # 4. Setup Gemini LLM using a simple dictionary to satisfy Pydantic
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0, 
        google_api_key=api_key,
        client_options={"api_endpoint": "generativelanguage.googleapis.com"}
    )
    
    # 5. Run chain
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"context": context_text, "question": query})