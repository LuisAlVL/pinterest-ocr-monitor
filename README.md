# 📌 Pinterest OCR Trend Monitor

A Python pipeline that scrapes Pinterest search results, downloads images, extracts text using Tesseract OCR, and generates visual trend reports showing the most frequent words found across images.

```
Enter query -> Scrape Pinterest → Download Images → Run OCR → Analyze Trends → Generate Reports
```

---

## 🖼️ Example Output

| Bar Chart | Word Cloud |
|-----------|------------|
| Top 20 most frequent words across all images | Visual summary of dominant themes |

> Reports are saved to `output/reports/` after each run.

---

## ⚙️ Requirements

- Python 3.9+
- Google Chrome installed
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) installed and added to PATH

Verify Tesseract is working:
```cmd
tesseract --version
```

---

## 🚀 Setup & Run

```cmd
git clone https://github.com/YOUR_USERNAME/pinterest-ocr-monitor.git
cd pinterest-ocr-monitor

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

python main.py
```

---

## 📁 Project Structure

```
pinterest-ocr-monitor/
│
├── scraper/
│   └── pinterest.py        # Selenium + BeautifulSoup scraper
│
├── ocr/
│   └── extractor.py        # Tesseract OCR pipeline
│
├── analysis/
│   └── trends.py           # Word frequency analysis + charts
│
├── output/
│   ├── images/             # Downloaded Pinterest images (gitignored)
│   └── reports/            # Generated charts and CSVs (gitignored)
│
├── main.py                 # Entry point — runs the full pipeline
├── config.py               # Search URL, language, limits, stopwords
└── requirements.txt
```

---

## 📊 Output Files

Each run generates the following inside `output/reports/`:

| File | Description |
|------|-------------|
| `top_words_bar.png` | Horizontal bar chart of top 20 words |
| `wordcloud.png` | Word cloud sized by frequency |
| `per_image_stats.png` | Per-image word count + OCR confidence |
| `word_frequencies.csv` | Full word frequency table with percentages |
| `image_results.csv` | Per-image file, word count, confidence, text preview |

---

## 🔧 Configuration

Edit `config.py` to customize the run:

```python
# Change the search topic
PINTEREST_URL = "https://www.pinterest.com/search/pins/?q="

# Number of images to process
MAX_IMAGES = 40

# OCR language: "eng", "spa", or "spa+eng" for both
OCR_LANG = "eng"
```

---

## ⚠️ Known Limitations

- Pinterest may throttle or block requests — if it fails, wait a few minutes and try again.
- OCR accuracy depends heavily on image quality. Blurry or stylized fonts will produce lower confidence scores.
- The scraper targets infographic-style images (`236x` / `736x` Pinterest URLs). Profile pictures and icons are filtered out automatically.
- Tesseract must be installed as a system binary, not just via `pip`. The path in `ocr/extractor.py` defaults to `C:\Program Files\Tesseract-OCR\tesseract.exe` — update it if your installation path differs.

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| Selenium | Browser automation and dynamic page rendering |
| BeautifulSoup | HTML parsing |
| Tesseract + pytesseract | OCR engine |
| Pillow | Image preprocessing |
| matplotlib | Chart generation |
| wordcloud | Word cloud generation |
| pandas | CSV export |
| webdriver-manager | Automatic ChromeDriver management |
