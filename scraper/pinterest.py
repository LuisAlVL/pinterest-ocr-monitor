import time
import requests
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

from config import PINTEREST_URL, MAX_IMAGES, PAGE_LOAD_WAIT, IMAGES_DIR


def create_driver():
    """
    Sets up and returns a Chrome browser controlled by Selenium.
    """
    options = webdriver.ChromeOptions()

    # Run browser in the background (no visible window)
    # Comment this line out if you want to SEE the browser open
    options.add_argument("--headless=new")

    # These options make the browser more stable and avoid detection
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Pretend to be a real user browser, not a bot
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # webdriver-manager automatically downloads the correct ChromeDriver version
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    return driver


def scroll_and_collect(driver, query):
    """
    Scrolls down the Pinterest page several times to trigger
    lazy loading, then collects all image URLs found.
    """
    print(f"[Scraper] Opening: {PINTEREST_URL + query}")
    driver.get(PINTEREST_URL + query)

    # Wait until at least one <img> tag appears on the page
    # This prevents BeautifulSoup from parsing an empty page
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "img"))
    )

    image_urls = set()  # Use a set to automatically avoid duplicates

    # Scroll down multiple times to load more images
    # Pinterest loads images in batches as you scroll (lazy loading)
    scroll_attempts = 5
    for i in range(scroll_attempts):
        print(f"[Scraper] Scroll {i + 1}/{scroll_attempts}...")

        # Scroll to the very bottom of the page
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait for new images to load after scrolling
        time.sleep(PAGE_LOAD_WAIT)

        # Hand the current page HTML to BeautifulSoup for parsing
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Find all <img> tags and extract their src attribute
        for img in soup.find_all("img"):
            src = img.get("src") or img.get("data-src")

            # Filter out small icons, avatars and placeholders
            # Pinterest uses "236x" or "736x" in the URL for real pin images
            if src and ("236x" in src or "736x" in src):
                image_urls.add(src)

        print(f"[Scraper] {len(image_urls)} unique images found so far...")

        if len(image_urls) >= MAX_IMAGES:
            break

    return list(image_urls)[:MAX_IMAGES]


def download_images(image_urls):
    """
    Downloads each image URL to the output/images/ folder.
    Returns a list of local file paths for the OCR module to process.
    """
    os.makedirs(IMAGES_DIR, exist_ok=True)
    local_paths = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    for i, url in enumerate(image_urls):
        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                filename = f"pin_{i+1:03d}.jpg"
                filepath = os.path.join(IMAGES_DIR, filename)

                with open(filepath, "wb") as f:
                    f.write(response.content)

                local_paths.append(filepath)
                print(f"[Downloader] Saved: {filename}")
            else:
                print(f"[Downloader] Failed ({response.status_code}): {url}")

        except Exception as e:
            print(f"[Downloader] Error on image {i+1}: {e}")

    return local_paths


def run_scraper(query):
    """
    Main function that orchestrates the full scraping flow:
    1. Open browser
    2. Scroll and collect image URLs
    3. Download images locally
    4. Close browser
    """
    driver = create_driver()

    try:
        image_urls = scroll_and_collect(driver, query)
        print(f"\n[Scraper] Total images collected: {len(image_urls)}")

        local_paths = download_images(image_urls)
        print(f"[Scraper] Total images downloaded: {len(local_paths)}\n")

        return local_paths

    finally:
        # Always close the browser, even if an error occurred
        driver.quit()
        print("[Scraper] Browser closed.")