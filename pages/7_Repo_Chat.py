import os
os.environ["TRANSFORMERS_NO_TORCHVISION"] = "1"

import ast
import re
import numpy as np
import streamlit as st

from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document

from sentence_transformers import CrossEncoder
from rank_bm25 import BM25Okapi

from ui_components import (
    apply_custom_css,
    render_header,
    render_footer,
    render_lottie_transparent
)


# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="RepoTalk Chat",
    layout="wide",
    initial_sidebar_state="collapsed"
)


# =====================================================
# APPLY GLOBAL THEME
# =====================================================

apply_custom_css()
render_header()


# =====================================================
# MINIMAL PAGE CSS
# =====================================================

st.markdown("""
<style>

/* hide sidebar */
[data-testid="stSidebar"] {
    display: none;
}

/* Force main page to be non-scrollable */
html, body, [data-testid="stAppViewContainer"] {
    overflow: hidden !important;
    height: 100vh !important;
}

/* Adjust main block container for fixed viewport */
.block-container {
    padding-top: 160px !important;
    padding-bottom: 0 !important;
    height: 100vh !important;
    overflow: hidden !important;
    display: flex !important;
    flex-direction: column !important;
}

/* text colors */
html, body, p, span, label, div, li, ul, ol, small, strong, em, h1, h2, h3, h4, h5, h6 {
    color: #e6edf3 !important;
}

/* markdown */
.stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown div {
    color: #e6edf3 !important;
}

/* code blocks */
.stCodeBlock pre, [data-testid="stMarkdownContainer"] pre {
    background: rgba(15,23,35,0.95) !important;
    color: #d6e2f0 !important;
    border-radius: 14px !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    padding: 1rem !important;
    overflow-x: auto !important;
}

/* inline code */
p code, li code, span code {
    background: rgba(255,255,255,0.06) !important;
    color: #d6e2f0 !important;
    padding: 2px 6px !important;
    border-radius: 6px !important;
}

/* chat input placeholder */
[data-testid="stChatInput"] textarea::placeholder {
    color: #aebdce !important;
    opacity: 1 !important;
}

/* input text */
[data-testid="stChatInput"] textarea {
    color: #e6edf3 !important;
}

/* hide spinner */
[data-testid="stSpinner"] {
    display: none !important;
}

</style>
""", unsafe_allow_html=True)


# =====================================================
# CONFIG
# =====================================================

API_KEY = st.secrets["NVIDIA_API_KEY"]


# =====================================================
# SESSION STATE
# =====================================================

if "repochat_messages" not in st.session_state:
    st.session_state.repochat_messages = []

if "repo_ready" not in st.session_state:
    st.session_state.repo_ready = False

if "reranker" not in st.session_state:

    st.session_state.reranker = CrossEncoder(
        "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )


# =====================================================
# LOAD REPOSITORY
# =====================================================

current_file_dir = os.path.dirname(
    os.path.abspath(__file__)
)

project_root = os.path.dirname(
    current_file_dir
)

repo_path = os.path.join(
    project_root,
    "temp_repo"
)

if not os.path.exists(repo_path):

    st.error(
        "Repository not found. Please process repository first."
    )

    st.stop()

st.session_state.repo_ready = True


# =====================================================
# HELPERS
# =====================================================

def tokenize(text):

    return re.findall(
        r"[A-Za-z0-9_]+",
        text.lower()
    )


def chunk_file(file_path, content):

    ext = file_path.split(".")[-1].lower()

    docs = []

    if ext == "py":

        try:

            tree = ast.parse(content)

            lines = content.splitlines()

            for node in ast.walk(tree):

                if isinstance(
                    node,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                        ast.ClassDef
                    )
                ):

                    chunk = "\n".join(
                        lines[node.lineno - 1:node.end_lineno]
                    )

                    node_name = getattr(
                        node,
                        "name",
                        ""
                    )

                    chunk_type = type(node).__name__

                    enhanced_content = f"""
FILE: {file_path}
NAME: {node_name}
TYPE: {chunk_type}

CODE:
{chunk}
"""

                    docs.append(
                        Document(
                            page_content=enhanced_content,
                            metadata={
                                "file": file_path,
                                "type": "python",
                                "name": node_name,
                                "chunk_type": chunk_type
                            }
                        )
                    )

            if docs:
                return docs

        except:
            pass

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=150
    )

    parts = splitter.split_text(content)

    enhanced_docs = []

    for p in parts:

        enhanced_content = f"""
FILE: {file_path}
TYPE: {ext}

CONTENT:
{p}
"""

        enhanced_docs.append(
            Document(
                page_content=enhanced_content,
                metadata={
                    "file": file_path,
                    "type": ext
                }
            )
        )

    return enhanced_docs


