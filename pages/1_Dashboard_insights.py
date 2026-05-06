import os
import re
import json
import base64
import subprocess
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import git
from datetime import datetime
from langchain_nvidia_ai_endpoints import ChatNVIDIA

from ui_components import apply_custom_css, render_header, render_footer, render_lottie_transparent


# 1. Guard: Ensure user has processed the repo
if not st.session_state.get("processing_complete"):
    st.switch_page("app1.py")


# Custom CSS for Background, Animations, and Typography
apply_custom_css()

# render header
render_header()

def fetch_insights():
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_file_dir)

    repo_path = os.path.join(project_root, "temp_repo")

    if not os.path.exists(repo_path):
        st.error(f"Could not find repository at: {repo_path}")
        print(f"DEBUG: Path does not exist: {repo_path}")
        return

    repo = git.Repo(repo_path)
    print(f"DEBUG: Found repository: {repo}")
    default_branch = repo.remotes.origin.refs.HEAD.reference.name.split('/')[-1]
    commits = list(repo.iter_commits(default_branch))
    contributors = set(c.author.name for c in commits)

    st.session_state.insights = {
        "total_commits": len(commits),
        "total_contributors": len(contributors),
        "active_branch": repo.active_branch.name,
        "last_commit": datetime.fromtimestamp(commits[0].committed_date).strftime('%Y-%m-%d')
    }
    return st.session_state.insights

