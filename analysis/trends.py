import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import Counter
from wordcloud import WordCloud

from config import STOPWORDS, REPORTS_DIR


# ---------------------------------------------------------------
# TEXT CLEANING PIPELINE
# Raw OCR output is messy. Before counting words we need to:
#   1. Lowercase everything (so "Tips" and "tips" are the same)
#   2. Remove special characters and numbers
#   3. Strip extra whitespace
#   4. Remove stopwords (common words with no analytical value)
#   5. Remove very short tokens (single letters, artifacts)
# ---------------------------------------------------------------

def clean_text(text):
    """
    Cleans a raw OCR string into a list of meaningful tokens.

    A "token" is just a single word after all cleaning is applied.
    We return a list instead of a string because the analysis
    functions work directly on word lists.

    Parameters:
      text : str — raw OCR output from extractor.py

    Returns:
      list of str — cleaned, filtered word tokens
    """

    if not text or not text.strip():
        return []

    # --- Step 1: Lowercase ---
    # Unifies word variants: "Health", "HEALTH", "health" → "health"
    text = text.lower()

    # --- Step 2: Remove special characters ---
    # re.sub replaces anything that is NOT a letter or whitespace
    # with a space. This removes: punctuation, numbers, symbols,
    # OCR artifacts like "|", "}", "#", etc.
    # The pattern [^a-záéíóúüñ\s] covers both English and Spanish.
    text = re.sub(r"[^a-záéíóúüñ\s]", " ", text)

    # --- Step 3: Tokenize ---
    # Split the cleaned string on whitespace into individual words.
    tokens = text.split()

    # --- Step 4 & 5: Filter stopwords and short tokens ---
    # We discard any word that:
    #   - Is in our STOPWORDS set (defined in config.py)
    #   - Is 2 characters or shorter (likely OCR noise: "i", "a", "lt")
    tokens = [
        word for word in tokens
        if word not in STOPWORDS and len(word) > 2
    ]

    return tokens


def aggregate_tokens(ocr_results):
    """
    Takes the full list of OCR result dicts from the extractor
    and flattens all tokens into a single Counter object.

    A Counter is a dictionary subclass that maps each unique
    word to the number of times it appeared across ALL images.

    Parameters:
      ocr_results : list of dicts — output from run_ocr()
        Each dict has at least: { "file": ..., "text": ... }

    Returns:
      tuple:
        - Counter object  { "health": 14, "tips": 11, ... }
        - int: total images that had at least some text
        - int: total tokens across all images
    """

    all_tokens = []
    images_with_text = 0

    for result in ocr_results:
        tokens = clean_text(result.get("text", ""))

        if tokens:
            images_with_text += 1
            all_tokens.extend(tokens)  # flatten all tokens into one list

    word_counts = Counter(all_tokens)
    return word_counts, images_with_text, len(all_tokens)


# ---------------------------------------------------------------
# VISUALIZATION 1 — Horizontal Bar Chart
# Shows the top N most frequent words as a ranked bar chart.
# Horizontal bars are easier to read for word labels than
# vertical bars, especially with longer words.
# ---------------------------------------------------------------

