import streamlit as st
if not st.session_state.get("processing_complete"):
    st.switch_page("app1.py")

import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain.tools import tool
import os

@tool
def read_repository_file(file_path: str):
    """
    Read the raw content of a file from the repository. 
    Use this when the user asks for the source code of a specific file.
    The path should be relative to the repository root (e.g., 'src/main.ts').
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    repo_path = os.path.join(project_root, "temp_repo")
    full_path = os.path.join(repo_path, file_path)
    
    if not os.path.exists(full_path):
        return f"Error: File '{file_path}' not found in repository."
    
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Prevent massive files from blowing up the context window
            if len(content) > 20000:
                return content[:20000] + f"\n\n...[TRUNCATED: File exceeds 20,000 characters. Length was {len(content)}]"
            return content
    except Exception as e:
        return f"Error reading file '{file_path}': {e}"

async def get_repo_data(prompt):
    try:
        # Use cached MCP tools from session state to avoid spawning a new
        # npx subprocess on every message. We also use `async with` so the
        # client (and its subprocess) is properly cleaned up after use when
        # the tools are first fetched.
        if "mcp_client" not in st.session_state:
            st.session_state["mcp_client"] = MultiServerMCPClient(
                {
                    "gitnexus": {
                        "transport": "stdio",
                        "command": "npx",
                        "args": ["-y", "gitnexus", "mcp"]
                    }
                }
            )
            st.session_state["mcp_tools"] = await st.session_state["mcp_client"].get_tools()

        tools = list(st.session_state["mcp_tools"]) + [read_repository_file]

        llm = ChatNVIDIA(
            model="meta/llama-3.1-70b-instruct",
            api_key="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", 
            temperature=0.2,
            top_p=0.7,
            max_completion_tokens=1024,
        )   

        agent = create_agent(
            llm,
            tools
        )

        system_prompt = """
        You are 'Repo Whisperer', an AI assistant designed to help developers analyze and understand their codebase.
        - You can answer general greetings and conversation.
        - For repository-specific questions, use your tools to query the code or read file contents.
        - If you need structural info (like "which file has many references"), use the 'cypher' tool.
        
        Knowledge Graph Schema:
        - Nodes: File (attr: filePath), Symbol (attr: name)
        - Relationships: File -[:IMPORT]-> File, File -[:HAS_SYMBOL]-> Symbol
        
        CRITICAL RULES FOR PREVENTING CONTEXT OVERFLOW:
        1. Cypher Tool: ALWAYS append `LIMIT 10` (or fewer) to your Cypher queries. NEVER query for all nodes/edges without a strict limit, as this will crash the system.
        2. Reading Files: Only read specific files if specifically requested, and be aware their contents may be truncated.

        Example Cypher for "lots of references":
        MATCH (f:File)<-[r:IMPORT]-(other) RETURN f.filePath, count(r) ORDER BY count(r) DESC LIMIT 5

        - Use 'temp_repo' as the target repository name.
        - If you don't need a tool to answer (like for "hi"), just reply directly.
        """

        result = await agent.ainvoke({
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
        })

        if isinstance(result, dict) and 'messages' in result:
            return result['messages'][-1].content
        else:
            # Fallback for different response formats
            if hasattr(result, 'content'):
                return result.content
            return str(result)
            
    except Exception as e:
        st.error(f"Error in get_repo_data: {e}")
        return f"An error occurred: {e}"



st.markdown("""
    <style>
    /* Target the container holding the nav bar */
    div.fixed-nav {
        position: fixed;
        top: 0px;
        left: 0;
        width: 100%;
        background-color: white; /* Match your app theme */
        padding: 10px 20px;
        z-index: 1000; /* Ensure it stays above other content */
        border-bottom: 1px solid #ddd;
    }
    /* Add padding to the top of the main content so it isn't hidden by the bar */
    .stApp {
        padding-top: 80px;
    }
    </style>
    """, unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<div class="fixed-nav">', unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🏠 Home", type="tertiary"):
            st.switch_page("app1.py")
    with col2:
        if st.button("📊 Dashboard", type="tertiary"):
            st.switch_page("pages/2_Dashboard.py")
    with col3:
        if st.button("🤖 Repo Chat", type="primary"):
            pass
    with col4:
        if st.button("⚙️ Settings", type="tertiary"):
            st.switch_page("pages/4_Settings.py")
    st.markdown('</div>', unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

chat_container = st.container(height=350, border=True)
with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]): 
            st.markdown(msg["content"])

if prompt := st.chat_input("Ask about your code..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with chat_container:
        with st.chat_message("user"): 
            st.markdown(prompt)
    
    with st.spinner("Thinking..."):
        retrieved = asyncio.run(get_repo_data(prompt))
    
    with chat_container:
        with st.chat_message("assistant"): 
            st.markdown(retrieved)
    
    st.session_state.messages.append({"role": "assistant", "content": retrieved})
    st.rerun()