def fetch_criticality_index():
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_file_dir)
    repo_path = os.path.join(project_root, "temp_repo")

    query = "MATCH (f:File)<-[r]-(other) RETURN f.filePath, count(r) ORDER BY count(r) DESC LIMIT 5"

    try:
        with st.spinner("Calculating Criticality Index..."):
            result = subprocess.run(
                ["npx", "-y", "gitnexus", "cypher", "--repo", "temp_repo", query],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                output = result.stdout
                data = json.loads(output)
                criticality_data = []
                if "markdown" in data:
                    lines = data["markdown"].split('\n')
                    for line in lines:
                        if "|" in line and "filePath" not in line and "---" not in line:
                            parts = [p.strip() for p in line.split('|') if p.strip()]
                            if len(parts) == 2:
                                try:
                                    file_path = parts[0]
                                    score = int(parts[1])
                                    criticality_data.append({"File": file_path, "Score": score})
                                except ValueError:
                                    continue
                st.session_state.criticality_index = criticality_data

                if criticality_data:
                    top_files = criticality_data[:3]
                    analyze_top_files_risk(top_files)

    except Exception as e:
        st.error(f"Error fetching criticality index: {e}")

def fetch_impact_radius():
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_file_dir)
    repo_path = os.path.join(project_root, "temp_repo")

    query = "MATCH (f:File)<-[*1..5]-(other:File) RETURN f.filePath, count(DISTINCT other) ORDER BY count(DISTINCT other) DESC LIMIT 5"

    try:
        with st.spinner("Analyzing Structural Impact Radius..."):
            result = subprocess.run(
                ["npx", "-y", "gitnexus", "cypher", "--repo", "temp_repo", query],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                output = result.stdout
                data = json.loads(output)
                impact_data = []
                if "markdown" in data:
                    lines = data["markdown"].split('\n')
                    for line in lines:
                        if "|" in line and "filePath" not in line and "---" not in line:
                            parts = [p.strip() for p in line.split('|') if p.strip()]
                            if len(parts) == 2:
                                try:
                                    impact_data.append({"File": parts[0], "Impact_Radius": int(parts[1])})
                                except:
                                    continue
                st.session_state.impact_radius = impact_data
    except Exception as e:
        st.error(f"Error fetching Impact Radius: {e}")

def fetch_process_flows():
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_file_dir)
    repo_path = os.path.join(project_root, "temp_repo")

    query = "MATCH (n:Process) RETURN n.id, n.label, n.processType, n.stepCount ORDER BY n.stepCount DESC"

    try:
        with st.spinner("Tracing Process Flows..."):
            result = subprocess.run(
                ["npx", "-y", "gitnexus", "cypher", "--repo", "temp_repo", query],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                output = result.stdout
                data = json.loads(output)
                processes = []
                if "markdown" in data:
                    lines = data["markdown"].split('\n')
                    for line in lines:
                        if "|" in line and "n.id" not in line and "---" not in line:
                            parts = [p.strip() for p in line.split('|') if p.strip()]
                            if len(parts) == 4:
                                try:
                                    processes.append({
                                        "ID": parts[0],
                                        "Process": parts[1],
                                        "Type": parts[2],
                                        "Steps": int(parts[3])
                                    })
                                except (ValueError, IndexError):
                                    continue
                st.session_state.process_flows = processes
    except Exception as e:
        st.error(f"Error fetching Process Flows: {e}")

def analyze_top_files_risk(top_files):
    risks = []
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_file_dir)
    repo_path = os.path.join(project_root, "temp_repo")

    client = ChatNVIDIA(
        model="meta/llama-3.1-70b-instruct",
        api_key="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",
        temperature=0.1,
    )
    total = len(top_files)
    progress_bar = st.progress(0)
    lottie_placeholder = st.empty()
    with lottie_placeholder:
        # Get path to LOADING.json in assets folder
        assets_path = os.path.join(project_root, "assets", "AI.json")
        render_lottie_transparent(assets_path, height=200)
    
    for i, item in enumerate(top_files):
        full_path = os.path.join(repo_path, item["File"])
        content = ""
        if os.path.exists(full_path):
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read(5000)
            except:
                content = "Could not read file."

        prompt = f"""
        Analyze the following code from file '{item['File']}'.
        Provide:
        1. A 'Complexity Score' from 1 to 10 (where 10 is extremely complex/hard to maintain and required area of improvement).
        2. A short 'Risk Justification' (max 50 words) explaining why this file might be a maintenance hazard.

        Return in format: Score: [number], Justification: [text]

        Code:
        {content}
        """
        try:
            response = client.invoke(prompt).content

            match_score = re.search(r"Score:\s*(\d+)", response)
            match_just = re.search(r"Justification:\s*(.*)", response)

            complexity = int(match_score.group(1)) if match_score else 0
            justification = match_just.group(1).strip() if match_just else "No justification provided."

            if complexity == 0 or justification == "No justification provided.":
                progress_bar.progress((i + 1) / total)
                continue

            risks.append({
                "File": item["File"],
                "Centrality": item["Score"],
                "AI_Complexity": complexity,
                "Risk_Score": item["Score"] * complexity,
                "Justification": justification
            })
        except Exception as e:
            st.warning(f"AI Analysis failed for {item['File']}: {e}")
        progress_bar.progress((i + 1) / total)

    lottie_placeholder.empty()
    st.session_state.ai_risk_data = sorted(risks, key=lambda x: x["Risk_Score"], reverse=True)

def analyze_technical_debt():
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_file_dir)
    repo_path = os.path.join(project_root, "temp_repo")
    repo = git.Repo(repo_path)

    files = []
    for root, dirs, filenames in os.walk(repo_path):
        if ".gitNexus" in root or ".git" in root or "node_modules" in root:
            continue
        for f in filenames:
            if f.endswith(('.py', '.ts', '.js')):
                files.append(os.path.relpath(os.path.join(root, f), repo_path))

    with st.spinner("Analyzing Churn..."):
        file_churn = []
        for f_path in files:
            commits = list(repo.iter_commits(paths=f_path, max_count=100))
            file_churn.append({"File": f_path, "Churn": len(commits)})

        top_churn = sorted(file_churn, key=lambda x: x["Churn"], reverse=True)[:5]

    client = ChatNVIDIA(
        model="meta/llama-3.1-70b-instruct",
        api_key="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",
        temperature=0.1,
    )

    hotspots = []
    for item in top_churn:
        full_path = os.path.join(repo_path, item["File"])
        content = ""
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read(5000)
        except:
            continue

        prompt = f"Rate the code complexity and technical debt of '{item['File']}' from 1-10. Return only: Score: [num]"
        try:
            response = client.invoke(prompt).content
            match = re.search(r"Score:\s*(\d+)", response)
            complexity = int(match.group(1)) if match else 5
            hotspots.append({
                "File": item["File"],
                "Display": item["File"].split("/")[-1],
                "Churn": item["Churn"],
                "Complexity": complexity,
                "Hotspot_Score": item["Churn"] * complexity
            })
        except:
            continue

    st.session_state.hotspots_data = hotspots


