import streamlit as st
import shutil

st.title("🌐 Repo Whisperer")

with st.container(border=True):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🏠 Home", type="tertiary"):
            st.switch_page("app1.py")
    with col2:
        if st.button("📊 Dashboard", type="tertiary"):
            st.switch_page("pages/2_Dashboard.py")
    with col3:
        if st.button("🤖 Repo Chat", type="tertiary"):
            st.switch_page("pages/3_Chat.py")
    with col4:
        if st.button("⚙️ Settings", type="primary"):
            pass

if st.button("🗑️ Clear Database"):
    shutil.rmtree(st.session_state.temp_dir)
    st.session_state.processing_complete = False
    st.session_state.messages = []
    st.success("Database wiped.")