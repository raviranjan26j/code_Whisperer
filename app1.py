import streamlit as st
import os
import subprocess
import shutil
import threading
from git import Repo
from datetime import datetime
import re
import json
from ui_components import apply_custom_css, render_header, render_footer
from util import initialize_rag_pipeline


# --- Session Management ---
if "processing_complete" not in st.session_state: st.session_state.processing_complete = False
if "repo_url" not in st.session_state: st.session_state.repo_url = ""
if "rag_initializing" not in st.session_state: st.session_state.rag_initializing = False

def bg_initialize_rag(repo_path):
    try:
        st.session_state.vectorstore = initialize_rag_pipeline(repo_path)
    except Exception as e:
        print(f"Error in background RAG initialization: {e}")
    finally:
        st.session_state.rag_initializing = False


def run_pipeline(repo_url):
    temp_dir = "./temp_repo"
    st.session_state.temp_dir = temp_dir
    if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
    with st.spinner(" Extracting Repository..."):
        repo = Repo.clone_from(repo_url, temp_dir)
        
    # Start RAG initialization in parallel
    st.session_state.rag_initializing = True
    rag_thread = threading.Thread(
        target=bg_initialize_rag, 
        args=(os.path.abspath(temp_dir),)
    )
    # Add script run context to the thread to allow access to st.session_state
    from streamlit.runtime.scriptrunner import add_script_run_ctx
    add_script_run_ctx(rag_thread)
    rag_thread.start()

    # run gitnexus analyze
    with st.spinner("Analyzing Repository..."):
        subprocess.run(["npx", "--y", "gitnexus", "analyze"], cwd=temp_dir)

        # Basic identifiers
        st.session_state.repo_name = os.path.basename(repo_url.rstrip('/'))
        st.session_state.repo_owner = repo_url.split('/')[-2] if '/' in repo_url else "Unknown"
        st.session_state.repo_url_clean = repo_url.rstrip('/')

        # README snippet
        readme_path = os.path.join(temp_dir, "README.md")
        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as f:
                st.session_state.repo_description = f.read(500) + "..."
        else:
            st.session_state.repo_description = "No description provided."

        # Git metadata
        try:
            # Safely get the default branch name, handling slashes in names (e.g. dependabot branches)
            ref_name = repo.remotes.origin.refs.HEAD.reference.name
            default_branch = ref_name.replace('origin/', '', 1) if ref_name.startswith('origin/') else ref_name
        except Exception:
            try:
                default_branch = repo.active_branch.name
            except Exception:
                default_branch = 'HEAD'
        
        st.session_state.repo_default_branch = default_branch
        try:
            st.session_state.repo_active_branch = repo.active_branch.name
        except Exception:
            st.session_state.repo_active_branch = "Detached HEAD"

        # Use HEAD if default_branch resolution was problematic, ensuring iter_commits succeeds
        commits = list(repo.iter_commits(default_branch if default_branch != 'HEAD' else repo.head))
        st.session_state.repo_total_commits = len(commits)
        contributors = set(c.author.email for c in commits)
        st.session_state.repo_total_contributors = len(contributors)

        if commits:
            st.session_state.repo_last_commit_date = datetime.fromtimestamp(
                commits[0].committed_date).strftime('%Y-%m-%d')
            st.session_state.repo_last_commit_msg = commits[0].message.split('\n')[0][:80]
            st.session_state.repo_first_commit_date = datetime.fromtimestamp(
                commits[-1].committed_date).strftime('%Y-%m-%d')
        else:
            st.session_state.repo_last_commit_date = "N/A"
            st.session_state.repo_last_commit_msg = "N/A"
            st.session_state.repo_first_commit_date = "N/A"

        # Detect languages from file extensions
        ext_counts = {}
        ext_map = {
            ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
            ".java": "Java", ".go": "Go", ".rs": "Rust",
            ".cpp": "C++", ".c": "C", ".rb": "Ruby",
            ".cs": "C#", ".php": "PHP", ".swift": "Swift",
            ".kt": "Kotlin", ".scala": "Scala", ".sh": "Shell",
        }
        for root, dirs, filenames in os.walk(temp_dir):
            dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', '.gitnexus', '.claude')]
            for fn in filenames:
                if fn in ("AGENTS.md", "CLAUDE.md"): continue
                ext = os.path.splitext(fn)[1].lower()
                if ext in ext_map:
                    lang = ext_map[ext]
                    ext_counts[lang] = ext_counts.get(lang, 0) + 1
        top_langs = sorted(ext_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        st.session_state.repo_languages = top_langs

        # Total file count
        total_files = sum(
            len([f for f in files if f not in ("AGENTS.md", "CLAUDE.md")])
            for root, dirs, files in os.walk(temp_dir)
            if not any(d in root for d in ('.git', 'node_modules', '.gitnexus', '.claude'))
        )
        st.session_state.repo_total_files = total_files

        st.session_state.processing_complete = True

st.set_page_config(page_title="Repo Whisperer", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for Background, Animations, and Typography
apply_custom_css()

render_header()

col_empty1, col_main, col_empty2 = st.columns([1, 2, 1])

with col_main:
    # URL input
    if "repo_url" not in st.session_state:
        st.session_state.repo_url = ""
        
    repo_url = st.text_input("Enter GitHub Repository URL", 
        value=st.session_state.repo_url, 
        key="input_repo_url",
        placeholder="https://github.com/username/repo")
    st.session_state.repo_url = repo_url
    
    st.write("") # small gap
    
    # Start button
    if st.button("🚀 Start Extraction", use_container_width=True):
        if repo_url:
            repo_url = repo_url.strip()
            if re.match(r'^(https?://)?(www\.)?github\.com/[\w-]+/[\w.-]+/?$', repo_url):
                run_pipeline(repo_url)
                st.session_state.processing_complete = True
                st.success("Extraction complete! Redirecting...")
                st.switch_page("pages/1_Dashboard_insights.py")
            else:
                st.error("Please enter a valid GitHub repository URL (e.g., https://github.com/username/repo).")
        else:
            st.warning("Please enter a GitHub URL.")

    if st.session_state.processing_complete:
        st.write("")
        if st.button("📊 Go to Dashboard", use_container_width=True):
            st.switch_page("pages/1_Dashboard_insights.py")

st.write("---")

# Helpful documentation section
st.markdown("<h3 style='text-align: center; color: floralwhite margin-bottom: 2rem;'>💡 How It Works ?</h3>", unsafe_allow_html=True)
col_card1, col_card2, col_card3 = st.columns(3)

with col_card1:
    st.markdown("""
    <div class="info-card">
        <h3>1. Connect Repository</h3>
        <p>Simply paste the URL of any public GitHub project. Our intelligence agent immediately parses the source code safely.</p>
    </div>
    """, unsafe_allow_html=True)

with col_card2:
    st.markdown("""
    <div class="info-card">
        <h3>2. Deep AI Analysis</h3>
        <p>GitNexus runs deep scans to understand architectural coherence, measure complexity, and evaluate contributor health seamlessly.</p>
    </div>
    """, unsafe_allow_html=True)

with col_card3:
    st.markdown("""
    <div class="info-card">
        <h3>3. Actionable Insights</h3>
        <p>Uncover risk factors, view real-time dependency maps, and interact with the codebase via our intuitive, AI-driven dashboard.</p>
    </div>
    """, unsafe_allow_html=True)

st.write("---")

render_footer()