def plot_bar_chart(word_counts, top_n=20):
    """
    Generates and saves a horizontal bar chart of the top N words.

    Parameters:
      word_counts : Counter — from aggregate_tokens()
      top_n       : int — how many top words to display

    Returns:
      str — file path of the saved chart image
    """

    # most_common(n) returns a list of (word, count) tuples
    # sorted from highest to lowest frequency
    top_words = word_counts.most_common(top_n)

    if not top_words:
        print("[Analysis] No words to plot.")
        return None

    # Unpack into two separate lists for matplotlib
    words  = [item[0] for item in top_words]   # ["health", "tips", ...]
    counts = [item[1] for item in top_words]   # [14, 11, ...]

    # Reverse so the highest count appears at the TOP of the chart
    words  = words[::-1]
    counts = counts[::-1]

    # --- Build a color gradient ---
    # We map each bar's rank to a color from the "Blues" colormap.
    # Colormaps in matplotlib are functions that take a value 0.0–1.0
    # and return an RGBA color tuple.
    cmap   = plt.cm.Blues
    colors = [cmap(0.4 + 0.6 * (i / len(words))) for i in range(len(words))]

    # --- Figure setup ---
    # figsize is in inches. 10x8 gives enough room for 20 labels.
    fig, ax = plt.subplots(figsize=(10, 8))

    # barh = horizontal bar chart
    # zip pairs each word with its count and color
    bars = ax.barh(words, counts, color=colors, edgecolor="white", height=0.7)

    # --- Add count labels at the end of each bar ---
    for bar, count in zip(bars, counts):
        ax.text(
            bar.get_width() + 0.2,      # x position: just past the bar end
            bar.get_y() + bar.get_height() / 2,  # y position: bar center
            str(count),
            va="center",
            fontsize=9,
            color="#333333"
        )

    # --- Styling ---
    ax.set_xlabel("Frequency", fontsize=11)
    ax.set_title(f"Top {top_n} Most Frequent Words in Pinterest Images", 
                 fontsize=13, fontweight="bold", pad=15)
    ax.spines["top"].set_visible(False)      # remove top border
    ax.spines["right"].set_visible(False)    # remove right border
    ax.set_xlim(0, max(counts) * 1.15)       # add padding on the right

    plt.tight_layout()

    # --- Save ---
    os.makedirs(REPORTS_DIR, exist_ok=True)
    output_path = os.path.join(REPORTS_DIR, "top_words_bar.png")
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()  # free memory — important in long pipelines

    print(f"[Analysis] Bar chart saved → {output_path}")
    return output_path


# ---------------------------------------------------------------
# VISUALIZATION 2 — Word Cloud
# A word cloud renders each word at a size proportional to its
# frequency. It gives an instant visual summary of dominant themes.
# ---------------------------------------------------------------

def plot_wordcloud(word_counts):
    """
    Generates and saves a word cloud image from the word frequencies.

    The WordCloud library accepts a pre-computed frequency dictionary
    directly via generate_from_frequencies(), so we don't need to
    pass raw text (Tesseract already did the hard work).

    Parameters:
      word_counts : Counter — from aggregate_tokens()

    Returns:
      str — file path of the saved word cloud image
    """

    if not word_counts:
        print("[Analysis] No words to generate word cloud.")
        return None

    # --- WordCloud configuration ---
    # width/height   : output image dimensions in pixels
    # background_color: canvas color
    # colormap       : matplotlib colormap for word colors
    # max_words      : cap on how many words to render
    # min_font_size  : smallest font allowed (avoids illegible tiny words)
    # collocations   : False prevents pairing words into bigrams
    wc = WordCloud(
        width=1200,
        height=600,
        background_color="white",
        colormap="viridis",
        max_words=100,
        min_font_size=10,
        collocations=False
    )

    # generate_from_frequencies() accepts a dict {word: count}
    # Counter IS a dict subclass, so we pass it directly
    wc.generate_from_frequencies(word_counts)

    # --- Plot with matplotlib ---
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")  # hide axes — they make no sense on an image
    ax.set_title(
        "Word Cloud — Pinterest Image Text Trends",
        fontsize=14, fontweight="bold", pad=12
    )

    plt.tight_layout()

    output_path = os.path.join(REPORTS_DIR, "wordcloud.png")
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"[Analysis] Word cloud saved → {output_path}")
    return output_path


# ---------------------------------------------------------------
# VISUALIZATION 3 — Per-Image Word Count Timeline
# Shows how many words were extracted from each image in order.
# Useful for spotting which images had the most text content,
# and identifying images where OCR likely failed (word count = 0).
# ---------------------------------------------------------------

