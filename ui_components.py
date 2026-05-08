import os
import base64
import streamlit as st
import streamlit.components.v1 as components

# Get absolute path to the current file's directory
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

def apply_custom_css():
    st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">

<style>

.lottie-wrapper div {
    background-color: transparent !important;
}

/* Animated Gradient Background */
.stApp {
    background: linear-gradient(-45deg, #0b0d17, #1c2541, #3a506b, #0b0d17);
    background-size: 400% 400%;
    animation: gradientBG 10s ease infinite;
    color: #e0e1dd;
    font-family: 'Inter', sans-serif;
}

@keyframes gradientBG {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* Floating animation for title */
@keyframes float {
    0% { transform: translateY(0px); }
    50% { transform: translateY(-10px); }
    100% { transform: translateY(0px); }
}

.floating-title {
    animation: float 4s ease-in-out infinite;
    text-align: center;
    font-size: 4rem;
    font-weight: 800;
    margin-top: 1rem;
    margin-bottom: 0.5rem;
    background: -webkit-linear-gradient(#ffffff, cornflowerblue);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

/* Subtitle styling */
.subtitle {
    text-align: center;
    font-size: 1.2rem;
    color: #a0aab2;
    margin-bottom: 0.5rem;
    font-family: 'Inter', sans-serif;
}

/* Center markdown content globally */
[data-testid="stMarkdownContainer"] {
    text-align: center;
}

/* Preserve left alignment for specific components */
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
.info-card [data-testid="stMarkdownContainer"],
.tooltiptext [data-testid="stMarkdownContainer"],
.rule-row [data-testid="stMarkdownContainer"] {
    text-align: left !important;
}

/* Global Heading Styles for consistency */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Inter', sans-serif
}

/* Custom cards for Helpful notes */
.info-card {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 15px;
    padding: 1.5rem;
    backdrop-filter: blur(5px);
    -webkit-backdrop-filter: blur(5px);
    height: 100%;
    min-height: 180px; /* Ensures uniform height across cards */
    display: flex;
    flex-direction: column;
    text-align: left;
    transition: transform 0.3s ease;
    border: 1px solid rgba(0, 210, 255, 0.2); 
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.8);    
}

.info-card:hover {
    transform: translateY(-5px);
    background: rgba(255, 255, 255, 0.1);
}

.info-card h3 {
    margin-top: 0;
    color: cornflowerblue;
    font-size: 1.2rem;
}

.info-card p {
    color: #e0e1dd;
    font-size: 0.95rem;
}

/* Hide top header to look cleaner */
header {display: none !important;}

/* Adjust main container flow and make room for the fixed header */
.block-container,
[data-testid="stAppViewBlockContainer"],
[data-testid="stMainBlockContainer"] {
    padding-top: 175px !important;
    padding-bottom: 1rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    max-width: 98% !important;
}

/* Full-Width Fixed Header Container via Anchor */
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] > div:has(.header-anchor) {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    width: 100vw !important;
    margin: 0 !important;
    z-index: 1000000 !important;
    display: flex !important;
    justify-content: center !important;
    background: rgba(11, 13, 23, 0.2) !important;
    backdrop-filter: blur(20px) saturate(180%) !important;
    -webkit-backdrop-filter: blur(20px) saturate(180%) !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
    padding: 10px 0 !important;
}

.header-anchor {
    display: none;
}

/* Completely collapse and hide the Streamlit container that holds the anchor */
div[data-testid="stElementContainer"]:has(.header-anchor) {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    min-height: 0 !important;
    max-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
    position: absolute !important;
}

/* Adjust input text size & styling */
div[data-baseweb="input"] {
    background-color: rgba(255, 255, 255, 0.05) !important;
    border-radius: 10px !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    transition: box-shadow 0.3s ease, border-color 0.3s ease;
}

div[data-baseweb="input"]:focus-within {
    border-color: cornflowerblue !important;
    box-shadow: 0 0 8px rgba(100, 149, 237, 0.6) !important;
}

/* Customize st.button styling */
div.stButton > button {
    background: linear-gradient(135deg, cornflowerblue, #3a506b);
    color: white;
    border-radius: 10px;
    border: none;
    padding: 0.75rem 2rem;
    font-weight: 600;
    width: 100%;
    transition: all 0.3s ease;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
}
div.stButton > button:hover {
    box-shadow: 0 0 20px rgba(100, 149, 237, 0.6);
    background: linear-gradient(135deg, #3a506b, cornflowerblue);
    color: #ffffff;
    border-color: transparent;
    transform: translateY(-2px);
}

/* Make tabs full width and equal */
div[data-testid="stTabs"] button {
    flex: 1;
    text-align: center;
    color: #a0aab2 !important;
    transition: all 0.3s ease;
}

div[data-testid="stTabs"] button p {
    color: #a0aab2 !important;
}

div[data-testid="stTabs"] button[aria-selected="true"] {
    color: cornflowerblue !important;
    background: rgba(100, 149, 237, 0.1) !important;
}

div[data-testid="stTabs"] button[aria-selected="true"] p {
    color: cornflowerblue !important;
}

/* Tab indicator (the moving underline) */
div[data-testid="stTabs"] [data-baseweb="tab-highlight"] {
    background-color: cornflowerblue !important;
}

/* Hover effect for tabs */
div[data-testid="stTabs"] button:hover {
    color: #ffffff !important;
}

div[data-testid="stTabs"] button:hover p {
    color: #ffffff !important;
}

/* Custom styling for st.chat_input */
div[data-testid="stChatInput"] {
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    border-radius: 12px !important;
    background-color: rgba(255, 255, 255, 0.05) !important;
    padding: 2px !important;
}

/* Remove ALL inner borders and focus rings from Streamlit/BaseWeb */
div[data-testid="stChatInput"] > div,
div[data-testid="stChatInput"] [data-baseweb="textarea"],
div[data-testid="stChatInput"] [data-baseweb="textarea"] > div,
div[data-testid="stChatInput"] textarea {
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
    background-color: transparent !important;
}

div[data-testid="stChatInput"] textarea {
    color: #e0e1dd !important;
}

div[data-testid="stChatInput"]:focus-within {
    border-color: cornflowerblue !important;
    box-shadow: 0 0 10px rgba(100, 149, 237, 0.4) !important;
}

/* High-contrast Glassmorphism for containers (Chatbox) */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(145deg, rgba(10, 15, 28, 0.98), rgba(28, 37, 65, 0.98)) !important;
    backdrop-filter: blur(20px) !important;
    border: 1px solid rgba(100, 149, 237, 0.4) !important;
    border-radius: 20px !important;
    padding: 24px !important;
    box-shadow: 0 12px 60px rgba(0, 0, 0, 0.8) !important;
    margin-top: 10px !important;
}

/* More distinct styling for individual chat messages */
[data-testid="stChatMessage"] {
    background-color: rgba(255, 255, 255, 0.04) !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    border-radius: 16px !important;
    margin-bottom: 16px !important;
    padding: 12px !important;
    transition: all 0.3s ease;
}

[data-testid="stChatMessage"]:hover {
    background-color: rgba(100, 149, 237, 0.08) !important;
    border-color: rgba(100, 149, 237, 0.4) !important;
    transform: translateX(5px);
}

/* Tooltip container */
.tooltip {
    position: relative;
    display: inline-block;
    cursor: pointer;
    margin-left: 8px;
    margin-right: 15px;
    vertical-align: middle;
    color: cornflowerblue;
}

/* Tooltip text */
.tooltip .tooltiptext {
    visibility: hidden;
    width: 220px;
    background: rgba(15, 23, 42, 0.95);
    color: #fff;
    text-align: left;
    border: 1px solid rgba(100, 149, 237, 0.3);
    border-radius: 12px;
    padding: 13px;
    position: absolute;
    z-index: 10000;
    bottom: 125%;
    left: 50%;
    transform: translateX(-50%);
    opacity: 0;
    transition: opacity 0.3s, transform 0.3s;
    backdrop-filter: blur(15px);
    box-shadow: 0 12px 40px rgba(0,0,0,0.6);
    font-size: 0.85rem;
    line-height: 1.5;
}

/* Tooltip arrow */
.tooltip .tooltiptext::after {
    content: "";
    position: absolute;
    top: 100%;
    left: 50%;
    margin-left: -6px;
    border-width: 6px;
    border-style: solid;
    border-color: rgba(100, 149, 237, 0.3) transparent transparent transparent;
}

/* Show the tooltip text on hover */
.tooltip:hover .tooltiptext {
    visibility: visible;
    opacity: 1;
    transform: translateX(-50%) translateY(-5px);
}

.score-badge {
    padding: 6px 14px;
    border-radius: 30px;
    font-weight: 700;
    font-size: 1rem;
    display: inline-flex;
    align-items: center;
    gap: 8px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}

.score-high { background: rgba(239, 68, 68, 0.15); color: #ff5f5f; border: 1px solid rgba(239, 68, 68, 0.4); }
.score-med { background: rgba(245, 158, 11, 0.15); color: #ffb02e; border: 1px solid rgba(245, 158, 11, 0.4); }
.score-low { background: rgba(34, 197, 94, 0.15); color: #4ade80; border: 1px solid rgba(34, 197, 94, 0.4); }

.rule-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 4px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    padding-bottom: 4px;
}
.rule-name { color: #a0aab2; }
.rule-weight { color: cornflowerblue; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

def render_lottie_transparent(filepath: str, height: int = 200, align: str = "center"):
    if not os.path.exists(filepath):
        return
    with open(filepath, "r") as f:
        lottie_json = f.read()
    b64_json = base64.b64encode(lottie_json.encode('utf-8')).decode('utf-8')
    data_uri = f"data:application/json;base64,{b64_json}"
    
    html_str = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <script src="https://unpkg.com/@lottiefiles/lottie-player@latest/dist/lottie-player.js"></script>
        <style>
            body, html {{
                margin: 0;
                padding: 0;
                background-color: transparent !important;
                overflow: hidden;
            }}
        </style>
    </head>
    <body style="background-color: transparent !important; display: flex; justify-content: {align if align != 'right' else 'flex-end'}; align-items: center;">
        <lottie-player 
            src="{data_uri}"
            background="transparent" 
            speed="1" 
            style="width: {height}px; height: {height}px;" 
            loop 
            autoplay>
        </lottie-player>
    </body>
    </html>
    """
    components.html(html_str, height=height)

def render_header():
    with st.container():
        st.markdown('<div class="header-anchor"></div>', unsafe_allow_html=True)
        # Adjusted split to visually balance the narrow logo and wide title
        col_logo, col_title = st.columns([1.6, 2.4])
        with col_logo:
            # Logo right-aligned in its column
            render_lottie_transparent(os.path.join(ROOT_DIR, "assets", "AI.json"), height=130, align="right")
        with col_title:
            # Title left-aligned in its column
            st.markdown('<div class="floating-title" style="text-align: left; font-size: 4rem; margin-top: 25px; margin-left: -1rem; white-space: nowrap;">Repo Whisperer</div>', unsafe_allow_html=True)

        # Subtitle centered below the logo+title group
        st.markdown('<div class="subtitle" style="text-align: center; margin-top: -40px;">- AI-Powered Repository Intelligence & Analysis</div>', unsafe_allow_html=True)
        st.markdown("<hr style='margin-top: 5px; margin-bottom: 10px; opacity: 0.1;'/>", unsafe_allow_html=True)

def render_footer():
    st.markdown("""
<div style="text-align: center; color: #a0aab2; font-size: 0.75rem; margin-top: 0.5rem; margin-bottom: 1rem;">
    ⚠️ <b>AI Warning:</b> The analyses, risks, and insights provided by Repo Whisperer are generated using Artificial Intelligence. 
    While designed to be helpful, they may occasionally produce inaccurate or incomplete information.
</div>
""", unsafe_allow_html=True)
