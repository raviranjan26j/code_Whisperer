import streamlit as st
import os
from gitingest import ingest
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate

# Check if processing is complete to allow access
if not st.session_state.get("processing_complete"):
    st.switch_page("app1.py")

# Persistent fixed navigation bar styling matching 3_Chat.py
st.markdown("""
    <style>
    div.fixed-nav {
        position: fixed;
        top: 0px;
        left: 0;
        width: 100%;
        background-color: white;
        padding: 10px 20px;
        z-index: 1000;
        border-bottom: 1px solid #ddd;
    }
    .stApp {
        padding-top: 80px;
    }
    </style>
    """, unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<div class="fixed-nav">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🏠 Home", type="tertiary", key="home"):
            st.switch_page("app1.py")
    with col2:
        if st.button("📊 Dashboard", type="tertiary", key="dash"):
            st.switch_page("pages/2_Dashboard.py")
    with col3:
        if st.button("🤖 Repo Chat", type="tertiary", key="chat"):
            st.switch_page("pages/3_Chat.py")
    with col4:
        # Provide an active primary button showing we are in RepoTalk Chat as alternative
        if st.button("💬 RepoTalk", type="primary", key="repotalk"):
            pass
    st.markdown('</div>', unsafe_allow_html=True)

st.title("🤖 RepoTalk Chat (Gitingest RAG)")

if "repochat_messages" not in st.session_state:
    st.session_state.repochat_messages = []

# Initialize Vectorstore with Gitingest
if "vectorstore" not in st.session_state:
    with st.spinner("Ingesting and analyzing repository structure with Gitingest..."):
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            repo_path = os.path.join(project_root, "temp_repo")
            
            # Use gitingest on local directory
            exclude_patterns = {".claude", ".gitnexus", "AGENTS.md", "CLAUDE.md"}
            summary, tree, content = ingest(repo_path, exclude_patterns=exclude_patterns)
            
            # Batch string into chunks suitable for indexing
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
            combined_text = f"Repository Summary:\\n{summary}\\n\\nRepository Structure:\\n{tree}\\n\\nCodebase Files:\\n{content}"
            chunks = text_splitter.split_text(combined_text)
            
            # Embed using local HF model
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            st.session_state.vectorstore = FAISS.from_texts(chunks, embeddings)
            st.success("Successfully ingested the codebase!")
        except Exception as e:
            st.error(f"Error initializing RAG context: {e}")

# Display previously recorded messages
chat_container = st.container(height=350, border=True)
with chat_container:
    for msg in st.session_state.repochat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# Chat Input & Invocation
if prompt := st.chat_input("Ask me anything about the codebase structure or files..."):
    # Render user prompt
    st.session_state.repochat_messages.append({"role": "user", "content": prompt})
    with chat_container:
        with st.chat_message("user"):
            st.markdown(prompt)

    # Retrieval generation
    with st.spinner("Thinking..."):
        try:
            llm = ChatNVIDIA(
                model="meta/llama-3.1-70b-instruct",
                api_key="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", 
                temperature=0.2,
                max_tokens=1024,
            )
            
            # Setup retriever to get top 5 chunks
            retriever = st.session_state.vectorstore.as_retriever(search_kwargs={"k": 5})
            
            system_prompt = (
                "You are 'RepoTalk', an AI assistant powered by Gitingest context to help developers "
                "analyze and understand their codebase based on the retrieved snippets below.\\n"
                "Provide detailed, structured and accurate responses.\\n\\n"
                "Context Snippets:\\n{context}"
            )
            
            prompt_tmpl = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{input}"),
            ])
            
            def format_docs(docs):
                return "\\n\\n".join(doc.page_content for doc in docs)
                
            rag_chain = (
                {"context": retriever | format_docs, "input": RunnablePassthrough()}
                | prompt_tmpl
                | llm
            )
            
            response = rag_chain.invoke(prompt)
            answer = response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            answer = f"An error occurred while fetching the answer: {str(e)}"
            
    with chat_container:
        with st.chat_message("assistant"):
            st.markdown(answer)
            
    st.session_state.repochat_messages.append({"role": "assistant", "content": answer})
    st.rerun()