def analyze_dependency_vulnerabilities():
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_file_dir)
    repo_path = os.path.join(project_root, "temp_repo")

    manifest_path = None
    manifest_type = None
    manifests = [
        "package.json", "requirements.txt", "pyproject.toml", "Pipfile",
        "pom.xml", "build.gradle", "go.mod", "Gemfile", "Cargo.toml"
    ]
    for f in manifests:
        path = os.path.join(repo_path, f)
        if os.path.exists(path):
            manifest_path = path
            manifest_type = f
            break

    if not manifest_path:
        st.warning("No package.json or requirements.txt found for dependency scan.")
        return

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            content = f.read(10000)

        client = ChatNVIDIA(
            model="meta/llama-3.1-70b-instruct",
            api_key="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",
            temperature=0.1,
        )

        prompt = f"""
        Analyze the following {manifest_type} file and identify the top 5 most risky packages or libraries.
        Focus on:
        1. Known security vulnerabilities (CVEs) associated with these versions.
        2. Maintenance risk (deprecated, unmaintained, or very old versions).
        3. Reliability risks.

        Return a JSON-style list of objects with:
        'Package', 'Version', 'Risk_Level' (High/Medium/Low), and 'Justification' (max 20 words).

        Format:
        [
            {{"Package": "name", "Version": "vX.Y", "Risk_Level": "High", "Justification": "..."}}
        ]

        Manifest Content:
        {content}
        """
        response = client.invoke(prompt).content
        match = re.search(r"(\[.*\])", response, re.DOTALL)
        if match:
            risks = json.loads(match.group(1))
            st.session_state.dependency_risks = risks
            if not risks:
                st.success("✅ No high-risk packages detected in your manifest!")
        else:
            if "no risky" in response.lower() or "no vulnerabilities" in response.lower():
                st.session_state.dependency_risks = []
                st.success("✅ No high-risk packages detected by AI analysis.")
            else:
                st.error("AI could not extract dependency risks in the correct format.")
    except Exception as e:
        st.error(f"Dependency scan failed: {e}")


# ─────────────────────────────────────────────
# Page Layout
# ─────────────────────────────────────────────

# 2. Repository Details
repo_name   = st.session_state.get("repo_name", "N/A")
repo_owner  = st.session_state.get("repo_owner", "N/A")
repo_url_cl = st.session_state.get("repo_url_clean", "#")
repo_branch = st.session_state.get("repo_default_branch", st.session_state.get("repo_active_branch", "N/A"))
repo_commits = st.session_state.get("repo_total_commits", "—")
repo_contributors = st.session_state.get("repo_total_contributors", "—")
repo_files  = st.session_state.get("repo_total_files", "—")
repo_first  = st.session_state.get("repo_first_commit_date", "N/A")
repo_last   = st.session_state.get("repo_last_commit_date", "N/A")
repo_last_msg = st.session_state.get("repo_last_commit_msg", "N/A")
repo_langs  = st.session_state.get("repo_languages", [])
repo_desc   = st.session_state.get("repo_description", "No description provided.")

# Language pills HTML
lang_pill_colors = ["#6495ED","#3a506b","#27ae60","#e67e22","#8e44ad"]
lang_pills_html = "".join(
    f'<span style="background:{lang_pill_colors[i % len(lang_pill_colors)]};color:#fff;'
    f'border-radius:20px;padding:3px 12px;font-size:0.78rem;margin-right:6px;font-weight:600;">'
    f'{lang} <span style="opacity:0.75;">({cnt})</span></span>'
    for i, (lang, cnt) in enumerate(repo_langs)
) or "<span style='color:#a0aab2;font-size:0.85rem;'>N/A</span>"


