import os

# Target URL (Pinterest board or search)
PINTEREST_URL = "https://www.pinterest.com/search/pins/?q="

# How many images to process per run
MAX_IMAGES = 40

# Wait time for page to load (seconds)
PAGE_LOAD_WAIT = 4

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(BASE_DIR, "output", "images")
REPORTS_DIR = os.path.join(BASE_DIR, "output", "reports")

# OCR language (spa = Spanish, eng = English, spa+eng = both)
OCR_LANG = "eng"

# Stopwords to ignore in analysis
STOPWORDS = {
    "the", "and", "for", "with", "you", "are", "this",
    "that", "have", "from", "your", "will", "can", "not",
    "de", "la", "el", "en", "es", "un", "que", "se", "por", 
    "uno", "una", "eso", "esa", "los", "las", "esta", "esto"
}