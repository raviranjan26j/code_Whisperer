import os
import re
import git
import pandas as pd
import plotly.express as px
import streamlit as st
import requests
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from datetime import date, timedelta, datetime
from collections import defaultdict
from ui_components import apply_custom_css, render_header, render_footer

if not st.session_state.get("processing_complete"):
    st.switch_page("app1.py")

# Ensure LLM model initialization
def get_ai_reviewer():
    return ChatNVIDIA(
        model="meta/llama-3.1-70b-instruct",
        api_key="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", 
        temperature=0.2,
        top_p=0.7,
        max_completion_tokens=1024,
    )

st.set_page_config(page_title="Repo Insights", layout="wide")

# Apply custom CSS and render header
apply_custom_css()
render_header()

repo_owner = st.session_state.get("repo_owner")
repo_name = st.session_state.get("repo_name")

if not repo_owner or not repo_name or repo_owner == "Unknown":
    st.warning("Repository details are incomplete. Please start extraction from the Home page.")
    st.stop()

# Navigation row
_spacer, _btn_col1, _btn_col2 = st.columns([5.3, 1.1, 1.1])

with _btn_col1:
    if st.button("📊 Dashboard", use_container_width=True):
        st.switch_page("pages/1_Dashboard_insights.py")
with _btn_col2:
    if st.button("💬 RepoTalk", use_container_width=True):
        st.switch_page("pages/7_Repo_Chat.py")

st.markdown(f"""
<div style="
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(100,149,237,0.25);
    border-radius: 16px;
    padding: 1rem 1.5rem;
    backdrop-filter: blur(6px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.6);
    margin-bottom: 1.5rem;
    display: flex;
    align-items: center;
    gap: 10px;
">
    <div style="font-size: 1.5rem;">📈</div>
    <div>
        <div style="font-size: 1.2rem; font-weight: 700; color: #fff;">Repository Insights</div>
        <div style="font-size: 0.9rem; color: cornflowerblue; font-weight: 600;">{repo_owner}/{repo_name}</div>
    </div>
</div>
""", unsafe_allow_html=True)

def fetch_pull_requests(owner, repo):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=all&per_page=5"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