def build_bm25(docs):

    corpus = [
        tokenize(d.page_content)
        for d in docs
    ]

    return BM25Okapi(corpus)


def bm25_search(query, bm25, docs, top_k=6):

    tokenized = tokenize(query)

    scores = bm25.get_scores(tokenized)

    ranked_idx = np.argsort(scores)[::-1][:top_k]

    return [docs[i] for i in ranked_idx]


def filename_search(query, docs):

    query = query.lower()

    matches = []

    for d in docs:

        file_path = d.metadata.get(
            "file",
            ""
        ).lower()

        if query in file_path:
            matches.append(d)

    return matches[:5]


def hybrid_retrieval(
    queries,
    vectorstore,
    bm25,
    docs
):

    all_docs = []

    for q in queries:

        dense = vectorstore.similarity_search(
            q,
            k=8
        )

        sparse = bm25_search(
            q,
            bm25,
            docs,
            top_k=6
        )

        filename_matches = filename_search(
            q,
            docs
        )

        all_docs.extend(
            filename_matches +
            dense +
            sparse
        )

    return all_docs


def deduplicate_docs(docs):

    seen = set()

    unique = []

    for d in docs:

        key = (
            hash(d.page_content),
            d.metadata.get("file")
        )

        if key not in seen:

            seen.add(key)

            unique.append(d)

    return unique


def rerank(query, docs):

    reranker = st.session_state.reranker

    pairs = [
        (query, d.page_content)
        for d in docs
    ]

    scores = reranker.predict(
        pairs,
        batch_size=8
    )

    ranked = sorted(
        zip(docs, scores),
        key=lambda x: x[1],
        reverse=True
    )

    return [d for d, _ in ranked]


# =====================================================
# INITIALIZE RAG
# =====================================================

if "vectorstore" not in st.session_state or "bm25" not in st.session_state or "docs" not in st.session_state:
    loading_placeholder = st.empty()
    with loading_placeholder.container():
        st.markdown(
            "<h4 style='text-align: center; color: #a0aab2; margin-bottom: -15px;'>Ingesting and analyzing repository structure...</h4>",
            unsafe_allow_html=True
        )
        render_lottie_transparent(os.path.join(os.path.dirname(__file__), "..", "assets", "AI.json"), height=200)

    with st.spinner("Indexing repository..."):

        all_docs = []

        EXCLUDE_DIRS = {
            ".git",
            "node_modules",
            ".venv",
            "__pycache__",
            "dist",
            "build",
            ".gitnexus"
        }

        ALLOWED_EXTENSIONS = {
            ".py",
            ".js",
            ".ts",
            ".java",
            ".json",
            ".md",
            ".txt"
        }

        for root, dirs, files in os.walk(repo_path):

            dirs[:] = [
                d for d in dirs
                if d not in EXCLUDE_DIRS
            ]

            for f in files:

                path = os.path.join(root, f)

                ext = os.path.splitext(f)[1].lower()

                if ext not in ALLOWED_EXTENSIONS:
                    continue

                try:

                    with open(
                        path,
                        "r",
                        encoding="utf-8",
                        errors="ignore"
                    ) as file:

                        content = file.read()

                    if not content.strip():
                        continue

                    all_docs.extend(
                        chunk_file(path, content)
                    )

                except:
                    continue

        embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )

        vectorstore = FAISS.from_documents(
            all_docs,
            embeddings
        )

        bm25 = build_bm25(all_docs)

        st.session_state.vectorstore = vectorstore
        st.session_state.docs = all_docs
        st.session_state.bm25 = bm25

    loading_placeholder.empty()


