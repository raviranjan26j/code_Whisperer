import streamlit as st
import shutil
import os
from ui_components import render_header, render_footer, apply_custom_css

apply_custom_css()
render_header()

if st.button("🗑️ Clear Database"):
    # Safely get temp_dir or use default
    temp_dir = st.session_state.get("temp_dir", "./temp_repo")
    
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        
        # Reset core session state
        st.session_state.processing_complete = False
        st.session_state.repochat_messages = []
        
        # Clear RAG components if they exist
        for key in ["vectorstore", "bm25", "docs"]:
            if key in st.session_state:
                del st.session_state[key]
                
        st.success("Database wiped successfully. Redirecting...")
        st.switch_page("app1.py")
    else:
        st.info("No temporary database found to clear.")

render_footer()