def fetch_pr_diff(owner, repo, pull_number):
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"
    headers = {"Accept": "application/vnd.github.v3.diff"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    return ""

CODING_STANDARDS = {
    "Security": "Hardcoded secrets, vulnerable dependencies, SQL injection, insecure API usage.",
    "Code Quality": "Logic errors, complexity, redundant code, edge case handling, bug potential.",
    "Maintainability": "Naming conventions, documentation/comments, modularity, readability.",
    "Performance": "Inefficient loops, resource leaks, unnecessary computations, optimization opportunities."
}

WEIGHTS = {
    "Security": 0.35,
    "Code Quality": 0.30,
    "Maintainability": 0.20,
    "Performance": 0.15
}

def generate_ai_review(diff: str):
    if not diff:
        return {"error": "Could not fetch diff for this Pull Request."}
    
    if len(diff) > 20000:
        diff = diff[:20000] + "\n...[TRUNCATED]"
        
    llm = get_ai_reviewer()
    
    standards_prompt = "\n".join([f"- {k}: {v}" for k, v in CODING_STANDARDS.items()])
    
    system_prompt = (
        "You are an expert AI code reviewer. Your task is to analyze the following Git diff "
        "and evaluate it based on these standards:\n"
        f"{standards_prompt}\n\n"
        "Instructions:\n"
        "1. Give a score from 0 to 10 for each category (0 is poor/risky, 10 is excellent/safe).\n"
        "2. Provide a detailed summary of the review (markdown format).\n"
        "3. If the diff is perfectly fine, you can still give high scores (9-10) and say 'no major action needed'.\n"
        "4. Your response MUST be valid JSON. Ensure all newlines in the 'review_text' are properly escaped as '\\n'.\n"
        "{\n"
        "  \"scores\": {\"Security\": 8, \"Code Quality\": 7, \"Maintainability\": 9, \"Performance\": 10},\n"
        "  \"review_text\": \"... markdown review text ...\"\n"
        "}"
    )
    user_prompt = f"Diff:\n{diff}"
    
    try:
        import json
        response = llm.invoke([("system", system_prompt), ("user", user_prompt)])
        content = response.content
        
        # Try to find JSON in the response if the LLM adds chatter
        if "{" in content and "}" in content:
            start = content.find("{")
            end = content.rfind("}") + 1
            json_str = content[start:end]
            
            # Use strict=False to handle unescaped newlines/tabs from AI
            data = json.loads(json_str, strict=False)
            
            # Calculate Risk Score (0-100)
            # Weighted average of scores (which are 0-10, so multiply by 10)
            total_score = 0
            for cat, weight in WEIGHTS.items():
                cat_score = data.get("scores", {}).get(cat, 10) # Default to 10 if missing
                total_score += (cat_score * 10) * weight
            
            data["total_score"] = round(total_score)
            return data
        else:
            return {"error": "AI returned invalid format", "raw": content}
    except Exception as e:
        return {"error": f"Error connecting to AI Provider: {e}"}

from datetime import date, timedelta

# Helper to fetch commits
def fetch_commits_by_date(owner, repo, start, end):
    since_str = f"{start}T00:00:00Z"
    until_str = f"{end}T23:59:59Z"
    url = f"https://api.github.com/repos/{owner}/{repo}/commits?since={since_str}&until={until_str}&per_page=100"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return []

def generate_release_notes(commits) -> str:
    if not commits:
        return "No commits provided."
        
    commit_texts = []
    for c in commits:
        # Extract the commit message and author name (handle missing author safely)
        msg = c.get('commit', {}).get('message', '').split('\n')[0]
        author = c.get('commit', {}).get('author', {}).get('name', 'Unknown')
        commit_texts.append(f"- {msg} (by {author})")
        
    commits_str = "\n".join(commit_texts)
    
    # Prune if there are way too many commits to avoid context length error
    if len(commits_str) > 20000:
        commits_str = commits_str[:20000] + "\n...[TRUNCATED]"
        
    llm = get_ai_reviewer()
    system_prompt = (
        "You are an expert technical writer and release manager. Your task is to review the following "
        "list of Git commits and generate a well-formatted Markdown Release Note. "
        "Categorize the commits logically (e.g., 'Features', 'Bug Fixes', 'Refactoring & Maintenance'). "
        "Summarize verbose commits and make it user-friendly. "
        "Start directly with the markdown formatted output."
    )
    user_prompt = f"Commits:\n{commits_str}"
    
    try:
        response = llm.invoke([("system", system_prompt), ("user", user_prompt)])
        return response.content
    except Exception as e:
        return f"Error connecting to AI Provider: {e}"

def analyze_feature_fix_ratio(days=7):
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_file_dir)
    repo_path = os.path.join(project_root, "temp_repo")
    repo = git.Repo(repo_path)

    # Calculate 'since' date
    since_date = datetime.now() - timedelta(days=days)
    since_str = since_date.strftime('%Y-%m-%d')

    with st.spinner(f"Classifying Commits from the last {days} days..."):
        commits = list(repo.iter_commits(since=since_str))
        
        if not commits:
            st.session_state.commit_stats = None
            return

        messages = [c.message.split('\n')[0] for c in commits]

        client = ChatNVIDIA(
            model="meta/llama-3.1-70b-instruct",
            api_key="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",
            temperature=0.1,
        )

        prompt = f"""
        You are a Git analyst. Classify all {len(commits)} commit messages below into exactly three categories:
        1. 'Feature' (new functionality, enhancements)
        2. 'Fix' (bug fixes, patches)
        3. 'Refactor' (code cleanup, maintenance, documentation, anything else)

        Rules:
        - Every single message must be counted.
        - The sum of counts MUST equal {len(commits)}.
        - Return ONLY the counts in the format: Feature: X, Fix: Y, Refactor: Z

        Messages:
        {chr(10).join(messages)}
        """
        try:
            response = client.invoke(prompt).content

            def get_count(key, text):
                # Search for the key, handle case insensitivity and optional plural 's'
                m = re.search(f"{key}s?:?\\s*(\\d+)", text, re.IGNORECASE)
                return int(m.group(1)) if m else 0

            feat = get_count("Feature", response)
            fix = get_count("Fix", response)
            ref = get_count("Refactor", response)
            
            # If AI missed some (bad at math), distribute the remainder to Refactor
            total_extracted = feat + fix + ref
            if total_extracted < len(commits):
                ref += (len(commits) - total_extracted)

            st.session_state.commit_stats = {
                "Feature": feat,
                "Fix": fix,
                "Refactor": ref,
                "total": len(commits)
            }
        except Exception as e:
            st.error(f"Failed to classify commits: {e}")

