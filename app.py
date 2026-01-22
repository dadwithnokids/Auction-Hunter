import streamlit as st
import subprocess
import sys
import requests
import pandas as pd
from playwright.sync_api import sync_playwright
import time

# --- BROWSER SETUP ---
@st.cache_resource
def install_browsers():
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])

install_browsers()

# --- PAGE CONFIG ---
st.set_page_config(page_title="Vintage Hunter 3.0", page_icon="📼", layout="wide")

st.title("📼 Vintage Tech Hunter")

# --- 1. SESSION STATE (The Memory Fix) ---
# This block ensures your custom keywords don't disappear when you click buttons.
if 'results_df' not in st.session_state:
    st.session_state.results_df = None

# We initialize defaults only if they don't exist yet
if 'urls' not in st.session_state:
    st.session_state.urls = "https://www.govdeals.com/search?kWord=vintage&miles=100&zipCode=40202\nhttps://hibid.com/lots?q=vcr&zip=40202&miles=100"

# --- 2. THE CONTROLS (Categorized Inputs) ---
with st.expander("🛠️ Search Settings & Keywords", expanded=True):
    col1, col2, col3 = st.columns(3)
    
    # We create 3 separate keyword buckets
    with col1:
        st.markdown("### 📼 VCRs")
        vcr_keys = st.text_area("VCR Keywords", value="sony, vcr, beta, svhs, jvc, deck", height=100, key="vcr_input")
    
    with col2:
        st.markdown("### 💻 Computers")
        pc_keys = st.text_area("Computer Keywords", value="pentium, 486, tower, vintage pc, floppy, crt monitor", height=100, key="pc_input")
    
    with col3:
        st.markdown("### 📺 Broadcast/TV")
        tv_keys = st.text_area("TV Keywords", value="pvm, bvm, trinitron, broadcast, camcorder, console", height=100, key="tv_input")

    st.markdown("---")
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.markdown("**Search Targets (URLs)**")
        # We bind this text area to session_state.urls so it remembers your changes
        urls_input = st.text_area("Paste URLs here", value=st.session_state.urls, height=100, key="url_input")
    with col_b:
        st.markdown("**Notification**")
        topic = st.text_input("Ntfy Topic", value="louisville_tech_hunter")
        exclude = st.text_input("Exclude Words", value="remote, cable, manual, parts only")

# --- 3. THE SEARCH LOGIC ---
if st.button("🔎 START SEARCH", type="primary", use_container_width=True):
    
    status = st.status("Starting scanner...", expanded=True)
    found_items = []
    
    # Prepare lists
    cat_map = {
        "VCR": [k.strip().lower() for k in vcr_keys.split(",") if k.strip()],
        "Computer": [k.strip().lower() for k in pc_keys.split(",") if k.strip()],
        "TV/Broadcast": [k.strip().lower() for k in tv_keys.split(",") if k.strip()]
    }
    excludes = [e.strip().lower() for e in exclude.split(",") if e.strip()]
    url_list = [u.strip() for u in urls_input.split("\n") if u.strip()]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        page = context.new_page()

        for url in url_list:
            status.write(f"Scanning: {url}...")
            try:
                page.goto(url, timeout=45000)
                page.wait_for_timeout(3000)
                page.mouse.wheel(0, 4000)
                time.sleep(1)
                
                links = page.query_selector_all("a")
                
                for link in links:
                    text = link.inner_text().lower().strip()
                    href = link.get_attribute("href")
                    
                    if not text or len(text) < 4: continue
                    
                    # check exclusion
                    if any(ex in text for ex in excludes): continue
                    
                    # check categories
                    matched_category = None
                    for cat_name, keywords in cat_map.items():
                        if any(k in text for k in keywords):
                            matched_category = cat_name
                            break
                    
                    if matched_category and href:
                        full_url = href if href.startswith("http") else f"https://{url.split('/')[2]}{href}"
                        
                        found_items.append({
                            "Category": matched_category,
                            "Item Name": text.upper(),
                            "Source": url.split('/')[2],
                            "Link": full_url
                        })
                        
                        # Notify
                        try:
                            requests.post(f"https://ntfy.sh/{topic}", 
                                          data=f"Found: {text}", headers={"Click": full_url})
                        except: pass

            except Exception as e:
                status.warning(f"Error on {url}")

        browser.close()
    
    if found_items:
        st.session_state.results_df = pd.DataFrame(found_items)
        status.update(label=f"✅ Found {len(found_items)} items!", state="complete", expanded=False)
    else:
        status.update(label="❌ No results found.", state="error", expanded=False)

# --- 4. THE RESULTS DISPLAY (Tabs) ---
st.divider()

if st.session_state.results_df is not None:
    df = st.session_state.results_df
    
    # Create Tabs for each category + an "All" tab
    tabs = st.tabs(["📂 ALL RESULTS", "📼 VCRs", "💻 Computers", "📺 TV/Broadcast"])
    
    # Tab 1: All
    with tabs[0]:
        st.dataframe(
            df, 
            column_config={"Link": st.column_config.LinkColumn("Listing URL")},
            use_container_width=True,
            hide_index=True
        )
        
    # Tab 2: VCRs
    with tabs[1]:
        vcr_df = df[df["Category"] == "VCR"]
        if not vcr_df.empty:
            st.dataframe(
                vcr_df, 
                column_config={"Link": st.column_config.LinkColumn("Listing URL")},
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No VCRs found.")

    # Tab 3: Computers
    with tabs[2]:
        pc_df = df[df["Category"] == "Computer"]
        if not pc_df.empty:
            st.dataframe(
                pc_df, 
                column_config={"Link": st.column_config.LinkColumn("Listing URL")},
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No Computers found.")

    # Tab 4: TV
    with tabs[3]:
        tv_df = df[df["Category"] == "TV/Broadcast"]
        if not tv_df.empty:
            st.dataframe(
                tv_df, 
                column_config={"Link": st.column_config.LinkColumn("Listing URL")},
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No TV/Broadcast gear found.")
            
else:
    st.info("👋 Set your keywords above and click 'START SEARCH'")
