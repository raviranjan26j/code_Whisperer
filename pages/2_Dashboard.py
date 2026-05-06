import os
import streamlit as st
import subprocess
import json
import re
import pandas as pd

# 1. Guard: Ensure user has processed the repo
if not st.session_state.get("processing_complete"):
    st.switch_page("app1.py")

import git
from datetime import datetime
from langchain_nvidia_ai_endpoints import ChatNVIDIA
import pandas as pd
import plotly.express as px

st.title("🌐 Repo Whisperer")

st.markdown("""
    <style>
    .fixed-nav {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        background-color: white;
        padding: 15px 20px;
        z-index: 9999;
        border-bottom: 1px solid #e6e9ef;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.05);
    }
    .main-content { padding-top: 80px; }
    </style>
    """, unsafe_allow_html=True)

with st.container(border=True):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if st.button("🏠 Home", type="tertiary"):
            st.switch_page("app1.py")
    with col2:
        if st.button("📊 Dashboard", type="primary"):
            pass
    with col3:
        if st.button("🤖 Repo Chat", type="tertiary"):
            st.switch_page("pages/3_Chat.py")
    with col4:
        if st.button("⚙️ Settings", type="tertiary"):
            st.switch_page("pages/4_Settings.py")


def fetch_insights():
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_file_dir) 
    
    repo_path = os.path.join(project_root, "temp_repo")

    # Check if path exists for debugging
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
                    # Format: | f.filePath | COUNT(r._ID) |
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
                
                # Automatically trigger AI risk analysis for top 3 files if not already done
                if criticality_data:
                    top_files = criticality_data[:3]
                    analyze_top_files_risk(top_files)

    except Exception as e:
        st.error(f"Error fetching criticality index: {e}")

def fetch_impact_radius():
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_file_dir)
    repo_path = os.path.join(project_root, "temp_repo")
    
    # Recursive query (depth 1..5) to find foundational files (generic relationship)
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
                                except: continue
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
    
    st.session_state.ai_risk_data = sorted(risks, key=lambda x: x["Risk_Score"], reverse=True)

def analyze_technical_debt():
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_file_dir)
    repo_path = os.path.join(project_root, "temp_repo")
    repo = git.Repo(repo_path)
    
    hotspots = []
    # Get all files in repo (excluding some patterns)
    files = []
    for root, dirs, filenames in os.walk(repo_path):
        if ".gitNexus" in root or ".git" in root or "node_modules" in root: continue
        for f in filenames:
            if f.endswith(('.py', '.ts', '.js')):
                files.append(os.path.relpath(os.path.join(root, f), repo_path))
    
    # Analyze churn for all files, but AI complexity only for top churn files
    with st.spinner("Analyzing Churn..."):
        file_churn = []
        for f_path in files:
            commits = list(repo.iter_commits(paths=f_path, max_count=100))
            file_churn.append({"File": f_path, "Churn": len(commits)})
        
        # Sort by churn and take top 5 for AI analysis
        top_churn = sorted(file_churn, key=lambda x: x["Churn"], reverse=True)[:5]
    
    client = ChatNVIDIA(
        model="meta/llama-3.1-70b-instruct",
        api_key="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", 
        temperature=0.1,
    )

    for item in top_churn:
        full_path = os.path.join(repo_path, item["File"])
        content = ""
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read(5000)
        except: continue
        
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
        except: continue
    
    st.session_state.hotspots_data = hotspots

def analyze_feature_fix_ratio():
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_file_dir)
    repo_path = os.path.join(project_root, "temp_repo")
    repo = git.Repo(repo_path)
    
    with st.spinner("Classifying Commits..."):
        commits = list(repo.iter_commits(max_count=100))
        messages = [c.message.split('\n')[0] for c in commits]
        
        client = ChatNVIDIA(
            model="meta/llama-3.1-70b-instruct",
            api_key="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", 
            temperature=0.1,
        )
        
        prompt = f"""
        Classify the following commit messages into three categories: 'Feature', 'Fix', or 'Refactor'.
        Return the counts in this format: Feature: [num], Fix: [num], Refactor: [num]
        
        Messages:
        {chr(10).join(messages)}
        """
        try:
            response = client.invoke(prompt).content
            def get_count(key, text):
                m = re.search(f"{key}:\\s*(\\d+)", text)
                return int(m.group(1)) if m else 0
            
            st.session_state.commit_stats = {
                "Feature": get_count("Feature", response),
                "Fix": get_count("Fix", response),
                "Refactor": get_count("Refactor", response)
            }
        except Exception as e:
            st.error(f"Failed to classify commits: {e}")