def generate_contributor_kudos(author: str, commits: list) -> str:
    if not commits:
        return "No commits provided."
        
    commits_str = "\n".join(commits)
    if len(commits_str) > 5000:
        commits_str = commits_str[:5000] + "\n...[TRUNCATED]"
        
    llm = get_ai_reviewer()
    system_prompt = (
        f"You are a supportive engineering manager. Your task is to write a short, personalized "
        f"'Kudos' and shoutout paragraph for the contributor named '{author}'. "
        f"Summarize their recent efforts based on the commit messages provided. "
        f"Keep the tone extremely uplifting, appreciative, and concise (2-3 sentences max). "
        f"Do not use greetings, output the paragraph directly."
    )
    user_prompt = f"Recent Commits by {author}:\n{commits_str}"
    
    try:
        response = llm.invoke([("system", system_prompt), ("user", user_prompt)])
        return response.content
    except Exception as e:
        return f"Error connecting to AI Provider: {e}"

tab1, tab2, tab3 = st.tabs(["Pull Requests Review", "Spotlight Insights", "Release Notes Generator"])

with tab1:
    st.subheader("Latest Pull Requests")
    prs = fetch_pull_requests(repo_owner, repo_name)
    
    if not prs:
        st.info("No pull requests found or unable to fetch.")
    else:
        for pr in prs:
            with st.expander(f"#{pr['number']} - {pr['title']} ({pr['state']})", expanded=False):
                st.write(f"**Author:** {pr['user']['login']}")
                st.write(f"**Created At:** {pr['created_at']}")
                st.markdown(f"[View PR on GitHub]({pr['html_url']})")
                
                button_key = f"review_btn_{pr['number']}"
                
                if st.button("Review with AI", key=button_key):
                    with st.spinner("Analyzing PR Diff..."):
                        diff = fetch_pr_diff(repo_owner, repo_name, pr['number'])
                        if not diff:
                            st.error("No diff available or PR is empty.")
                        else:
                            result = generate_ai_review(diff)
                            
                            if "error" in result:
                                st.error(result["error"])
                            else:
                                score = result.get("total_score", 0)
                                review_text = result.get("review_text", "")
                                
                                # Determine score class
                                score_class = "score-low" # Green (low risk)
                                if score < 60:
                                    score_class = "score-high" # Red (high risk)
                                elif score < 85:
                                    score_class = "score-med" # Orange (medium risk)
                                
                                # Build calculation hover text
                                hover_html = "".join([
                                    f'<div class="rule-row"><span class="rule-name">{k}</span> <span class="rule-weight">{int(v*100)}%</span></div>'
                                    for k, v in WEIGHTS.items()
                                ])
                                
                                st.markdown(f"""
                                <div class="info-card">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                                        <h3 style="margin: 0;">🤖 AI Review</h3>
                                        <div style="display: flex; align-items: center;">
                                            <div class="score-badge {score_class}">
                                                Pull Request Score: {score}/100
                                            </div>
                                            <div class="tooltip">
                                                <span style="font-size: 1.2rem; margin-left: 8px;">ⓘ</span>
                                                <div class="tooltiptext">
                                                    <strong>Pull Request Score Calculation</strong><br/>
                                                    Based on weighted coding standards:<br/><br/>
                                                    {hover_html}
                                                    <br/>
                                                    <i>AI evaluates each rule (0-10) and applies weights to generate the final score.</i>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                    <div style="color: #e0e1dd; font-size: 0.95rem;">{review_text}</div>
                                </div>
                                """, unsafe_allow_html=True)