# =====================================================
# HERO SECTION
# =====================================================

# =====================================================
# UI LAYOUT
# =====================================================

_spacer_col, _btn_col, _title_col, _spacer_col = st.columns([0.1, 2, 5, 2])
with _btn_col:
    st.markdown("<div style='padding-left: 20px;'>", unsafe_allow_html=True)
    if st.button("◀  Go to Dashboard", key="back_to_dashboard"):
        st.switch_page("pages/1_Dashboard_insights.py")
    st.markdown("</div>", unsafe_allow_html=True)
with _title_col:
    st.markdown("<h2 style='text-align: center; color: cornflowerblue;'>RepoTalk Chat</h2>", unsafe_allow_html=True)


# =====================================================
# CHAT
# =====================================================
# =====================================================
# CHAT
# =====================================================

llm = ChatNVIDIA(
    model="meta/llama-3.1-70b-instruct",
    api_key=API_KEY,
    temperature=0.2,
    max_tokens=2048
)

col_spacer1, col_chat, col_spacer2 = st.columns([0.1, 9.8, 0.1])

with col_chat:
    # Display previously recorded messages

    chat_container = st.container(height=350, border=True)
    with chat_container:
        for msg in st.session_state.repochat_messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    query = st.chat_input("Ask me anything about the repository...")

    if query:
        with chat_container:
            with st.chat_message("user"):
                st.markdown(query)

        st.session_state.repochat_messages.append({
            "role": "user",
            "content": query
        })

        # -----------------------------------------
        # AI THINKING ANIMATION
        # -----------------------------------------
        with chat_container:
            thinking_placeholder = st.empty()
            with thinking_placeholder.container():
                with st.chat_message("assistant"):
                    anim_col, _ = st.columns([1, 9])
                    with anim_col:
                        render_lottie_transparent(os.path.join(os.path.dirname(__file__), "..", "assets", "chat_thinking.json"), height=50)

        try:
            if "bm25" not in st.session_state or "docs" not in st.session_state:
                thinking_placeholder.empty()
                st.error("Search index not initialized. Please refresh the page to re-initialize the repository context.")
                st.stop()

            all_results = hybrid_retrieval(
                [query],
                st.session_state.vectorstore,
                st.session_state.bm25,
                st.session_state.docs
            )

            unique_docs = deduplicate_docs(all_results)
            ranked_docs = rerank(query, unique_docs[:30])
            top_docs = ranked_docs[:6]

            context = "\n\n".join([d.page_content for d in top_docs])

            # Clear thinking animation before showing response
            thinking_placeholder.empty()

            prompt = ChatPromptTemplate.from_messages([
                ("system", """
You are 'RepoTalk', an AI assistant powered by Gitingest context to help developers analyze and understand their codebase based on the retrieved snippets below.

Strict Rules:
- Use ONLY provided context
- No hallucinations
- Mention files/functions/classes
- Explain flow clearly
- If missing say "Not found in codebase"

Provide detailed, structured and accurate responses.

Context Snippets:
{context}
"""),
                ("human", "{input}")
            ])

            chain = prompt | llm
            full = ""

            with chat_container:
                with st.chat_message("assistant"):
                    response_placeholder = st.empty()
                    stream = chain.stream({
                        "context": context,
                        "input": query
                    })

                    for chunk in stream:
                        token = chunk.content if hasattr(chunk, "content") else str(chunk)
                        full += token
                        response_placeholder.markdown(full)

                    sources = list(set([d.metadata["file"] for d in top_docs]))
                    sources_md = "\n".join([f"- `{s}`" for s in sources])
                    final_response = f"{full}\n\n### 📂 Sources\n\n{sources_md}"
                    response_placeholder.markdown(final_response)

            st.session_state.repochat_messages.append({
                "role": "assistant",
                "content": final_response
            })
            st.rerun()

        except Exception as e:
            thinking_placeholder.empty()
            st.error(str(e))


# =====================================================
# FOOTER
# =====================================================

render_footer()