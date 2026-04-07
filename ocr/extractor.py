import os
import pytesseract
from PIL import Image, ImageFilter, ImageEnhance
from config import OCR_LANG, IMAGES_DIR

# ---------------------------------------------------------------
# IMPORTANT: Tell pytesseract where the Tesseract binary lives.
# If you installed Tesseract in a different path, update this.
# ---------------------------------------------------------------
pytesseract.pytesseract.tesseract_cmd = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)


# ---------------------------------------------------------------
# PAGE SEGMENTATION MODES (PSM)
# Tesseract needs to know HOW to read the image layout.
# Each mode tells the engine what to expect:
#
#  3  → Fully automatic page segmentation (default)
#       Best for complex layouts: columns, mixed text/images
#
#  6  → Assume a single uniform block of text
#       Best for infographics, memes, quote images
#
#  11 → Sparse text — find as much text as possible
#       Best for images with scattered words (labels, tags)
#
#  12 → Sparse text with OSD (orientation detection)
#       Like 11 but also detects if text is rotated
#
# We'll use PSM 6 as default since Pinterest images tend to be
# self-contained blocks of text (tips, quotes, infographics).
# ---------------------------------------------------------------
DEFAULT_PSM = 6


# ---------------------------------------------------------------
# OCR ENGINE MODES (OEM)
# Controls WHICH recognition engine Tesseract uses internally:
#
#  0 → Legacy engine only (old, pattern-matching based)
#  1 → Neural net LSTM engine only (modern, deep learning)
#  2 → Legacy + LSTM combined
#  3 → Default — Tesseract picks the best available
#
# We use OEM 3 so Tesseract decides, but LSTM (mode 1) is
# generally more accurate for clean, modern fonts.
# ---------------------------------------------------------------
DEFAULT_OEM = 3


def preprocess_image(image_path):
    """
    Loads and prepares an image for OCR.

    Raw photos straight from Pinterest are often not ideal for
    Tesseract: they may be too small, blurry, low contrast, or
    have color backgrounds that confuse the engine.

    Preprocessing converts the image to a state where Tesseract
    can recognize characters more accurately.

    Steps applied:
      1. Open image with Pillow
      2. Convert to grayscale
      3. Resize if too small
      4. Sharpen edges
      5. Increase contrast
      6. Convert to pure black & white (binarization)
    """

    # --- Step 1: Open the image ---
    # Pillow (PIL) loads the image into memory as a pixel matrix.
    # It supports JPG, PNG, WEBP, BMP, and more automatically.
    img = Image.open(image_path)

    # --- Step 2: Convert to Grayscale ---
    # Tesseract works on luminance (brightness), not color.
    # Converting to "L" mode (8-bit grayscale) removes color
    # channels (R, G, B) and keeps only brightness per pixel.
    # This reduces noise introduced by color variations.
    img = img.convert("L")

    # --- Step 3: Resize if the image is too small ---
    # Tesseract struggles with small text. If either dimension
    # is under 1000px, we scale up by 2x using LANCZOS resampling,
    # which is the highest quality algorithm for upscaling.
    # More pixels = more detail for the OCR engine to work with.
    width, height = img.size
    if width < 1000 or height < 1000:
        img = img.resize((width * 2, height * 2), Image.LANCZOS)

    # --- Step 4: Sharpen ---
    # Pinterest images sometimes have slight blurring from compression.
    # The SHARPEN filter applies a convolution kernel that enhances
    # edge contrast between adjacent pixels, making letter outlines
    # crisper and easier to detect.
    img = img.filter(ImageFilter.SHARPEN)

    # --- Step 5: Enhance Contrast ---
    # ImageEnhance.Contrast adjusts the difference between dark and
    # light pixels. A factor of 2.0 doubles the contrast:
    # dark areas get darker, light areas get lighter.
    # This is especially helpful for images with gray-on-white or
    # light-colored text on pale backgrounds.
    img = ImageEnhance.Contrast(img).enhance(2.0)

    # --- Step 6: Binarization (Thresholding) ---
    # This converts the grayscale image to pure black and white.
    # Every pixel below brightness 140 becomes black (0),
    # every pixel at or above 140 becomes white (255).
    # Tesseract's internal models were trained on black text on
    # white backgrounds, so this dramatically improves accuracy.
    # The threshold value 140 works well for most infographics;
    # you can tune it between 100–180 depending on your images.
    img = img.point(lambda pixel: 0 if pixel < 140 else 255, "1")

    return img


