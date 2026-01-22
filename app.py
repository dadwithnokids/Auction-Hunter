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
st.set_page_config(page_title="Vintage Hunter Debugger", page_icon="📼", layout="wide")

st.title("📼 Vintage Tech Hunter (Debug Mode)")

# --- SESSION STATE ---
if 'results_df' not in st.session_state:
    st.session_state.results_df = None
if 'urls' not in st.session_state:
    st.session_state.urls = "https://www.govdeals.com/search?kWord=vintage&miles=100&zipCode=40202\nhttps://hibid.com/lots?q=vcr&zip=40202&miles=100"

# --- CONTROLS ---
with st.expander("🛠️ Search Settings", expanded=True):
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("### 🔍 Keywords")
        # Simplified for debugging - one box for all Positive keywords
        keywords_input = st.text_area("All Target Keywords", value="sony, vcr, beta, computer, pentium, tower, camcorder, broadcast", height=100)
    with col2:
        st.markdown("### 🚫 Exclude")
        exclude_input = st.text_input("Exclude Words", value="remote, cable, manual, parts only")
        st.markdown("### 🔗 Targets")
        urls_input = st.text_area("URLs", value=st.session_state.urls, height=100, key="url_input")

    # DEBUG TOGGLE
    show_debug = st.toggle("📸 Show Debug Screenshots (Turn this on if finding nothing)", value=True)

# --- SEARCH LOGIC ---
if st.button("🔎 START SEARCH", type="primary", use_container_width=True):
    
    status = st.status("Starting scanner...", expanded=True)
    found_items = []
    
    # Prepare lists
    keywords = [k.strip().lower() for k in keywords_input.split(",") if k.strip()]
    excludes = [e.strip().lower() for e in exclude_input.split(",") if e.strip()]
    url_list = [u.strip() for u in urls_input.split("\n") if u.strip()]

    with sync_playwright() as p:
        # Launch browser with specific args to try and look "human"
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        
        # User Agent is critical for bypassing blocks
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()

        for url in url_list:
            status.write(f"Scanning: {url}...")
            try:
                page.goto(url, timeout=60000)
                page.wait_for_timeout(5000) # Wait 5 seconds for overlays to clear
                
                # Scroll down to trigger lazy loading
                page.mouse.wheel(0, 5000)
                time.sleep(2)
                
                # --- DEBUG SECTION ---
                if show_debug:
                    st.warning(f"Debug Info for: {url}")
                    st.write(f"**Page Title:** {page.title()}")
                    # Take screenshot and show it
                    screenshot = page.screenshot()
                    st.image(screenshot, caption=f"What the bot sees on {url}", use_container_width=True)
                
                # --- SCRAPER ---
                # Strategy: Get ALL text elements, not just links, to see if we can find matches
                # Then find the closest link to that text.
                
                # 1. Get all links
                links = page.query_selector_all("a")
                
                # 2. Also look for "cards" (GovDeals specific)
                # This grabs all link text
                for link in links:
                    # Get text including children elements
                    text = link.inner_text().lower().strip() 
                    href = link.get_attribute("href")
                    
                    if not text or len(text) < 4: continue
                    
                    # Logic
                    if any(k in text for k in keywords) and not any(e in text for e in excludes):
                        if href:
                            full_url = href if href.startswith("http") else f"https://{url.split('/')[2]}{href}"
                            
                            found_items.append({
                                "Item Name": text.replace("\n", " ").upper(), # Clean up newlines
                                "Source": url.split('/')[2],
                                "Link": full_url
                            })
                            
            except Exception as e:
                status.error(f"Error reading {url}: {str(e)}")

        browser.close()
    
    # Results
    if found_items:
        df = pd.DataFrame(found_items)
        st.session_state.results_df = df
        status.update(label=f"✅ Found {len(found_items)} items!", state="complete", expanded=False)
        
        st.divider()
        st.dataframe(
            df, 
            column_config={"Link": st.column_config.LinkColumn("Listing URL")},
            use_container_width=True, hide_index=True
        )
    else:
        status.update(label="❌ No results found.", state="error", expanded=False)
        st.info("Check the screenshot above. If you see a 'Verify you are human' or 'Access Denied' screen, GovDeals is blocking the cloud server.")
