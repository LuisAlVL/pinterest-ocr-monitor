
from analysis.trends import clean_text, aggregate_tokens

fake_results = [
    {'file': 'pin_001.jpg', 'text': 'Health tips for better living every day', 'words': 7, 'avg_conf': 88},
    {'file': 'pin_002.jpg', 'text': 'Best healthy food recipes tips', 'words': 5, 'avg_conf': 91},
]

counts, imgs, total = aggregate_tokens(fake_results)
print(counts.most_common(5))