def extract_text(image_path, psm=DEFAULT_PSM, oem=DEFAULT_OEM):
    """
    Runs Tesseract OCR on a single image and returns the
    extracted text as a clean string.

    Parameters:
      image_path : str  — path to the .jpg file
      psm        : int  — Page Segmentation Mode (see above)
      oem        : int  — OCR Engine Mode (see above)

    Returns:
      str — the raw text found in the image, or "" if nothing found
    """

    try:
        # Preprocess the image before sending to Tesseract
        img = preprocess_image(image_path)

        # --- Tesseract Configuration String ---
        # This is passed directly to the Tesseract binary as CLI flags.
        # --psm : page segmentation mode
        # --oem : OCR engine mode
        # -c tessedit_char_whitelist : optional character whitelist
        #   (commented out here, but you could restrict to only
        #    letters+numbers if you wanted cleaner output)
        config = f"--psm {psm} --oem {oem}"

        # --- image_to_string() ---
        # This is the core pytesseract call. It:
        #   1. Saves the Pillow image to a temp file internally
        #   2. Calls the Tesseract binary with your config flags
        #   3. Reads Tesseract's stdout (the recognized text)
        #   4. Returns it as a Python string
        # The `lang` parameter maps to Tesseract's trained data files
        # located in its tessdata/ folder (e.g. eng.traineddata)
        raw_text = pytesseract.image_to_string(
            img,
            lang=OCR_LANG,
            config=config
        )

        # Clean the output: strip leading/trailing whitespace
        # and collapse multiple blank lines into one
        cleaned = "\n".join(
            line for line in raw_text.splitlines() if line.strip()
        )

        return cleaned

    except Exception as e:
        print(f"[OCR] Error processing {image_path}: {e}")
        return ""


def extract_with_confidence(image_path, min_confidence=60):
    """
    Advanced version: extracts text word-by-word WITH confidence scores.

    Tesseract can return a confidence score (0-100) for each word
    it recognizes. This lets us filter out low-confidence guesses
    that are likely garbage characters.

    Uses image_to_data() instead of image_to_string() — this returns
    a TSV (tab-separated) table with one row per word, containing:
      - level      : hierarchy level (page/block/line/word)
      - left/top   : pixel position of the word
      - width/height: bounding box dimensions
      - conf       : confidence score (-1 means non-text element)
      - text       : the recognized word

    Parameters:
      image_path     : str — path to the image
      min_confidence : int — discard words below this score (0-100)

    Returns:
      dict with keys:
        "text"       : filtered text string
        "words"      : list of (word, confidence) tuples
        "avg_conf"   : average confidence across all valid words
    """

    try:
        img = preprocess_image(image_path)
        config = f"--psm {DEFAULT_PSM} --oem {DEFAULT_OEM}"

        # image_to_data returns a pandas-style TSV string by default.
        # Output type DICT gives us a Python dictionary directly,
        # where each key is a column name and values are lists.
        data = pytesseract.image_to_data(
            img,
            lang=OCR_LANG,
            config=config,
            output_type=pytesseract.Output.DICT
        )

        words = []
        confidences = []

        # Iterate over each detected word
        n_boxes = len(data["text"])
        for i in range(n_boxes):
            word = data["text"][i].strip()
            conf = int(data["conf"][i])

            # conf == -1 means Tesseract detected a layout element
            # (like a block separator), not actual text — skip it.
            # We also skip empty strings and low-confidence words.
            if conf == -1 or not word:
                continue

            if conf >= min_confidence:
                words.append((word, conf))
                confidences.append(conf)

        # Reconstruct the filtered text from accepted words only
        filtered_text = " ".join(w for w, _ in words)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0

        return {
            "text": filtered_text,
            "words": words,
            "avg_conf": round(avg_conf, 2)
        }

    except Exception as e:
        print(f"[OCR] Error in confidence extraction: {e}")
        return {"text": "", "words": [], "avg_conf": 0}


def process_all_images(image_paths, use_confidence=False, min_confidence=60):
    """
    Runs OCR on a list of image paths and returns structured results.

    Parameters:
      image_paths    : list of str — paths from the scraper module
      use_confidence : bool — use basic or confidence-based extraction
      min_confidence : int — minimum word confidence threshold

    Returns:
      list of dicts, one per image:
        {
          "file"    : filename,
          "path"    : full path,
          "text"    : extracted text,
          "avg_conf": average confidence (0 if basic mode),
          "words"   : word count
        }
    """

    results = []
    total = len(image_paths)

    for i, path in enumerate(image_paths):
        filename = os.path.basename(path)
        print(f"[OCR] Processing {i+1}/{total}: {filename}")

        if use_confidence:
            extracted = extract_with_confidence(path, min_confidence)
            text = extracted["text"]
            avg_conf = extracted["avg_conf"]
        else:
            text = extract_text(path)
            avg_conf = 0

        word_count = len(text.split()) if text else 0

        results.append({
            "file": filename,
            "path": path,
            "text": text,
            "avg_conf": avg_conf,
            "words": word_count
        })

        # Show a preview of what was found
        preview = text[:80].replace("\n", " ") if text else "(no text detected)"
        print(f"         → {word_count} words | Preview: {preview}...")

    print(f"\n[OCR] Done. Processed {total} images.\n")
    return results


def run_ocr(image_paths):
    """
    Entry point called by main.py.
    Uses confidence-based extraction for better quality results.
    """
    return process_all_images(
        image_paths,
        use_confidence=True,
        min_confidence=60
    )