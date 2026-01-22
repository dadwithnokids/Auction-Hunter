import streamlit as st
import subprocess
import sys
import requests
import pandas as pd # New library for the fancy table
from playwright.sync_api import sync_playwright
import time

# --- BROWSER SETUP ---
@st.cache_resource
def install_browsers():
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])

install_browsers()

# --- APP CONFIG ---
st.set_page_config(page_title="Vintage Hunter 2.0", page_icon="📼", layout="wide") # 'wide' mode uses full screen

st.title("📼 Vintage Tech Hunter")

# --- SESSION STATE (Memory) ---
# This keeps your settings saved even if you click buttons
if 'keywords' not in st.session_state:
    st.session_state.keywords = "sony, vcr, beta, broadcast, pallet"
if 'results_df' not in st.session_state:
    st.session_state.results_df = None

# --- TABS LAYOUT ---
tab1, tab2 = st.tabs(["🔎 Control Panel", "📊 Results & Filter"])

with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("1. Choose Your Hunt")
        # Quick Preset Buttons
        st.caption("Tap a preset to auto-load keywords:")
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        if btn_col1.button("📼 VCRs"):
            st.session_state.keywords = "sony, vcr, beta, broadcast, svhs, jvc"
            st.rerun()
        if btn_col2.button("💻 Computers"):
            st.session_state.keywords = "vintage computer, 486, pentium, tower, crt monitor, floppy"
            st.rerun()
        if btn_col3.button("🎥 Cameras"):
            st.session_state.keywords = "handycam, camcorder, video8, hi8, digital8, ccd"
            st.rerun()

        # The Keyword Inputs
        keywords_input = st.text_area("Target Keywords", value=st.session_state.keywords, height=100)
        exclude_input = st.text_input("Exclude Keywords", value="remote, cable, manual, parts only, cracked")
    
    with col2:
        st.subheader("2. Target Sites")
        default_urls = "https://www.govdeals.com/search?kWord=vintage&miles=100&zipCode=40202\nhttps://hibid.com/lots?q=vcr&zip=40202&miles=100"
        urls_input = st.text_area("Paste Search URLs", value=default_urls, height=180)
        
        st.subheader("3. Notifications")
        topic = st.text_input("Ntfy Topic Name", value="louisville_tech_hunter")

    # The Big Search Button
    st.divider()
    if st.button("🚀 LAUNCH SEARCH ENGINE", type="primary", use_container_width=True):
        
        status_box = st.status("Starting engines...", expanded=True)
        found_data = [] # List to store data for the table
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            page = context.new_page()

            url_list = urls_input.split("\n")
            for url in url_list:
                url = url.strip()
                if not url: continue
                
                status_box.write(f"Scanning: {url}...")
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
                        
                        # Filtering Logic
                        clean_keys = [k.strip().lower() for k in keywords_input.split(",") if k.strip()]
                        clean_excl = [e.strip().lower() for e in exclude_input.split(",") if e.strip()]
                        
                        if any(k in text for k in clean_keys) and not any(e in text for e in clean_excl):
                            if href:
                                full_url = href if href.startswith("http") else f"https://{url.split('/')[2]}{href}"
                                
                                # Add to data list
                                found_data.append({
                                    "Item Name": text.upper(),
                                    "Source": url.split('/')[2], # Extracts 'govdeals.com'
                                    "Link": full_url
                                })
                                
                                # Send Notification
                                try:
                                    requests.post(f"https://ntfy.sh/{topic}", 
                                                  data=f"Found: {text}", headers={"Click": full_url})
                                except: pass

                except Exception as e:
                    status_box.warning(f"⚠️ Issues with {url}")
            
            browser.close()
        
        # Save results to session state
        if found_data:
            st.session_state.results_df = pd.DataFrame(found_data)
            status_box.update(label=f"✅ Found {len(found_data)} items!", state="complete", expanded=False)
        else:
            st.session_state.results_df = None
            status_box.update(label="❌ No items found.", state="error", expanded=False)

with tab2:
    st.header("Search Results")
    
    if st.session_state.results_df is not None:
        # DATA EDITOR: This is the magic sortable table
        st.data_editor(
            st.session_state.results_df,
            column_config={
                "Link": st.column_config.LinkColumn("Listing URL") # Makes links clickable
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Run a search in the 'Control Panel' tab to see results here.")
