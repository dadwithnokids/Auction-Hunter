import streamlit as st
import subprocess
import sys
import requests
from playwright.sync_api import sync_playwright
import time

# --- BROWSER SETUP (The Cloud Fix) ---
@st.cache_resource
def install_browsers():
    # This installs the browser binaries inside the cloud container
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])

install_browsers()

# --- APP CONFIG ---
st.set_page_config(page_title="Vintage Hunter", page_icon="📼", layout="centered")

st.title("📼 Vintage Tech Hunter")
st.markdown("Your custom dashboard for finding broadcast gear, VCRs, and vintage computers.")

# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # 1. Topic
    topic = st.text_input("Ntfy Topic", value="louisville_tech_hunter")
    st.caption(f"Subscribe to '{topic}' in the Ntfy app on your phone.")
    
    # 2. Keywords
    st.subheader("Filters")
    keywords = st.text_area("Positive Keywords", value="sony, vcr, beta, broadcast, pallet, vintage, console").split(",")
    exclude = st.text_area("Negative Keywords", value="remote, cable, manual, parts only, cracked").split(",")

    # 3. URLs
    st.subheader("Search Targets")
    default_urls = "https://www.govdeals.com/search?kWord=vintage&miles=100&zipCode=40202\nhttps://hibid.com/lots?q=vcr&zip=40202&miles=100"
    urls = st.text_area("Paste URLs (One per line)", value=default_urls, height=150).split("\n")

# --- MAIN SEARCH BUTTON ---
if st.button("🔎 RUN SEARCH NOW", type="primary", use_container_width=True):
    
    status_box = st.status("Starting Search Engine...", expanded=True)
    results_container = st.container()
    found_count = 0
    
    with sync_playwright() as p:
        # Launch browser (Headless=True is required for cloud)
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        page = context.new_page()

        for url in urls:
            url = url.strip()
            if not url: continue
            
            status_box.write(f"Scanning: {url}...")
            try:
                page.goto(url, timeout=45000) # 45 second timeout
                page.wait_for_timeout(3000) # Wait 3 seconds for JS to load
                
                # Scroll to trigger lazy loading
                page.mouse.wheel(0, 4000)
                time.sleep(1)
                
                links = page.query_selector_all("a")
                
                for link in links:
                    text = link.inner_text().lower().strip()
                    href = link.get_attribute("href")
                    
                    if not text or len(text) < 4: continue
                    
                    # Clean the inputs
                    clean_keys = [k.strip().lower() for k in keywords if k.strip()]
                    clean_excl = [e.strip().lower() for e in exclude if e.strip()]
                    
                    # Logic: Must have Good Keyword AND No Bad Keyword
                    if any(k in text for k in clean_keys) and not any(e in text for e in clean_excl):
                        
                        # Build full URL
                        if href:
                            full_url = href if href.startswith("http") else f"https://{url.split('/')[2]}{href}"
                            
                            # Display Result
                            with results_container:
                                st.success(f"**{text.upper()}**")
                                st.markdown(f"[🔗 Open Listing]({full_url})")
                                st.divider()
                            
                            found_count += 1
                            
                            # Send Phone Notification
                            try:
                                requests.post(f"https://ntfy.sh/{topic}", 
                                              data=f"Found: {text}",
                                              headers={"Click": full_url})
                            except:
                                pass

            except Exception as e:
                status_box.warning(f"⚠️ Trouble reading {url}. (It might be blocking bots).")
        
        browser.close()
        
    if found_count > 0:
        status_box.update(label=f"✅ Scan Complete! Found {found_count} items.", state="complete", expanded=False)
    else:
        status_box.update(label="❌ No items found.", state="error", expanded=False)