def plot_per_image_stats(ocr_results):
    """
    Generates a line+scatter chart showing word count per image.

    Parameters:
      ocr_results : list of dicts — output from run_ocr()

    Returns:
      str — file path of the saved chart
    """

    labels = [r["file"] for r in ocr_results]
    counts = [r["words"] for r in ocr_results]
    confs  = [r.get("avg_conf", 0) for r in ocr_results]

    x = range(len(labels))

    fig, ax1 = plt.subplots(figsize=(12, 5))

    # --- Primary axis: word count as a filled area line ---
    ax1.fill_between(x, counts, alpha=0.3, color="#4C72B0")
    ax1.plot(x, counts, color="#4C72B0", linewidth=2, marker="o", markersize=4)
    ax1.set_ylabel("Word Count", color="#4C72B0", fontsize=10)
    ax1.tick_params(axis="y", labelcolor="#4C72B0")

    # --- Secondary axis: confidence score as a dashed line ---
    # twinx() creates a second Y axis sharing the same X axis.
    # This lets us overlay two different scales on one chart.
    ax2 = ax1.twinx()
    ax2.plot(x, confs, color="#DD8452", linewidth=1.5,
             linestyle="--", marker="s", markersize=3, alpha=0.8)
    ax2.set_ylabel("Avg OCR Confidence (%)", color="#DD8452", fontsize=10)
    ax2.set_ylim(0, 100)
    ax2.tick_params(axis="y", labelcolor="#DD8452")

    # --- X axis labels ---
    # Only show every 3rd label to avoid overcrowding
    ax1.set_xticks(list(x)[::3])
    ax1.set_xticklabels(labels[::3], rotation=45, ha="right", fontsize=7)

    # --- Legend ---
    patch1 = mpatches.Patch(color="#4C72B0", label="Word Count")
    patch2 = mpatches.Patch(color="#DD8452", label="OCR Confidence %")
    ax1.legend(handles=[patch1, patch2], loc="upper right", fontsize=9)

    ax1.set_title("Per-Image OCR Stats", fontsize=13, fontweight="bold", pad=12)
    ax1.spines["top"].set_visible(False)

    plt.tight_layout()

    output_path = os.path.join(REPORTS_DIR, "per_image_stats.png")
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"[Analysis] Per-image stats chart saved → {output_path}")
    return output_path


# ---------------------------------------------------------------
# CSV EXPORT
# Saves the full word frequency table as a CSV file.
# Useful for further analysis in Excel, pandas, or a database.
# ---------------------------------------------------------------

def export_csv(word_counts, ocr_results):
    """
    Exports two CSV files:
      1. word_frequencies.csv — word, count, percentage
      2. image_results.csv    — per-image file, word count, confidence, text preview

    Parameters:
      word_counts : Counter
      ocr_results : list of dicts
    """

    os.makedirs(REPORTS_DIR, exist_ok=True)
    total_words = sum(word_counts.values())

    # --- CSV 1: Word frequencies ---
    freq_data = [
        {
            "word": word,
            "count": count,
            "percentage": round(count / total_words * 100, 2)
        }
        for word, count in word_counts.most_common()
    ]
    freq_df = pd.DataFrame(freq_data)
    freq_path = os.path.join(REPORTS_DIR, "word_frequencies.csv")
    freq_df.to_csv(freq_path, index=False, encoding="utf-8")
    print(f"[Analysis] Word frequencies CSV saved → {freq_path}")

    # --- CSV 2: Per-image results ---
    image_data = [
        {
            "file": r["file"],
            "word_count": r["words"],
            "avg_confidence": r.get("avg_conf", 0),
            "text_preview": r["text"][:120].replace("\n", " ")
        }
        for r in ocr_results
    ]
    image_df = pd.DataFrame(image_data)
    image_path = os.path.join(REPORTS_DIR, "image_results.csv")
    image_df.to_csv(image_path, index=False, encoding="utf-8")
    print(f"[Analysis] Image results CSV saved → {image_path}")


# ---------------------------------------------------------------
# MAIN ENTRY POINT
# Called by main.py with the OCR results list.
# Runs the full analysis and generation pipeline.
# ---------------------------------------------------------------

def run_analysis(ocr_results):
    """
    Orchestrates the full analysis pipeline:
      1. Aggregate and count all tokens
      2. Print a summary to the console
      3. Generate bar chart
      4. Generate word cloud
      5. Generate per-image stats chart
      6. Export CSVs

    Parameters:
      ocr_results : list of dicts — from run_ocr()
    """

    print("[Analysis] Starting trend analysis...\n")

    word_counts, images_with_text, total_tokens = aggregate_tokens(ocr_results)

    # --- Console summary ---
    print(f"  Images processed     : {len(ocr_results)}")
    print(f"  Images with text     : {images_with_text}")
    print(f"  Total tokens found   : {total_tokens}")
    print(f"  Unique words         : {len(word_counts)}")
    print(f"\n  Top 10 trending words:")
    for word, count in word_counts.most_common(10):
        bar = "█" * count
        print(f"    {word:<20} {count:>4}  {bar}")
    print()

    # --- Generate outputs ---
    plot_bar_chart(word_counts, top_n=20)
    plot_wordcloud(word_counts)
    plot_per_image_stats(ocr_results)
    export_csv(word_counts, ocr_results)

    print("\n[Analysis] All reports saved to output/reports/")
    return word_counts