def analyze_dependency_vulnerabilities():
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_file_dir)
    repo_path = os.path.join(project_root, "temp_repo")
    
    # Try to find common manifest files
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
            content = f.read(10000) # Read up to 10kb
            
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
        # Extract JSON list using regex
        match = re.search(r"(\[.*\])", response, re.DOTALL)
        if match:
            risks = json.loads(match.group(1))
            st.session_state.dependency_risks = risks
            if not risks:
                st.success("✅ No high-risk packages detected in your manifest!")
        else:
            # Check if AI explicitly said no risks
            if "no risky" in response.lower() or "no vulnerabilities" in response.lower():
                st.session_state.dependency_risks = []
                st.success("✅ No high-risk packages detected by AI analysis.")
            else:
                st.error("AI could not extract dependency risks in the correct format.")
    except Exception as e:
        st.error(f"Dependency scan failed: {e}")

# 2. Repository Details (Directly in the page)
with st.container(border=True):
    st.subheader("📁 Repository Details")
    col1, col2, col3 = st.columns(3)
    col1.markdown(f"**Name:** {st.session_state.get('repo_name', 'N/A')}")
    col2.markdown(f"**Owner:** {st.session_state.get('repo_owner', 'N/A')}")
    col3.markdown(f"**Description:** {st.session_state.get('repo_description', 'N/A')}")

st.write("---")


data = fetch_insights()
# 1. Display Metrics
st.subheader("📈 Repository Insights")
c1, c2, c3 = st.columns(3)
c1.metric("Total Commits", data["total_commits"])
c2.metric("Contributors", data["total_contributors"])
c3.metric("Last Commit", data["last_commit"])
st.write(f"**Active Branch:** `{data['active_branch']}`")

st.write("---")