with tab2:
    st.subheader("🏆 Spotlight Insights")
    st.write("Recognize the most active contributors and team overall contribution over a specified timeframe.")
    
    timeframe = st.selectbox("Timeframe", ["Last 7 Days", "Last 30 Days"], index=0)
    
    if st.button("Generate Spotlights", type="primary"):
        days = 7 if timeframe == "Last 7 Days" else 30
        start_date = date.today() - timedelta(days=days)
        end_date = date.today()
        
        with st.spinner(f"Fetching commits for the {timeframe.lower()}..."):
            commits = fetch_commits_by_date(repo_owner, repo_name, start_date, end_date)
            
        if not commits:
            st.warning("No commits found in this timeframe.")
            st.session_state.spotlights = None
        else:
            author_commits = defaultdict(list)
            for c in commits:
                author_name = c.get('commit', {}).get('author', {}).get('name', 'Unknown')
                msg = c.get('commit', {}).get('message', '').split('\n')[0]
                author_commits[author_name].append(msg)
                
            sorted_authors = sorted(author_commits.items(), key=lambda item: len(item[1]), reverse=True)
            top_authors = sorted_authors[:3]
            
            spotlights = []
            for author_name, msgs in top_authors:
                with st.spinner(f"Generating Kudos for {author_name}..."):
                    kudos = generate_contributor_kudos(author_name, msgs)
                    spotlights.append({"author": author_name, "count": len(msgs), "kudos": kudos})
            
            st.session_state.spotlights = spotlights
            st.session_state.spotlight_meta = f"Analyzed {len(commits)} commits across {len(author_commits)} authors."
            
            # Automatically run Team Contribution analysis in parallel
            analyze_feature_fix_ratio(days=days)
            
    if st.session_state.get("spotlights"):
        st.success(st.session_state.spotlight_meta)
        for s in st.session_state.spotlights:
            st.markdown(f"""
            <div class="info-card" style="margin-bottom: 1rem;">
                <h3>🌟 {s['author']} <span style="font-size: 0.9rem; color: #a0aab2; font-weight: 400;">({s['count']} commits)</span></h3>
                <p>{s['kudos']}</p>
            </div>
            """, unsafe_allow_html=True)

        st.write("---")
        st.subheader("📊 Team Contribution")
        st.write("Distribution of effort across features, fixes, and refactors.")

        if "commit_stats" in st.session_state and st.session_state.commit_stats:
            st.write("#### Effort Distribution")
            stats = st.session_state.commit_stats
            total = stats.get("total", sum([v for k, v in stats.items() if k != "total"]))
            
            if total > 0:
                c1, c2, c3 = st.columns([1, 1, 1])
                c1.metric("Features", f"{stats['Feature']}")
                c2.metric("Fixes", f"{stats['Fix']}")
                c3.metric("Refactors", f"{stats['Refactor']}")

                # Filter out 'total' for the graph
                graph_stats = {k: v for k, v in stats.items() if k != "total"}
                dist_df = pd.Series(graph_stats).reset_index()
                dist_df.columns = ["Type", "Count"]

                fig_dist = px.pie(
                    dist_df, 
                    values="Count", 
                    names="Type",
                    hole=0.5,
                    color="Type",
                    color_discrete_map={
                        "Feature": "#27ae60",   # Greenish
                        "Fix": "#e74c3c",       # Reddish
                        "Refactor": "#6495ED"    # Blueish
                    }
                )
                fig_dist.update_layout(
                    showlegend=True,
                    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                    margin=dict(t=30, b=0, l=0, r=0),
                    height=350,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color="white")
                )
                fig_dist.update_traces(textposition='inside', textinfo='percent+label')
                
                st.plotly_chart(fig_dist, use_container_width=True)
            else:
                st.warning("No commits found to analyze.")

with tab3:
    st.subheader("Automated Release Notes")
    st.write("Select a date range to generate a changelog from merged commits.")
    
    colA, colB = st.columns(2)
    with colA:
        start_date = st.date_input("Start Date", value=date.today() - timedelta(days=14))
    with colB:
        end_date = st.date_input("End Date", value=date.today())
        
    if st.button("Fetch Commits & Generate Notes", type="primary"):
        with st.spinner("Fetching commits..."):
            commits = fetch_commits_by_date(repo_owner, repo_name, start_date, end_date)
            
        if not commits:
            st.warning("No commits found in the selected date range.")
            st.session_state.release_notes = None
        else:
            st.success(f"Successfully fetched {len(commits)} commits.")
            with st.spinner("Generating Release Notes with AI..."):
                st.session_state.release_notes = generate_release_notes(commits)
                
    if st.session_state.get("release_notes"):
        st.markdown("---")
        st.markdown(f"""
        <div class="info-card" style="margin-bottom: 1.5rem;">
            <h3>📦 Generated Release Notes</h3>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(st.session_state.release_notes)
        
        st.download_button(
            label="📥 Download Release Notes",
            data=st.session_state.release_notes,
            file_name=f"release_notes_{start_date}_to_{end_date}.md",
            mime="text/markdown"
        )

st.write("---")
render_footer()