# Navigation row — home on left, buttons on right
_home_col, _spacer, _btn_col1, _btn_col2 = st.columns([1, 4.5, 1.1, 1.1])

with _home_col:
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("app1.py")
with _btn_col1:
    if st.button("📊 Git Insight", use_container_width=True):
        st.switch_page("pages/5_Insights.py")
with _btn_col2:
    if st.button("💬 RepoTalk", use_container_width=True):
        st.switch_page("pages/7_Repo_Chat.py")

st.markdown(f"""

<div style="
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(100,149,237,0.25);
    border-radius: 16px;
    padding: 1.5rem 2rem;
    backdrop-filter: blur(6px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.6);
    margin-bottom: 0.5rem;
">
  <!-- Header row -->
  <div style="display:flex;align-items:center;gap:1rem;margin-bottom:1rem;">
    <div>
      <div style="font-size:1.7rem;font-weight:800;color:#fff;line-height:1.1;">
        📦 {repo_name}
      </div>
      <div style="color:#a0aab2;font-size:0.9rem;margin-top:2px;">
        👤 {repo_owner} &nbsp;·&nbsp;
        <a href="{repo_url_cl}" target="_blank"
           style="color:cornflowerblue;text-decoration:none;font-size:0.88rem;">
          🔗 View on GitHub ↗
        </a>
      </div>
    </div>
  </div>

  <!-- Stats row -->
  <div style="display:grid;grid-template-columns:repeat(6,1fr);gap:0.9rem;margin-bottom:1.2rem;">
    <div style="background:rgba(100,149,237,0.12);border-radius:10px;padding:0.65rem 0.5rem;text-align:center;">
      <div style="font-size:1.4rem;font-weight:700;color:#6495ED;">{repo_commits}</div>
      <div style="font-size:0.7rem;color:#a0aab2;text-transform:uppercase;letter-spacing:0.05em;">Commits</div>
    </div>
    <div style="background:rgba(100,149,237,0.12);border-radius:10px;padding:0.65rem 0.5rem;text-align:center;">
      <div style="font-size:1.4rem;font-weight:700;color:#6495ED;">{repo_contributors}</div>
      <div style="font-size:0.7rem;color:#a0aab2;text-transform:uppercase;letter-spacing:0.05em;">Contributors</div>
    </div>
    <div style="background:rgba(100,149,237,0.12);border-radius:10px;padding:0.65rem 0.5rem;text-align:center;">
      <div style="font-size:1.4rem;font-weight:700;color:#6495ED;">{repo_files}</div>
      <div style="font-size:0.7rem;color:#a0aab2;text-transform:uppercase;letter-spacing:0.05em;">Files</div>
    </div>
    <div style="background:rgba(39,174,96,0.12);border-radius:10px;padding:0.65rem 0.5rem;text-align:center;">
      <div style="font-size:1rem;font-weight:700;color:#27ae60;">🌿 {repo_branch}</div>
      <div style="font-size:0.7rem;color:#a0aab2;text-transform:uppercase;letter-spacing:0.05em;">Default Branch</div>
    </div>
    <div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:0.65rem 0.5rem;text-align:center;">
      <div style="font-size:0.95rem;font-weight:600;color:#e0e1dd;">📅 {repo_first}</div>
      <div style="font-size:0.7rem;color:#a0aab2;text-transform:uppercase;letter-spacing:0.05em;">First Commit</div>
    </div>
    <div style="background:rgba(255,255,255,0.05);border-radius:10px;padding:0.65rem 0.5rem;text-align:center;">
      <div style="font-size:0.95rem;font-weight:600;color:#e0e1dd;">📅 {repo_last}</div>
      <div style="font-size:0.7rem;color:#a0aab2;text-transform:uppercase;letter-spacing:0.05em;">Last Commit</div>
    </div>
  </div>

  <!-- Languages -->
  <div style="margin-bottom:1rem;">
    <div style="font-size:0.78rem;color:#a0aab2;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">🧩 Languages</div>
    {lang_pills_html}
  </div>


  <!-- Description -->
  <div>
    <div style="font-size:0.78rem;color:#a0aab2;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">📄 README Snippet</div>
    <div style="font-size:0.85rem;color:#c8cdd3;line-height:1.6;">{repo_desc}</div>
  </div>
</div>
""", unsafe_allow_html=True)

