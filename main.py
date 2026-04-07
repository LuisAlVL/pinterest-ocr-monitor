import os
import sys
import time
from datetime import datetime

from scraper.pinterest import run_scraper
from ocr.extractor import run_ocr
from analysis.trends import run_analysis


# ---------------------------------------------------------------
# BANNER
# Just a visual separator so the console output is easy to read
# when you run the full pipeline.
# ---------------------------------------------------------------

def print_banner():
    print("""
╔══════════════════════════════════════════════╗
║       Pinterest OCR Trend Monitor            ║
║       Scrape → Extract → Analyze             ║
╚══════════════════════════════════════════════╝
    """)


def print_step(step_number, title):
    print(f"\n{'='*50}")
    print(f"  STEP {step_number}: {title}")
    print(f"{'='*50}\n")


# ---------------------------------------------------------------
# STEP RUNNERS
# Each function wraps one module and handles timing + errors
# independently so a failure in one step doesn't silently corrupt
# the next one.
# ---------------------------------------------------------------

def step_scrape(query):
    """
    Runs the Pinterest scraper.
    Returns a list of local image file paths, or exits if it fails.
    """
    print_step(1, "Scraping Pinterest & Downloading Images")
    start = time.time()

    try:
        image_paths = run_scraper(query)
    except Exception as e:
        print(f"\n[ERROR] Scraper failed: {e}")
        print("  Possible causes:")
        print("  - No internet connection")
        print("  - Pinterest blocked the request (try again in a few minutes)")
        print("  - ChromeDriver version mismatch (run: pip install --upgrade webdriver-manager)")
        sys.exit(1)

    elapsed = round(time.time() - start, 2)

    if not image_paths:
        print("[ERROR] No images were downloaded. Exiting.")
        sys.exit(1)

    print(f"\n  ✓ {len(image_paths)} images downloaded in {elapsed}s")
    return image_paths


def step_ocr(image_paths):
    """
    Runs Tesseract OCR on every downloaded image.
    Returns a list of result dicts with extracted text.
    """
    print_step(2, "Running OCR on Downloaded Images")
    start = time.time()

    try:
        ocr_results = run_ocr(image_paths)
    except Exception as e:
        print(f"\n[ERROR] OCR failed: {e}")
        print("  Possible causes:")
        print("  - Tesseract is not installed or not in PATH")
        print("  - Wrong tesseract_cmd path in extractor.py")
        print("  - Language pack not installed (run: pip install pytesseract)")
        sys.exit(1)

    elapsed = round(time.time() - start, 2)

    # Count how many images actually had text
    with_text = sum(1 for r in ocr_results if r["words"] > 0)
    avg_conf  = sum(r["avg_conf"] for r in ocr_results) / len(ocr_results)

    print(f"\n  ✓ OCR complete in {elapsed}s")
    print(f"  ✓ {with_text}/{len(ocr_results)} images contained readable text")
    print(f"  ✓ Average OCR confidence: {round(avg_conf, 1)}%")

    return ocr_results


def step_analysis(ocr_results):
    """
    Runs the trend analysis and generates all output files.
    """
    print_step(3, "Analyzing Trends & Generating Reports")
    start = time.time()

    try:
        word_counts = run_analysis(ocr_results)
    except Exception as e:
        print(f"\n[ERROR] Analysis failed: {e}")
        print("  Possible causes:")
        print("  - wordcloud or matplotlib not installed")
        print("  - output/reports/ folder has a permission issue")
        sys.exit(1)

    elapsed = round(time.time() - start, 2)
    print(f"\n  ✓ Analysis complete in {elapsed}s")
    return word_counts


# ---------------------------------------------------------------
# FINAL SUMMARY
# Printed at the end of a successful run so you know exactly
# where to find every output file.
# ---------------------------------------------------------------

def print_summary(image_paths, ocr_results, word_counts, run_start):
    total_time = round(time.time() - run_start, 2)
    top5 = word_counts.most_common(5)

    print(f"""
╔══════════════════════════════════════════════╗
║               RUN COMPLETE ✓                 ║
╚══════════════════════════════════════════════╝

  Total runtime        : {total_time}s
  Images scraped       : {len(image_paths)}
  Images with text     : {sum(1 for r in ocr_results if r['words'] > 0)}
  Unique words found   : {len(word_counts)}

  Top 5 trending words :
    { chr(10).join(f"    {i+1}. {w:<18} ({c} times)" for i, (w,c) in enumerate(top5)) }

  Output files:
    output/images/          ← downloaded Pinterest images
    output/reports/top_words_bar.png
    output/reports/wordcloud.png
    output/reports/per_image_stats.png
    output/reports/word_frequencies.csv
    output/reports/image_results.csv

  Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    """)


# ---------------------------------------------------------------
# ENTRY POINT
# Python runs this block when you call: python main.py
# The `if __name__ == "__main__"` guard ensures this code
# doesn't execute if another module imports main.py.
# ---------------------------------------------------------------

if __name__ == "__main__":
    run_start = time.time()
    print_banner()

    query = input("Enter a topic: ")

    image_paths  = step_scrape(query)
    ocr_results  = step_ocr(image_paths)
    word_counts  = step_analysis(ocr_results)

    print_summary(image_paths, ocr_results, word_counts, run_start)