# Display Insights if they have been fetched
if "criticality_index" in st.session_state:

    if st.button("📊 Re-fetch AI Insights", type="primary"):
        fetch_criticality_index()
        fetch_impact_radius()
        fetch_process_flows()
        st.rerun()

    # 4. Display AI Maintenance Risk Score
    if "ai_risk_data" in st.session_state and st.session_state.ai_risk_data:
        st.write("---")
        st.subheader("🤖 AI Maintenance Risk Assessment")
        st.warning("Centrality with AI-analyzed Code Complexity.")
        
        risk_df = pd.DataFrame(st.session_state.ai_risk_data)
        
        # Display highlights for top 3
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


    # 2. Display Criticality Index
    if "criticality_index" in st.session_state and st.session_state.criticality_index:
        st.subheader("🎯 Criticality Index", help="Measures immediate architectural importance. It counts how many files point directly to this file in the code knowledge graph.")
        st.info("Files with the highest impact on the rest of the system.")
        
        # Display as a table
        st.dataframe(pd.DataFrame(st.session_state.criticality_index), hide_index=True, use_container_width=True)

        st.write("---")
        # Display as a bar chart (full paths, horizontal)
        df = pd.DataFrame(st.session_state.criticality_index)
        df["Display"] = df["File"].apply(lambda x: x.split("/")[-1])
        fig_crit = px.bar(df, x="Score", y="Display", orientation='h', 
                          title="Top Files by Criticality",
                          labels={"Score": "Dependency Count", "Display": "File Name"},
                          hover_data={"File": True, "Display": False},
                          color="Score", color_continuous_scale="Blues")
        fig_crit.update_layout(yaxis={'categoryorder':'total ascending'}, height=400)
        st.plotly_chart(fig_crit, use_container_width=True)

    # 3. Display Impact Radius
    if "impact_radius" in st.session_state and st.session_state.impact_radius:
        st.write("---")
        st.subheader("🌐 Structural Impact Radius", help="Measures the recursive 'ripple effect' of a change. It counts how many unique files across the entire system eventually depend on this file (up to 5 levels deep).")
        st.info("Foundational files with the largest recursive 'impact radius' (downstream dependents).")
        
        impact_df = pd.DataFrame(st.session_state.impact_radius)
        impact_df["Display"] = impact_df["File"].apply(lambda x: x.split("/")[-1])
        fig_impact = px.bar(impact_df, x="Impact_Radius", y="Display", orientation='h',
                            title="Structural Impact Radius",
                            labels={"Impact_Radius": "Downstream Impact", "Display": "File Name"},
                            hover_data={"File": True, "Display": False},
                            color="Impact_Radius", color_continuous_scale="Viridis")
        fig_impact.update_layout(yaxis={'categoryorder':'total ascending'}, height=400)
        st.plotly_chart(fig_impact, use_container_width=True)


    # 6. Process Flows (Intra vs Cross-Community)
    if "process_flows" in st.session_state:
        st.write("---")
        st.subheader("🔄 Process Flows", help="End-to-end execution paths traced through the knowledge graph. Intra-community = low coupling. Cross-community = flows that cross module boundaries = higher integration risk.")
        st.info("**Cross-community** processes span multiple modules — a high proportion signals tight inter-module coupling.")

        proc_data = st.session_state.process_flows
        if proc_data:
            proc_df = pd.DataFrame(proc_data)

            # Add emoji badge for type
            proc_df["Type Badge"] = proc_df["Type"].apply(
                lambda t: "🟢 intra" if t == "intra_community" else "🔴 cross"
            )

            intra_count = (proc_df["Type"] == "intra_community").sum()
            cross_count  = (proc_df["Type"] == "cross_community").sum()
            total_count  = len(proc_df)

            # Summary metrics
            pm1, pm2, pm3 = st.columns(3)
            pm1.metric("Total Processes", total_count)
            pm2.metric("🟢 Intra-Community", intra_count, help="Stays within one module — low coupling")
            pm3.metric("🔴 Cross-Community", cross_count, help="Crosses module boundaries — integration risk")

            # Donut chart
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

            # Detailed table
            st.write("#### Process Detail")
            st.dataframe(
                proc_df[["Process", "Type Badge", "Steps"]].rename(columns={"Type Badge": "Type"}),
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No process flow data found. Re-run `gitnexus analyze` on the repository.")

    # 7. Advanced Metrics Section
    st.write("---")
    st.subheader("🛠️ Advanced Developer Insights")

    if st.button("🔥 Calculate Code Hotspots"):
        with st.spinner("Calculating hotspots..."):
            analyze_technical_debt()

    # Display Hotspots if calculated
    if "hotspots_data" in st.session_state:
        st.write("#### Technical Debt Hotspots")
        st.info("High Churn + High Complexity = Maintenance Hotspots.")
        df_hs = pd.DataFrame(st.session_state.hotspots_data)
        st.scatter_chart(df_hs, x="Churn", y="Complexity", size="Hotspot_Score", color="Display")
        # Note: st.scatter_chart has built-in hover for all columns
        st.dataframe(df_hs.sort_values("Hotspot_Score", ascending=False), hide_index=True)
    
    st.write("---")

    if st.button("🎯 Feature vs Fix Ratio"):
        with st.spinner("Analyzing commit history..."):
            analyze_feature_fix_ratio()
    # Display Commit Stats if calculated
    if "commit_stats" in st.session_state:
        st.write("#### Feature vs Fix Efficiency")
        stats = st.session_state.commit_stats
        total = sum(stats.values())
        if total > 0:
            c1, c2, c3 = st.columns(3)
            c1.metric("Features", f"{stats['Feature']}")
            c2.metric("Fixes", f"{stats['Fix']}")
            c3.metric("Refactors", f"{stats['Refactor']}")
            
            # Simple horizontal bar chart for distribution
            dist_df = pd.Series(stats).reset_index()
            dist_df.columns = ["Type", "Count"]
            fig_dist = px.bar(dist_df, x="Count", y="Type", orientation='h',
                              title="Commit Distribution",
                              color="Type", color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_dist, use_container_width=True)
        else:
            st.warning("No commits found to analyze.")
        
    st.write("---")
    st.subheader("🛡️ Dependency Risk Shield", help="AI-powered scan of your libraries for vulnerabilities and maintenance risks.")
    
    if st.button("🔍 Scan Dependencies"):
        with st.spinner("Scanning for risky packages..."):
            analyze_dependency_vulnerabilities()
            
    if "dependency_risks" in st.session_state:
        df_deps = pd.DataFrame(st.session_state.dependency_risks)
        st.dataframe(df_deps, hide_index=True, use_container_width=True)
        st.info("💡 Always cross-verify AI security insights with official tools like `npm audit` or `safety`.")

else:
    if st.button("📊 Fetch AI Insights", type="primary"):
        fetch_criticality_index()
        fetch_impact_radius()
        fetch_process_flows()
        st.rerun()

st.write("---")