st.write("---")

# 1. Display Metrics
data = fetch_insights()

# Create Tabs
tab1, tab2 = st.tabs(["Architecture & Risk", "Advanced Insights"])

with tab1:
    # Display Insights if they have been fetched
    if "criticality_index" in st.session_state:

        if st.button("📊 Re-fetch AI Insights", type="primary"):
            fetch_criticality_index()
            fetch_impact_radius()
            fetch_process_flows()
            st.rerun()

        # 4. AI Maintenance Risk Score
        if "ai_risk_data" in st.session_state and st.session_state.ai_risk_data:
            st.subheader("AI Maintenance Risk Assessment")
            st.info("Files with the high risk of breakdown.")

            risk_df = pd.DataFrame(st.session_state.ai_risk_data)

            cols = st.columns(min(3, len(st.session_state.ai_risk_data)))
            for idx, row in risk_df.head(3).iterrows():
                with cols[idx]:
                    help_text = (
                        "**AI Scoring Criteria:**\n"
                        "- 🏗️ Area of improvement\n"
                        "- 🧱 Lack of modularity\n"
                        "- 🧠 Complex boolean logic or long functions\n\n"
                        f"**AI Reason:** {row['Justification']}"
                    )
                    st.metric(
                        label=f"🚀 {row['File'].split('/')[-1]}",
                        value=f"Risk: {row['Risk_Score']}",
                        delta=f"Cplx: {row['AI_Complexity']}",
                        help=help_text
                    )

            st.write("#### Detailed AI Risk Breakdown")
            st.dataframe(risk_df[["File", "Risk_Score", "Centrality", "AI_Complexity", "Justification"]], hide_index=True)

        # 2. Criticality Index
        if "criticality_index" in st.session_state and st.session_state.criticality_index:
            st.subheader(
                "🎯 Criticality Index",
                help="Measures immediate architectural importance. It counts how many files point directly to this file in the code knowledge graph."
            )
            st.info("Files with the highest impact on the rest of the system.")

            st.dataframe(pd.DataFrame(st.session_state.criticality_index), hide_index=True, use_container_width=True)

            st.write("---")
            df = pd.DataFrame(st.session_state.criticality_index)
            df["Display"] = df["File"].apply(lambda x: x.split("/")[-1])
            fig_crit = px.bar(
                df, x="Score", y="Display", orientation='h',
                title="Top Files by Criticality",
                labels={"Score": "Dependency Count", "Display": "File Name"},
                hover_data={"File": True, "Display": False},
                color="Score", color_continuous_scale="Blues"
            )
            fig_crit.update_layout(yaxis={'categoryorder': 'total ascending'}, height=400)
            st.plotly_chart(fig_crit, use_container_width=True)

        # 3. Impact Radius
        if "impact_radius" in st.session_state and st.session_state.impact_radius:
            st.write("---")
            st.subheader(
                "Structural Impact Radius",
                help="Measures the recursive 'ripple effect' of a change. It counts how many unique files across the entire system eventually depend on this file (up to 5 levels deep)."
            )
            st.info("Foundational files with the largest recursive 'impact radius' (downstream dependents).")

            impact_df = pd.DataFrame(st.session_state.impact_radius)
            impact_df["Display"] = impact_df["File"].apply(lambda x: x.split("/")[-1])
            fig_impact = px.bar(
                impact_df, x="Impact_Radius", y="Display", orientation='h',
                title="Structural Impact Radius",
                labels={"Impact_Radius": "Downstream Impact", "Display": "File Name"},
                hover_data={"File": True, "Display": False},
                color="Impact_Radius", color_continuous_scale="Viridis"
            )
            fig_impact.update_layout(yaxis={'categoryorder': 'total ascending'}, height=400)
            st.plotly_chart(fig_impact, use_container_width=True)

        # 6. Process Flows
        if "process_flows" in st.session_state:
            st.write("---")
            st.subheader(
                "🔄 Process Flows",
                help="End-to-end execution paths traced through the knowledge graph. Intra-community = low coupling. Cross-community = flows that cross module boundaries = higher integration risk."
            )
            st.info("**Cross-community** processes span multiple modules — a high proportion signals tight inter-module coupling.")

            proc_data = st.session_state.process_flows
            if proc_data:
                proc_df = pd.DataFrame(proc_data)

                proc_df["Type Badge"] = proc_df["Type"].apply(
                    lambda t: "🟢 intra" if t == "intra_community" else "🔴 cross"
                )

                intra_count = (proc_df["Type"] == "intra_community").sum()
                cross_count = (proc_df["Type"] == "cross_community").sum()
                total_count = len(proc_df)

                pm1, pm2, pm3 = st.columns(3)
                pm1.metric("Total Processes", total_count)
                pm2.metric("🟢 Intra-Community", intra_count, help="Stays within one module — low coupling")
                pm3.metric("🔴 Cross-Community", cross_count, help="Crosses module boundaries — integration risk")

                if total_count > 0:
                    pie_df = pd.DataFrame({
                        "Type": ["Intra-Community", "Cross-Community"],
                        "Count": [intra_count, cross_count]
                    })
                    fig_pie = px.pie(
                        pie_df, values="Count", names="Type",
                        title="Process Type Distribution",
                        color="Type",
                        color_discrete_map={"Intra-Community": "#27ae60", "Cross-Community": "#e74c3c"},
                        hole=0.45
                    )
                    fig_pie.update_traces(textinfo="percent+label")
                    st.plotly_chart(fig_pie, use_container_width=True)

                st.write("#### Process Detail")
                st.dataframe(
                    proc_df[["Process", "Type Badge", "Steps"]].rename(columns={"Type Badge": "Type"}),
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("No process flow data found. Re-run `gitnexus analyze` on the repository.")
    else:
        # Trigger fetch automatically on first load
        fetch_criticality_index()
        fetch_impact_radius()
        fetch_process_flows()
        st.rerun()

with tab2:
    # 7. Advanced Developer Insights
    st.subheader("Advanced Developer Insights")

    if st.button("🔥 Calculate Code Hotspots"):
        with st.spinner("Calculating hotspots..."):
            analyze_technical_debt()

    if "hotspots_data" in st.session_state:
        st.write("#### Technical Debt Hotspots")
        st.info("High Churn + High Complexity = Maintenance Hotspots.")
        df_hs = pd.DataFrame(st.session_state.hotspots_data)
        st.scatter_chart(df_hs, x="Churn", y="Complexity", size="Hotspot_Score", color="Display")
        st.dataframe(df_hs.sort_values("Hotspot_Score", ascending=False), hide_index=True)


    st.write("---")
    st.subheader(
        "🛡️ Dependency Risk Shield",
        help="AI-powered scan of your libraries for vulnerabilities and maintenance risks."
    )

    if st.button("🔍 Scan Dependencies"):
        with st.spinner("Scanning for risky packages..."):
            analyze_dependency_vulnerabilities()

    if "dependency_risks" in st.session_state:
        df_deps = pd.DataFrame(st.session_state.dependency_risks)
        st.dataframe(df_deps, hide_index=True, use_container_width=True)
        st.info("💡 Always cross-verify AI security insights with official tools like `npm audit` or `safety`.")

st.write("---")

render_footer()
